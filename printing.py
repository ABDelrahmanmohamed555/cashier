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


def _image_to_raster(img, mirror=False, rotate180=False):
    """تحويل صورة PIL لبيانات ESC/POS raster (GS v 0) بالترتيب القياسي:
    كل بايت = 8 نقط أفقية، وأقصى نقطة على الشمال هي bit 7 (MSB-first).
    مفيش تقليص للعرض هنا — الصورة لازم تكون جاهزة بالعرض النهائي بالنقط.
    mirror: قلب أفقي (مرآة) — rotate180: دوران 180° (مقلوب تماماً)."""
    # طبّق التحويل الهندسي قبل التحويل النقطي — أدق وأسرع من الحساب اليدوي
    if rotate180:
        img = img.transpose(Image.ROTATE_180)
    elif mirror:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    img = img.convert("L")
    # تحسين جودة الطباعة شوية: autocontrast مع عتبة 135 (كان 130) يعطي أسود أغمق وحواف أوضح للباركود
    img = ImageOps.autocontrast(img, cutoff=0.5)
    img = img.point(lambda p: 255 if p >= 135 else 0)

    w = img.width
    width_bytes = (w + 7) // 8
    pixels = img.load()
    data = bytearray()
    for y in range(img.height):
        for bx in range(width_bytes):
            byte = 0
            for bit in range(8):
                x0 = bx * 8 + bit
                x = x0
                if x < w and pixels[x, y] == 0:
                    byte |= 1 << (7 - bit)
            data.append(byte)
    return width_bytes, img.height, bytes(data)


def _build_escpos(image, mirror=False, rotate180=False):
    """بناء أمر GS v 0 (raster) — الوضع القياسي لكل طابعات ESC/POS.
    نبدأ بـ ESC @ (تهيئة) عشان أي وضع شغال عند الطابعة يرجع لطبيعته."""
    wb, h, data = _image_to_raster(image, mirror=mirror, rotate180=rotate180)
    cmd = b"\x1b\x40"  # تهيئة
    cmd += b"\x1d\x76\x30\x00"  # GS v 0
    cmd += bytes([wb & 0xFF, (wb >> 8) & 0xFF])
    cmd += bytes([h & 0xFF, (h >> 8) & 0xFF])
    cmd += data
    return cmd


def _build_escpos_text(image, width_dots=None, mirror=False, rotate180=False):
    """للتوافق مع الكود القديم: بتبعت الصورة بأمر GS v 0 (بعد إصلاح الترتيب)."""
    return _build_escpos(image, mirror=mirror, rotate180=rotate180)


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


