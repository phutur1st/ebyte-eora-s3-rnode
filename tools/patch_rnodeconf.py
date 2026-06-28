#!/usr/bin/env python3
"""Add the Ebyte EoRa-S3 / RL-ReadyNode (model 0xD8) to the installed RNS rnodeconf.

RNS/rnodeconf ships a fixed table of known RNode models. Our firmware reports
model 0xD8, which upstream RNS does not know, so `rnodeconf --info` crashes with
`KeyError: 216`. This script injects the three needed entries (ROM constants,
the `models` band/power row, and the `products` display name) into the copy of
`RNS/Utilities/rnodeconf.py` that your install actually imports.

It auto-locates that file even when RNS is installed in a pipx/venv that the
system Python can't import: it reads the `rnodeconf` launcher's shebang to find
the right interpreter, then asks it where RNS lives. You can still pass `--path`
(a source file, a launcher shim, or a directory — it resolves all three).

It is idempotent (safe to run repeatedly), marks its additions with sentinel
comments, makes a one-time `.bak`, and supports `--revert`. Re-run it after
upgrading RNS, since pip/pipx will overwrite the file with a clean upstream copy.

Usage:
    python3 patch_rnodeconf.py            # auto-locate and apply
    python3 patch_rnodeconf.py --revert   # remove our additions
    python3 patch_rnodeconf.py --path /path/to/rnodeconf[.py]   # or a venv/dir
"""
import argparse
import os
import re
import shutil
import subprocess
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


# --- locating the real RNS/Utilities/rnodeconf.py -------------------------

def _is_source(path):
    """True if `path` is the rnodeconf source (has the model table), not a shim."""
    if not path or not os.path.isfile(path):
        return False
    try:
        with open(path, "r", errors="ignore") as f:
            head = f.read(20000)
    except OSError:
        return False
    return "MODEL_DD" in head and "models = {" in head


def _interp_from_launcher(launcher):
    """Read a launcher script's shebang and return the interpreter path."""
    try:
        with open(launcher, "r", errors="ignore") as f:
            first = f.readline().strip()
    except OSError:
        return None
    if not first.startswith("#!"):
        return None
    parts = first[2:].strip().split()
    if not parts:
        return None
    # handle '#!/usr/bin/env python' as well as an absolute interpreter path
    interp = parts[1] if os.path.basename(parts[0]) == "env" and len(parts) > 1 else parts[0]
    return interp if os.path.exists(interp) else None


def _via_interpreter(py):
    """Ask interpreter `py` where its RNS rnodeconf.py is."""
    if not py or not os.path.exists(py):
        return None
    try:
        out = subprocess.run(
            [py, "-c", "import RNS,os;print(os.path.join(os.path.dirname(RNS.__file__),'Utilities','rnodeconf.py'))"],
            capture_output=True, text=True, timeout=30,
        )
    except Exception:
        return None
    cand = out.stdout.strip()
    return cand if _is_source(cand) else None


def _search_dir(root):
    for base, _, files in os.walk(root):
        if "rnodeconf.py" in files and base.replace("\\", "/").endswith("RNS/Utilities"):
            cand = os.path.join(base, "rnodeconf.py")
            if _is_source(cand):
                return cand
    return None


def resolve_source(explicit):
    """Resolve to the real rnodeconf.py from a source path, launcher, dir, or env."""
    # 1) explicit path: accept source directly, or resolve a shim / directory
    if explicit:
        if _is_source(explicit):
            return explicit
        if os.path.isdir(explicit):
            hit = _search_dir(explicit)
            if hit:
                return hit
        if os.path.isfile(explicit):  # likely a launcher shim
            hit = _via_interpreter(_interp_from_launcher(explicit))
            if hit:
                return hit

    # 2) importable by the interpreter running this script
    hit = _via_interpreter(sys.executable)
    if hit:
        return hit

    # 3) the `rnodeconf` launcher on PATH -> its interpreter -> RNS (handles pipx)
    launcher = shutil.which("rnodeconf")
    if launcher:
        hit = _via_interpreter(_interp_from_launcher(launcher))
        if hit:
            return hit

    # 4) brute-force the usual pipx/venv roots
    for root in [os.path.expanduser(p) for p in (
        "~/.local/share/pipx/venvs", "~/.local/pipx/venvs",
        "~/.local/lib", "~/.virtualenvs",
    )]:
        if os.path.isdir(root):
            hit = _search_dir(root)
            if hit:
                return hit
    return None


# --- patching -------------------------------------------------------------

def apply_patch(text):
    changed = False
    if "MODEL_D8" not in text:
        anchor = re.search(r"^( *MODEL_DD *= *0xDD.*\n)", text, re.M)
        if not anchor:
            raise RuntimeError("could not find MODEL_DD anchor for constants")
        text = text[:anchor.end()] + CONSTANTS + text[anchor.end():]
        changed = True
    if "0xD8:" not in text:
        anchor = re.search(r"^( *0xDD: *\[.*\],.*\n)", text, re.M)
        if not anchor:
            raise RuntimeError("could not find 0xDD models anchor")
        text = text[:anchor.end()] + MODEL_ROW + text[anchor.end():]
        changed = True
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
    ap.add_argument("--path", help="rnodeconf.py source, a launcher shim, or a venv/dir to search")
    ap.add_argument("--revert", action="store_true", help="remove our additions")
    args = ap.parse_args()

    path = resolve_source(args.path)
    if not path:
        print("ERROR: could not locate the RNS rnodeconf.py source.")
        print("  Tried: --path, this interpreter, the `rnodeconf` launcher on PATH, and pipx/venv roots.")
        print("  Find it manually and pass it, e.g.:")
        print("    find ~/.local ~/.local/share -path '*RNS/Utilities/rnodeconf.py'")
        print("    python3 patch_rnodeconf.py --path <that path>")
        return 1
    if args.path and os.path.realpath(args.path) != os.path.realpath(path):
        print(f"resolved {args.path} -> {path}")
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
