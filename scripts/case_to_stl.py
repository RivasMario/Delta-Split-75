"""
DeltaSplit 75 — case DXF -> STL (standalone, no FreeCAD).

Uses ezdxf + shapely + numpy-stl.
Run: python scripts/case_to_stl.py
Output: output/3d/*.stl
"""

import os, math
import numpy as np
import ezdxf
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.ops import unary_union, polygonize
from stl.mesh import Mesh

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(BASE, "output", "3d")
os.makedirs(OUT, exist_ok=True)

EPS = 0.05   # mm snap tolerance

# (rel_path, thickness_mm, is_middle, mode)
# mode "direct"   -> extrude each closed polygon as-is (bezels, bottom, middle)
# mode "subtract" -> largest polygon OR bbox minus all cutouts (plates)
LAYERS = {
    "bezel_standard":     (r"case/bezel/top bezel - Standard.dxf",          3.0,  False, "direct"),
    "bezel_winkeyless":   (r"case/bezel/top bezel - Winkeyless.dxf",         3.0,  False, "direct"),
    "bezel_blocked":      (r"case/bezel/top bezel - blocked corner.dxf",     3.0,  False, "direct"),
    "plate_left_mx":      (r"case/left/plate/MX LEFT B.dxf",                 1.5,  False, "subtract"),
    "plate_left_alps":    (r"case/left/plate/ALPS LEFT B.dxf",               1.5,  False, "subtract"),
    "plate_left_alpsmx":  (r"case/left/plate/ALPS+MX LEFT B.dxf",            1.5,  False, "subtract"),
    "plate_left_costars": (r"case/left/plate/MX LEFT B COSTARS.dxf",         1.5,  False, "subtract"),
    "plate_right_mx":     (r"case/right/plate/MX RIGHT B.dxf",               1.5,  False, "subtract"),
    "plate_right_alps":   (r"case/right/plate/ALPS RIGHT B.dxf",             1.5,  False, "subtract"),
    "plate_right_alpsmx": (r"case/right/plate/ALPS+MX RIGHT B.dxf",          1.5,  False, "subtract"),
    "bottom_left":        (r"case/left/bottom/Bottom Layer - LEFT B.dxf",    3.0,  False, "direct"),
    "bottom_right":       (r"case/right/bottom/bottom layers - RIGHT B.dxf", 3.0,  False, "direct"),
    "middle_left":        (r"case/left/middle/Middle layers - LEFT B.dxf",   3.0,  True,  "direct"),
    "middle_right":       (r"case/right/middle/middle layers - RIGHT B.dxf", 3.0,  True,  "direct"),
}

# ── DXF -> shapely polygons ────────────────────────────────────────────────────

def _circle_pts(cx, cy, r, n=64):
    angles = np.linspace(0, 2*math.pi, n, endpoint=False)
    return [(cx + r*math.cos(a), cy + r*math.sin(a)) for a in angles]


def _dxf_to_lines(msp, y_lo=None, y_hi=None):
    """Return list of (x0,y0,x1,y1) segments and list of circle Polygons."""
    segs, circles = [], []
    for e in msp:
        t = e.dxftype()
        if t == "LINE":
            s, p = e.dxf.start, e.dxf.end
            my = (s.y + p.y) / 2
            if y_lo is not None and not (y_lo <= my <= y_hi):
                continue
            if math.hypot(p.x-s.x, p.y-s.y) < EPS:
                continue
            segs.append((s.x, s.y, p.x, p.y))
        elif t == "CIRCLE":
            cx, cy, r = e.dxf.center.x, e.dxf.center.y, e.dxf.radius
            if y_lo is not None and not (y_lo <= cy <= y_hi):
                continue
            circles.append(Polygon(_circle_pts(cx, cy, r)))
        elif t == "ARC":
            cx, cy, r = e.dxf.center.x, e.dxf.center.y, e.dxf.radius
            sa, ea = math.radians(e.dxf.start_angle), math.radians(e.dxf.end_angle)
            if ea < sa:
                ea += 2*math.pi
            n = max(8, int((ea-sa)/(math.pi/16)))
            angles = np.linspace(sa, ea, n)
            pts = [(cx+r*math.cos(a), cy+r*math.sin(a)) for a in angles]
            if len(pts) >= 2:
                segs.append((pts[0][0], pts[0][1], pts[-1][0], pts[-1][1]))
    return segs, circles


