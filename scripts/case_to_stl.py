"""
DeltaSplit 75 — case DXF -> STL (standalone, no FreeCAD).

Uses ezdxf + shapely + numpy-stl.
Run: python scripts/case_to_stl.py
Output: output/3d/*.stl
"""

import os, math
import numpy as np
import ezdxf
import mapbox_earcut as earcut
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
            for k in range(len(pts)-1):
                segs.append((pts[k][0], pts[k][1], pts[k+1][0], pts[k+1][1]))
        elif t == "LWPOLYLINE":
            pts = [(x, y) for x, y, *_ in e.get_points("xy")]
            closed = bool(e.closed)
            if not pts:
                continue
            mx = sum(x for x, _ in pts) / len(pts)
            my = sum(y for _, y in pts) / len(pts)
            if y_lo is not None and not (y_lo <= my <= y_hi):
                continue
            for k in range(len(pts)-1):
                x0, y0 = pts[k]
                x1, y1 = pts[k+1]
                if math.hypot(x1-x0, y1-y0) >= EPS:
                    segs.append((x0, y0, x1, y1))
            if closed and len(pts) >= 3:
                x0, y0 = pts[-1]
                x1, y1 = pts[0]
                if math.hypot(x1-x0, y1-y0) >= EPS:
                    segs.append((x0, y0, x1, y1))
        elif t == "POLYLINE":
            vtx = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
            if not vtx:
                continue
            mx = sum(x for x, _ in vtx) / len(vtx)
            my = sum(y for _, y in vtx) / len(vtx)
            if y_lo is not None and not (y_lo <= my <= y_hi):
                continue
            for k in range(len(vtx)-1):
                x0, y0 = vtx[k]
                x1, y1 = vtx[k+1]
                if math.hypot(x1-x0, y1-y0) >= EPS:
                    segs.append((x0, y0, x1, y1))
            if e.is_closed and len(vtx) >= 3:
                x0, y0 = vtx[-1]
                x1, y1 = vtx[0]
                if math.hypot(x1-x0, y1-y0) >= EPS:
                    segs.append((x0, y0, x1, y1))
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


def _snap_segs(segs, grid=1e-3):
    """Round segment endpoints to a grid so float noise doesn't break polygonize."""
    out = []
    for x0, y0, x1, y1 in segs:
        x0 = round(x0 / grid) * grid
        y0 = round(y0 / grid) * grid
        x1 = round(x1 / grid) * grid
        y1 = round(y1 / grid) * grid
        if math.hypot(x1-x0, y1-y0) >= EPS:
            out.append((x0, y0, x1, y1))
    return out


def _all_polys_from_segs(segs, circles):
    segs = _snap_segs(segs)
    segs = _bridge_dangling(segs)
    lines = [LineString([(x0,y0),(x1,y1)]) for x0,y0,x1,y1 in segs]
    polys = list(polygonize(unary_union(lines)))
    return segs, polys + circles


def _nest_polys(polys):
    """Group polys into shells with holes by geometric containment.

    Walks largest->smallest to assign each polygon an immediate parent (smallest
    enclosing larger poly). Even-depth polys become shells; odd-depth become
    holes of their parent shell. Depth-2 (island inside a hole) starts a new shell.

    Uses shell-only polygons (strips any pre-existing interior rings) for the
    containment check, so holes already baked in by polygonize don't block
    nesting of the standalone duplicate polys that polygonize also emits.
    """
    shell_only = []
    for p in polys:
        if hasattr(p, 'exterior') and len(list(p.exterior.coords)) >= 4:
            shell_only.append(Polygon(list(p.exterior.coords)))
        else:
            shell_only.append(p)

    order = sorted(range(len(polys)), key=lambda i: -shell_only[i].area)
    parent = {}
    for pos, i in enumerate(order):
        best_parent = None
        best_area = float('inf')
        for j in order[:pos]:
            if shell_only[j].area <= shell_only[i].area:
                continue
            if shell_only[j].contains(shell_only[i]):
                if shell_only[j].area < best_area:
                    best_parent = j
                    best_area = shell_only[j].area
        parent[i] = best_parent

    depth = {}
    def get_depth(i):
        if i in depth:
            return depth[i]
        depth[i] = 0 if parent[i] is None else get_depth(parent[i]) + 1
        return depth[i]
    for i in order:
        get_depth(i)

    shells = []
    for i in order:
        if depth[i] % 2 != 0:
            continue
        ext = list(shell_only[i].exterior.coords)
        holes = [list(shell_only[j].exterior.coords)
                 for j in order if parent.get(j) == i and depth[j] % 2 == 1]
        shells.append(Polygon(ext, holes=holes) if holes else Polygon(ext))
    return shells


# ── STL extrusion ─────────────────────────────────────────────────────────────

def _triangulate_polygon(poly):
    """Return list of triangles [(p0,p1,p2), ...] for a shapely Polygon with holes.
    Uses mapbox-earcut constrained triangulation (respects interior rings as holes).
    """
    if poly.is_empty or not hasattr(poly, 'exterior'):
        return []
    ext = list(poly.exterior.coords)[:-1]  # drop duplicate closing vertex
    rings = [ext]
    for interior in poly.interiors:
        rings.append(list(interior.coords)[:-1])

    flat = np.array([pt for ring in rings for pt in ring], dtype=np.float64)
    # mapbox_earcut ring_end_indices: END index of exterior + END of each hole
    ring_ends = []
    cursor = 0
    for ring in rings:
        cursor += len(ring)
        ring_ends.append(cursor)
    ring_arr = np.array(ring_ends, dtype=np.uint32)
    result_idx = earcut.triangulate_float64(flat, ring_arr)

    tris = []
    for i in range(0, len(result_idx), 3):
        a, b, c = result_idx[i], result_idx[i+1], result_idx[i+2]
        tris.append([tuple(flat[a]), tuple(flat[b]), tuple(flat[c])])
    return tris


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

