# Feature status

| Feature        | Status | Notes |
|----------------|:------:|-------|
| USB serial RNode | ✅ | Detected by `rnodeconf`, host-controlled mode |
| SX1262 radio     | ✅ | Bidirectional TX/RX verified between two units |
| OLED display     | ✅ | SSD1306 128×64 @ 0x3C on I2C SDA18/SCL17 |
| BLE              | ✅ | Nordic UART service; advertises as `RNode XXXX` |
| Battery (LiPo)   | ⚠️ | Works but multiplier is uncalibrated — see below |
| Button           | ➖ | Only RESET is exposed externally on the RL-ReadyNode |

## OLED

Standard SSD1306. Shows the RNode status screen (device ID, radio stats). No
configuration needed; if the panel is absent, init fails gracefully and the rest
of the firmware runs normally.

## BLE

ESP32-S3 supports BLE only (no Bluetooth Classic). Enable per device:

```bash
rnodeconf --bluetooth-on  /dev/cu.usbmodemXXXX
rnodeconf --bluetooth-pair /dev/cu.usbmodemXXXX   # pairing mode
```

The device advertises the Nordic UART Service
(`6e400001-b5a3-f393-e0a9-e50e24dcca9e`) with name `RNode <hex>`, usable from
Sideband / the RNode app.

> **macOS name caching:** if this board previously ran Meshtastic, macOS may keep
> showing its old GAP name (e.g. `Meshtastic_a4a4`) instead of `RNode XXXX`.
> The live advertised name (`adv_local_name`) is correct. Use *Forget This
> Device* in macOS Bluetooth settings to clear the stale cache.

## Battery

The RL-ReadyNode has a LiPo connector wired to GPIO1 through a 2×1 MΩ divider.
Battery state/percent is reported over the RNode protocol (`CMD_STAT_BAT`) and on
the OLED.

The voltage multiplier (`analogRead/4095 × 6.96`) is taken from Meshtastic's
EoRa-S3 figure (2.11 × 3.3 V) and is **uncalibrated** — on USB power with a full
cell it reads `CHARGED / 100%`, which is plausible but unverified. To calibrate:
measure actual pack voltage with a multimeter and adjust the `6.96` constant in
`Power.h` (proportionally) so the reported voltage matches.
