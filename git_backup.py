# git_backup.py — نسخ احتياطي عبر git (add/commit/push) مع جدولة
# الاستخدام:
#   ./venv/bin/python git_backup.py                  # نسخ فوري
#   ./venv/bin/python git_backup.py --check          # يفحص الجدولة وينفذ لو حان الوقت
#   ./venv/bin/python git_backup.py --install-cron   # تثبيت cron حسب الإعدادات

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "assets", "backup_config.json")
TOKEN_PATHS = [
    os.path.expanduser("~/.config/cashier/github_token"),
    os.path.expanduser("~/.config/prot/github_token"),
    os.path.join(BASE_DIR, "assets", ".github_token"),
    os.path.join(BASE_DIR, ".github_token"),
]

DEFAULT_CONFIG = {
    "enabled": False,
    "frequency": "daily",  # daily | every2days | weekly | monthly
    "time": "02:00",
    "last_run": "",  # YYYY-MM-DD
}


def load_backup_config():
    if not os.path.exists(CONFIG_PATH):
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        return {
            "enabled": bool(d.get("enabled", False)),
            "frequency": str(d.get("frequency", "daily")).strip() or "daily",
            "time": str(d.get("time", "02:00")).strip() or "02:00",
            "last_run": str(d.get("last_run", "")).strip(),
        }
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_backup_config(enabled, frequency, time_str, last_run=None):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    cur = load_backup_config()
    if last_run is None:
        last_run = cur.get("last_run", "")
    data = {
        "enabled": bool(enabled),
        "frequency": str(frequency).strip() or "daily",
        "time": time_str.strip(),
        "last_run": str(last_run).strip(),
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def _get_token_path():
    for p in TOKEN_PATHS:
        if os.path.exists(p):
            return p
    return TOKEN_PATHS[0]

def load_github_token():
    for p in TOKEN_PATHS:
        try:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    tok = f.read().strip()
                if tok:
                    return tok
        except Exception:
            continue
    # fallback: حاول قراءة من git credential
    return None

def save_github_token(token):
    token = (token or "").strip()
    if not token:
        return False, "التوكن فارغ"
    # نظف التوكن من أي مسافات أو أسطر جديدة
    token = token.split()[0]
    if not (token.startswith("ghp_") or token.startswith("github_pat_") or len(token) >= 20):
        # تحذير فقط، لكن نسمح بأي توكن طويل
        pass
    path = _get_token_path()
    # لو المسار الافتراضي غير موجود، استخدم الأول
    if not os.path.exists(os.path.dirname(path)):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        except Exception:
            pass
    # اختر المسار الأكثر أماناً (home config)
    path = TOKEN_PATHS[0]
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(token + "\n")
        os.chmod(path, 0o600)
        # أيضاً احفظ نسخة في assets للتوافق
        try:
            alt = TOKEN_PATHS[1]
            os.makedirs(os.path.dirname(alt), exist_ok=True)
            with open(alt, "w", encoding="utf-8") as f:
                f.write(token + "\n")
            os.chmod(alt, 0o600)
        except Exception:
            pass
        return True, f"تم حفظ التوكن ✓ ({path})"
    except Exception as e:
        return False, f"فشل حفظ التوكن: {e}"

def clear_github_token():
    removed = []
    for p in TOKEN_PATHS:
        try:
            if os.path.exists(p):
                os.remove(p)
                removed.append(p)
        except Exception:
            pass
    return removed

def _parse_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def should_run_today(frequency, last_run_str, today=None):
    """هل يجب تنفيذ النسخ اليوم حسب التكرار؟"""
    if today is None:
        today = date.today()
    last = _parse_date(last_run_str) if last_run_str else None
    if not last:
        return True  # أول مرة
    delta = (today - last).days
    if delta < 0:
        return False
    if frequency == "daily":
        return delta >= 1
    elif frequency == "every2days":
        return delta >= 2
    elif frequency == "weekly":
        return delta >= 7
    elif frequency == "monthly":
        # شهري: نفس اليوم من الشهر التالي أو 30 يوم
        # نبسط: 30 يوم أو اختلاف الشهر
        if delta >= 30:
            return True
        # لو اختلف الشهر والسنة وكان اليوم >= يوم آخر تشغيل
        if today.month != last.month or today.year != last.year:
            return True
        return False
    else:
        return delta >= 1


def do_git_backup(custom_message=None):
    """تنفيذ git add . && git commit -m "backup" && git push"""
    cwd = BASE_DIR
    # تحقق مستودع git
    if not os.path.exists(os.path.join(cwd, ".git")):
        return False, "المجلد ليس مستودع git"

    # git add .
    try:
        r1 = subprocess.run(["git", "add", "."], cwd=cwd, capture_output=True, text=True, timeout=30)
        if r1.returncode != 0:
            return False, f"فشل git add: {r1.stderr or r1.stdout}"
    except Exception as e:
        return False, f"خطأ git add: {e}"

    # فحص هل يوجد تغييرات
    try:
        status = subprocess.run(["git", "status", "--porcelain"], cwd=cwd, capture_output=True, text=True, timeout=10)
        if not status.stdout.strip():
            return True, "لا يوجد تغييرات للرفع — كل شيء محدث"
    except Exception:
        pass

    # git commit
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = custom_message or f"backup {now_str}"
    try:
        r2 = subprocess.run(["git", "commit", "-m", msg], cwd=cwd, capture_output=True, text=True, timeout=30)
        if r2.returncode != 0:
            out = (r2.stdout + " " + r2.stderr).lower()
            if "nothing to commit" in out or "no changes added" in out:
                return True, "لا يوجد تغييرات للـ commit"
            return False, f"فشل commit: {r2.stderr or r2.stdout}"
    except Exception as e:
        return False, f"خطأ commit: {e}"

    # git push — مع دعم التوكن لمرة واحدة
    token = load_github_token()
    # دالة مساعدة لمحاولة push مع التوكن
    def _try_push_with_token(tok):
        try:
            # احصل على remote الحالي
            r_remote = subprocess.run(["git", "config", "--get", "remote.origin.url"], cwd=cwd, capture_output=True, text=True, timeout=10)
            remote_url = (r_remote.stdout or "").strip()
            if not remote_url:
                remote_url = "https://github.com/ABDelrahmanmohamed555/cashier.git"
            # حوله لـ https مع توكن
            # مثال: https://github.com/user/repo.git → https://<token>@github.com/user/repo.git
            # لو كان SSH نحوله لـ https
            if remote_url.startswith("git@"):
                # git@github.com:user/repo.git → https://github.com/user/repo.git
                try:
                    # git@github.com:ABDelrahmanmohamed555/cashier.git → https://github.com/ABDelrahmanmohamed555/cashier.git
                    part = remote_url.split(":", 1)[1]
                    remote_url = f"https://github.com/{part}"
                except Exception:
                    remote_url = "https://github.com/ABDelrahmanmohamed555/cashier.git"
            if "github.com" in remote_url and tok:
                # أدخل التوكن: https://<tok>@github.com/...
                if "@" not in remote_url.split("github.com")[0]:
                    remote_url = remote_url.replace("https://", f"https://{tok}@")
                # حاول push عبر URL المؤقت بدون حفظه (HEAD:main)
                try:
                    # احصل على الفرع الحالي
                    br = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd, capture_output=True, text=True, timeout=10)
                    branch = (br.stdout or "main").strip() or "main"
                except Exception:
                    branch = "main"
                r = subprocess.run(["git", "push", remote_url, f"HEAD:{branch}"], cwd=cwd, capture_output=True, text=True, timeout=60)
                return r
            # fallback عادي
            return subprocess.run(["git", "push"], cwd=cwd, capture_output=True, text=True, timeout=60)
        except Exception as e:
            return subprocess.CompletedProcess(args=["git","push"], returncode=1, stdout="", stderr=str(e))

    try:
        # المحاولة الأولى: push عادي (لو كان credential helper مضبوط)
        r3 = subprocess.run(["git", "push"], cwd=cwd, capture_output=True, text=True, timeout=60)
        if r3.returncode == 0:
            return True, f"تم الرفع بنجاح — {msg}"
        err = r3.stderr or r3.stdout or ""
        # لو فشل بسبب مصادقة، جرّب التوكن المحفوظ
        needs_token = any(x in err.lower() for x in ["could not read username", "authentication failed", "invalid username or password", "support for password authentication was removed", "403", "401"])
        if needs_token and token:
            r_tok = _try_push_with_token(token)
            if r_tok.returncode == 0:
                return True, f"تم الرفع بنجاح عبر التوكن — {msg}"
            err2 = r_tok.stderr or r_tok.stdout or ""
            return False, f"فشل push حتى مع التوكن: {err2[:500]} — تأكد أن التوكن صحيح (ghp_...) وله صلاحية repo"
        if "could not read" in err.lower() or "no configured push destination" in err.lower():
            if token:
                return False, f"فشل push: {err[:300]} — جرّب التوكن المحفوظ أو حدّثه من الإعدادات"
            return False, f"فشل push: {err[:300]} — أدخل GitHub Token مرة واحدة من الإعدادات (سيُحفظ تلقائياً)"
        return False, f"فشل push: {err[:500]}"
    except Exception as e:
        return False, f"خطأ push: {e}"


