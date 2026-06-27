#!/usr/bin/env python3
"""Bless the currently-running RNode firmware on a device.

When you flash custom RNode firmware out-of-band (esptool) instead of through
rnodeconf, the firmware-hash target stored in EEPROM still refers to the old
image. device_validate_partitions() then sets fw_signature_validated = false,
device_init() returns false, hw_ready stays false, and the radio refuses to
start (CMD_RADIO_STATE reports 0 with no INITRADIO error).

This tool reads the device's own computed running-firmware hash (CMD_HASHES,
sub 0x02) and writes it back as the stored target (CMD_FW_HASH). The device
saves it and hard-resets; on the next boot the hashes match and hw_ready goes
true. Run this once after every esptool flash.
"""
import argparse
import sys
import time

import serial

FEND = 0xC0
FESC = 0xDB
TFEND = 0xDC
TFESC = 0xDD

CMD_FW_HASH = 0x58
CMD_HASHES = 0x60
DEV_HASH_LEN = 32


def escape(data: bytes) -> bytes:
    return data.replace(bytes([FESC]), bytes([FESC, TFESC])).replace(
        bytes([FEND]), bytes([FESC, TFEND])
    )


def unescape(data: bytes) -> bytes:
    return data.replace(bytes([FESC, TFEND]), bytes([FEND])).replace(
        bytes([FESC, TFESC]), bytes([FESC])
    )


def frame(cmd: int, payload: bytes = b"") -> bytes:
    return bytes([FEND, cmd]) + escape(payload) + bytes([FEND])


def read_frames(port, duration: float):
    raw = bytearray()
    deadline = time.time() + duration
    while time.time() < deadline:
        d = port.read(256)
        if d:
            raw += d
    frames = []
    i = 0
    while i < len(raw):
        if raw[i] == FEND:
            j = i + 1
            buf = bytearray()
            while j < len(raw) and raw[j] != FEND:
                buf.append(raw[j])
                j += 1
            if buf:
                frames.append(bytes(buf))
            i = j
        else:
            i += 1
    return frames


def get_running_hash(port) -> bytes:
    port.reset_input_buffer()
    port.write(frame(CMD_HASHES, bytes([0x02])))
    port.flush()
    for f in read_frames(port, 1.0):
        if f and f[0] == CMD_HASHES and len(f) >= 2 and f[1] == 0x02:
            return unescape(f[2:])[:DEV_HASH_LEN]
    return b""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("port")
    args = ap.parse_args()

    with serial.Serial(args.port, 115200, timeout=0.15) as s:
        time.sleep(0.3)
        running = get_running_hash(s)
        if len(running) != DEV_HASH_LEN:
            print(f"FAIL: could not read running firmware hash (got {len(running)} bytes)")
            return 1
        print(f"running fw hash: {running.hex()}")
        s.write(frame(CMD_FW_HASH, running))
        s.flush()
        print("wrote target hash; device should save and hard-reset...")
        time.sleep(2.5)

    # Reopen after the reset/re-enumeration and verify target now matches.
    time.sleep(1.5)
    try:
        with serial.Serial(args.port, 115200, timeout=0.15) as s:
            time.sleep(0.3)
            s.reset_input_buffer()
            s.write(frame(CMD_HASHES, bytes([0x01])))  # target hash
            s.flush()
            target = b""
            for f in read_frames(s, 1.0):
                if f and f[0] == CMD_HASHES and len(f) >= 2 and f[1] == 0x01:
                    target = unescape(f[2:])[:DEV_HASH_LEN]
            print(f"stored target : {target.hex()}")
            if target == running:
                print("PASS: firmware blessed, target matches running image")
                return 0
            print("WARN: target does not match yet (device may still be rebooting)")
            return 1
    except serial.SerialException as e:
        print(f"NOTE: could not reopen port to verify ({e}); re-enumeration is normal")
        return 0


if __name__ == "__main__":
    sys.exit(main())
