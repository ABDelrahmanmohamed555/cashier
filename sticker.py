import json
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "assets", "sticker_config.json")
FONT_PATH = os.path.join(os.path.dirname(__file__), "assets", "fonts", "Tajawal-Regular.ttf")
FONT_BOLD_PATH = os.path.join(os.path.dirname(__file__), "assets", "fonts", "Tajawal-Bold.ttf")
LOGO_PATH = os.path.join(os.path.dirname(__file__), "icon.png")
SS = 4  # supersampling: نرسم بدقة مضاعفة ونصغّر عشان الحروف تطلع ناعمة ومبكسلةش
SAFE_MARGIN_MM = 1.5  # مسافة أمان عند الأطراف عشان الحروف متخرجش برا الستيكر

_font_cache = {}
_logo_cache = {}


def _is_arabic(text):
    """هل النص فيه حروف عربية؟ (الرقم والتاريخ اللي بالانجليزي بيتطبعوا عادي)"""
    return any(
        "\u0600" <= c <= "\u06FF" or "\u0750" <= c <= "\u077F"
        or "\uFB50" <= c <= "\uFDFF" or "\uFE70" <= c <= "\uFEFF"
        for c in str(text)
    )


def _layout(text):
    """إعدادات الرسم الصحيحة للعربي: بنبعت النص العربي خام (من غير reshaper)
    وخلّي libraqm المتضمن في Pillow يشكّله ويرتبه بنفسه (direction=rtl).
    الـ reshaper القديم كان بيسبب اتجاه معكوس وفراغات بين الحروف."""
    if _is_arabic(text):
        return {"direction": "rtl", "language": "ar"}
    return {}


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def px_per_mm(cfg):
    return cfg["dpi"] / 25.4


def _get_font(size_pt, bold=False):
    key = (size_pt, bold)
    if key not in _font_cache:
        try:
            path = FONT_BOLD_PATH if bold else FONT_PATH
            font = ImageFont.truetype(path, int(size_pt * 1.33 * SS))
            _font_cache[key] = font
        except Exception:
            _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]


def _tracking_px(el, size_pt):
    """تباعد بين الحروف بالبكسل: letter_spacing_pt = 1% من حجم الخط مثلًا."""
    ls = float(el.get("letter_spacing_pt", 0) or 0)
    return ls * 1.33 * SS


def _shrink_font(draw, text, font, max_w, layout):
    """تصغير الخط تلقائياً لو النص أطول من المساحة المتاحة (عشان ميقطعش برا الستيكر)."""
    if draw.textlength(text, font=font, **layout) <= max_w:
        return font
    size = font.size
    small = font
    while size > 5 * SS:
        size -= SS
        try:
            small = ImageFont.truetype(font.path, size)
        except Exception:
            small = font
        if draw.textlength(text, font=small, **layout) <= max_w:
            return small
    return small


def _draw_fitted(draw, text, x, y, font, anchor, target_w_px, target_h_px, pmm,
                 letter_spacing=0):
    """رسم نص مضمّن جوه الستيكر: تصغير الخط لو طويل + منعه من الخروج من الأطراف."""
    safe = SAFE_MARGIN_MM * pmm
    max_w = max(1, target_w_px - 2 * safe)
    layout = _layout(text)

    font = _shrink_font(draw, text, font, max_w, layout)
    bbox = draw.textbbox((x, y), text, font=font, anchor=anchor, **layout)
    if bbox[1] < safe:
        y += safe - bbox[1]
    limit = target_h_px - safe
    if bbox[3] > limit:
        y -= bbox[3] - limit
    draw.text((x, y), text, fill="black", font=font, anchor=anchor,
              letter_spacing=letter_spacing, **layout)


def _logo_bw(path=LOGO_PATH):
    """اللوجو بالأسود والأبيض: خلفية بيضاء وشعار أسود (مع قص تلقائي للخلفية الغامقة).
    المسار بيبقى مفتاح في الكاش عشان نقدر نستخدم أكتر من لوجو."""
    if path in _logo_cache:
        return _logo_cache[path]
    try:
        logo = Image.open(path)
        if logo.mode == "RGBA":
            bg = Image.new("RGBA", logo.size, (255, 255, 255, 255))
            logo = Image.alpha_composite(bg, logo)
        logo = logo.convert("L")
        bw = logo.point(lambda p: 0 if p < 128 else 255)
        # قص للشعار نفسه (صندوق البكسلات السوداء)
        bbox = bw.getbbox()
        if bbox:
            bw = bw.crop(bbox)
        else:
            bw = bw.crop((0, 0, 1, 1))
        # لو الشعار غالبًا أسود على فاتح بعد القص، اقلب الألوان
        dark = sum(1 for b in bw.tobytes() if b < 128)
        if dark > bw.width * bw.height * 0.55:
            bw = bw.point(lambda p: 255 - p)
        _logo_cache[path] = bw
        return bw
    except Exception:
        return None


