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
- `docs/reference/rp2040_designguide_schematic.md` — calliah333 canonical RP2040 reference schematic (ref-designator breakdown).
- `docs/reference/nckiser_repos.md` — Noah's GitHub repos cloned to `../../NCKiser_refs/`.
- `docs/reference/kicad_toolchain.md` — install order for KiCad 10 + marbastlib + KLE placer + Keebio-Parts.

### Phase 0 — install toolchain (one-time)

- [ ] Install KiCad 10.0.1.
- [ ] PCM: install **ebastler/marbastlib** (upstream, not NCKiser fork).
- [ ] PCM: install **zykrah/kicad-kle-placer** via `https://raw.githubusercontent.com/zykrah/zykrah-kicad-repository/main/repository.json`.
- [ ] Link `Keebio-Parts.pretty` (from `../../NCKiser_refs/`) in `fp-lib-table`.

### Phase 1 — project scaffold

- [ ] Copy `le_chiffre_keyboard_stm32/kicad/pcb/` layout skeleton to `pcb/kicad/`.
- [ ] Add KiCad project: `pcb/kicad/deltasplit75_rp2040.kicad_pro`.
- [ ] Copy `kibot.yml` → `.github/workflows/` once the KiCad project builds.

### Phase 2 — schematic (reference: `docs/reference/rp2040_designguide_schematic.md`)

- [ ] Open RP2040-Guide.pdf side-by-side with KiCad; replicate MCU block 1:1 (U3 RP2040, U1 W25Q128, U2 USBLC6 ESD, U4 XC6206 LDO, Y1 12MHz + 22pF + 1kΩ, F1 500mA PTC, SW1 boot button, J2 SWD).
- [ ] Set exact passive values per the PDF table: 5.1kΩ CC pulldowns, 27Ω USB series, 10µF bulk, 100nF per 3V3 pin, 1µF on 1V1/LDO in/out.
- [ ] Create hierarchical `key_matrix.kicad_sch` with 86× SW + 86× D + stabilizers. Name SW1…SW86 so KLE-placer can match.

### Phase 3 — PCB layout

- [ ] Import existing DeltaSplit gerbers as reference layer (File → Import → Gerber).
- [ ] Place ONE switch + its diode manually at the desired relative offset.
- [ ] Run **KLE Placer** plugin with `kle/deltasplit75_raw.json` → auto-places remaining 85 switches + diodes on the 0.79375 mm grid.
- [ ] Route per §4 hierarchy (USB diff → crystal → power → matrix → GND pour + stitching).
- [ ] Cross-check board outline vs `case/` plate DXFs — mounting holes align.
- [ ] Decide hotswap-vs-solder; if hotswap, apply §3 collision rules for the detachable seam switch.

### Phase 4 — KLE enrichment for placer

- [ ] Add label-position-4 reference numbers (`1`…`86`) to every key in `kle/deltasplit75_raw.json` — required for **Specific Reference Mode** (needed once any rotated key is introduced).
- [ ] Add multilayout labels (position 3) if supporting ANSI/ISO/Costar variants on one PCB.

## Nice-to-have

- [ ] Source a 3D-printable version of bezel (instead of laser-cut acrylic).
