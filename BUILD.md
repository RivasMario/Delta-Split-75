# Build / Fab Order Guide

## PCB

- Single board, ~322 × 120 mm, 2-layer.
- Gerbers in `pcb/gerbers/` — KiCad 4.0.6 output, format 4.6 mm absolute.
- File naming uses `split left-*` as prefix (project name, not a half). All 11 standard gerber+drill files present:
  - F.Cu / B.Cu / F.Mask / B.Mask / F.SilkS / B.SilkS / F.Paste / B.Paste / Edge.Cuts / `.drl` / `NPTH.drl`.
- Fab: JLCPCB / PCBWay accept this set as-is. Rename `split left-Edge.Cuts.gm1` → `*-Edge_Cuts.gml` if fab requires standard extension.

## Plates (aluminium)

1. Pick switch variant from `PLATES.md` (MX / ALPS / ALPS+MX / MX Costars).
2. Send LEFT and RIGHT DXF as **two separate parts** on the SendCutSend quote.
3. Material: 1.5 mm 5052 aluminium (match original spec).
4. Finish: raw / clear anodize.

## Acrylic layers

- **Top bezel**: 2 × 3 mm of chosen variant.
- **Middle**: 5 × 3 mm per side. Source DXF stacks all 5 in one file — split or let fab cut as-is if bed is big enough.
- **Bottom**: 1 × 3 mm per side.
- Pick color; shared mounting holes keep alignment.

## Assembly order

1. Bottom acrylic → middle stack → plate → PCB → switches → bezel.
2. M2 or M3 through-bolt at each mounting hole (count TBD — measure from plate DXF).
3. Align left + right halves at the stitch seam before tightening.

## Open questions

- Screw spec: original docs don't list diameter/length. Check `docs/deltasplit.pdf`.
- Standoff height: derive from total stack 22.5 mm minus hardware.
