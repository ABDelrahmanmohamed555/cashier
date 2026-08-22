# printing.py
import glob
import json
import os
import threading
import time
from PIL import Image, ImageOps

from config import BASE_DIR
from sticker import load_config, draw_sticker

_PRINTER_GLOB = "/dev/usb/lp*"
_CONFIG_PATH = os.path.join(BASE_DIR, "assets", "sticker_config.json")


def find_printer():
    """إرجاع أول جهاز طابعة USB متاح (مثل /dev/usb/lp0) أو None."""
    devices = sorted(glob.glob(_PRINTER_GLOB))
    return devices[0] if devices else None


def printer_available():
    return find_printer() is not None


def _load_print_cfg():
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg.get("print", {})


def _image_to_raster(img, mirror=False):
    """تحويل صورة PIL لبيانات ESC/POS raster (GS v 0) بالترتيب القياسي:
    كل بايت = 8 نقط أفقية، وأقصى نقطة على الشمال هي bit 7 (MSB-first).
    مفيش تقليص للعرض هنا — الصورة لازم تكون جاهزة بالعرض النهائي بالنقط."""
    img = img.convert("L")
    img = ImageOps.autocontrast(img)
    img = img.point(lambda p: 255 if p >= 140 else 0)

    w = img.width
    width_bytes = (w + 7) // 8
    pixels = img.load()
    data = bytearray()
    for y in range(img.height):
        for bx in range(width_bytes):
            byte = 0
            for bit in range(8):
                x0 = bx * 8 + bit
                x = x0 if not mirror else w - 1 - x0
                if x < w and pixels[x, y] == 0:
                    byte |= 1 << (7 - bit)
            data.append(byte)
    return width_bytes, img.height, bytes(data)


def _build_escpos(image, mirror=False):
    """بناء أمر GS v 0 (raster) — الوضع القياسي لكل طابعات ESC/POS.
    نبدأ بـ ESC @ (تهيئة) عشان أي وضع شغال عند الطابعة يرجع لطبيعته."""
    wb, h, data = _image_to_raster(image, mirror=mirror)
    cmd = b"\x1b\x40"  # تهيئة
    cmd += b"\x1d\x76\x30\x00"  # GS v 0
    cmd += bytes([wb & 0xFF, (wb >> 8) & 0xFF])
    cmd += bytes([h & 0xFF, (h >> 8) & 0xFF])
    cmd += data
    return cmd


def _build_escpos_text(image, width_dots=None, mirror=False):
    """للتوافق مع الكود القديم: بتبعت الصورة بأمر GS v 0 (بعد إصلاح الترتيب)."""
    return _build_escpos(image, mirror=mirror)


def _feed_dots(n_dots):
    """تغذية ورق بعدد نقط بالظبط (ESC J) — مقسمة لدفعات لأن الأمر بيقبل حتى 255."""
    n = max(0, int(n_dots))
    cmd = b""
    while n > 0:
        chunk = min(255, n)
        cmd += b"\x1b\x4a" + bytes([chunk])
        n -= chunk
    return cmd