def install_cron(frequency=None, time_str=None):
    """تثبيت cron يشغل git_backup.py --check في الوقت المحدد.
    نستخدم تشغيل يومي عند الوقت المختار، والسكربت نفسه يراعي التكرار."""
    cfg = load_backup_config()
    if frequency is None:
        frequency = cfg.get("frequency", "daily")
    if time_str is None:
        time_str = cfg.get("time", "02:00")
    try:
        hh, mm = [int(x) for x in str(time_str).strip().split(":")]
        hh = max(0, min(23, hh))
        mm = max(0, min(59, mm))
    except Exception:
        hh, mm = 2, 0

    # الأمر: يومياً عند HH:MM يشغل السكربت مع --check
    # السكربت سيقرر داخلياً هل اليوم يستحق حسب frequency
    cmd = " ".join([
        f"cd {BASE_DIR} &&",
        f"{sys.executable} {os.path.join(BASE_DIR, 'git_backup.py')} --check",
        f">> {os.path.join(BASE_DIR, 'reports', 'backup_cron.log')} 2>&1",
    ])
    # cron يشتغل يومياً — التكرار يحسمه السكربت
    entry = f"{mm} {hh} * * * {cmd}\n"
    try:
        cr = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        existing = cr.stdout if cr.returncode == 0 else ""
    except Exception:
        existing = ""
    # احذف أي جدولة قديمة لنفس السكربت
    if "git_backup.py" in existing:
        lines = [ln for ln in existing.splitlines() if "git_backup.py" not in ln]
        existing = "\n".join(lines) + ("\n" if lines else "")
        print("تم تحديث جدولة النسخ القديمة.")
    new = existing + entry
    try:
        subprocess.run(["crontab", "-"], input=new, text=True, check=True)
        print("اتثبتت جدولة النسخ في crontab:")
        print(entry)
        return True
    except Exception as e:
        print(f"فشل تثبيت crontab: {e}")
        print(f"أضف يدوياً:\n{entry}")
        return False