def _build_tspl(img, label_w_mm, label_h_mm, gap_mm, copies=1, sensor_align=True, mirror=False, rotate180=False, direction=None):
    """بناء أوامر TSPL (وضع Label Mode / الملصقات).
    الطابعة في وضع Label بتفهم لغة TSPL مش ESC/POS.
    sensor_align = تفعيل أمر GAPDETECT ON: الطابعة بتسحب الورق وتقف
    بحساس الفجوة عند أول الستيكر قبل كل طباعة (تظبيط تلقائي).
    mirror/rotate180: قلب/دوران الصورة قبل الإرسال — مهم لو الطباعة طالعة مقلوبة.
    direction: 0=عادي 1=مقلوب 180° (يقلب الستيكر نفسه مع المحتوى) — لإصلاح أن الستيكر نفسه مقلوب بينما الحروف سليمة.
    ملحوظة: طابعات TSPL بتطبع البت = 1 أبيض — فبنعكس البايتات (XOR 0xFF)
    عشان الخلفية تطلع بيضا والكتابة سودا (زي ما حصل في وضع receipt)."""
    wb, h, data = _image_to_raster(img, mirror=mirror, rotate180=rotate180)
    data = bytes(b ^ 0xFF for b in data)
    cmd = b""
    cmd += f"SIZE {label_w_mm:g} mm, {label_h_mm:g} mm\r\n".encode()
    cmd += f"GAP {gap_mm:g} mm, 0\r\n".encode()
    if sensor_align:
        cmd += b"GAPDETECT ON\r\n"
    # إصلاح دائم: الستيكر نفسه مقلوب بينما الحروف سليمة — نستخدم DIRECTION لقلب اتجاه الطباعة
    # بدون تدوير الصورة (rotate180=False) + DIRECTION 1 يعطي الحروف سليمة والستيكر في مكانه الصحيح
    if direction is not None:
        try:
            cmd += f"DIRECTION {int(direction)}\r\n".encode()
        except Exception:
            pass
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
    # --- إصلاح دائم للطباعة المقلوبة ---
    # الحالة الحالية: الحروف سليمة لكن الستيكر نفسه مقلوب 180° — لذلك لا ندوّر الصورة (rotate=False)
    # بل نستخدم أمر TSPL DIRECTION 1 لقلب اتجاه الستيكر نفسه مع الحفاظ على الحروف.
    _cfg_mirror = bool(pcfg.get("mirror", False))
    _cfg_rotate = bool(pcfg.get("rotate180", False) or pcfg.get("rotate_180", False))
    mode = pcfg.get("printer_mode", "receipt")
    if mode == "label":
        mirror = False
        rotate180 = False  # الحروف سليمة — لا تدوير
        direction = 1  # اقلب الستيكر نفسه (قفل دائم)
    else:
        mirror = _cfg_mirror
        rotate180 = _cfg_rotate
        direction = pcfg.get("direction", None)

    img = draw_sticker(cfg, order_data)

    if mode == "label":
        return _build_tspl(img, label_w_mm_t, label_h_mm_t, gap_mm,
                           copies=max(1, int(copies)),
                           sensor_align=bool(pcfg.get("sensor_align", True)),
                           mirror=mirror, rotate180=rotate180, direction=direction)

    # ---------- ESC/POS ----------
    if label_w > head_dots:
        ratio = head_dots / img.width
        img = img.resize((head_dots, max(1, round(img.height * ratio))), Image.LANCZOS)
    elif img.width < head_dots:
        side = (head_dots - img.width) // 2
        padded = Image.new("RGB", (head_dots, img.height), "white")
        padded.paste(img, (side, 0))
        img = padded

    payload = _build_escpos(img, mirror=mirror, rotate180=rotate180)

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
    """طباعة الستيكر حسب وضع الطابعة المحدد في الإعدادات (printer_mode).
    في وضع الملصقات ومع نسخ متعددة: كل نسخة في وظيفة منفصلة
    وبينها تأخير (inter_copy_delay_ms) حتى يلحق حساس الفجوة
    يظبط أول الستيكر قبل النسخة التالية — أول واحدة كانت
    مظبوطة والباقي لا بسبب الطباعة المتتابعة بدون انتظار."""
    cfg = load_config()
    pcfg = _load_print_cfg()
    copies = max(1, int(copies))
    mode = pcfg.get("printer_mode", "receipt")
    try:
        if mode == "label" and copies > 1:
            delay = float(pcfg.get("inter_copy_delay_ms", 3500)) / 1000.0
            payload_one = _build_payload(cfg, order_data, copies=1)
            for i in range(copies):
                _send_payload(payload_one)
                if i < copies - 1:
                    time.sleep(delay)
        else:
            payload = _build_payload(cfg, order_data, copies=copies)
            _send_payload(payload)
    except PermissionError:
        return False, "صلاحية الوصول للطابعة مرفوضة (شوف udev rules)"
    except OSError as e:
        return False, f"فشل الطباعة: {e}"

    return True, "تمت الطباعة"


