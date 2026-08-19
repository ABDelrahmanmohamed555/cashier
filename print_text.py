#!/usr/bin/env python3
"""طباعة أي نص عربي/إنجليزي على الطابعة الحرارية.
Usage:
    python print_text.py "مرحبا بكم"
    python print_text.py "hello world"
    python print_text.py "رقم الطلب: 0012"
"""
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
from printing import _build_escpos, _send_payload, _feed_dots
from sticker import _layout

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "assets", "fonts", "Tajawal-Regular.ttf")
FONT_BOLD_PATH = os.path.join(BASE_DIR, "assets", "fonts", "Tajawal-Bold.ttf")
PRINTER_WIDTH = 384


def print_text(text, bold=False, font_size=48):
    """طباعة نص عربي/إنجليزي على الطابعة الحرارية مع ضبط تلقائي للحجم.
    العربي بيتطبع بالنص الخام + libraqm (direction=rtl) من غير reshaper
    عشان ميحصلش انعكاس أو فراغات بين الحروف."""

    layout = _layout(text)
    font_file = FONT_BOLD_PATH if bold else FONT_PATH
    font = ImageFont.truetype(font_file, font_size)

    bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=font, **layout)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    while text_w > PRINTER_WIDTH - 20 and font_size > 12:
        font_size -= 4
        font = ImageFont.truetype(font_file, font_size)
        bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=font, **layout)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

    img_h = max(60, text_h + 20)
    img = Image.new("RGB", (PRINTER_WIDTH, img_h), "white")
    d = ImageDraw.Draw(img)
    d.text((PRINTER_WIDTH - 10, (img_h - text_h) // 2), text,
           fill="black", font=font, anchor="rm", **layout)

    cmd = _build_escpos(img)
    cmd += _feed_dots(40)

    _send_payload(cmd)
    print(f"تمت الطباعة: {text}")


if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "مرحبا بكم"
    print_text(text)
