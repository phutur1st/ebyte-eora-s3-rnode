# Ebyte EoRa-S3 / Rabbit-Labs RL-ReadyNode — RNode Firmware port

Run the **Ebyte EoRa-S3** (E22-900MM22S, ESP32-S3 + Semtech SX1262), sold by
Rabbit-Labs as the **RL-ReadyNode**, as an [RNode](https://unsigned.io/rnode/)
for [Reticulum](https://reticulum.network/). This repo packages a flashable
firmware image, the corresponding source patch, the host-side device-list patch,
and the tooling needed for the dev loop.

This is a port of [RNode Firmware CE](https://github.com/liberatedsystems/RNode_Firmware_CE)
to a board it doesn't ship support for. Not affiliated with or endorsed by
Rabbit-Labs, Ebyte, or the RNode / Reticulum projects.

## Status

| Feature | | | Feature | |
|---|:--:|---|---|:--:|
| USB serial RNode | ✅ | | OLED (SSD1306) | ✅ |
| SX1262 radio (TX/RX) | ✅ | | BLE | ✅ |
| `rnodeconf` integration | ✅ | | Battery (uncalibrated) | ⚠️ |

See [docs/features.md](docs/features.md) for details.

## Quick start

```bash
# 1. host deps + signing key + teach rnodeconf about this board (idempotent)
python3 -m pip install --upgrade rns esptool pyserial
python3 tools/patch_rnodeconf.py
rnodeconf -k                         # once per machine, if you don't have a key

# 2. flash the merged image (find your port first: ls /dev/cu.usbmodem*)
PORT=/dev/cu.usbmodemXXXX
esptool.py --chip esp32s3 --port "$PORT" --baud 460800 \
  write_flash -z 0x0 firmware/bin/rnode_firmware_ebyte_eora_s3-merged.bin

# 3. provision the EEPROM (config + signature), then bless the firmware hash
rnodeconf "$PORT" -r --platform ESP32 --model d8 --product ec --hwrev 1
python3 tools/rnode_bless_fw.py "$PORT"

# 4. verify
rnodeconf --info "$PORT"
```

Full guide (incl. the re-flash / dev loop): **[docs/flashing.md](docs/flashing.md)**.

> ⚠️ **Flashing alone is not enough.** A working RNode needs both firmware *and*
> per-device provisioning (step 3). The radio stays offline — no error — until
> the device is provisioned and its firmware hash is blessed. The merged image
> wipes existing provisioning, so it's for first install; to re-flash a working
> board use the split set (see the guide).

## What's here

```
firmware/
  bin/        flashable images (merged + split) + SHA256SUMS
  patches/    the port as a patch vs upstream RNode CE @a42f8d3
  build.sh    reproduce the bins from upstream + patch
tools/
  rnode_bless_fw.py    bless firmware after an esptool flash (required)
  rnode_kiss_ping.py   two-radio RF loopback test over KISS
  patch_rnodeconf.py   add model 0xD8 to your installed RNS rnodeconf
docs/
  flashing.md  pinmap.md  features.md
```

## Building from source

```bash
./firmware/build.sh      # clones RNode CE @pinned commit, applies the patch, rebuilds bin/
```

The shipped binaries are produced this way; see [build.sh](firmware/build.sh).

### Flashing a source build (the upstream way)

If you're working from a patched RNode CE checkout (what `build.sh` produces in
`firmware/.build/RNode_Firmware_CE`), the patch adds the standard CE make
targets, so you can build, flash, and provision in one step instead of the
manual esptool + `-r` + bless sequence:

```bash
make firmware-ebyte_eora_s3                          # compile
make upload-ebyte_eora_s3 port=/dev/cu.usbmodemXXXX  # flash + console image + firmware-hash
rnodeconf "$PORT" -r --platform ESP32 --model d8 --product ec --hwrev 1  # first time only: provision/sign
```

`upload-ebyte_eora_s3` runs `arduino-cli upload` (which preserves an existing
EEPROM provisioning), flashes the OLED console image, and sets the firmware hash
via CE's own `partition_hashes` tool — the same thing `tools/rnode_bless_fw.py`
does, just the canonical way. This is the flow used for the upstream PR.

> **Two audiences, two flows.** End users flashing the prebuilt image in
> `firmware/bin/` should follow [docs/flashing.md](docs/flashing.md) (esptool +
> `tools/`). The `make upload` flow above is for source builders / contributors
> and isn't needed if you're just flashing the released `.bin`.

## Board summary

ESP32-S3 + SX1262, 850–960 MHz, 22 dBm. **Crystal, not TCXO.** IDs `ec:d8:46`.
Full pin map: [docs/pinmap.md](docs/pinmap.md).

## License & credits

GPLv3 (inherited from RNode Firmware CE). See [LICENSE](LICENSE) and
[ATTRIBUTION.md](ATTRIBUTION.md).
