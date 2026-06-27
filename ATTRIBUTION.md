# Attribution

This repository is a hardware port and packaging effort that builds entirely on
the work of others.

## Firmware

- **[RNode Firmware CE](https://github.com/liberatedsystems/RNode_Firmware_CE)**
  — Liberated Embedded Systems and contributors. The firmware in this repo is
  RNode Firmware CE plus the patch in `firmware/patches/`, built from upstream
  commit `a42f8d325f660ef46fb6a4997b8c9e95dbbee2c7`. Licensed **GPLv3**; this
  repo inherits that license.
- **[RNode Firmware](https://github.com/markqvist/RNode_Firmware)** /
  **[Reticulum](https://github.com/markqvist/Reticulum)** — Mark Qvist. Original
  RNode design and the `rnodeconf` / RNS tooling this port integrates with.

## Pin map references

The SX1262 / OLED / battery pin map was confirmed against:

- **[Meshtastic](https://github.com/meshtastic/firmware)** —
  `variants/esp32s3/CDEBYTE_EoRa-S3` (notably its note that the board uses an
  XTAL, not a TCXO).
- **[MeshCore](https://github.com/ripplebiz/MeshCore)** — `boards/ebyte_eora-s3`
  and its `ebyte_eora_s3` variant.

## Hardware

- **Ebyte (Chengdu Ebyte)** — EoRa-S3 / E22-900MM22S module.
- **Rabbit-Labs** — RL-ReadyNode product based on the EoRa-S3.

## Host tool modification

`tools/patch_rnodeconf.py` modifies the model table in
`RNS/Utilities/rnodeconf.py` (part of [Reticulum / RNS](https://github.com/markqvist/Reticulum),
Mark Qvist) **in place on the user's machine**. This repo does not redistribute
RNS source; it only adds an entry for model `0xD8` to an existing installation.

## Scope

Independent community port. Not affiliated with or endorsed by any of the above
projects or vendors. The board IDs `0xEC / 0x46 / 0xD8` are self-allocated and
not officially assigned by the RNode project.
