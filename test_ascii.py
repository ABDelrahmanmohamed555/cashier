#!/usr/bin/env python3
"""Test printer with raw ASCII text via ESC commands (no raster) to isolate mirroring."""
import sys
import os

_v = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "bin", "activate_this.py")
if os.path.exists(_v):
    exec(open(_v).read(), {"__file__": _v})
elif os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv")):
    import subprocess
    venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "bin", "python3")
    if os.path.exists(venv_python) and sys.executable != venv_python:
        os.execv(venv_python, [venv_python] + sys.argv)

from printing import _send_payload

# ESC @ = initialize printer
# ESC a n = alignment: 0=left, 1=center, 2=right
# ESC ! n = font mode: bit 0=bold, 3=double height, 4=double width, 7=double both

tests = [
    ("Left aligned 'ABCD'", b"\x1b\x61\x00" + b"Left: ABCD\n"),
    ("Center aligned 'ABCD'", b"\x1b\x61\x01" + b"Center: ABCD\n"),
    ("Right aligned 'ABCD'", b"\x1b\x61\x02" + b"Right: ABCD\n"),
    ("All 26 letters", b"\x1b\x61\x01" + b"ABCDEFGHIJKLMNOPQRSTUVWXYZ\n"),
    ("Numbers", b"\x1b\x61\x01" + b"0123456789\n"),
    ("Double width", b"\x1b\x61\x01\x1b\x21\x20" + b"Double Width ABCD\n"),
    ("Double height", b"\x1b\x61\x01\x1b\x21\x10" + b"Double Height ABCD\n"),
    ("Bold", b"\x1b\x61\x01\x1b\x21\x08" + b"Bold ABCD\n"),
]

for name, data in tests:
    payload = b"\x1b\x40" + data + b"\n"
    try:
        _send_payload(payload)
        print(f"OK: {name}")
    except Exception as e:
        print(f"FAIL: {name}: {e}")

# Final form feed
_send_payload(b"\x1b\x40\x0c")
print("Done.")
