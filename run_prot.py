#!/usr/bin/env python3
# run_prot.py — مشغل منفصل لنظام الباركود (prot) كـ sibling لـ cashier
import os
import sys

# مجلد cashier الحالي
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# مجلد prot كـ sibling (Desktop/prot) أو داخل cashier/prot
for _cand in [os.path.join(BASE_DIR, "prot"), os.path.join(os.path.dirname(BASE_DIR), "prot")]:
    if os.path.exists(_cand):
        PROT_DIR = _cand
        break
else:
    PROT_DIR = os.path.join(BASE_DIR, "prot")

if PROT_DIR not in sys.path:
    sys.path.insert(0, PROT_DIR)
PARENT = os.path.dirname(PROT_DIR)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)
# أيضاً أضف cashier للاستيرادات المتقاطعة
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from prot.db.database import init_db
try:
    from prot.login import ProtLoginWindow
    HAS_LOGIN = True
except Exception as e:
    print(f"ProtLogin import failed: {e}")
    HAS_LOGIN = False
from prot.main import ProtWindow

if __name__ == "__main__":
    init_db()
    if HAS_LOGIN:
        app = ProtLoginWindow()
    else:
        app = ProtWindow(user={"name": "admin", "role": "admin"})
    app.mainloop()
