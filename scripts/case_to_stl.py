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

LAYERS = {
    "bezel_standard":     (r"case/bezel/top bezel - Standard.dxf",          3.0,  False),
    "bezel_winkeyless":   (r"case/bezel/top bezel - Winkeyless.dxf",         3.0,  False),
    "bezel_blocked":      (r"case/bezel/top bezel - blocked corner.dxf",     3.0,  False),
    "plate_left_mx":      (r"case/left/plate/MX LEFT B.dxf",                 1.5,  False),
    "plate_left_alps":    (r"case/left/plate/ALPS LEFT B.dxf",               1.5,  False),
    "plate_left_alpsmx":  (r"case/left/plate/ALPS+MX LEFT B.dxf",            1.5,  False),
    "plate_left_costars": (r"case/left/plate/MX LEFT B COSTARS.dxf",         1.5,  False),
    "plate_right_mx":     (r"case/right/plate/MX RIGHT B.dxf",               1.5,  False),
    "plate_right_alps":   (r"case/right/plate/ALPS RIGHT B.dxf",             1.5,  False),
    "plate_right_alpsmx": (r"case/right/plate/ALPS+MX RIGHT B.dxf",          1.5,  False),
    "bottom_left":        (r"case/left/bottom/Bottom Layer - LEFT B.dxf",    3.0,  False),
    "bottom_right":       (r"case/right/bottom/bottom layers - RIGHT B.dxf", 3.0,  False),
    "middle_left":        (r"case/left/middle/Middle layers - LEFT B.dxf",   3.0,  True),
    "middle_right":       (r"case/right/middle/middle layers - RIGHT B.dxf", 3.0,  True),
}

# ── DXF → shapely polygons ────────────────────────────────────────────────────

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


def _segs_to_polys(segs, circles):
    """Convert line segments + circles -> list of closed polygons.
    Each closed shape is returned as-is — no subtraction, no merging.
    The DXF already encodes the correct geometry (ring, cutout, etc).
    """
    segs = _bridge_dangling(segs)
    lines = [LineString([(x0,y0),(x1,y1)]) for x0,y0,x1,y1 in segs]
    polys = list(polygonize(unary_union(lines)))
    return polys + circles


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

    # side walls from polygon exterior ring
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


# ── middle stack ──────────────────────────────────────────────────────────────

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
        polys = _segs_to_polys(segs, circles)
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


# ── single layer ──────────────────────────────────────────────────────────────

def process_single(dxf_path, thickness):
    doc_dxf = ezdxf.readfile(dxf_path)
    msp = doc_dxf.modelspace()
    segs, circles = _dxf_to_lines(msp)
    polys = _segs_to_polys(segs, circles)
    if not polys:
        return None
    n = len(polys)
    total = sum(p.area for p in polys)
    print(f"    {n} polys, total area={total:.0f} mm2")
    return _polys_to_mesh(polys, thickness)


# ── main ──────────────────────────────────────────────────────────────────────

def run():
    print("=== DeltaSplit 75 -> STL ===\n")
    for name, (rel_path, thickness, is_middle) in LAYERS.items():
        dxf_path = os.path.join(BASE, rel_path)
        if not os.path.exists(dxf_path):
            print(f"SKIP (not found): {name}")
            continue
        label = f"{'[MIDDLE 5-layer fused 15mm]' if is_middle else f'[{thickness} mm]'}"
        print(f"{name}  {label}")
        try:
            mesh = (process_middle(dxf_path, thickness) if is_middle
                    else process_single(dxf_path, thickness))
            if mesh is None:
                print(f"  ERROR: no mesh produced\n")
                continue
            out_path = os.path.join(OUT, f"{name}.stl")
            mesh.save(out_path)
            print(f"  -> {out_path}\n")
        except Exception as ex:
            print(f"  ERROR: {ex}\n")
    print("Done.")


if __name__ == "__main__":
    run()
