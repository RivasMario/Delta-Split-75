# Delta Split 75

Fork/mirror of the DeltaSplit75 V2 open-source keyboard: case DXF/DWG files, PCB gerbers, and 3D model. Reorganized for local iteration and fab prep.

## What this is

DeltaSplit 75 is a **dual-mode 75% keyboard**:

1. **One-piece mode** — left + right plates butt-join into a single unibody case; all keys present.
2. **Spread-split mode** — same PCB/plates but mounted in two separate shells with a physical gap between halves. At the seam there's a **detachable switch** that gets populated for one-piece mode and removed (or a blocker inserted) for spread mode.

The PCB is one ~322 × 120 mm board regardless of mode. Plates ship as **left + right DXFs** because the combined ~680 mm width exceeds most laser beds, and because the spread mode needs them as separate parts anyway.

## Layout

```
case/
  bezel/        top bezel — Standard / Winkeyless / blocked-corner
  left/
    plate/      MX, ALPS, ALPS+MX, MX Costars
    middle/     5× stacked in one DXF
    bottom/
  right/
    plate/      MX, ALPS, ALPS+MX   (no Costars variant)
    middle/
    bottom/
pcb/
  gerbers/      KiCad 4.0.6 output, 11 files (Cu/Mask/Paste/SilkS/Edge.Cuts/drills)
docs/
  DeltaSplit-Final.step    3D assembly
  deltasplit.pdf           original build doc
  PCB_Dimension.dwg
  ORIGINAL_README.md
archive/
  *.zip, *.bak             source archives, AutoCAD backups
```

## Stackup (top → bottom)

| Qty | Thickness | Material | Layer |
|----|-----------|----------|-------|
| 2  | 3.0 mm   | acrylic  | top bezel |
| 1  | 1.5 mm   | aluminium | switch plate |
| 5  | 3.0 mm   | acrylic  | middle |
| 1  | 3.0 mm   | acrylic  | bottom |

Total case height ≈ **22.5 mm**.

## Next

See `PLATES.md` for plate variant matrix, `BUILD.md` for fab-order guide, `STATUS.md` for current issues / TODOs.
