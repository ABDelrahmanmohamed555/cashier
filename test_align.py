#!/usr/bin/env python3
"""اختبار محاذاة الستيكر التلقائية حسب وضع الطابعة الحالي:
- printer_mode=label  => بيبعت أوامر TSPL (الطابعة بتقدّم للستيكر وتقف عنده تلقائيًا)
- printer_mode=receipt => بيبعت أوامر ESC/POS مع FF (تغذية حساس الفجوة)

بيرسم خط أسود رفيع في أعلى 3 استيكرات متتالية:
- لو الخطوط كلها في أول 3 استيكرات متتالية => المحاذاة شغالة => تمام.
- لو زاغت => عاير الحساس يدويًا (زرار FEED مع التشغيل) أو عدّل الإعدادات.
"""
import os
import sys

_v = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "bin", "activate_this.py")
if os.path.exists(_v):
    exec(open(_v).read(), {"__file__": _v})
elif os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv")):
    import subprocess
    venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "bin", "python3")
    if os.path.exists(venv_python) and sys.executable != venv_python:
        os.execv(venv_python, [venv_python] + sys.argv)

from PIL import Image
from printing import _build_escpos, _feed_dots, _send_payload, _build_tspl
from sticker import load_config


def strip_image(width, height=8, for_label_mode=False):
    """شريط أسود بعرض كامل. لو وضع label: نرسمه أبيض على أسود لأن الـ TSPL
    بيعكس الألوان (بيطبع البت 1 أبيض) والكود بيعكسها فترجع أسود على أبيض."""
    im = Image.new("RGB", (width, height), (0, 0, 0) if for_label_mode else (255, 255, 255))
    im.paste((255, 255, 255) if for_label_mode else (0, 0, 0), (0, 0, width, height))
    return im


def main():
    cfg = load_config()
    pcfg = cfg["print"]
    mode = pcfg.get("printer_mode", "label")

    if mode == "label":
        w_mm = cfg["sticker_width_mm"]
        h_mm = cfg["sticker_height_mm"]
        gap_mm = pcfg.get("label_gap_mm", 2)
        payload = b""
        for i in range(3):
            payload += _build_tspl(
                strip_image(int(w_mm * cfg["dpi"] / 25.4), for_label_mode=True),
                w_mm, h_mm, gap_mm)
        print("وضع الطابعة: label (TSPL) — اتأكد إن الطابعة على Label Mode")
    else:
        payload = b"\x1b\x40"
        for i in range(3):
            payload += b"\x0c"  # FF: قدّم للستيكر اللي بعده عند حساس الفجوة
            payload += b"\x1b\x4a\x08"  # هامش صغير 1مم بعد الفجوة
            payload += _build_escpos(strip_image(384))
        payload += b"\x0c"
        print("وضع الطابعة: receipt (ESC/POS)")

    _send_payload(payload)
    print("تم الإرسال. اشوف 3 خطوط متتالية — كل خط لازم يبدأ في أول ستيكر جديد.")


if __name__ == "__main__":
    main()