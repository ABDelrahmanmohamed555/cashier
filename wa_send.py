#!/usr/bin/env python3
# wa_send.py — إرسال ملف/نص واتساب: مباشر (headless) أو فتح واتس ويب يدوي
# الاستخدام:
#   ./venv/bin/python wa_send.py --file reports/daily_2026-08-19.pdf --to 201012345678
#   ./venv/bin/python wa_send.py --file reports/....pdf --to "اسم عميل" [--manual]
#   --to بيقبل رقم (كود دولي أو 01x مصري) أو اسم عميل موجود في قاعدة البيانات
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WA_CONFIG_PATH = os.path.join(BASE_DIR, "assets", "wa_config.json")
WA_BOT_DIR = os.path.join(BASE_DIR, "wa_bot")
NODE = shutil.which("node") or "/usr/bin/node"


def load_config():
    try:
        with open(WA_CONFIG_PATH, "r", encoding="utf-8") as f:
            lines = [ln for ln in f if not ln.strip().startswith("//")]
        return json.loads("\n".join(lines))
    except Exception:
        return {"mode": "direct", "recipient": "", "caption": "قائمة شغل اليوم"}


def db_lookup_name(name):
    """إرجاع رقم أول عميل مطابق بالاسم — أو رسالة توضيح لو في أكتر من واحد."""
    sys.path.insert(0, BASE_DIR)
    from db.database import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT name, phone FROM customers WHERE name = ? ORDER BY id DESC LIMIT 20",
        (name.strip(),),
    )
    rows = [tuple(r) for r in cur.fetchall()]
    conn.close()
    if not rows:
        return None, f"ما لقيتش عميل باسم «{name}»."
    if len(rows) > 1:
        return None, "في أكتر من عميل بنفس الاسم — استخدم الرقم مباشرة:\n" + "\n".join(f"{n} → {p}" for n, p in rows)
    return rows[0][1], None


def resolve_recipient(to):
    """تحويل رقم أو اسم لمستقبل (رقم بالكود الدولي)."""
    digits = re.sub(r"\D", "", str(to))
    if digits:  # الرقم متحدد
        if digits.startswith("00"):
            digits = digits[2:]
        if digits.startswith("0"):            # 01x... -> 20 1x...
            digits = "20" + digits[1:]
        elif len(digits) == 10 and digits.startswith("1"):
            digits = "20" + digits            # 1xxxxxxxxx (10 أرقام)
        elif not digits.startswith("20"):
            digits = "20" + digits
        return digits, None
    return db_lookup_name(to)  # الاسم


def build_wa_me_url(number, message):
    from urllib.parse import quote
    return f"https://wa.me/{number}?text={quote(message)}"


def send_direct(path, number, caption):
    """إرسال الملف مباشرة عبر البوت المحلي — بدون فتح أي نافذة (خصوصية).
    لو الجلسة مش مقترنة، البوت هيرفض بنفسه ويقول لك تشتغل pair أول مرة."""
    cmd = [NODE, "wa_bot.js", "send", number, os.path.abspath(path)]
    if caption:
        cmd += ["--caption", caption]
    print("إرسال مباشر (headless) ...")
    res = subprocess.run(cmd, cwd=WA_BOT_DIR, timeout=120)
    return res.returncode == 0


def send_manual(path, number, caption):
    """فتح واتس ويب برسالة جاهزة — تنتظرك تضغط إرسال بمفردك."""
    message = f"{caption}\n{os.path.basename(path)}"
    url = build_wa_me_url(number, message)
    print("افتحت واتس ويب برسالة جاهزة — اضغط إرسال:")
    print("  " + url)
    print(f"ملف الـ PDF بتاعك: {os.path.abspath(path)}")
    try:
        webbrowser.open(url)
    except Exception as e:
        print("مش قادر أفتح المتصفح تلقائيًا:", e)


def parse_recipients(raw):
    """قبول رقم واحد (str) أو قائمة أرقام/أسماء — والفصل بينهم بفاصلة أو مسافة."""
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        parts = []
        for x in raw:
            parts.extend(parse_recipients(x))
        return parts
    text = str(raw).strip()
    if not text:
        return []
    return [p.strip() for p in re.split(r"[,;،\s]+", text) if p.strip()]


def main():
    ap = argparse.ArgumentParser(description="إرسال ملف/نص عبر واتساب")
    ap.add_argument("--file", help="مسار الملف (PDF أو صورة)")
    ap.add_argument("--to", action="append", help="رقم/اسم مستقبل — تقدر تكررها أو تفصل بفاصلة")
    ap.add_argument("--manual", action="store_true", help="فتح واتس ويب يدوي بدل الإرسال المباشر")
    ap.add_argument("--caption", help="نص مرافق (اختياري)", default=None)
    args = ap.parse_args()

    cfg = load_config()
    mode = "manual" if args.manual else cfg.get("mode", "direct")
    path = args.file
    caption = args.caption if args.caption is not None else cfg.get("caption", "")

    to_list = parse_recipients(args.to) or parse_recipients(cfg.get("recipient", ""))

    if not path or not os.path.isfile(path):
        print("خطأ: عايز --file بمسار حقيقي لملف PDF")
        sys.exit(2)
    if not to_list:
        print("خطأ: حدد --to برقم أو اسم، أو حط recipient في assets/wa_config.json")
        sys.exit(2)

    results = []
    for to in to_list:
        number, err = resolve_recipient(to)
        if err:
            print(f"✗ {to}: {err}")
            results.append(False)
            continue
        print(f"→ الإرسال لـ {number}")
        if mode == "manual":
            send_manual(path, number, caption)
            results.append(True)
        else:
            results.append(send_direct(path, number, caption))

    if mode != "manual" and not all(results):
        print(f"فشل الإرسال لـ {results.count(False)} من أصل {len(results)} مستقبل.")
        sys.exit(1)


if __name__ == "__main__":
    main()