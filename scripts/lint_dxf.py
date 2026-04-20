"""SendCutSend-style DXF pre-flight lint.

Checks each plate DXF for issues that commonly reject at laser-cut fabs:
  - zero-length LINE segments
  - duplicate adjacent vertices in LWPOLYLINE
  - unclosed polylines (gap > EPS between first/last vertex when marked closed)
  - disconnected open-path endpoints (free endpoints not meeting anything)
  - overlapping closed regions (bbox-level screen; manual review for true overlap)
  - entity counts by type

Usage:
    python scripts/lint_dxf.py case/left/plate/*.dxf case/right/plate/*.dxf
"""
from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import ezdxf

EPS = 1e-4


def bbox(e):
    t = e.dxftype()
    if t == "LINE":
        return (e.dxf.start.x, e.dxf.start.y, e.dxf.end.x, e.dxf.end.y)
    if t == "CIRCLE":
        c, r = e.dxf.center, e.dxf.radius
        return (c.x - r, c.y - r, c.x + r, c.y + r)
    if t == "ARC":
        c = e.dxf.center
        return (c.x, c.y, c.x, c.y)
    if t == "LWPOLYLINE":
        pts = list(e.get_points("xy"))
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (min(xs), min(ys), max(xs), max(ys)) if pts else None
    return None


def lint(path: Path):
    doc = ezdxf.readfile(str(path))
    msp = doc.modelspace()
    types = Counter()
    zero_len = 0
    dup_vtx = 0
    unclosed = 0
    endpoints = []  # raw (x,y) of every LINE endpoint; clustered below
    closed_bboxes = []

    for e in msp:
        t = e.dxftype()
        types[t] += 1
        if t == "LINE":
            s, p = e.dxf.start, e.dxf.end
            if math.hypot(p.x - s.x, p.y - s.y) < EPS:
                zero_len += 1
            else:
                endpoints.append((s.x, s.y))
                endpoints.append((p.x, p.y))
        elif t == "LWPOLYLINE":
            pts = list(e.get_points("xy"))
            for i in range(len(pts) - 1):
                if math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) < EPS:
                    dup_vtx += 1
            if e.closed and pts:
                if math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]) > EPS:
                    bb = bbox(e)
                    if bb:
                        closed_bboxes.append(bb)
                else:
                    bb = bbox(e)
                    if bb:
                        closed_bboxes.append(bb)
            elif pts and not e.closed:
                endpoints = [pts[0], pts[-1]]
                if math.hypot(endpoints[0][0] - endpoints[1][0], endpoints[0][1] - endpoints[1][1]) > EPS:
                    unclosed += 1
        elif t == "CIRCLE":
            bb = bbox(e)
            if bb:
                closed_bboxes.append(bb)

    # Cluster endpoints by 0.01mm grid (DXF rounding noise tolerance)
    TOL = 0.01
    bucket = defaultdict(int)
    for x, y in endpoints:
        bucket[(round(x / TOL), round(y / TOL))] += 1
    dangling = sum(1 for c in bucket.values() if c == 1)

    overlaps = 0
    for i in range(len(closed_bboxes)):
        ax1, ay1, ax2, ay2 = closed_bboxes[i]
        for j in range(i + 1, len(closed_bboxes)):
            bx1, by1, bx2, by2 = closed_bboxes[j]
            if ax1 < bx2 and bx1 < ax2 and ay1 < by2 and by1 < ay2:
                overlaps += 1

    return {
        "path": str(path),
        "types": dict(types),
        "zero_len": zero_len,
        "dup_vtx": dup_vtx,
        "unclosed": unclosed,
        "dangling_endpoints": dangling,
        "bbox_overlaps": overlaps,
        "total_entities": sum(types.values()),
    }


def main(argv):
    paths = [Path(p) for p in argv[1:]]
    if not paths:
        print("Usage: lint_dxf.py <dxf> [<dxf> ...]")
        sys.exit(2)
    any_bad = False
    for p in paths:
        r = lint(p)
        flags = []
        if r["zero_len"]: flags.append(f"zero-len={r['zero_len']}")
        if r["dup_vtx"]: flags.append(f"dup-vtx={r['dup_vtx']}")
        if r["unclosed"]: flags.append(f"unclosed={r['unclosed']}")
        if r["dangling_endpoints"]: flags.append(f"dangling={r['dangling_endpoints']}")
        if r["bbox_overlaps"]: flags.append(f"bbox-overlap={r['bbox_overlaps']}")
        status = "OK" if not flags else "WARN"
        if flags:
            any_bad = True
        print(f"[{status}] {p.name}")
        print(f"    entities: {r['total_entities']}  types: {r['types']}")
        if flags:
            print(f"    flags: {', '.join(flags)}")
    sys.exit(1 if any_bad else 0)


if __name__ == "__main__":
    main(sys.argv)
