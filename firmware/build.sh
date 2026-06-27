#!/usr/bin/env bash
#
# Reproducible build of the Ebyte EoRa-S3 / RL-ReadyNode RNode firmware.
#
# Clones RNode Firmware CE at the exact upstream commit this port targets,
# applies our patch, builds with arduino-cli, and regenerates the flashable
# images in ./bin (both the single-file merged image and the split set).
#
# This is the GPLv3 "corresponding source" path: the bins in ./bin are produced
# from upstream@$UPSTREAM_COMMIT + patches/0001-ebyte-eora-s3-rnode-port.patch.
#
# Requirements: git, arduino-cli, esptool.py, and the esp32 core 2.0.17
# (the firmware's own `make prep-esp32` installs the toolchain/libs).
set -euo pipefail

UPSTREAM_REPO="https://github.com/liberatedsystems/RNode_Firmware_CE.git"
UPSTREAM_COMMIT="a42f8d325f660ef46fb6a4997b8c9e95dbbee2c7"
ESP_CORE_VER="2.0.17"

# Board identity (see ../docs/pinmap.md)
BOARD_MODEL="0x46"   # BOARD_EBYTE_EORA_S3
BOARD_VARIANT="0xD8" # MODEL_D8

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCH="$HERE/patches/0001-ebyte-eora-s3-rnode-port.patch"
OUT="$HERE/bin"
WORK="${1:-$HERE/.build}"  # pass a path to reuse a checkout
# arduino-cli requires the sketch folder to be named after its .ino, so the
# checkout must live in a dir called RNode_Firmware_CE.
SRC="$WORK/RNode_Firmware_CE"

echo "==> Upstream:  $UPSTREAM_REPO @ $UPSTREAM_COMMIT"
echo "==> Workdir:   $SRC"

mkdir -p "$WORK"
if [ ! -d "$SRC/.git" ]; then
  git clone "$UPSTREAM_REPO" "$SRC"
fi
cd "$SRC"
git fetch --all --quiet || true
git checkout -q "$UPSTREAM_COMMIT"
git reset --hard -q "$UPSTREAM_COMMIT"
git clean -fdq

echo "==> Applying patch"
git apply --whitespace=nowarn "$PATCH"

echo "==> Preparing esp32 toolchain (idempotent)"
make prep-esp32 || true

echo "==> Compiling (BOARD_MODEL=$BOARD_MODEL BOARD_VARIANT=$BOARD_VARIANT)"
arduino-cli compile --fqbn "esp32:esp32:esp32s3:CDCOnBoot=cdc" \
  -e --build-property "build.partitions=no_ota" \
  --build-property "upload.maximum_size=2097152" \
  --build-property "compiler.cpp.extra_flags=\"-DBOARD_MODEL=$BOARD_MODEL\" \"-DBOARD_VARIANT=$BOARD_VARIANT\""

B="build/esp32.esp32.esp32s3"
CORE_PARTS="$HOME/Library/Arduino15/packages/esp32/hardware/esp32/$ESP_CORE_VER/tools/partitions"
[ -d "$CORE_PARTS" ] || CORE_PARTS="$HOME/.arduino15/packages/esp32/hardware/esp32/$ESP_CORE_VER/tools/partitions"

mkdir -p "$OUT"
P="$OUT/rnode_firmware_ebyte_eora_s3"
cp "$B/RNode_Firmware_CE.ino.bootloader.bin" "$P.bootloader.bin"
cp "$B/RNode_Firmware_CE.ino.partitions.bin" "$P.partitions.bin"
cp "$B/RNode_Firmware_CE.ino.bin"            "$P.app.bin"
cp "$CORE_PARTS/boot_app0.bin"               "$P.boot_app0.bin"

echo "==> Merging single-file image"
esptool.py --chip esp32s3 merge_bin -o "$P-merged.bin" \
  --flash_mode dio --flash_freq 80m --flash_size 4MB \
  0x0     "$P.bootloader.bin" \
  0x8000  "$P.partitions.bin" \
  0xe000  "$P.boot_app0.bin" \
  0x10000 "$P.app.bin"

( cd "$OUT" && shasum -a 256 *.bin > SHA256SUMS )
echo "==> Done. Artifacts in $OUT"
ls -la "$OUT"