def _wait_for_printer(timeout=20):
    """انتظار الطابعة لحد ما تظهر (لأن الطابعات الصينية بتقطع وترجع تلقائياً)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        device = find_printer()
        if device:
            return device
        time.sleep(0.3)
    return None


def _send_payload(payload):
    """إرسال البيانات للطابعة عبر الناقل المحدد في الإعدادات:
    usb = كتابة مباشرة على /dev/usb/lp0 — tcp = طابعة شبكة (منفذ 9100).
    مع إعادة محاولة سريعة لأن الطابعات الصينية (STM32) بتعمل
    USB disconnect كل ثواني — لازم نكتبها في نافذة الاتصال القصيرة."""
    pcfg = _load_print_cfg()
    transport = pcfg.get("transport", "usb")
    if transport == "tcp":
        import socket
        host = pcfg.get("printer_host", "192.168.1.100")
        port = int(pcfg.get("printer_port", 9100))
        with socket.create_connection((host, port), timeout=5) as s:
            s.sendall(payload)
        return
    max_attempts = int(pcfg.get("usb_retries", 20))
    last_err = None
    for attempt in range(max_attempts):
        device = _wait_for_printer(timeout=3)
        if not device:
            time.sleep(1.0)
            continue
        try:
            with open(device, "wb", buffering=0) as f:
                f.write(payload)
                f.flush()
            return
        except OSError as e:
            last_err = e
            time.sleep(0.3)
    raise last_err


def _build_tspl(img, label_w_mm, label_h_mm, gap_mm, copies=1, sensor_align=True):
    """بناء أوامر TSPL (وضع Label Mode / الملصقات).
    الطابعة في وضع Label بتفهم لغة TSPL مش ESC/POS.
    sensor_align = تفعيل أمر GAPDETECT ON: الطابعة بتسحب الورق وتقف
    بحساس الفجوة عند أول الستيكر قبل كل طباعة (تظبيط تلقائي).
    ملحوظة: طابعات TSPL بتطبع البت = 1 أبيض — فبنعكس البايتات (XOR 0xFF)
    عشان الخلفية تطلع بيضا والكتابة سودا (زي ما حصل في وضع receipt)."""
    wb, h, data = _image_to_raster(img)
    data = bytes(b ^ 0xFF for b in data)
    cmd = b""
    cmd += f"SIZE {label_w_mm:g} mm, {label_h_mm:g} mm\r\n".encode()
    cmd += f"GAP {gap_mm:g} mm, 0\r\n".encode()
    if sensor_align:
        cmd += b"GAPDETECT ON\r\n"
    cmd += b"CLS\r\n"
    cmd += f"BITMAP 0,0,{wb},{h},1,".encode()
    cmd += data
    cmd += b"\r\n"
    cmd += f"PRINT {copies}\r\n".encode()
    return cmd


def _build_payload(cfg, order_data=None, copies=1):
    """بناء الحمولة الكاملة اللي هتتبعت للطابعة حسب وضع التشغيل:
    - printer_mode=label  → أوامر TSPL (الطابعة في وضع الملصقات)
    - printer_mode=receipt → أوامر ESC/POS (وضع الإيصالات)
    copies = عدد نسخ الطباعة (افتراضي 1)"""
    pcfg = _load_print_cfg()

    dpi = float(cfg.get("dpi", 203))
    ppm = dpi / 25.4
    scale = float(cfg.get("scale", 1.0))
    head_dots = int(pcfg.get("printer_width_dots", 384))

    label_w_mm_t = float(cfg["sticker_width_mm"]) * scale
    label_h_mm_t = float(cfg["sticker_height_mm"]) * scale
    label_w = max(1, int(round(label_w_mm_t * ppm)))
    label_h = max(1, int(round(label_h_mm_t * ppm)))
    gap_mm = float(pcfg.get("label_gap_mm", 2))
    gap_dots = int(round(gap_mm * ppm))
    mirror = bool(pcfg.get("mirror", False))
    mode = pcfg.get("printer_mode", "receipt")

    img = draw_sticker(cfg, order_data)

    if mode == "label":
        return _build_tspl(img, label_w_mm_t, label_h_mm_t, gap_mm,
                           copies=max(1, int(copies)),
                           sensor_align=bool(pcfg.get("sensor_align", True)))

    # ---------- ESC/POS ----------
    if label_w > head_dots:
        ratio = head_dots / img.width
        img = img.resize((head_dots, max(1, round(img.height * ratio))), Image.LANCZOS)
    elif img.width < head_dots:
        side = (head_dots - img.width) // 2
        padded = Image.new("RGB", (head_dots, img.height), "white")
        padded.paste(img, (side, 0))
        img = padded

    payload = _build_escpos(img, mirror=mirror)

    align_mode = pcfg.get("align_mode", "auto")
    if align_mode == "auto":
        offset_dots = max(0, int(pcfg.get("align_offset_dots", 8)))
        remaining = max(0, label_h - img.height)
        # 1) FF => الطابعة تسحب الستيكر وتقف عند أوله بحساس الفجوة
        # 2) هامش علوي صغير لو محدد
        # 3) نطبع المحتوى
        # 4) نطعم الباقي (ارتفاع - صورة) + الفجوة => الستيكر يخرج كامل واللي بعده يبدأ صح
        payload = b"\x0c" + _feed_dots(offset_dots) + payload
        payload += _feed_dots(remaining + gap_dots)
    else:
        remaining = max(0, label_h - img.height)
        payload += _feed_dots(remaining + gap_dots)

    return payload * max(1, int(copies))


def print_sticker(order_data=None, copies=1):
    """طباعة الستيكر حسب وضع الطابعة المحدد في الإعدادات (printer_mode)."""
    cfg = load_config()
    try:
        payload = _build_payload(cfg, order_data, copies=copies)
        _send_payload(payload)
    except PermissionError:
        return False, "صلاحية الوصول للطابعة مرفوضة (شوف udev rules)"
    except OSError as e:
        return False, f"فشل الطباعة: {e}"

    return True, "تمت الطباعة"


def print_sticker_async(order_data=None, callback=None, copies=1):
    """طباعة في Thread عشان الواجهة متتجمّدش."""
    def worker():
        ok, msg = print_sticker(order_data, copies=copies)
        if callback:
            callback(ok, msg)

    threading.Thread(target=worker, daemon=True).start()