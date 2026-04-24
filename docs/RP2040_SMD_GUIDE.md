# RP2040 SMD Implementation Guide (Lessons from SKYWAY-96)

This guide provides the verified hardware and firmware stack used in the successful SKYWAY-96 project, optimized for JLCPCB SMT assembly.

## 1. Verified BOM (LCSC Parts)

| Component | Description | Part Number (LCSC) | Notes |
|---|---|---|---|
| **MCU** | Raspberry Pi RP2040 | C2040 | QFN-56 |
| **Flash** | W25Q128JVS | C82431 | 128Mb (16MB) SOIC-8 |
| **LDO** | AMS1117-3.3 | C6186 | 5V to 3.3V Regulator |
| **ESD** | PRTR5V0U2X | C16223 | USB Data Protection |
| **Crystal** | 12MHz SMD | C115962 | 3.2x2.5mm |
| **USB-C** | HRO Type-C-31-M-12 | C165948 | 16-pin SMT |

## 2. Firmware Configuration (QMK keyboard.json)

The RP2040 build for QMK is significantly cleaner using the data-driven JSON format. 

### Essential ules.mk
`make
VIA_ENABLE = yes
RGBLIGHT_ENABLE = yes
RGBLIGHT_ANIMATIONS = yes
LTO_ENABLE = yes
`

### Essential keyboard.json Snippet
`json
{
    "processor": "RP2040",
    "bootloader": "rp2040",
    "matrix_pins": {
        "rows": ["GP0", "GP1", "GP2", "GP3", "GP4", "GP5"],
        "cols": ["GP6", "GP7", "GP8", "GP9", "GP10", "GP11", "GP12", "GP13", "GP14", "GP15", "GP16", "GP17", "GP18"]
    },
    "diode_direction": "COL2ROW",
    "rgblight": {
        "pin": "GP25",
        "led_count": 18,
        "animations": {
            "all": true
        }
    },
    "ws2812": {
        "pin": "GP25",
        "driver": "vendor"
    }
}
`

## 3. VIA/Vial Compatibility

To ensure the board is detected by VIA/Remap:
1.  **Lighting Tag**: In your ia.json, ensure "lighting": "qmk_rgblight" is set.
2.  **Vendor/Product IDs**: Ensure they match in both keyboard.json and the VIA JSON.
3.  **Sideloading**: If using Remap, ensure the matrix definition matches the physical layout exactly to avoid "missing key" errors.

## 4. Hardware Routing Lessons
*   **GP25 for RGB**: Using GP25 for the WS2812B data line is a reliable standard.
*   **Differential Pairs**: Keep USB D+/D- traces as short as possible and matched in length.
*   **Decoupling**: Ensure each VCC pin on the RP2040 has a 0.1uF capacitor as close to the pin as possible.
