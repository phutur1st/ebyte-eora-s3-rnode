#!/usr/bin/env python3
import argparse
import sys
import threading
import time

import serial

FEND = 0xC0
FESC = 0xDB
TFEND = 0xDC
TFESC = 0xDD

CMD_DATA = 0x00
CMD_FREQUENCY = 0x01
CMD_BANDWIDTH = 0x02
CMD_TXPOWER = 0x03
CMD_SF = 0x04
CMD_CR = 0x05
CMD_RADIO_STATE = 0x06
CMD_SEL_INT = 0x3E
CMD_STAT_RX = 0x21
CMD_STAT_TX = 0x22
CMD_ERROR = 0x90
RADIO_STATE_ON = 0x01

ERRORS = {
    0x01: "INITRADIO",
    0x02: "TXFAILED",
    0x04: "MODEM_TIMEOUT",
    0x05: "MEMORY_LOW",
}


def escape(data):
    return data.replace(bytes([FESC]), bytes([FESC, TFESC])).replace(bytes([FEND]), bytes([FESC, TFEND]))


def unescape(data):
    return data.replace(bytes([FESC, TFEND]), bytes([FEND])).replace(bytes([FESC, TFESC]), bytes([FESC]))


def frame(command, payload=b""):
    return bytes([FEND, command]) + escape(payload) + bytes([FEND])


def u32(value):
    return int(value).to_bytes(4, "big")


def configure(port, freq, bw, txp, sf, cr):
    for command, payload in (
        (CMD_FREQUENCY, u32(freq)),
        (CMD_BANDWIDTH, u32(bw)),
        (CMD_TXPOWER, bytes([txp])),
        (CMD_SF, bytes([sf])),
        (CMD_CR, bytes([cr])),
    ):
        port.write(frame(command, payload))
        port.flush()
        time.sleep(0.05)


def read_frames(label, port, stop, seen, expected):
    buf = bytearray()
    in_frame = False

    while not stop.is_set():
        data = port.read(1)
        if not data:
            continue

        b = data[0]
        if b == FEND:
            if in_frame and buf:
                command = buf[0]
                payload = unescape(bytes(buf[1:]))
                if command == CMD_DATA:
                    print(f"{label} DATA {payload!r}", flush=True)
                    if payload == expected:
                        seen.set()
                elif command == CMD_SEL_INT and payload:
                    print(f"{label} IFACE {payload[0]}", flush=True)
                elif command == CMD_RADIO_STATE and payload:
                    print(f"{label} RADIO_STATE {payload[0]}", flush=True)
                elif command == CMD_STAT_RX and payload:
                    print(f"{label} RX STAT {payload[0]}", flush=True)
                elif command == CMD_STAT_TX and payload:
                    print(f"{label} TX STAT {payload[0]}", flush=True)
                elif command == CMD_ERROR and payload:
                    print(f"{label} ERROR {payload[0]} {ERRORS.get(payload[0], 'UNKNOWN')}", flush=True)
            buf.clear()
            in_frame = True
        elif in_frame:
            buf.append(b)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tx", required=True)
    parser.add_argument("--rx", required=True)
    parser.add_argument("--message", default="eora-s3-kiss-test")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--freq", type=int, default=915000000)
    parser.add_argument("--bw", type=int, default=125000)
    parser.add_argument("--txp", type=int, default=10)
    parser.add_argument("--sf", type=int, default=7)
    parser.add_argument("--cr", type=int, default=5)
    args = parser.parse_args()

    expected = args.message.encode()
    stop = threading.Event()
    seen = threading.Event()

    with serial.Serial(args.rx, 115200, timeout=0.1) as rx, serial.Serial(args.tx, 115200, timeout=0.1) as tx:
        configure(rx, args.freq, args.bw, args.txp, args.sf, args.cr)
        configure(tx, args.freq, args.bw, args.txp, args.sf, args.cr)
        rx.write(frame(CMD_RADIO_STATE, bytes([RADIO_STATE_ON])))
        tx.write(frame(CMD_RADIO_STATE, bytes([RADIO_STATE_ON])))
        rx.flush()
        tx.flush()

        rx_reader = threading.Thread(target=read_frames, args=("RX", rx, stop, seen, expected), daemon=True)
        tx_reader = threading.Thread(target=read_frames, args=("TX", tx, stop, threading.Event(), expected), daemon=True)
        rx_reader.start()
        tx_reader.start()
        time.sleep(0.5)

        print(f"TX DATA {expected!r}", flush=True)
        tx.write(frame(CMD_DATA, expected))
        tx.flush()

        deadline = time.time() + args.timeout
        while time.time() < deadline and not seen.is_set():
            time.sleep(0.1)

        stop.set()
        rx_reader.join(timeout=1)
        tx_reader.join(timeout=1)

    if seen.is_set():
        print("PASS: received matching payload")
        return 0

    print("FAIL: no matching payload received")
    return 1


if __name__ == "__main__":
    sys.exit(main())