def _inject_circle_holes(material_polys, circles):
    """Add each circle as an interior ring of whichever material poly contains it.
    Circles are fed as separate shapely Polygons (from CIRCLE entities) and never
    reach polygonize, so we stitch them in here.
    """
    result = []
    for m in material_polys:
        if not hasattr(m, 'exterior'):
            result.append(m)
            continue
        ext = list(m.exterior.coords)
        holes = [list(r.coords) for r in m.interiors]
        shell_only = Polygon(ext)
        for c in circles:
            if not shell_only.contains(c.centroid):
                continue
            # Skip if circle already falls inside an existing interior ring
            already = False
            for h_coords in holes:
                if Polygon(h_coords).contains(c.centroid):
                    already = True
                    break
            if not already:
                holes.append(list(c.exterior.coords))
        result.append(Polygon(ext, holes=holes) if holes else m)
    return result


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
        material = _inject_circle_holes(material, circles)
        total = sum(p.area for p in material)
        total_holes = sum(len(list(p.interiors)) for p in material)
        print(f"    {len(material)} material section(s), {total_holes} holes, area={total:.0f} mm2")
        return _polys_to_mesh(material, thickness)

    # Fallback: outer boundary broken — cluster cutouts by x-gap, per-half bbox minus per-half cutouts.
    if not all_polys:
        bbox = _bbox_poly(bridged_segs)
        print(f"    no polys found, extruding bbox (area={bbox.area:.0f} mm2)")
        plate = bbox
    else:
        # Cluster cutouts into two halves by biggest x-gap between centroids.
        cents = sorted(((p.centroid.x, p) for p in all_polys), key=lambda t: t[0])
        gaps = [(cents[i+1][0] - cents[i][0], i) for i in range(len(cents)-1)]
        gaps.sort(reverse=True)
        if gaps and gaps[0][0] > 20.0:  # >20mm gap = separate halves
            split_idx = gaps[0][1]
            left = [p for _, p in cents[:split_idx+1]]
            right = [p for _, p in cents[split_idx+1:]]
            halves = []
            for group in (left, right):
                gb = _bbox_poly([(p.bounds[0], p.bounds[1], p.bounds[2], p.bounds[3]) for p in group])
                cut = unary_union(group)
                halves.append(gb.difference(cut))
            from shapely.geometry import MultiPolygon as MP
            plate = unary_union(halves)
            print(f"    boundary broken, clustered into 2 halves: {len(left)}/{len(right)} cutouts, area={plate.area:.0f} mm2")
        else:
            bbox = _bbox_poly(bridged_segs)
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

def process_middle(dxf_path, thickness):
    """Sheet holds 5 identical copies stacked in Y. Extract one band, extrude as a single layer.
    User prints the resulting STL multiple times to build the middle stack.
    """
    doc_dxf = ezdxf.readfile(dxf_path)
    msp = doc_dxf.modelspace()
    ys = sorted((e.dxf.start.y+e.dxf.end.y)/2 for e in msp if e.dxftype()=="LINE")
    y_min, y_max = min(ys), max(ys)
    band = (y_max - y_min) / 5

    # Try each band, pick the one with the most polygons (most complete copy).
    best = None
    for i in range(5):
        y_lo = y_min + i*band - EPS
        y_hi = y_min + (i+1)*band + EPS
        segs, circles = _dxf_to_lines(msp, y_lo, y_hi)
        _, polys = _all_polys_from_segs(segs, circles)
        if not polys:
            continue
        area = sum(p.area for p in polys)
        if best is None or len(polys) > best[1] or (len(polys) == best[1] and area > best[2]):
            best = (i, len(polys), area, polys)

    if best is None:
        print("    WARN: no polygons found in any band")
        return None

    i, npolys, area, polys = best
    shells = _nest_polys(polys)
    total_holes = sum(len(list(s.interiors)) for s in shells)
    print(f"    1 of 5 copies (band {i}): {len(shells)} shells, {total_holes} through-holes, area={sum(s.area for s in shells):.0f} mm2")
    return _polys_to_mesh(shells, thickness)


# ── single layer (direct) ─────────────────────────────────────────────────────

def process_single(dxf_path, thickness):
    doc_dxf = ezdxf.readfile(dxf_path)
    msp = doc_dxf.modelspace()
    segs, circles = _dxf_to_lines(msp)
    _, polys = _all_polys_from_segs(segs, circles)
    if not polys:
        return None
    shells = _nest_polys(polys)
    total = sum(s.area for s in shells)
    total_holes = sum(len(list(s.interiors)) for s in shells)
    print(f"    {len(shells)} shells, {total_holes} through-holes, area={total:.0f} mm2")
    return _polys_to_mesh(shells, thickness)


# ── main ──────────────────────────────────────────────────────────────────────

def run():
    print("=== DeltaSplit 75 -> STL ===\n")
    for name, (rel_path, thickness, is_middle, mode) in LAYERS.items():
        dxf_path = os.path.join(BASE, rel_path)
        if not os.path.exists(dxf_path):
            print(f"SKIP (not found): {name}")
            continue
        if is_middle:
            label = f"[middle {thickness} mm, 1 of 5 copies]"
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
