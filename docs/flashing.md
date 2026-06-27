# Flashing & first bring-up

This guide covers flashing the **prebuilt image** in `firmware/bin/` with
esptool. If you're building from source instead, the `make upload-ebyte_eora_s3`
target does flash + console image + firmware-hash in one step — see
[Building from source](../README.md#building-from-source).

The board is an ESP32-S3 with native USB. On macOS it appears as
`/dev/cu.usbmodemXXXX`; on Linux as `/dev/ttyACMX`.

A working RNode needs **two separate things**:

1. **Firmware** — the flashable image (this is the same for every unit).
2. **Provisioning** — per-device config + signature + firmware hash written to
   the EEPROM/NVS by `rnodeconf`. The firmware refuses to start its radio until
   the device is provisioned and the running firmware hash matches.

That's why flashing alone is not enough. Follow the right path below.

## 0. Prerequisites

```bash
python3 -m pip install --upgrade rns esptool pyserial
python3 tools/patch_rnodeconf.py     # teach rnodeconf about model 0xD8 (idempotent)
rnodeconf -k                         # generate a signing key (once per machine, if you don't have one)
```

`rnodeconf -P` shows your key; if it prints one, you already have it.

---

## A. First install (fresh board, or recovering one)

Use the **merged** image. It writes the whole flash from `0x0`, which also
wipes any existing NVS — fine here, because you (re)provision right after.

```bash
ls /dev/cu.usbmodem*                 # find the port
PORT=/dev/cu.usbmodemXXXX

# 1. flash firmware
esptool.py --chip esp32s3 --port "$PORT" --baud 460800 \
  write_flash -z 0x0 firmware/bin/rnode_firmware_ebyte_eora_s3-merged.bin

# 2. provision EEPROM (writes config + signs with your key); no reflash
rnodeconf "$PORT" -r --platform ESP32 --model d8 --product ec --hwrev 1

# 3. bless the firmware hash (provisioning sets a placeholder; this fixes the
#    "firmware corrupt" state and lets the radio start)
python3 tools/rnode_bless_fw.py "$PORT"
```

If esptool can't sync in step 1, enter the ROM bootloader: hold **BOOT**, tap
**RESET**, release **BOOT**, then retry. (On the RL-ReadyNode only RESET is
exposed externally; BOOT is on the PCB.)

---

## B. Re-flashing a board that is already provisioned (dev loop)

**Do not use the merged image here** — it would wipe your provisioning at
`0x9000`. Flash the **split** set, which only touches `0x0 / 0x8000 / 0xe000 /
0x10000` and leaves NVS intact:

```bash
P=firmware/bin/rnode_firmware_ebyte_eora_s3
esptool.py --chip esp32s3 --port "$PORT" --baud 460800 write_flash -z \
  0x0     $P.bootloader.bin \
  0x8000  $P.partitions.bin \
  0xe000  $P.boot_app0.bin \
  0x10000 $P.app.bin

python3 tools/rnode_bless_fw.py "$PORT"   # update the firmware hash for the new build
```

No re-provisioning needed — config and signature survive.

---

## Verify

```bash
rnodeconf --info "$PORT"
# Product : Ebyte EoRa-S3 / Rabbit-Labs RL-ReadyNode 850 - 960 MHz (ec:d8:46)
# Device signature : Validated - Local signature
```

RF loopback between two units (one TX, one RX):

```bash
python3 tools/rnode_kiss_ping.py --tx /dev/cu.usbmodemAAAA --rx /dev/cu.usbmodemBBBB --txp 5
# ... PASS: received matching payload
```

## Use it with Reticulum

Add to `~/.reticulum/config` (adjust port/frequency for your region/legal band):

```ini
[[RL ReadyNode]]
  type = RNodeInterface
  interface_enabled = True
  port = /dev/cu.usbmodemXXXX
  frequency = 915000000
  bandwidth = 125000
  txpower = 5
  spreadingfactor = 8
  codingrate = 5
```

## Troubleshooting

| Symptom (serial / OLED) | Cause | Fix |
|---|---|---|
| `rnodeconf` crash `KeyError: 216` | host doesn't know model 0xD8 | `tools/patch_rnodeconf.py` |
| OLED "missing config" / unprovisioned | no/erased provisioning (e.g. after merged flash) | path **A** step 2–3 |
| OLED "firmware corrupt" | stored fw hash ≠ running firmware | `tools/rnode_bless_fw.py "$PORT"` |
| Radio never TX/RX, `RADIO_STATE 0`, no error | `hw_ready` false (provisioning or hash) | provision + bless (path A) |

> Why the bless step exists: RNode firmware checks the SHA-256 of the running
> app partition against a value stored at provision time. A custom build flashed
> out-of-band (or a `-r` provision without the firmware file) leaves that value
> stale, so the radio stays off with no error. `rnode_bless_fw.py` reads the
> device's own computed hash and writes it back as the target.

## Recovery

ESP32-S3 boards are virtually unbrickable: enter the ROM bootloader (BOOT+RESET)
and reflash via path A. Sanity check the chip is reachable with:

```bash
esptool.py --chip esp32s3 --port "$PORT" chip_id
```