def print_pil_image(pil_img, copies=1):
    """طباعة صورة PIL مباشرة متناسبة مع مقاس الستيكر (للمنتجات والباركود)."""
    cfg = load_config()
    pcfg = _load_print_cfg()
    copies = max(1, int(copies))
    mode = pcfg.get("printer_mode", "receipt")

    # حضّر الصورة لتناسب الستيكر
    dpi = float(cfg.get("dpi", 203))
    ppm = dpi / 25.4
    scale = float(cfg.get("scale", 1.0))
    label_w_mm = float(cfg["sticker_width_mm"]) * scale
    label_h_mm = float(cfg["sticker_height_mm"]) * scale
    label_w_px = max(1, int(round(label_w_mm * ppm)))
    label_h_px = max(1, int(round(label_h_mm * ppm)))

    # صغّر أو كبّر الصورة لتناسب الستيكر مع الحفاظ على النسبة
    img = pil_img.convert("RGB")
    # خلفية بيضاء
    canvas = Image.new("RGB", (label_w_px, label_h_px), "white")
    # حساب التحجيم مع هامش 2مم
    margin_px = int(2 * ppm)
    avail_w = label_w_px - 2 * margin_px
    avail_h = label_h_px - 2 * margin_px
    ratio = min(avail_w / img.width, avail_h / img.height, 1.0)
    new_w = max(1, int(img.width * ratio))
    new_h = max(1, int(img.height * ratio))
    if ratio < 1.0:
        img = img.resize((new_w, new_h), Image.LANCZOS)
    # توسيط
    x = (label_w_px - img.width) // 2
    y = (label_h_px - img.height) // 2
    canvas.paste(img, (x, y))

    # ابنِ الحمولة حسب وضع الطابعة (يستخدم نفس إصلاح DIRECTION)
    try:
        if mode == "label":
            # استخدم نفس المنطق المقفل للـ label
            payload = _build_tspl(canvas, label_w_mm, label_h_mm, float(pcfg.get("label_gap_mm", 2)),
                                   copies=copies, sensor_align=bool(pcfg.get("sensor_align", True)),
                                   mirror=False, rotate180=False, direction=1)
            # إرسال مباشر
            if copies > 1:
                delay = float(pcfg.get("inter_copy_delay_ms", 3500)) / 1000.0
                # _build_tspl يبني لنسخ متعددة مرة واحدة، لكن نرسل واحدة واحدة للتأكد (تأخير 3.5 ثانية بين كل ستيكر)
                for i in range(copies):
                    _send_payload(payload if copies == 1 else _build_tspl(canvas, label_w_mm, label_h_mm, float(pcfg.get("label_gap_mm", 2)), copies=1, sensor_align=True, mirror=False, rotate180=False, direction=1))
                    if i < copies - 1:
                        time.sleep(delay)
                return True, "تمت الطباعة"
            _send_payload(payload)
        else:
            # receipt
            head_dots = int(pcfg.get("printer_width_dots", 384))
            # نفس منطق receipt في _build_payload
            if canvas.width > head_dots:
                ratio = head_dots / canvas.width
                canvas = canvas.resize((head_dots, max(1, round(canvas.height * ratio))), Image.LANCZOS)
            elif canvas.width < head_dots:
                side = (head_dots - canvas.width) // 2
                padded = Image.new("RGB", (head_dots, canvas.height), "white")
                padded.paste(canvas, (side, 0))
                canvas = padded
            payload = _build_escpos(canvas, mirror=False, rotate180=False)
            gap_mm = float(pcfg.get("label_gap_mm", 2))
            gap_dots = int(round(gap_mm * ppm))
            label_h = max(1, int(round(label_h_mm * ppm)))
            remaining = max(0, label_h - canvas.height)
            align_mode = pcfg.get("align_mode", "auto")
            if align_mode == "auto":
                offset_dots = max(0, int(pcfg.get("align_offset_dots", 8)))
                payload = b"\x0c" + _feed_dots(offset_dots) + payload
                payload += _feed_dots(remaining + gap_dots)
            else:
                payload += _feed_dots(remaining + gap_dots)
            _send_payload(payload * copies)
    except PermissionError:
        return False, "صلاحية الوصول للطابعة مرفوضة"
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


def feed_label(count=1):
    """دفع ورقة ستيكرات (بدون طباعة) — بديل لزرار FEED على الطابعة."""
    pcfg = _load_print_cfg()
    w = float(pcfg.get("sticker_width_mm", 40))
    h = float(pcfg.get("sticker_height_mm", 29.4))
    gap = float(pcfg.get("label_gap_mm", 1))
    cmd = (
        f"SIZE {w} mm,{h} mm\r\n"
        f"GAP {gap} mm,0\r\n"
        "CLS\r\n"
        f"PRINT {max(1, int(count))}\r\n"
    ).encode()
    _send_payload(cmd)


def pause_print():
    """إيقاف مؤقت أثناء الطباعة — بديل لزرار PAUSE على الطابعة.
    ملحوظة: مش بيشتغل غير أثناء أمر طباعة شغال."""
    _send_payload(b"PAUSE\r\n")