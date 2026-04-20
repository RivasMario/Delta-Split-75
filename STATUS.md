# Status / TODO

## Done

- [x] Inventoried source zip contents (case + gerbers).
- [x] Reorganized into `case/`, `pcb/`, `docs/`, `archive/`.
- [x] Git repo initialized.
- [x] README + PLATES + BUILD markdowns written.

## Lint results (2026-04-20)

`scripts/lint_dxf.py` — SCS-style pre-flight.

| DXF | Dangling endpoints | Verdict |
|---|---|---|
| ALPS LEFT B | 0 | clean |
| ALPS+MX LEFT B | 6 | 2× broken rects near (221.9,144.6) and (265.7,165.1) |
| MX LEFT B COSTARS | 0 | clean |
| MX LEFT B | 1 | orphan line at (257.3,380.9) — missing 3 sides of a switch cutout |
| ALPS RIGHT B | 1 | 1× orphan line |
| ALPS+MX RIGHT B | 0 | clean |
| MX RIGHT B | 1 | orphan line at (269.0,245.5) — missing 3 sides of a switch cutout |

No zero-length segs, dup vertices, unclosed polylines, or bbox overlaps. Orphan lines are ≥14 mm — SCS won't auto-repair; fab will either reject or laser-cut them as open scores.

## Open

- [ ] Fix orphan lines in MX LEFT, MX RIGHT, ALPS RIGHT, ALPS+MX LEFT before ordering.
- [ ] Measure Winkeyless + blocked-corner bezel DXFs, populate `PLATES.md` bezel table.
- [ ] Generate/extract KLE JSON for the DeltaSplit layout so `KB_PLATE_VALIDATOR/scripts/build_plate.py` can consume it.
- [ ] Mirror LEFT Costars geometry → create RIGHT Costars plate DXF.
- [ ] Count + locate mounting holes per layer; decide screw size for `BUILD.md`.
- [ ] Verify gerber file extensions against target fab (`gm1` → `gml`?).
- [ ] Render case/plate preview PNGs into `docs/` for README.

## Nice-to-have

- [ ] Source a 3D-printable version of bezel (instead of laser-cut acrylic).
- [ ] Check if PCB schematic source is recoverable anywhere (only gerbers present, no `.sch`/`.kicad_pcb`).
