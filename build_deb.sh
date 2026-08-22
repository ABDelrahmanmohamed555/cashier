#!/usr/bin/env bash
# build_deb.sh — تحويل المشروع إلى حزمة .deb جاهزة للتثبيت على Ubuntu/Debian
# الاستخدام:
#   bash build_deb.sh              → ينتج cashier_<version>.deb في مجلد المشروع
#   sudo apt install ./cashier_*.deb   ( على الجهاز الجديد )
set -e

SRC="$(cd "$(dirname "$0")" && pwd)"
VERSION="${VERSION:-1.0.0}"
ROOT="$(mktemp -d)"
OUT="$SRC/cashier_${VERSION}_amd64.deb"

echo "=== تجهيز البنية داخل $ROOT ==="
mkdir -p "$ROOT/opt/cashier" "$ROOT/DEBIAN" "$ROOT/usr/share/applications"

rsync -a \
  --exclude venv \
  --exclude "wa_bot/session" \
  --exclude __pycache__ \
  --exclude ".git" \
  --exclude "*.deb" \
  "$SRC"/ "$ROOT/opt/cashier"/

cat > "$ROOT/DEBIAN/control" <<EOF
Package: cashier
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Depends: python3, python3-venv, python3-tk, libraqm0, nodejs
Recommends: chromium
Maintainer: مركز الصيانة <cashier@local>
Homepage: http://localhost
Description: نظام الكاشير لمركز الصيانة
 قائمة شغل يومية + طباعة استيكرات + تقارير PDF وإرسال واتساب.
EOF

cat > "$ROOT/opt/cashier/cashier.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=نظام الكاشير
Comment=مركز الصيانة - نظام الكاشير
Exec=/opt/cashier/venv/bin/python /opt/cashier/run.py
Icon=/opt/cashier/icon.png
Terminal=false
Categories=Office;Utility;
StartupNotify=true
EOF

cat > "$ROOT/DEBIAN/postinst" <<'EOF'
#!/bin/bash
# بيشتغل مرة واحدة بعد التثبيت: يبني البيئة ويسجل اللانشر
set -e
echo "=== بناء بيئة بايثون للنظام ==="
python3 -m venv /opt/cashier/venv
/opt/cashier/venv/bin/pip install --upgrade pip
/opt/cashier/venv/bin/pip install \
  customtkinter pillow arabic-reshaper python-bidi python-xlib qrcode darkdetect
chown -R 1000:1000 /opt/cashier
cp /opt/cashier/cashier.desktop /usr/share/applications/cashier.desktop
echo ""
echo "✓ نظام الكاشير اتصب — افتحه من قائمة التطبيقات."
echo "  ملاحظة: لو رقم أول مستخدم على الجهاز مش 1000، شغّل: sudo chown -R \$USER /opt/cashier"
EOF
chmod 755 "$ROOT/DEBIAN/postinst"

echo "=== بناء الحزمة ==="
dpkg-deb --build --root-owner-group "$ROOT" "$OUT"
rm -rf "$ROOT"

echo ""
echo "تم! حزمة عنده: $OUT"
echo "  التثبيت على أي جهاز Ubuntu/Debian:"
echo "    sudo apt install ./cashier_${VERSION}_amd64.deb"
echo "  أو الفك يدويًا في أي وقت:"
echo "    sudo dpkg -r cashier"