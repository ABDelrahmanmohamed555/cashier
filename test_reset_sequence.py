#!/usr/bin/env python3
"""Test if printer state (upside-down, reverse, page mode) causes mirroring.
Send full reset sequence, then print raster ABCD + black bar."""
import sys
import os

_v = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "bin", "activate_this.py")
if os.path.exists(_v):
    exec(open(_v).read(), {"__file__": _v})
elif os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv")):
    venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "bin", "python3")
    if os.path.exists(venv_python) and sys.executable != venv_python:
        os.execv(venv_python, [venv_python] + sys.argv)

from PIL import Image, ImageDraw, ImageFont
from printing import _send_payload

FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts", "Tajawal-Regular.ttf")
W = 384

def make_test_image():
    img = Image.new("L", (W, 48), 255)
    d = ImageDraw.Draw(img)
    d.rectangle([10, 0, 30, 48], fill=0)  # black bar LEFT
    font = ImageFont.truetype(FONT_PATH, 32)
    d.text((W - 40, 8), "ABCD", fill=0, font=font)
    return img

def raster_lsb(img):
    wb = (W + 7) // 8
    data = bytearray()
    for y in range(img.height):
        for bx in range(wb):
            byte = 0
            for bit in range(8):
                x = bx * 8 + bit
                if x < W and img.getpixel((x, y)) == 0:
                    byte |= 1 << bit
            data.append(byte)
    return wb, img.height, bytes(data)

def raster_msb(img):
    wb = (W + 7) // 8
    data = bytearray()
    for y in range(img.height):
        for bx in range(wb):
            byte = 0
            for bit in range(8):
                x = bx * 8 + bit
                if x < W and img.getpixel((x, y)) == 0:
                    byte |= 1 << (7 - bit)
            data.append(byte)
    return wb, img.height, bytes(data)

img = make_test_image()

# Full reset sequence
reset = (
    b"\x1b\x40"       # ESC @ - initialize
    + b"\x1b\x7b\x00" # ESC { 0 - upside-down OFF
    + b"\x1d\x42\x00" # GS B 0 - reverse print OFF
    + b"\x1b\x52\x00" # ESC R 0 - select国际字符集 (international charset)
    + b"\x1b\x35\x00" # ESC 5 - cancel any scanner mode
    + b"\x1b\x4d\x00" # ESC M 0 - normal character spacing
)

tests = [
    ("Test 1: LSB + GS v 0 (full reset)", reset, "gs_v0_lsb", "gs_v0"),
    ("Test 2: MSB + GS v 0 (full reset)", reset, "gs_v0_msb", "gs_v0"),
    ("Test 3: LSB + ESC * 0 (full reset)", reset, "esc_star0_lsb", "esc_star0"),
    ("Test 4: MSB + ESC * 0 (full reset)", reset, "esc_star0_msb", "esc_star0"),
]

for name, prefix, tag, cmd in tests:
    if "lsb" in tag:
        wb, h, data = raster_lsb(img)
    else:
        wb, h, data = raster_msb(img)

    payload = prefix
    payload += f"\n{name}\n\n".encode()

    if cmd == "gs_v0":
        payload += b"\x1d\x76\x30\x00"
        payload += bytes([wb & 0xFF, (wb >> 8) & 0xFF])
        payload += bytes([h & 0xFF, (h >> 8) & 0xFF])
        payload += data
        payload += b"\x1d\x56\x41"
    else:
        for y in range(h):
            row = data[y * wb:(y + 1) * wb]
            payload += b"\x1b*" + bytes([0, wb & 0xFF, (wb >> 8) & 0xFF]) + row

    try:
        _send_payload(payload)
        print(f"OK: {name}")
    except Exception as e:
        print(f"FAIL: {name}: {e}")

# Also test if upside-down mode itself causes mirroring by printing text in upside-down mode
payload = b"\x1b\x40"  # init
payload += b"\nTest 5: ESC { 1 (upside-down ON)\n"
payload += b"\x1b\x7b\x01"  # ESC { 1 - upside-down ON
payload += b"This text should be upside down\n"
payload += b"\x1b\x7b\x00"  # ESC { 0 - upside-down OFF
payload += b"\nTest 6: Normal (reset)\n"
payload += b"This should be normal\n"
payload += b"\x0c"
try:
    _send_payload(payload)
    print("OK: Test 5+6 (upside-down test)")
except Exception as e:
    print(f"FAIL: Test 5+6: {e}")

print("\nDone. Please check:")
print("  - Test 1-4: Black bar should be on LEFT, ABCD left-to-right")
print("  - Test 5: Text should be upside-down (if printer supports it)")
print("  - Test 6: Text should be normal")
