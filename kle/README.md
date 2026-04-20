# KLE — DeltaSplit 75

`deltasplit75_raw.json` — user's on-record KLE for the DeltaSplit 75. Raw keyboard-layout-editor rows.

## Layout notes

- **Gap `{"x":2}`** in every row = the visual/physical split between LEFT and RIGHT halves.
- **Color coding:**
  - `#cccccc` — alphas
  - `#999999` — mods / function keys
  - `#6897ca` — arrow cluster
- **"Temp" keys** at end of rows 2–5 = placeholder labels on the right-hand column; rename when finalizing.
- **Row 6 (bottom)** has a 2u "Backspace" where a 2.75u Spacebar normally sits on the LEFT half — unusual. Check if this is the detachable seam switch or an intentional remap.
- **Seam switch / detachable key** — not yet identified in this KLE. If the spread-split variant omits a key, mark it with `{d:true}` (decal) or produce `deltasplit75_spread.json` variant.

## TODO

- [ ] Validate against PCB switch count (PCB `.kicad_pcb` TBD — currently only gerbers).
- [ ] Produce `deltasplit75_onepiece.json` and `deltasplit75_spread.json` variants.
- [ ] Wire into `KB_PLATE_VALIDATOR/scripts/build_plate.py --kle kle/deltasplit75_onepiece.json`.
