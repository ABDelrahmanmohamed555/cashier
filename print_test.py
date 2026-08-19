# print_test.py — طباعة أي كلمة عربي/إنجليزي كصورة عشان تجرب الطابعة
import sys
import os
from PIL import Image, ImageDraw, ImageFont
from printing import _build_escpos_text
from sticker import _layout

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "assets", "fonts", "Tajawal-Regular.ttf")


def make_word_image(text, width=384, height=120):
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)
    layout = _layout(text)
    size = 60
    while size > 10:
        font = ImageFont.truetype(FONT_PATH, size)
        _, _, tw, th = d.textbbox((0, 0), text, font=font, **layout)
        if tw <= width - 20:
            break
        size -= 2
    font = ImageFont.truetype(FONT_PATH, size)
    d.text((width - 10, 4), text, fill="black", font=font,
           anchor="rm", **layout)
    return img


def main():
    text = " ".join(sys.argv[1:]) or "روز"
    img = make_word_image(text)
    payload = _build_escpos_text(img)
    with open("/dev/usb/lp0", "wb") as f:
        f.write(payload)
    print(f"sent '{text}' as image ({len(payload)} bytes)")


if __name__ == "__main__":
    main()