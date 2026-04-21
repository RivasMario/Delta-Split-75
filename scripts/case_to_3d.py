"""
DeltaSplit 75 — case DXF → STEP/STL extrusion macro.

Run from FreeCAD's Macro editor:
    Tools > Macros > Create/Open > paste this file > Run

Produces one STEP + one STL per layer under output/3d/.
Middle layers (5 stacked in one DXF) are fused into a single 15 mm solid.

Requirements: FreeCAD >= 0.21 with ezdxf available in its Python.
  If ezdxf is missing, install it via FreeCAD's pip:
    Tools > Python console:
      import subprocess, sys; subprocess.run([sys.executable, "-m", "pip", "install", "ezdxf"])
"""

import FreeCAD as App
import Part
import math
import os
import ezdxf

# ── paths ────────────────────────────────────────────────────────────────────
BASE = r"C:\Users\v-mariorivas\OneDrive - Microsoft\Documents\GitHub\Delta Split 75"
OUT  = os.path.join(BASE, "output", "3d")
os.makedirs(OUT, exist_ok=True)

# (relative dxf path, layer_thickness_mm, is_middle_stack)
LAYERS = {
    "bezel_standard":     (r"case\bezel\top bezel - Standard.dxf",          3.0,  False),
    "bezel_winkeyless":   (r"case\bezel\top bezel - Winkeyless.dxf",         3.0,  False),
    "bezel_blocked":      (r"case\bezel\top bezel - blocked corner.dxf",     3.0,  False),
    "plate_left_mx":      (r"case\left\plate\MX LEFT B.dxf",                 1.5,  False),
    "plate_left_alps":    (r"case\left\plate\ALPS LEFT B.dxf",               1.5,  False),
    "plate_left_alpsmx":  (r"case\left\plate\ALPS+MX LEFT B.dxf",            1.5,  False),
    "plate_left_costars": (r"case\left\plate\MX LEFT B COSTARS.dxf",         1.5,  False),
    "plate_right_mx":     (r"case\right\plate\MX RIGHT B.dxf",               1.5,  False),
    "plate_right_alps":   (r"case\right\plate\ALPS RIGHT B.dxf",             1.5,  False),
    "plate_right_alpsmx": (r"case\right\plate\ALPS+MX RIGHT B.dxf",          1.5,  False),
    "bottom_left":        (r"case\left\bottom\Bottom Layer - LEFT B.dxf",    3.0,  False),
    "bottom_right":       (r"case\right\bottom\bottom layers - RIGHT B.dxf", 3.0,  False),
    # 5 layers stacked vertically in each file → fused into one 15 mm solid
    "middle_left":        (r"case\left\middle\Middle layers - LEFT B.dxf",   3.0,  True),
    "middle_right":       (r"case\right\middle\middle layers - RIGHT B.dxf", 3.0,  True),
}

EPS = 0.01  # mm — endpoint match tolerance

# ── geometry helpers ──────────────────────────────────────────────────────────

def _pt(x, y):
    return App.Vector(x, y, 0)


def _edges_from_dxf(msp, y_lo=None, y_hi=None):
    """Return Part.Edge list from LINE + CIRCLE entities in msp, filtered by Y band."""
    edges = []
    for e in msp:
        t = e.dxftype()
        if t == "LINE":
            s, p = e.dxf.start, e.dxf.end
            mid_y = (s.y + p.y) / 2
            if y_lo is not None and not (y_lo <= mid_y <= y_hi):
                continue
            if math.hypot(p.x - s.x, p.y - s.y) < EPS:
                continue
            edges.append(Part.makeLine(_pt(s.x, s.y), _pt(p.x, p.y)))
        elif t == "CIRCLE":
            cx, cy, r = e.dxf.center.x, e.dxf.center.y, e.dxf.radius
            mid_y = cy
            if y_lo is not None and not (y_lo <= mid_y <= y_hi):
                continue
            circle = Part.Circle(App.Vector(cx, cy, 0),
                                 App.Vector(0, 0, 1), r)
            edges.append(Part.Edge(circle))
        elif t == "ARC":
            cx, cy, r = e.dxf.center.x, e.dxf.center.y, e.dxf.radius
            sa = math.radians(e.dxf.start_angle)
            ea = math.radians(e.dxf.end_angle)
            mid_y = cy
            if y_lo is not None and not (y_lo <= mid_y <= y_hi):
                continue
            arc = Part.Arc(
                App.Vector(cx + r*math.cos(sa), cy + r*math.sin(sa), 0),
                App.Vector(cx + r*math.cos((sa+ea)/2), cy + r*math.sin((sa+ea)/2), 0),
                App.Vector(cx + r*math.cos(ea), cy + r*math.sin(ea), 0),
            )
            edges.append(Part.Edge(arc))
    return edges


