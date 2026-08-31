# daily_report.py — تقرير قائمة شغل اليوم PDF وإرساله واتساب
# الاستخدام:
#   ./venv/bin/python daily_report.py                  # تقرير PDF فقط (آخر يوم مكتمل لو الساعة قبل 4 ص)
#   ./venv/bin/python daily_report.py --date 2026-08-19
#   ./venv/bin/python daily_report.py --send           # تقرير + إرسال واتساب (حسب wa_config)
#   ./venv/bin/python daily_report.py --install-cron   # تثبيت جدولة الساعة 12 بالليل
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.database import get_connection
from sticker import _layout

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
WA_CONFIG_PATH = os.path.join(BASE_DIR, "assets", "wa_config.json")
REPORT_CONFIG_PATH = os.path.join(BASE_DIR, "assets", "report_config.json")

FONT = os.path.join(BASE_DIR, "assets", "fonts", "Tajawal-Regular.ttf")
FONT_BOLD = os.path.join(BASE_DIR, "assets", "fonts", "Tajawal-Bold.ttf")

SCALE = 200 / 150  # رفع الدقة: من 150dpi إلى 200dpi
PAGE_W, PAGE_H = 1654, 2339  # A4 عند 200dpi
MARGIN = 106
ROW_H = 72
HEADER_H = 80

COLS = [
    ("م", 70),
    ("رقم الطلب", 200),
    ("العميل", 330),
    ("الهاتف", 240),
    ("الجهاز", 160),
    ("الملاحظات", 250),
    ("وقت التسجيل", 192),
]
TOTAL_W = MARGIN * 2 + sum(w for _, w in COLS)  # 1654 — ملء الصفحة بالظبط

# الثيم الداكن
BG = (0x11, 0x13, 0x1B)
BG_ALT = (0x17, 0x1A, 0x25)
LINE = (0x2A, 0x30, 0x42)
TEXT = (0xE9, 0xEB, 0xF2)
MUTED = (0x8B, 0x94, 0xA8)
ACCENT = (0xC8, 0x94, 0x3A)


def _font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT, round(size * SCALE))


def _fit(draw, text, font, max_w):
    while draw.textlength(text, font=font, **_layout(text)) > max_w and font.size > round(20 * SCALE):
        font = ImageFont.truetype(font.path, font.size - 2)
    return font


def _truncate(draw, text, font, max_w):
    if draw.textlength(text, font=font, **_layout(text)) <= max_w:
        return text
    while text and draw.textlength(text + "\u2026", font=font, **_layout(text)) > max_w:
        text = text[:-1]
    return text + "\u2026"


