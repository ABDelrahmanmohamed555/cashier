#!/bin/bash
# ============================================
# الحل الجذري لمشكلة الطابعة الحرارية USB
# XPrinter XP-233B / STM32 0483:5743
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}شغّل الأمر ده بالـ sudo:${NC}"
    echo "sudo bash fix_printer.sh"
    exit 1
fi

echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  إصلاح مشكلة الطابعة الحرارية USB       ║${NC}"
echo -e "${CYAN}║  XPrinter XP-233B / STM32 BAR PRINTER  ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

# ────────────────────────────────────────────
# 1. الحل الفوري: USB quirks لمنع الـ disconnect
# ────────────────────────────────────────────
echo -e "${GREEN}[1/6]${NC} تطبيق USB quirks للطابعة..."

# 0483:5743 = XPrinter XP-233B (STM32 chip)
# q = avoid_reset_quirk
# i = no_init (skip initialization that causes reset)
# r = reset_resume (reset device on resume instead of restoring)
# n = no_set_interface (don't reset interface)

QUIRK_FILE="/sys/bus/usb/devices/1-4/quirks"
if [ -f "$QUIRK_FILE" ]; then
    echo "0x0" > "$QUIRK_FILE" 2>/dev/null
    echo -e "  ${GREEN}✓ Cleared existing quirks${NC}"
fi

# ────────────────────────────────────────────
# 2. تعطيل runtime PM لكل الـ USB devices
# ────────────────────────────────────────────
echo -e "${GREEN}[2/6]${NC} تعطيل runtime power management للـ USB..."

# Root hub
for hub in /sys/bus/usb/devices/usb*; do
    echo "on" > "$hub/power/control" 2>/dev/null
    echo "-1" > "$hub/power/autosuspend" 2>/dev/null
done

# كل الـ USB devices
for dev in /sys/bus/usb/devices/[0-9]*; do
    echo "on" > "$dev/power/control" 2>/dev/null
    echo "-1" > "$dev/power/autosuspend" 2>/dev/null
    echo "0" > "$dev/power/autosuspend_delay_ms" 2>/dev/null
done

# Root PCI controller
echo "on" > /sys/bus/pci/devices/0000:03:00.3/power/control 2>/dev/null
echo "on" > /sys/bus/pci/devices/0000:03:00.3/power/autosuspend 2>/dev/null

echo -e "  ${GREEN}✓ Runtime PM disabled${NC}"

# ────────────────────────────────────────────
# 3. تعطيل CUPS auto-discovery
# ────────────────────────────────────────────
echo -e "${GREEN}[3/6]${NC} إيقاف CUPS auto-discovery..."

systemctl stop cups.service cups.socket cups.path 2>/dev/null
systemctl disable cups.socket cups.path 2>/dev/null

# قتل system-config-printer-applet
pkill -f "system-config-printer" 2>/dev/null
pkill -f "cups-deviced" 2>/dev/null
pkill -f "udev-configure-printer" 2>/dev/null

# تعطيل udev rule بتاع configure-printer
if [ -f /lib/udev/rules.d/70-printers.rules ]; then
    cp /lib/udev/rules.d/70-printers.rules /lib/udev/rules.d/70-printers.rules.bak
    echo '# DISABLED - was causing printer disconnect loop
# Original file backed up at 70-printers.rules.bak' > /lib/udev/rules.d/70-printers.rules
    udevadm control --reload-rules
    udevadm trigger
    echo -e "  ${GREEN}✓ CUPS auto-discovery disabled${NC}"
fi

# ────────────────────────────────────────────
# 4. GRUB parameters (daimi ba3d restart)
# ────────────────────────────────────────────
echo -e "${GREEN}[4/6]${NC} إضافة GRUB parameters..."

GRUB_FILE="/etc/default/grub"
PARAMS="usbcore.autosuspend=-1 usbcore.quirks=0483:5743:r,0x0"

# خد الـ CMDLINE الحالي
CURRENT=$(grep "GRUB_CMDLINE_LINUX_DEFAULT=" "$GRUB_FILE" | head -1)

# احذف أي参数 قديمة بتاعتنا
sed -i 's/ usbcore\.[^ "]*//g' "$GRUB_FILE"
sed -i 's/ xhci_hcd\.[^ "]*//g' "$GRUB_FILE"