def _closed_wires(edges):
    """Assemble edges into closed wires via greedy endpoint chaining.
    Open chains (orphaned segments, USB notch, stab cutouts) are discarded —
    they cannot form a solid face. A diagnostic count is printed at run time.
    """
    remaining = list(edges)
    closed_wires = []
    open_count   = 0

    while remaining:
        chain = [remaining.pop(0)]
        changed = True
        while changed:
            changed = False
            tail = chain[-1].Vertexes[-1].Point
            for i, e in enumerate(remaining):
                v0 = e.Vertexes[0].Point
                v1 = e.Vertexes[-1].Point
                if tail.distanceToPoint(v0) < EPS:
                    chain.append(remaining.pop(i)); changed = True; break
                if tail.distanceToPoint(v1) < EPS:
                    chain.append(e.reversed()); remaining.pop(i); changed = True; break

        try:
            w = Part.Wire(chain)
            if w.isClosed():
                closed_wires.append(w)
            else:
                open_count += 1
        except Exception:
            open_count += 1

    if open_count:
        print(f"    (skipped {open_count} open chains — orphan/notch features)")
    return closed_wires


def _bbox_area(wire):
    bb = wire.BoundBox
    return bb.XLength * bb.YLength


def _make_face(wires):
    """Largest bbox wire = outer; rest = holes."""
    if not wires:
        return None
    wires_sorted = sorted(wires, key=_bbox_area, reverse=True)
    outer = wires_sorted[0]
    holes = wires_sorted[1:]
    try:
        return Part.Face(outer, holes) if holes else Part.Face(outer)
    except Exception:
        try:
            return Part.Face(outer)
        except Exception:
            return None


def extrude_dxf(dxf_path, thickness, y_lo=None, y_hi=None, z_offset=0.0):
    """Return a Part.Solid extruded from the DXF profile, placed at z_offset."""
    doc_dxf = ezdxf.readfile(dxf_path)
    msp = doc_dxf.modelspace()
    edges = _edges_from_dxf(msp, y_lo, y_hi)
    wires = _closed_wires(edges)
    face  = _make_face(wires)
    if face is None:
        print(f"  WARN: no face built for {os.path.basename(dxf_path)} y={y_lo}")
        return None
    solid = face.extrude(App.Vector(0, 0, thickness))
    if z_offset:
        solid.translate(App.Vector(0, 0, z_offset))
    return solid


def extrude_middle_stack(dxf_path, layer_thickness=3.0):
    """Split 5-layer stacked DXF → extrude each → fuse → single 15 mm solid."""
    doc_dxf = ezdxf.readfile(dxf_path)
    msp = doc_dxf.modelspace()

    # determine Y boundaries from line midpoints
    ys = sorted((e.dxf.start.y+e.dxf.end.y)/2
                for e in msp if e.dxftype() == "LINE")
    y_min, y_max = min(ys), max(ys)
    band = (y_max - y_min) / 5
    boundaries = [y_min + i*band for i in range(6)]

    solids = []
    for i in range(5):
        z_off = i * layer_thickness
        s = extrude_dxf(dxf_path, layer_thickness,
                        y_lo=boundaries[i] - EPS,
                        y_hi=boundaries[i+1] + EPS,
                        z_offset=z_off)
        if s:
            solids.append(s)
        else:
            print(f"  WARN: layer {i} of {os.path.basename(dxf_path)} failed")

    if not solids:
        return None
    if len(solids) == 1:
        return solids[0]

    fused = solids[0]
    for s in solids[1:]:
        fused = fused.fuse(s)
    return fused


# ── main ──────────────────────────────────────────────────────────────────────

def run():
    print("=== DeltaSplit 75 case_to_3d ===")
    for name, (rel_path, thickness, is_middle) in LAYERS.items():
        dxf_path = os.path.join(BASE, rel_path)
        if not os.path.exists(dxf_path):
            print(f"SKIP (missing): {name}")
            continue

        print(f"Processing: {name}  ({thickness} mm{'  [middle stack → fuse]' if is_middle else ''})")

        solid = (extrude_middle_stack(dxf_path, thickness)
                 if is_middle else
                 extrude_dxf(dxf_path, thickness))

        if solid is None:
            print(f"  ERROR: solid is None for {name}")
            continue

        step_out = os.path.join(OUT, f"{name}.step")
        stl_out  = os.path.join(OUT, f"{name}.stl")

        solid.exportStep(step_out)
        solid.exportStl(stl_out)
        print(f"  -> {step_out}")
        print(f"  -> {stl_out}")

    print("Done.")


run()
