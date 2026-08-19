#!/usr/bin/env python3
"""Test different raster bit orderings to find the correct one for XP-233B."""
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

from PIL import Image, ImageDraw, ImageFont
from printing import _send_payload

FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts", "Tajawal-Regular.ttf")
W = 384  # 58mm paper at 203 DPI

def make_pattern(mode):
    """Create a 48-pixel-tall image with text 'ABCD' and a black bar on the LEFT side.
    This is asymmetric, so mirroring will be obvious."""
    img = Image.new("L", (W, 48), 255)
    d = ImageDraw.Draw(img)
    
    # Black bar on LEFT (x=10..30) — should print on left if correct, right if mirrored
    d.rectangle([10, 0, 30, 48], fill=0)
    
    # Text ABCD
    font = ImageFont.truetype(FONT_PATH, 32)
    d.text((W - 40, 8), "ABCD", fill=0, font=font)
    return img


def raster_lsb_first(img):
    """LSB first: bit 0 = leftmost pixel (x=0)."""
    wb = (W + 7) // 8
    data = bytearray()
    for y in range(img.height):
        for bx in range(wb):
            byte = 0
            for bit in range(8):
                x = bx * 8 + bit
                if x < W and img.getpixel((x, y)) == 0:
                    byte |= 1 << bit  # LSB first
            data.append(byte)
    return wb, img.height, bytes(data)


def raster_msb_first(img):
    """MSB first: bit 7 = leftmost pixel (x=0)."""
    wb = (W + 7) // 8
    data = bytearray()
    for y in range(img.height):
        for bx in range(wb):
            byte = 0
            for bit in range(8):
                x = bx * 8 + bit
                if x < W and img.getpixel((x, y)) == 0:
                    byte |= 1 << (7 - bit)  # MSB first
            data.append(byte)
    return wb, img.height, bytes(data)


def raster_row_reversed(img):
    """LSB first but each byte is bit-reversed (reversed within byte)."""
    wb = (W + 7) // 8
    data = bytearray()
    for y in range(img.height):
        for bx in range(wb):
            byte = 0
            for bit in range(8):
                x = bx * 8 + (7 - bit)  # read pixels right-to-left within byte
                if x < W and img.getpixel((x, y)) == 0:
                    byte |= 1 << bit
            data.append(byte)
    return wb, img.height, bytes(data)


def send_gs_v_zero(wb, h, data, label):
    """Send via GS v 0."""
    cmd = b"\x1d\x76\x30\x00"
    cmd += bytes([wb & 0xFF, (wb >> 8) & 0xFF])
    cmd += bytes([h & 0xFF, (h >> 8) & 0xFF])
    cmd += data
    cmd += b"\x1d\x56\x41"  # cut
    return cmd


def send_esc_star(wb, h, data, label):
    """Send via ESC * mode 0 (single density)."""
    cmd = b"\x1b\x40"  # init
    for y in range(h):
        row = data[y * wb:(y + 1) * wb]
        cmd += b"\x1b*" + bytes([0, wb & 0xFF, (wb >> 8) & 0xFF]) + row
    cmd += b"\x1b\x40"  # reinit
    cmd += b"\x0c"  # form feed
    return cmd


img = make_pattern("test")

# Test all 6 combinations: 3 encodings × 2 commands
encodings = [
    ("LSB first", raster_lsb_first),
    ("MSB first", raster_msb_first),
    ("Row-reversed", raster_row_reversed),
]

commands = [
    ("GS v 0", send_gs_v_zero),
    ("ESC * 0", send_esc_star),
]

test_num = 0
for enc_name, enc_fn in encodings:
    wb, h, data = enc_fn(img)
    for cmd_name, cmd_fn in commands:
        test_num += 1
        payload = b"\x1b\x40"  # init
        payload += f"#{test_num} {enc_name} + {cmd_name}\n".encode()
        payload = b"\x1b\x40"
        payload += f"Test {test_num}: {enc_name} + {cmd_name}\n\n".encode()
        payload += cmd_fn(wb, h, data, f"test_{test_num}")
        try:
            _send_payload(payload)
            print(f"Sent test {test_num}: {enc_name} + {cmd_name}")
        except Exception as e:
            print(f"FAIL test {test_num}: {e}")

print("Done. Check printout:")
print("  - Black bar should be on LEFT")
print("  - ABCD should read left-to-right")
