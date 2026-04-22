# Build / Fab Order Guide

## PCB (RP2040 SMD Version)

- Single board designed to be snapped into two halves.
- MCU: RP2040 (direct SMT).
- Link: **USB-C to USB-C cable**. 
- *Caution:* Use a standard USB-C cable. The link uses the CC lines/Differential pairs for serial communication.

## Case (3D Printed)

1. Use STLs in `output/3d/`.
2. Recommended Material: PETG or PLA+.
3. Infill: 20-30% Grid for weight and sound dampening.
4. Hardware: M3 × 30mm screws + M3 nuts.

## Assembly Order

1. Print Left/Right halves.
2. Snap PCB halves apart.
3. Install USB-C mid-link jacks.
4. Bolt through: Bezel → Plate → Shell → Bottom.

## Open questions

- Screw spec: original docs don't list diameter/length. Check `docs/deltasplit.pdf`.
- Standoff height: derive from total stack 22.5 mm minus hardware.
