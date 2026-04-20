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

- [ ] **Investigate orphan lines before patching** — DeltaSplit 75 has a detachable seam switch (one-piece mode has it, spread mode omits it). The 1-orphan-line finding in MX LEFT/RIGHT may be an **intentional break-away tab** for the detachable cutout, not a defect. Check coords (257.3, 380.9) LEFT / (269.0, 245.5) RIGHT against the seam-switch position before editing the DXF.
- [ ] Generate **two KLE JSONs** for `KB_PLATE_VALIDATOR/scripts/build_plate.py`:
  - `kle/deltasplit75_onepiece.json` — full layout incl. seam switch.
  - `kle/deltasplit75_spread.json` — seam switch omitted.
- [ ] Measure Winkeyless + blocked-corner bezel DXFs, populate `PLATES.md` bezel table.
- [ ] Generate/extract KLE JSON for the DeltaSplit layout so `KB_PLATE_VALIDATOR/scripts/build_plate.py` can consume it.
- [ ] Mirror LEFT Costars geometry → create RIGHT Costars plate DXF.
- [ ] Count + locate mounting holes per layer; decide screw size for `BUILD.md`.
- [ ] Verify gerber file extensions against target fab (`gm1` → `gml`?).
- [ ] Render case/plate preview PNGs into `docs/` for README.

## RP2040 rebuild track

References:
- `docs/reference/rp2040_keyboard_design.md` — Noah-Kiser-derived BOM + routing constants.
- `docs/reference/nckiser_repos.md` — Noah's GitHub repos cloned to `../../NCKiser_refs/`; template is `le_chiffre_keyboard_stm32`, tutorial artifact is `TKL_VIDEO`.

### Phase 1 — project scaffold

- [ ] Copy `le_chiffre_keyboard_stm32/kicad/pcb/` layout skeleton to `pcb/kicad/`.
- [ ] Vendor `marbastlib-mx.pretty` + `Keebio-Parts.pretty` + `MX_Alps_Hybrid.pretty` into `pcb/kicad/library/`.
- [ ] Copy `kibot.yml` → `.github/workflows/` once the KiCad project builds.

### Phase 2 — schematic

- [ ] Open `NCKiser_refs/TKL_VIDEO/TKL_Video/TKL_Video.kicad_sch` in KiCad 10 as workflow study (step through `TKL_Video-backups/` in date order).
- [ ] Build DeltaSplit schematic: RP2040 (KiCad built-in `MCU_RaspberryPi:RP2040`) + W25Q128 QSPI + HRO TYPE-C-31-M-12 + XC6206 LDO + 12 MHz 3225 crystal + SRV05-4 ESD + 86× switch/diode matrix.

### Phase 3 — PCB layout

- [ ] Import existing DeltaSplit gerbers as reference layer (File → Import → Gerber).
- [ ] Extract key grid from `kle/deltasplit75_raw.json` → CSV (row, col, x_mm, y_mm, w_u) on the 0.79375 mm grid.
- [ ] Place switch/hotswap/diode footprints; cols top/vertical, rows bottom/horizontal.
- [ ] Route per §4 hierarchy (USB diff → crystal → power → matrix → GND pour + stitching).
- [ ] Cross-check board outline vs `case/` plate DXFs — mounting holes align.
- [ ] Decide hotswap-vs-solder; if hotswap, apply §3 collision rules for the detachable seam switch.

## Nice-to-have

- [ ] Source a 3D-printable version of bezel (instead of laser-cut acrylic).
