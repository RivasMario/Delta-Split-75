# Delta Split 75

Fork/mirror of the DeltaSplit75 V2 open-source keyboard: case DXF/DWG files, PCB gerbers, and 3D model. Reorganized for local iteration and fab prep.

## What this is

DeltaSplit 75 is a **one-piece 75% keyboard with a visual split** (not an ergo split — the two halves are stitched side-by-side into a single case). The PCB is one ~322 × 120 mm board. The case plates are delivered as **left + right DXFs** because the combined ~680 mm width exceeds most laser beds.

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