def get_orders(date_str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT o.order_number, c.name AS customer_name, c.phone,
               o.device_type, o.notes, o.created_at
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        WHERE DATE(o.created_at) = ?
        ORDER BY o.order_number ASC
        """,
        (date_str,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def to_12h(ts):
    """تحويل وقت 24 ساعة إلى 12 ساعة مع ص/م (مثال: 14:32:57 -> 2:32:57 م)."""
    h, m, s = [int(x) for x in ts.split(":")]
    suffix = "ص" if h < 12 else "م"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d}:{s:02d} {suffix}"


def draw_page(draw, date_str, start_y, rows, page_no, total_pages):
    f_title = _font(40, True)
    f_sub = _font(24)
    f_head = _font(22, True)
    f_cell = _font(20)

    title = "قائمة شغل اليوم"
    if page_no == 1:
        draw.text((PAGE_W - MARGIN, round(40 * SCALE)), title, font=f_title, fill=TEXT,
                  anchor="rm", **_layout(title))
        draw.text((PAGE_W // 2, round(95 * SCALE)), date_str, font=f_sub, fill=MUTED,
                  anchor="mm", **_layout(date_str))
    else:
        draw.text((PAGE_W // 2, round(24 * SCALE)), date_str, font=f_sub, fill=MUTED,
                  anchor="mm", **_layout(date_str))

    y = start_y
    x_left = MARGIN
    x_right = PAGE_W - MARGIN
    row_h = ROW_H

    draw.rectangle([x_left, y, x_right, y], fill=ACCENT)
    y += round(3 * SCALE)
    cur_x = x_left
    for name, w in COLS:
        draw.text((cur_x + w - 8, y + HEADER_H // 2), name, font=f_head,
                  fill=ACCENT, anchor="rm", **_layout(name))
        cur_x += w
    draw.rectangle([x_left, y, x_right, y + HEADER_H], outline=LINE, width=3)
    y += HEADER_H

    for idx, order in enumerate(rows):
        row_color = BG if idx % 2 == 0 else BG_ALT
        draw.rectangle([x_left, y, x_right, y + row_h], fill=row_color)
        draw.rectangle([x_left, y, x_right, y + row_h], outline=LINE, width=1)
        cells = [
            str(idx + 1),
            f"#{order['order_number']:04d}",
            order["customer_name"],
            order["phone"],
            order["device_type"],
            order["notes"] or "",
            to_12h(order["created_at"][11:19]),
        ]
        cur_x = x_left
        for (name, w), val in zip(COLS, cells):
            font = _fit(draw, _truncate(draw, val, f_cell, w - 20), f_cell, w - 20)
            draw.text((cur_x + w - 8, y + row_h // 2), val, font=font, fill=TEXT,
                      anchor="rm", **_layout(val))
            cur_x += w
        y += row_h

    draw.text((x_left, PAGE_H - MARGIN + 6), f"صفحة {page_no} من {total_pages}",
              font=f_sub, fill=MUTED, anchor="la")
    draw.text((x_right, PAGE_H - MARGIN + 6), "مركز الصيانة - نظام الكاشير",
              font=f_sub, fill=MUTED, anchor="ra")
    return y


def build_pdf(date_str, out_path):
    rows = get_orders(date_str)
    rows_per_page = max(1, (PAGE_H - MARGIN - HEADER_H - 160) // ROW_H)
    pages = [rows[i:i + rows_per_page] for i in range(0, len(rows), rows_per_page)] or [[]]

    images = []
    for pno, page_rows in enumerate(pages, 1):
        img = Image.new("RGB", (PAGE_W, PAGE_H), BG)
        draw = ImageDraw.Draw(img)
        if pno == 1:
            draw_page(draw, date_str, 200, page_rows, pno, len(pages))
        else:
            draw_page(draw, date_str, 80, page_rows, pno, len(pages))
        images.append(img)

    images[0].save(out_path, "PDF", save_all=True,
                   append_images=images[1:], resolution=200.0)
    return out_path, len(rows)


def default_date():
    now = datetime.now()
    if now.hour < 4:  # بعد منتصف الليل: اليوم اللي خلص هو اللي اتبعت
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    return now.strftime("%Y-%m-%d")


def _load_json_comments(path):
    """قراءة JSON مع دعم التعليقات // عشان الملف يكون سهل الواحد يفهمه."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = [ln for ln in f if not ln.strip().startswith("//")]
        return json.loads("\n".join(lines))
    except Exception:
        return {}


def load_wa_config():
    return _load_json_comments(WA_CONFIG_PATH)


def load_report_config():
    cfg = _load_json_comments(REPORT_CONFIG_PATH)
    # افتراضي: معطل، الوقت 23:59
    return {
        "enabled": bool(cfg.get("enabled", False)),
        "time": str(cfg.get("time", "23:59")).strip() or "23:59",
        "report_dir": str(cfg.get("report_dir", "")).strip(),
    }


def save_report_config(enabled, time_str, report_dir=""):
    os.makedirs(os.path.dirname(REPORT_CONFIG_PATH), exist_ok=True)
    data = {"enabled": bool(enabled), "time": time_str.strip(), "report_dir": report_dir.strip()}
    with open(REPORT_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def send_whatsapp(pdf_path, recipient=None, mode=None):
    cfg = load_wa_config()
    mode = mode or cfg.get("mode", "direct")
    # تجميع المستقبلين (يدعم قائمة أو نص بفواصل)
    recips = []
    if recipient not in (None, ""):
        if isinstance(recipient, (list, tuple)):
            recips = [str(r).strip() for r in recipient if str(r).strip()]
        else:
            import re
            recips = [p.strip() for p in re.split(r"[,;،\s]+", str(recipient)) if p.strip()]
    else:
        raw = cfg.get("recipient", "")
        if isinstance(raw, (list, tuple)):
            recips = [str(r).strip() for r in raw if str(r).strip()]
        elif raw:
            import re
            recips = [p.strip() for p in re.split(r"[,;،\s]+", str(raw)) if p.strip()]
    if not recips:
        print("خطأ: محدش الرقم/الاسم في assets/wa_config.json (recipient) أو بالـ --recipient")
        return False
    script = os.path.join(BASE_DIR, "wa_send.py")
    cmd = [sys.executable, script, "--file", pdf_path]
    for r in recips:
        cmd.extend(["--to", str(r)])
    if mode == "manual":
        cmd.append("--manual")
    try:
        res = subprocess.run(cmd, cwd=BASE_DIR, timeout=300)
        return res.returncode == 0
    except Exception as e:
        print("فشل الإرسال:", e)
        return False


def install_cron(time_str=None):
    """تثبيت جدولة cron حسب الوقت المحدد من لوحة الأدمن (افتراضي 00:00)."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    # لو لم يمرر وقت، اقرأه من report_config
    if not time_str:
        try:
            time_str = load_report_config().get("time", "00:00")
        except Exception:
            time_str = "00:00"
    # تحقق من الصيغة HH:MM
    try:
        hh, mm = [int(x) for x in str(time_str).strip().split(":")]
        hh = max(0, min(23, hh))
        mm = max(0, min(59, mm))
    except Exception:
        hh, mm = 0, 0
    cmd = " ".join([
        f"cd {BASE_DIR} &&",
        f"{sys.executable} {os.path.join(BASE_DIR, 'daily_report.py')} --send",
        f">> {os.path.join(REPORTS_DIR, 'cron.log')} 2>&1",
    ])
    entry = f"{mm} {hh} * * * {cmd}\n"
    try:
        crontab = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        existing = crontab.stdout if crontab.returncode == 0 else ""
    except Exception:
        existing = ""
    # احذف أي جدولة قديمة لنفس السكربت ثم أضف الجديدة (للسماح بتغيير الوقت)
    if "/daily_report.py" in existing:
        lines = [ln for ln in existing.splitlines() if "/daily_report.py" not in ln]
        existing = "\n".join(lines) + ("\n" if lines else "")
        print("تم تحديث الجدولة القديمة.")
    new = existing + entry
    try:
        subprocess.run(["crontab", "-"], input=new, text=True, check=True)
        print("اتثبتت الجدولة في crontab:")
        print(entry)
    except Exception as e:
        print(f"فشل تثبيت crontab: {e}")
        print(f"أضف يدويا هذا السطر إلى crontab -e:\n{entry}")


def main():
    ap = argparse.ArgumentParser(description="تقرير قائمة شغل اليوم PDF + واتساب")
    ap.add_argument("--date", help="اليوم بصيغة YYYY-MM-DD (الافتراضي: آخر يوم مكتمل)")
    ap.add_argument("--send", action="store_true", help="إرسال التقرير على واتساب بعد توليده")
    ap.add_argument("--recipient", help="رقم (بالكود الدولي) أو اسم عميل من قاعدة البيانات")
    ap.add_argument("--manual", action="store_true", help="فتح واتس ويب بصورة يدوية بدل الإرسال المباشر")
    ap.add_argument("--install-cron", action="store_true", help="جدولة التشغيل كل يوم الساعة 00:00")
    ap.add_argument("--out", help="مسار ملف PDF (اختياري)")
    args = ap.parse_args()

    os.makedirs(REPORTS_DIR, exist_ok=True)
    date_str = args.date or default_date()
    if args.install_cron:
        install_cron()
        return

    if args.out:
        out_path = args.out
    else:
        save_dir = (load_wa_config().get("report_dir") or "").strip() or REPORTS_DIR
        os.makedirs(save_dir, exist_ok=True)
        out_path = os.path.join(save_dir, f"_{date_str}.pdf")
    out_path, count = build_pdf(date_str, out_path)
    print(f"تم إنشاء التقرير ({count} طلب): {out_path}")

    if args.send:
        ok = send_whatsapp(out_path, args.recipient, "manual" if args.manual else None)
        print("تم إرسال التقرير ✓" if ok else "فشل الإرسال — شوف التفاصيل فوق")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()