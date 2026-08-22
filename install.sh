#!/usr/bin/env bash
# install.sh — تثبيت نظام الكاشير كنطبيق على سطح المكتب (Ubuntu / Debian)
# الاستخدام:  sudo bash install.sh
set -e

SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="${DEST:-/opt/cashier}"

if [ -z "$SUDO_USER" ]; then
  echo "شغّل السكربت بـ sudo:  sudo bash install.sh"
  exit 1
fi

echo "=== 1) اعتماديات النظام ==="
sudo apt update
if ! sudo apt install -y python3 python3-venv python3-pip python3-tk libraqm0 nodejs chromium; then
  echo "(chromium مش متاح apt على Ubuntu — بيتثبت snap) بنكمّل بباقي الحزم..."
  sudo apt install -y python3 python3-venv python3-pip python3-tk libraqm0 nodejs
fi

echo "=== 2) نسخ المشروع إلى $DEST ==="
sudo mkdir -p "$DEST"
sudo rsync -a --delete \
  --exclude venv \
  --exclude "wa_bot/session" \
  --exclude __pycache__ \
  "$SRC"/ "$DEST"/
sudo chown -R "$SUDO_USER":"$SUDO_USER" "$DEST"

echo "=== 3) بيئة بايثون (venv) ==="
sudo -u "$SUDO_USER" python3 -m venv "$DEST/venv"
sudo -u "$SUDO_USER" "$DEST/venv/bin/pip" install --upgrade pip
sudo -u "$SUDO_USER" "$DEST/venv/bin/pip" install \
  customtkinter pillow arabic-reshaper python-bidi python-xlib qrcode darkdetect

echo "=== 4) تعريف التطبيق (لانشر + أيقونة) ==="
sudo tee "$DEST/cashier.desktop" > /dev/null <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=نظام الكاشير
Comment=مركز الصيانة - نظام الكاشير
Exec=$DEST/venv/bin/python $DEST/run.py
Icon=$DEST/icon.png
Terminal=false
Categories=Office;Utility;
StartupNotify=true
EOF
sudo cp "$DEST/cashier.desktop" /usr/share/applications/cashier.desktop

echo "=== 5) صلاحية الطابعة ==="
sudo usermod -aG lp "$SUDO_USER"

echo ""
echo "تم التثبيت!"
echo "  → افتحه من قائمة التطبيقات: «نظام الكاشير»"
echo "  → لازم تسجل خروج ودخول مرة عشان صلاحية الطابعة تشتغل"
echo "  → لو أول مستخدم على الجهاز مش اللي ثبّت، شغّل: sudo chown -R \$USER $DEST"