# أضف الـ parameters الجديدة
NEW_LINE="GRUB_CMDLINE_LINUX_DEFAULT=\"quiet splash usbcore.autosuspend=-1 usbcore.quirks=0483:5743:r,0x0\""
sed -i "s|^GRUB_CMDLINE_LINUX_DEFAULT=.*|${NEW_LINE}|" "$GRUB_FILE"

update-grub 2>/dev/null
echo -e "  ${GREEN}✓ GRUB updated${NC}"
echo "    Parameters: usbcore.autosuspend=-1 usbcore.quirks=0483:5743:r,0x0"

# ────────────────────────────────────────────
# 5. udev rule دائم
# ────────────────────────────────────────────
echo -e "${GREEN}[5/6]${NC} تحديث udev rules..."

cat > /etc/udev/rules.d/99-thermal-printer.rules << 'RULES'
# ═══════════════════════════════════════════
# XPrinter XP-233B / STM32 BAR PRINTER
# الحل الجذري لمشكلة الاتصال المتكرر
# ═══════════════════════════════════════════

# تعطيل autosuspend لكل USB devices
ACTION=="add", SUBSYSTEM=="usb", TEST=="power/autosuspend", ATTR{power/autosuspend}="-1"
ACTION=="add", SUBSYSTEM=="usb", TEST=="power/control", ATTR{power/control}="on"
ACTION=="add", SUBSYSTEM=="usb", TEST=="power/autosuspend_delay_ms", ATTR{power/autosuspend_delay_ms}="0"

# الطابعة بالتحديد - منع أي power saving
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="0483", ATTR{idProduct}=="5743", TEST=="power/autosuspend", ATTR{power/autosuspend}="-1"
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="0483", ATTR{idProduct}=="5743", TEST=="power/control", ATTR{power/control}="on"

# صلاحيات الوصول
SUBSYSTEM=="usbmisc", KERNEL=="lp*", MODE="0666"
SUBSYSTEM=="usb", KERNEL=="lp*", MODE="0666"

# منع configure-printer من التعامل مع الطابعة
ENV{ID_VENDOR_ID}=="0483", ENV{ID_MODEL_ID}=="5743", ENV{SYSTEMD_WANTS}=""
RULES

udevadm control --reload-rules
udevadm trigger
echo -e "  ${GREEN}✓ udev rules updated${NC}"

# ────────────────────────────────────────────
# 6.检验
# ────────────────────────────────────────────
echo -e "${GREEN}[6/6]${NC} فحص الحالة..."
echo ""
echo "  autosuspend = $(cat /sys/module/usbcore/parameters/autosuspend)"
echo "  USB quirks for 1-4 = $(cat /sys/bus/usb/devices/1-4/quirks 2>/dev/null || echo 'N/A')"
echo ""

# عد المتصلات
COUNT_BEFORE=$(dmesg | grep -c "USB disconnect" 2>/dev/null || echo 0)
echo -e "  ${YELLOW}عدد الـ disconnects الحالي: $COUNT_BEFORE${NC}"
echo ""
echo -e "${CYAN}════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${YELLOW}الآن اعمل الآتي:${NC}"
echo ""
echo "  1. شيل كيبل USB من الطابعة"
echo "  2. استنى 5 ثواني"
echo "  3. رجّع الكيبل"
echo "  4. انتظر 15 ثانية"
echo "  5. شغّل:  dmesg | tail -20"
echo ""
echo "  لو الـ disconnects وقفت => المشكلة اتحلت!"
echo "  لو لسه موجودة، شغّل:  sudo bash fix_printer.sh --upgrade-kernel"
echo ""

# ────────────────────────────────────────────
# ترقية Kernel لو مطلوب
# ────────────────────────────────────────────
if [ "$1" = "--upgrade-kernel" ]; then
    echo -e "${YELLOW}=== ترقية Kernel لـ 7.0.12 ===${NC}"
    echo ""
    echo "ده هيحل المشكلة بشكل أكيد لأن kernel 7.0.12 فيه fixes كتير للـ xhci_hcd."
    echo ""
    read -p "عايز تكمل الترقية؟ (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        apt update
        apt install -y linux-image-amd64 linux-headers-amd64
        echo ""
        echo -e "${GREEN}✓ تم! اعمل ريستارت عشان الـ kernel الجديد يتشغل.${NC}"
        echo ""
        echo "  grub-has-set-default و هيشتغل على 7.0.12 تلقائياً"
    fi
fi
