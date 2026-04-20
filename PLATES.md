# Plate Variants

All plate DXFs are **1.5 mm aluminium**, one per half. BBox from ezdxf parse.

| Variant       | Left (W×H mm)   | Right (W×H mm)  | Notes |
|---------------|-----------------|-----------------|-------|
| MX            | 340.2 × 129.3   | 351.9 × 129.3   | standard MX switch cutouts |
| ALPS          | present         | present         | |
| ALPS+MX       | present         | present         | hybrid — both footprints |
| MX Costars    | 340.2 × 129.3   | **missing**     | Costar stabilizer cutouts; only LEFT exists in source repo |

## Middle layers

Single DXF per side contains 5 vertically stacked layers (~142 mm each × 5 = 710 mm tall). Split before ordering if fab bed < 750 mm.

| Side  | W × H mm       |
|-------|----------------|
| Left  | 340.2 × 710.5  |
| Right | 351.9 × 731.2  |

## Bottom layer

| Side  | W × H mm       |
|-------|----------------|
| Left  | 340.2 × 129.3  |
| Right | 351.9 × 129.3  |

## Bezel (single DXF, one piece)

Bezel variants are full-width single pieces, not split:

| Variant        | Size (W×H mm)  |
|----------------|----------------|
| Standard       | 345.1 × 129.3  |
| Winkeyless     | — (check DXF)  |
| Blocked corner | — (check DXF)  |

## Stitch seam

Left and bottom layers butt-join in world coords at x ≈ 320–372 mm. When fabbed, halves align by shared mounting-hole positions — no keying feature in DXF.

## Known gaps

- **No RIGHT Costars plate** — either use ALPS+MX as base and edit, or mirror LEFT Costars geometry.
- **Bezel DXFs not yet measured** for Winkeyless / blocked-corner — populate table.