def _bridge_dangling(segs, max_gap=5.0):
    """Add bridge segments to close gaps between dangling endpoints (< max_gap mm)."""
    from collections import defaultdict
    SNAP = 0.02
    bucket = defaultdict(list)
    for x0,y0,x1,y1 in segs:
        for px,py in ((x0,y0),(x1,y1)):
            bucket[(round(px/SNAP), round(py/SNAP))].append((px,py))
    dangling = []
    for v in bucket.values():
        if len(v) == 1:
            dangling.append(v[0])
    bridges = []
    used = set()
    for i,(ax,ay) in enumerate(dangling):
        if i in used: continue
        best, bj = None, -1
        for j,(bx,by) in enumerate(dangling):
            if j <= i or j in used: continue
            d = math.hypot(bx-ax, by-ay)
            if 0 < d <= max_gap and (best is None or d < best[0]):
                best, bj = (d, bx, by), j
        if best:
            bridges.append((ax, ay, best[1], best[2]))
            used.add(i); used.add(bj)
    if bridges:
        print(f"    (bridged {len(bridges)} gap(s), max {max(math.hypot(b[2]-b[0],b[3]-b[1]) for b in bridges):.3f} mm)")
    return segs + bridges


def _bbox_poly(segs):
    """Bounding box polygon enclosing all segment endpoints."""
    xs = [c for x0,y0,x1,y1 in segs for c in (x0,x1)]
    ys = [c for x0,y0,x1,y1 in segs for c in (y0,y1)]
    return Polygon([(min(xs),min(ys)),(max(xs),min(ys)),(max(xs),max(ys)),(min(xs),max(ys))])


def _all_polys_from_segs(segs, circles):
    segs = _bridge_dangling(segs)
    lines = [LineString([(x0,y0),(x1,y1)]) for x0,y0,x1,y1 in segs]
    polys = list(polygonize(unary_union(lines)))
    return segs, polys + circles


# ── STL extrusion ─────────────────────────────────────────────────────────────

def _triangulate_polygon(poly):
    """Return list of triangles [(p0,p1,p2), ...] for a shapely Polygon."""
    from shapely.ops import triangulate as delaunay_triangulate
    tris = delaunay_triangulate(poly, tolerance=0.01)
    result = []
    for tri in tris:
        if poly.contains(tri.centroid):
            coords = list(tri.exterior.coords)[:-1]
            result.append(coords)
    return result


def _extrude_to_stl(poly, thickness, z_base=0.0):
    """Return numpy-stl Mesh from a shapely Polygon extruded by thickness."""
    if poly is None or poly.is_empty:
        return None

    faces = []
    # bottom + top caps
    for tri in _triangulate_polygon(poly):
        zb = z_base
        zt = z_base + thickness
        p0b, p1b, p2b = [(x, y, zb) for x, y in tri]
        p0t, p1t, p2t = [(x, y, zt) for x, y in tri]
        faces.append([p0b, p2b, p1b])  # bottom (reversed = outward normal down)
        faces.append([p0t, p1t, p2t])  # top

    # side walls from polygon exterior + interior rings
    rings = [poly.exterior] + list(poly.interiors) if hasattr(poly, 'exterior') else []
    for ring in rings:
        coords = list(ring.coords)
        for i in range(len(coords)-1):
            x0, y0 = coords[i]
            x1, y1 = coords[i+1]
            zb, zt = z_base, z_base + thickness
            a = (x0, y0, zb); b = (x1, y1, zb)
            c = (x1, y1, zt); d = (x0, y0, zt)
            faces.append([a, b, c])
            faces.append([a, c, d])

    if not faces:
        return None
    fa = np.array(faces, dtype=np.float32)
    mesh = Mesh(np.zeros(len(fa), dtype=Mesh.dtype))
    for i, f in enumerate(fa):
        mesh.vectors[i] = f
    return mesh


def _polys_to_mesh(polys, thickness, z_base=0.0):
    """Extrude a list of polygons to thickness and combine into one Mesh."""
    meshes = []
    for poly in polys:
        m = _extrude_to_stl(poly, thickness, z_base=z_base)
        if m:
            meshes.append(m)
    if not meshes:
        return None
    return Mesh(np.concatenate([m.data for m in meshes]))


# ── plate mode (subtract) ─────────────────────────────────────────────────────