def remove_cron():
    try:
        cr = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        existing = cr.stdout if cr.returncode == 0 else ""
        if "git_backup.py" not in existing:
            return True
        lines = [ln for ln in existing.splitlines() if "git_backup.py" not in ln]
        new = "\n".join(lines) + ("\n" if lines else "")
        subprocess.run(["crontab", "-"], input=new, text=True, check=True)
        print("تمت إزالة جدولة النسخ من crontab")
        return True
    except Exception as e:
        print(f"cron remove err: {e}")
        return False


def main():
    ap = argparse.ArgumentParser(description="نسخ احتياطي git")
    ap.add_argument("--check", action="store_true", help="يفحص الجدولة وينفذ لو حان الوقت")
    ap.add_argument("--install-cron", action="store_true", help="تثبيت cron")
    ap.add_argument("--remove-cron", action="store_true", help="إزالة cron")
    ap.add_argument("--message", help="رسالة commit مخصصة")
    ap.add_argument("--set-token", help="حفظ GitHub Token لمرة واحدة (ghp_...)")
    ap.add_argument("--clear-token", action="store_true", help="حذف التوكن المحفوظ")
    ap.add_argument("--token-status", action="store_true", help="عرض حالة التوكن")
    args = ap.parse_args()

    if args.set_token is not None:
        ok, msg = save_github_token(args.set_token)
        print(msg)
        sys.exit(0 if ok else 1)
    if args.clear_token:
        removed = clear_github_token()
        print(f"تم حذف التوكن من: {', '.join(removed) if removed else 'لا يوجد توكن'}")
        sys.exit(0)
    if args.token_status:
        tok = load_github_token()
        if tok:
            masked = tok[:4] + "*"*(len(tok)-8) + tok[-4:] if len(tok) > 8 else "***"
            print(f"التوكن محفوظ ✓ {masked} ({_get_token_path()})")
        else:
            print("لا يوجد توكن محفوظ — أدخل واحداً عبر --set-token أو من الإعدادات")
        sys.exit(0)

    if args.install_cron:
        install_cron()
        return
    if args.remove_cron:
        remove_cron()
        return

    if args.check:
        cfg = load_backup_config()
        if not cfg.get("enabled"):
            print("النسخ معطل")
            return
        now = datetime.now()
        cur_time = now.strftime("%H:%M")
        target = cfg.get("time", "02:00")
        today_str = now.strftime("%Y-%m-%d")
        freq = cfg.get("frequency", "daily")
        last = cfg.get("last_run", "")
        # تحقق الوقت
        if cur_time != target:
            # للـ cron نسمح بفرق دقيقة واحدة بسبب تأخر التنفيذ
            try:
                ch, cm = map(int, cur_time.split(":"))
                th, tm = map(int, target.split(":"))
                diff = abs((ch*60+cm) - (th*60+tm))
                if diff > 1:
                    print(f"ليس وقت التنفيذ الآن {cur_time} != {target}")
                    return
            except Exception:
                if cur_time != target:
                    return
        if not should_run_today(freq, last, now.date()):
            print(f"ليس موعد التكرار ({freq}) — آخر تشغيل {last}")
            return
        ok, msg = do_git_backup(args.message)
        print(msg)
        if ok:
            # حدث last_run فقط عند النجاح أو عدم وجود تغييرات (يعتبر نجاح)
            try:
                save_backup_config(cfg["enabled"], freq, target, last_run=today_str)
            except Exception:
                pass
        sys.exit(0 if ok else 1)
    else:
        # نسخ فوري
        ok, msg = do_git_backup(args.message)
        print(msg)
        if ok:
            try:
                cfg = load_backup_config()
                today_str = datetime.now().strftime("%Y-%m-%d")
                save_backup_config(cfg.get("enabled", False), cfg.get("frequency", "daily"), cfg.get("time", "02:00"), last_run=today_str)
            except Exception:
                pass
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
