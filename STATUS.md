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

- [x] Generate **two KLE JSONs** for `KB_PLATE_VALIDATOR/scripts/build_plate.py`:
  - `kle/deltasplit75_onepiece.json` — full layout incl. seam switch.
  - `kle/deltasplit75_spread.json` — seam switch omitted.
- [x] Measure Winkeyless + blocked-corner bezel DXFs, populate `PLATES.md` bezel table.
- [x] Generate/extract KLE JSON for the DeltaSplit layout so `KB_PLATE_VALIDATOR/scripts/build_plate.py` can consume it.
- [x] Mirror LEFT Costars geometry → create RIGHT Costars plate DXF.
- [ ] Count + locate mounting holes per layer; decide screw size for `BUILD.md`.
- [ ] Verify gerber file extensions against target fab (`gm1` → `gml`?).
- [ ] Render case/plate preview PNGs into `docs/` for README.

## PCB reverse-engineering findings (2026-04-21)

Gerber silkscreen (`output/pcb_preview/F.SilkS.png`) + drill analysis (`pcb/gerbers/split left*.drl`):

- **Designer/year**: `DeltaSplit75 R2 xyxjj 2017`.
- **MCU**: socketed **ProMicro** daughterboard (2× 12-pin headers per half, 48× Ø1.016mm PTH), not SMT ATmega32u4.
- **Inter-half link**: TRRS 4-pin jack (marked `4PIN` on silk; 9× Ø0.991mm PTH matches 2× 4-pin jacks + mounting).
- **Per-key (86 switches)**: 5-pin MX footprint — 2× Ø1.499mm PTH signal, 2× Ø1.702mm NPTH plastic posts, 1× Ø3.988mm NPTH center post. Plus 1N4148 diode per key.
- **Mounting**: 12× Ø3.048mm NPTH = M3 case screws.
- **Stabilizers**: PCB-mount (additional Ø1.702/Ø3.988 NPTH beyond 86-switch count).
- **On-silk assembly order**: "1. Diodes → 2. ProMicro headers → 4. TRRS jacks → 5. Switches → 6. ProMicro. **INSTALL PRO MICRO LAST**."
- **B1/B2 switches**: dual-switch position in bottom row (confirms snap-off position note in `PLATES.md`).

Implication: **no MCU/crystal/USB on the board** — all on ProMicro module. Schematic reduces to matrix + 2× ProMicro headers + 2× TRRS. Trivial compared to a full ATmega32u4 build.

## Phase A — recreate original PCB in KiCad

Target project: `pcb/DeltaSplit_ProMicro.{kicad_pro,kicad_pcb}` (bootstrapped via `GerbView → File → Export → Export to Pcbnew`).

- [x] Export gerbers to `.kicad_pcb` via GerbView (graphics-only, no nets).
- [ ] Build schematic `pcb/DeltaSplit_ProMicro.kicad_sch`:
  - 86× `SW?` (marbastlib MX hotswap or solder footprint) + 86× `D?` (1N4148, THT DO-35 or SOD-123).
  - 2× ProMicro 12-pin header pair (Keebio-Parts `ProMicro.kicad_mod`).
  - 2× TRRS 4-pin jack (`PJ-320A` — check marbastlib-various or Keebio-Parts).
  - PCB-mount stabilizers for space/shift/backspace/enter (marbastlib `Stabilizer_Cherry_MX`).
  - Matrix wiring: rows × cols per ProMicro GPIO.
- [ ] Import netlist to existing `.kicad_pcb`.
- [ ] Place footprints over gerber-graphics by matching pad centers; KLE Placer for switch grid after anchor switch placed.
- [ ] Route to match visible copper — or use schematic-driven clean routing; rip graphics once done.
- [ ] ERC + DRC clean.

## Phase B — RP2040 drop-in (revised)

Easiest: **ProMicro RP2040 module** (Elite-Pi / 0xCB Helios / SparkFun). Pin-compatible with existing ProMicro headers → **zero PCB/schematic changes**. Just flash QMK/KMK with RP2040 matrix config.

Harder direct-SMT RP2040 path (calliah333 schematic) only if dropping daughterboard for cost/slim-profile reasons.

## RP2040 rebuild track

References:
- `docs/reference/rp2040_keyboard_design.md` — Noah-Kiser-derived BOM + routing constants.
- `docs/reference/rp2040_designguide_schematic.md` — calliah333 canonical RP2040 reference schematic (ref-designator breakdown).
- `docs/reference/nckiser_repos.md` — Noah's GitHub repos cloned to `../../NCKiser_refs/`.
- `docs/reference/kicad_toolchain.md` — install order for KiCad 10 + marbastlib + KLE placer + Keebio-Parts.

**RP2040 port strategy** (revised given ProMicro-based original):
Easiest path = **drop-in ProMicro-RP2040 daughterboard**: Elite-Pi, 0xCB Helios, or SparkFun ProMicro RP2040. Pin-compatible with original ProMicro headers → zero PCB changes needed for RP2040. The calliah333 full-SMT RP2040 schematic is only relevant if going direct-SMT MCU (harder rebuild, more components).

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