def process_subtract(dxf_path, thickness):
    """Plate: extrude material polygons (those with interior holes = switch cutouts).
    Fallback: bbox minus all cutout polys when outer boundary is broken.
    """
    doc_dxf = ezdxf.readfile(dxf_path)
    msp = doc_dxf.modelspace()
    raw_segs, circles = _dxf_to_lines(msp)
    bridged_segs, all_polys = _all_polys_from_segs(raw_segs, circles)

    # Polygons with interior holes already encode the plate material (outer - cutouts).
    # They appear when polygonize finds the plate boundary as a closed polygon.
    material = [p for p in all_polys if len(list(p.interiors)) > 0]

    if material:
        total = sum(p.area for p in material)
        total_holes = sum(len(list(p.interiors)) for p in material)
        print(f"    {len(material)} material section(s), {total_holes} holes, area={total:.0f} mm2")
        return _polys_to_mesh(material, thickness)

    # Fallback: outer boundary broken — use bbox minus all found polys (all are cutouts)
    bbox = _bbox_poly(bridged_segs)
    if not all_polys:
        print(f"    no polys found, extruding bbox (area={bbox.area:.0f} mm2)")
        plate = bbox
    else:
        cutouts = unary_union(all_polys)
        plate = bbox.difference(cutouts)
        print(f"    boundary broken, bbox({bbox.area:.0f}) - {len(all_polys)} cutouts = {plate.area:.0f} mm2 ({plate.geom_type})")

    if plate.is_empty:
        return None
    if plate.geom_type == "MultiPolygon":
        geoms = list(plate.geoms)
    elif plate.geom_type == "Polygon":
        geoms = [plate]
    else:
        geoms = [g for g in plate.geoms if g.geom_type == "Polygon"]
    return _polys_to_mesh(geoms, thickness)


# ── middle stack ──────────────────────────────────────────────────────────────

def process_middle(dxf_path, layer_thickness):
    """Split 5-layer stacked DXF by Y band; extrude each layer's polys at z = i*thickness."""
    doc_dxf = ezdxf.readfile(dxf_path)
    msp = doc_dxf.modelspace()
    ys = sorted((e.dxf.start.y+e.dxf.end.y)/2 for e in msp if e.dxftype()=="LINE")
    y_min, y_max = min(ys), max(ys)
    band = (y_max - y_min) / 5
    bounds = [y_min + i*band for i in range(6)]

    all_meshes = []
    for i in range(5):
        segs, circles = _dxf_to_lines(msp, bounds[i]-EPS, bounds[i+1]+EPS)
        _, polys = _all_polys_from_segs(segs, circles)
        if not polys:
            print(f"  WARN: layer {i} no polygons")
            continue
        z_off = i * layer_thickness
        m = _polys_to_mesh(polys, layer_thickness, z_base=z_off)
        if m:
            all_meshes.append(m)
        total_area = sum(p.area for p in polys)
        print(f"  layer {i}: {len(polys)} polys total area={total_area:.0f} mm2, z={z_off:.1f}-{z_off+layer_thickness:.1f} mm")

    if not all_meshes:
        return None
    return Mesh(np.concatenate([m.data for m in all_meshes]))


# ── single layer (direct) ─────────────────────────────────────────────────────

def process_single(dxf_path, thickness):
    doc_dxf = ezdxf.readfile(dxf_path)
    msp = doc_dxf.modelspace()
    segs, circles = _dxf_to_lines(msp)
    _, polys = _all_polys_from_segs(segs, circles)
    if not polys:
        return None
    n = len(polys)
    total = sum(p.area for p in polys)
    print(f"    {n} polys, total area={total:.0f} mm2")
    return _polys_to_mesh(polys, thickness)


# ── main ──────────────────────────────────────────────────────────────────────

def run():
    print("=== DeltaSplit 75 -> STL ===\n")
    for name, (rel_path, thickness, is_middle, mode) in LAYERS.items():
        dxf_path = os.path.join(BASE, rel_path)
        if not os.path.exists(dxf_path):
            print(f"SKIP (not found): {name}")
            continue
        if is_middle:
            label = "[MIDDLE 5-layer 15mm]"
        else:
            label = f"[{thickness} mm {mode}]"
        print(f"{name}  {label}")
        try:
            if is_middle:
                mesh = process_middle(dxf_path, thickness)
            elif mode == "subtract":
                mesh = process_subtract(dxf_path, thickness)
            else:
                mesh = process_single(dxf_path, thickness)

            if mesh is None:
                print(f"  ERROR: no mesh produced\n")
                continue
            out_path = os.path.join(OUT, f"{name}.stl")
            mesh.save(out_path)
            print(f"  -> {out_path}\n")
        except Exception as ex:
            import traceback
            print(f"  ERROR: {ex}")
            traceback.print_exc()
            print()
    print("Done.")


if __name__ == "__main__":
    run()