def _resolve_text(el, order_data, now_text):
    """نص العنصر (سطر نصي): dynamic بياخد القيمة من الطلب، static من الإعدادات."""
    t = el["type"]
    if t == "dynamic":
        if el["field"] == "date":
            return now_text if now_text else datetime.now().strftime("%Y/%m/%d")
        return str(order_data.get(el["field"], "") or "")
    if t == "static":
        return el["content"]
    return None


def draw_sticker(cfg, order_data=None):
    base_pmm = px_per_mm(cfg)
    scale = float(cfg.get("scale", 1.0))
    target_w = max(1, int(round(cfg["sticker_width_mm"] * scale * base_pmm)))
    target_h = max(1, int(round(cfg["sticker_height_mm"] * scale * base_pmm)))
    pmm = base_pmm * SS

    img = Image.new("RGB", (target_w * SS, target_h * SS), "white")
    draw = ImageDraw.Draw(img)

    # border (border_width_px = 0 يعني من غير فريم)
    bw = int(cfg.get("border_width_px", 2))
    if bw > 0:
        r = int(cfg["border_radius_mm"] * scale * pmm)
        draw.rounded_rectangle([2, 2, target_w * SS - 3, target_h * SS - 3],
                               radius=r, outline="black", width=bw * SS)

    if order_data is None:
        order_data = {}

    now_text = datetime.now().strftime("%Y/%m/%d")
    safe = SAFE_MARGIN_MM * pmm
    max_w = target_w * SS - 2 * safe
    lay_cfg = cfg.get("layout", {})
    auto_on = lay_cfg.get("mode", "manual") == "auto"
    gap_px = float(lay_cfg.get("gap_mm", 1.0)) * pmm
    min_fs = float(lay_cfg.get("min_font_pt", 10))

    auto_els, pinned_els = [], []
    for el in cfg["elements"]:
        text = _resolve_text(el, order_data, now_text)
        if text is None:
            pinned_els.append(el)
        elif auto_on and el.get("auto_layout", True):
            auto_els.append(el)
        else:
            pinned_els.append(el)

    def measure(factor):
        """قياس ارتفاع حبر كل سطر عند نسبة تصغير معينة (بعد تصغير العرض أولاً)."""
        out = []
        for el in auto_els:
            text = _resolve_text(el, order_data, now_text)
            if not text:
                continue
            layout = _layout(text)
            fs = max(float(el.get("font_size_pt", 10)) * factor, min_fs)
            font = _get_font(fs, bold=el.get("bold", False))
            font = _shrink_font(draw, text, font, max_w, layout)
            ls = _tracking_px(el, fs)
            bb = draw.textbbox((0, 0), text, font=font, anchor="mm",
                               **layout)
            out.append((el, text, layout, font, bb[3] - bb[1], ls, bb))
        return out

    def draw_auto_item(el, text, layout, font, ih, ls, x, anchor):
        ay = el["y_mm"] * scale * pmm
        draw.text((x, ay), text, fill="black", font=font, anchor=anchor,
                  letter_spacing=ls, **layout)

    if auto_els:
        last_ay = max(el["y_mm"] for el in auto_els) * scale * pmm
        below = [el["y_mm"] * scale * pmm for el in pinned_els if el["y_mm"] * scale * pmm > last_ay]
        limit_px = min(below) - gap_px if below else target_h * SS - safe
        factor = 1.0
        for _ in range(25):
            items = measure(factor)
            n = len(items)
            if n == 0:
                break
            s = 1.0
            for i in range(n):
                ih = items[i][4]
                ay = items[i][0]["y_mm"] * scale * pmm
                if i == 0 and ih > 0:
                    s = min(s, (ay - safe) / (ih / 2))
                if i == n - 1 and ih > 0:
                    s = min(s, (limit_px - ay) / (ih / 2))
                if i < n - 1:
                    ay_next = items[i + 1][0]["y_mm"] * scale * pmm
                    ih_next = items[i + 1][4]
                    if ih + ih_next > 0:
                        s = min(s, (ay_next - ay - gap_px) / ((ih + ih_next) / 2))
            if s >= 1.0:
                break
            new_factor = factor * max(0.3, s)
            if new_factor >= factor:
                break
            factor = new_factor
        items = measure(factor)

        cx = target_w * SS // 2
        for el, text, layout, font, ih, ls, bb in items:
            if el.get("align") == "center":
                draw_auto_item(el, text, layout, font, ih, ls, cx, "mm")
            else:
                draw_auto_item(el, text, layout, font, ih, ls,
                               el["x_mm"] * scale * pmm, "rm")

    # حساب حجم خط السعر (أكبر من التاريخ بـ 5%)
    _date_fs = None
    for _e in cfg.get("elements", []):
        if _e.get("id") == "date":
            _date_fs = float(_e.get("font_size_pt", 19))
            break

    for el in pinned_els:
        t = el["type"]
        x = int(el["x_mm"] * scale * pmm)
        y = int(el["y_mm"] * scale * pmm)
        fs = int(el.get("font_size_pt", 10) * scale)
        # فرض حجم السعر = تاريخ +5%
        if el.get("id") == "price" and _date_fs is not None:
            fs = int(round(_date_fs * 1.05 * scale))
        font = _get_font(fs, bold=el.get("bold", False))
        align = el.get("align", "right")
        target_w_px = target_w * SS
        target_h_px = target_h * SS

        if t == "field_with_label":
            label = el["label_text"]
            raw_val = order_data.get(el["field"], "") if el["field"] else ""
            # تنسيق السعر: إضافة "جنيه" لو غير موجود
            if el.get("id") == "price" and raw_val:
                _rv = str(raw_val).strip()
                if "جنيه" not in _rv and "ج.م" not in _rv and "EGP" not in _rv:
                    raw_val = f"{_rv} جنيه"
                else:
                    raw_val = _rv
            full_text = f"{label} {raw_val}" if raw_val else label
            if full_text:
                if align == "center":
                    cx = target_w_px // 2
                    _draw_fitted(draw, full_text, cx, y, font, "mm",
                                 target_w_px, target_h_px, pmm,
                                 letter_spacing=_tracking_px(el, fs))
                else:
                    _draw_fitted(draw, full_text, x, y, font, "rm",
                                 target_w_px, target_h_px, pmm,
                                 letter_spacing=_tracking_px(el, fs))
            if (not raw_val or el.get("underline_with_value", False)) and el.get("underline", False):
                ul_px = int(el["underline_length_mm"] * scale * pmm)
                line_y = y + int(fs * 1.33 * SS * 0.5)
                if align == "center":
                    cx = target_w_px // 2
                    draw.line([(cx - ul_px // 2, line_y),
                               (cx + ul_px // 2, line_y)], fill="black", width=SS)
                else:
                    label_w = draw.textlength(label, font=font, **_layout(label)) if label else 0
                    gap = 6 * SS if label else 0  # لو مفيش كلمة، الخط ينتهي عند x مباشرة
                    draw.line([(x - label_w - gap - ul_px, line_y),
                               (x - label_w - gap, line_y)], fill="black", width=SS)

        elif t == "image":
            logo = _logo_bw(el.get("path", LOGO_PATH))
            if logo is None:
                continue
            sz = int(el.get("size_mm", 8) * scale * pmm)
            logo_resized = logo.resize((sz, sz), Image.LANCZOS)
            if el.get("align") == "center":
                x = (target_w_px - sz) // 2  # توسيط أفقى على الستيكر
            img.paste(logo_resized, (x, y))

        elif t in ("static", "dynamic"):
            text = _resolve_text(el, order_data, now_text)
            if not text:
                continue
            # تنسيق السعر للديناميك أيضا
            if el.get("id") == "price" and text:
                _rv = str(text).strip()
                if "جنيه" not in _rv and "ج.م" not in _rv and "EGP" not in _rv:
                    text = f"{_rv} جنيه"
            ls = _tracking_px(el, fs)
            if align == "center":
                cx = target_w_px // 2
                _draw_fitted(draw, text, cx, y, font, "mm",
                             target_w_px, target_h_px, pmm, letter_spacing=ls)
            else:
                _draw_fitted(draw, text, x, y, font, "rm",
                             target_w_px, target_h_px, pmm, letter_spacing=ls)

    return img.resize((target_w, target_h), Image.LANCZOS)


def generate_preview(order_data=None):
    cfg = load_config()
    img = draw_sticker(cfg, order_data)
    out = os.path.join(os.path.dirname(__file__), "assets", "sticker_preview.png")
    img.save(out)
    return out


if __name__ == "__main__":
    sample = {"order_number": "0012", "customer_name": "أحمد علي", "phone": "01012345678"}
    path = generate_preview(sample)
    print(f"Saved: {path}")