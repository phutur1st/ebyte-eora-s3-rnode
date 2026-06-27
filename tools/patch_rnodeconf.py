#!/usr/bin/env python3
"""Add the Ebyte EoRa-S3 / RL-ReadyNode (model 0xD8) to the installed RNS rnodeconf.

RNS/rnodeconf ships a fixed table of known RNode models. Our firmware reports
model 0xD8, which upstream RNS does not know, so `rnodeconf --info` crashes with
`KeyError: 216`. This script injects the three needed entries (ROM constants,
the `models` band/power row, and the `products` display name) into the copy of
`RNS/Utilities/rnodeconf.py` that your Python environment actually imports.

It is idempotent (safe to run repeatedly), marks its additions with sentinel
comments, makes a one-time `.bak`, and supports `--revert`. Re-run it after
upgrading RNS, since pip will overwrite the file with a clean upstream copy.

Usage:
    python3 patch_rnodeconf.py            # apply
    python3 patch_rnodeconf.py --revert   # remove our additions
    python3 patch_rnodeconf.py --path /custom/rnodeconf.py
"""
import argparse
import os
import re
import shutil
import sys

TAG = "ebyte-eora-s3"  # sentinel substring marking lines we own

CONSTANTS = f"""
    PRODUCT_EBYTE_EORA  = 0xEC  # {TAG}
    BOARD_EBYTE_EORA_S3 = 0x46  # {TAG}
    MODEL_D8            = 0xD8  # {TAG} Ebyte EoRa-S3 / Rabbit-Labs RL-ReadyNode, 868/915 MHz SX1262
"""

MODEL_ROW = (
    '    0xD8: [850000000, 960000000, 22, "850 - 960 MHz", '
    f'"rnode_firmware_ebyte_eora_s3.zip", "SX1262"],  # {TAG}\n'
)

PRODUCT_ROW = (
    '    ROM.PRODUCT_EBYTE_EORA: "Ebyte EoRa-S3 / Rabbit-Labs RL-ReadyNode",'
    f'  # {TAG}\n'
)


def find_rnodeconf():
    try:
        import RNS  # noqa: F401
    except ImportError:
        return None
    return os.path.join(os.path.dirname(RNS.__file__), "Utilities", "rnodeconf.py")


def apply_patch(text):
    changed = False

    # 1) ROM constants: anchor after the Xiao MODEL_DD line.
    if "MODEL_D8" not in text:
        anchor = re.search(r"^( *MODEL_DD *= *0xDD.*\n)", text, re.M)
        if not anchor:
            raise RuntimeError("could not find MODEL_DD anchor for constants")
        text = text[:anchor.end()] + CONSTANTS + text[anchor.end():]
        changed = True

    # 2) models row: anchor after the 0xDD models entry.
    if "0xD8:" not in text:
        anchor = re.search(r"^( *0xDD: *\[.*\],.*\n)", text, re.M)
        if not anchor:
            raise RuntimeError("could not find 0xDD models anchor")
        text = text[:anchor.end()] + MODEL_ROW + text[anchor.end():]
        changed = True

    # 3) products row: anchor after the Xiao product line.
    if "PRODUCT_EBYTE_EORA:" not in text:
        anchor = re.search(r"^( *ROM\.PRODUCT_XIAO_S3: *\".*\",.*\n)", text, re.M)
        if not anchor:
            raise RuntimeError("could not find PRODUCT_XIAO_S3 products anchor")
        text = text[:anchor.end()] + PRODUCT_ROW + text[anchor.end():]
        changed = True

    return text, changed


def revert_patch(text):
    lines = text.splitlines(keepends=True)
    kept = [ln for ln in lines if f"# {TAG}" not in ln]
    return "".join(kept), len(kept) != len(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", help="explicit path to rnodeconf.py")
    ap.add_argument("--revert", action="store_true", help="remove our additions")
    args = ap.parse_args()

    path = args.path or find_rnodeconf()
    if not path or not os.path.isfile(path):
        print("ERROR: could not locate rnodeconf.py (is RNS installed in this env?)")
        print("       pass --path /path/to/RNS/Utilities/rnodeconf.py")
        return 1
    print(f"target: {path}")

    with open(path, "r") as f:
        original = f.read()

    if args.revert:
        new, changed = revert_patch(original)
        action = "reverted"
    else:
        new, changed = apply_patch(original)
        action = "patched"

    if not changed:
        print(f"already up to date ({'no marks found' if args.revert else 'model 0xD8 present'}); nothing to do")
        return 0

    bak = path + ".bak"
    if not os.path.exists(bak) and not args.revert:
        shutil.copy2(path, bak)
        print(f"backup: {bak}")

    with open(path, "w") as f:
        f.write(new)
    print(f"{action}: model 0xD8 (Ebyte EoRa-S3 / RL-ReadyNode)")
    print("verify with:  rnodeconf --info <port>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
