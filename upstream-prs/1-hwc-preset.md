# vaillant: add DHW comfort/eco preset and eco settings to the VRC 720 controller
Branch: `upstream-hwc-preset` (on top of upstream master). Messages: `HwcPreset`, `HwcEcoTempDesired`, `HwcEcoChargeHyst`, `HwcEcoMinTemp13h`, `HwcEcoMinTemp24h` in `15.ctlv2.tsp` (group 01, inside `HotWaterCircuit`, so conditioned on `hwcenabled=1`).

Verified on `MF=Vaillant;ID=BASV3`/sensoCOMFORT VRC 720/3 (SW 0808, HW 8004) next to an aroTHERM plus.

| message | b524 id | type |
|---|---|---|
| HwcPreset | `020001001400` | UCH 0=comfort;1=eco |
| HwcEcoTempDesired | `020001001500` | EXP °C (panel: "Reduced DHW temperature", factory 49 °C) |
| HwcEcoChargeHyst | `020001001600` | EXP K ("Red. cyl. charging hysteresis", 5 K) |
| HwcEcoMinTemp13h | `020001001700` | EXP °C ("Min. temp. after 13 hrs", 43 °C) |
| HwcEcoMinTemp24h | `020001001800` | EXP °C ("Min. temp. after 24 hrs", 40 °C) |

Evidence: toggled Comfort↔Eco on the panel while polling b524 group 01: reg 0x14 goes 0→1 and back; regs 0x15–0x18 change the
flag byte 02 (inactive) → 03 (active) while Eco is selected; reg 0x19 goes 4→0. Changing "Reduced DHW temperature" on the panel
moved 0x15 40.0→41.0→40.0. Values on this unit: 40 / 10 / 43 / 40. Names/factory values from the VRC 720/3 manual (0020334316_03).
Raw reply format: `LL FF GG RR 00 <value>`; FF: 00 unused, 01 read-only, 02 inactive setting, 03 active setting.

Open: min/max ranges of the four settings are not in the manual excerpt I have, so no `@minValue/@maxValue` yet.
