#!/usr/bin/env python3
# other/label_editor.py — مصمم ستيكر بسيط: اكتب أي نص (اسم منتج + سعر + ملاحظة)
# واضبط الخطوط والمسافات والمحاذاة بالعين والنظرة الحية — والطابعة تطبعه فورًا.
# الاستخدام:  ./venv/bin/python other/label_editor.py
import json
import os
import shutil
import sys
import threading

import customtkinter as ctk
from PIL import Image, ImageDraw

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from config import COLORS
from arabic_entry import ArabicEntry
from utils import reshape_arabic
from sticker import (_get_font, _layout, _shrink_font, _tracking_px,
                     _is_arabic, SS, SAFE_MARGIN_MM)
import printing

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CFG_FILE = os.path.join(APP_DIR, "label_config.json")

DEFAULT_CFG = {
    "sticker_width_mm": 50.0,
    "sticker_height_mm": 29.4,
    "gap_mm": 1.0,
    "copies": 1,
    "image_scale": 3.0,
    "v_align": "top",
    "elements": [
        {"id": "product", "label": "اسم المنتج", "text": " ", "font_size_pt": 22,
         "align": "center", "bold": True, "letter_spacing_pt": 0.0},
        {"id": "price", "label": "السعر", "text": "120 جنيه", "font_size_pt": 30,
         "align": "center", "bold": True, "letter_spacing_pt": 0.0, "underline": True},
        {"id": "note", "label": "ملاحظة", "text": "", "font_size_pt": 14,
         "align": "center", "bold": False, "letter_spacing_pt": 0.0},
    ],
}


# قيم العرض للقوائم: بتتخزن عربي طبيعي في الكود، وتعرض بشكلها النهائي
# (نفس أسلوب البرنامج الرئيسي) لأن ودجتس Tk مش بتطبق تشكيل/اتجاه عربي.
_VALIGN_DISP = {"top": reshape_arabic("أعلى"), "middle": reshape_arabic("وسط"),
                "bottom": reshape_arabic("أسفل")}
_VALIGN_REV = {v: k for k, v in _VALIGN_DISP.items()}
_ALIGN_DISP = {"right": reshape_arabic("يمين"), "center": reshape_arabic("وسط"),
               "left": reshape_arabic("يسار")}
_ALIGN_REV = {v: k for k, v in _ALIGN_DISP.items()}


def load_cfg():
    try:
        with open(CFG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for i, el in enumerate(DEFAULT_CFG["elements"]):
            if i < len(data["elements"]):
                data["elements"][i].update(
                    {k: v for k, v in el.items() if k not in data["elements"][i]})
        return data
    except Exception:
        return json.loads(json.dumps(DEFAULT_CFG))


def save_cfg(cfg):
    try:
        with open(CFG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def render(cfg):
    """رسم الستيكر عالي الجودة (نفس أسلوب sticker.py) ويرجع صورة PIL والتكبير للعرض."""
    scale_img = float(cfg.get("image_scale", 2.0))
    dpi = 203
    pmm0 = dpi / 25.4
    pmm = pmm0 * SS
    w_mm = float(cfg["sticker_width_mm"])
    h_mm = float(cfg["sticker_height_mm"])
    W = max(1, int(round(w_mm * pmm0))) * SS
    H = max(1, int(round(h_mm * pmm0))) * SS
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)

    safe = SAFE_MARGIN_MM * pmm
    gap_px = float(cfg.get("gap_mm", 1.0)) * pmm
    max_w = W - 2 * safe
    min_fs = 10

    def layout_for(el, fs):
        font = _get_font(fs, bold=bool(el.get("bold", False)))
        font = _shrink_font(d, el["_text"], font, max_w, el["_layout"])
        ls = _tracking_px(el, fs)
        bb = d.textbbox((0, 0), el["_text"], font=font, anchor="mm", **el["_layout"])
        return font, ls, bb[3] - bb[1]

    # تجهيز النصوص: بنبعت النص خام ونخلّي libraqm يشكّل ويحدد الاتجاه
    # (نفس أسلوب sticker.py بالظبط) — الـ reshape المسبق كان يسبب نص معكوس
    # لأن المحرك بيطبق bidi تاني على النص الجاهز فيرجعه لعكس اتجاهه.
    texts = []
    for el in cfg["elements"]:
        raw = str(el.get("text", "") or "").strip()
        if not raw:
            continue
        el = {**el, "_text": raw, "_layout": _layout(raw)}
        _, _, ih = layout_for(el, float(el.get("font_size_pt", 16)))
        texts.append((el, ih))

    # تصغير نسبي تلقائي لو السطور مش بتكفى (نفس فكرة الـ auto mode)
    total_h = sum(ih for _, ih in texts) + gap_px * (len(texts) - 1)
    factor = 1.0
    if texts and total_h > H - 2 * safe:
        factor = (H - 2 * safe) / total_h

    # قياسات نهائية بعد التصغير (ثابتة لكل سطر)
    final = []
    for el, _ in texts:
        fs = max(min_fs, float(el.get("font_size_pt", 16)) * factor)
        font, ls, ih = layout_for(el, fs)
        final.append((el, el["_text"], y_fs := fs, y_font := font, ls, ih))

    total_final = sum(ih for *_, ih in final) + gap_px * (len(final) - 1)

    # وضع الكتلة رأسيا حسب الاختيار: أعلى / وسط / أسفل
    v_align = cfg.get("v_align", "top")
    if v_align == "bottom":
        start_y = max(safe, H - safe - total_final)
    elif v_align == "middle":
        start_y = max(safe, (H - total_final) / 2)
    else:
        start_y = safe

    used = []
    prev_bottom = start_y
    for el, text, fs, font, ls, ih in final:
        y = prev_bottom + ih / 2
        align = el.get("align", "right")
        if align == "center":
            x, anchor = W / 2, "mm"
        elif align == "left":
            x, anchor = safe, "lm"
        else:
            x, anchor = W - safe, "rm"
        d.text((x, y), el["_text"], fill="black", font=font, anchor=anchor,
               letter_spacing=ls, **el["_layout"])
        used.append((el, el["_text"], y, ih))
        prev_bottom = y + ih / 2 + gap_px

    # خط سفلي تحت السعر (اختياري)
    for el, text, y, ih in used:
        if el.get("id") == "price" and el.get("underline"):
            font, ls, _ = layout_for(el, float(el.get("font_size_pt", 16)) * factor)
            text_w = d.textlength(text, font=font, **el["_layout"]) + ls * max(0, len(text) - 1)
            if el.get("align") == "center":
                x1, x2 = W / 2 - text_w / 2, W / 2 + text_w / 2
            elif el.get("align") == "left":
                x1, x2 = safe, safe + text_w
            else:
                x1, x2 = W - safe - text_w, W - safe
            d.line([(x1, y + ih / 2 + 2), (x2, y + ih / 2 + 2)], fill="black", width=2 * SS)

    out = img.resize((int(W / SS), int(H / SS)), Image.LANCZOS)
    disp = out.resize((int(out.width * scale_img), int(out.height * scale_img)), Image.LANCZOS)
    return out, disp


class LabelEntry(ArabicEntry):
    """نفس خانة الكتابة العربية المعتمدة في المشروع — مع إمكانية تزويد نص مبدئي وإفراغه."""

    def set_text(self, text):
        self._raw_text = str(text or "")
        self._update_display()


class LabelEditor(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        cfg = load_cfg()

        # نافذة عادية بإطار النظام وأزراره القياسية (غلق/تكبير/تصغير)
        self.title("مصمم ستيكر المنتجات")

        self.geometry("1020x640")
        self.minsize(900, 560)
        self.configure(fg_color=COLORS["bg_dark"])
        self._cfg = cfg
        self._pending = None

        self._build_ui()
        self._refresh()

    # ---------- واجهة ----------

    def _build_ui(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=18, pady=(12, 14))

        left = ctk.CTkFrame(main, fg_color=COLORS["bg_card"], corner_radius=12)
        left.pack(side="left", fill="y", padx=(0, 14), pady=4)
        left.configure(width=400)

        ctk.CTkLabel(left, text=reshape_arabic("مصمم الستيكر"), font=("Tajawal Bold", 20),
                     text_color=COLORS["accent"]).pack(anchor="w", padx=18, pady=(14, 2))
        ctk.CTkLabel(left, text=reshape_arabic(
            f'مقاس الورقة: {self._cfg["sticker_width_mm"]}×{self._cfg["sticker_height_mm"]} مم — أي تغيير بيبان في المعاينة فورًا'),
            font=("Tajawal", 12), text_color=COLORS["text_light"]).pack(anchor="w", padx=18)

        for i, el in enumerate(self._cfg["elements"]):
            self._build_line_block(left, i, el)

        gap_row = ctk.CTkFrame(left, fg_color="transparent")
        gap_row.pack(fill="x", padx=18, pady=(8, 0))
        ctk.CTkLabel(gap_row, text=reshape_arabic("المسافة بين السطور (مم)"), font=("Tajawal", 14),
                     text_color=COLORS["text_white"]).pack(side="left")
        self._gap_lbl = ctk.CTkLabel(gap_row, text="1.0", font=("Tajawal Bold", 14),
                                     text_color=COLORS["accent"], width=40)
        self._gap_lbl.pack(side="right")
        self._gap_scale = ctk.CTkSlider(left, from_=0.2, to=5.0, number_of_steps=48,
                                        command=self._on_gap)
        self._gap_scale.set(float(self._cfg.get("gap_mm", 1.0)))
        self._gap_scale.pack(fill="x", padx=18, pady=(2, 6))

        valign_row = ctk.CTkFrame(left, fg_color="transparent")
        valign_row.pack(fill="x", padx=18, pady=(8, 0))
        ctk.CTkLabel(valign_row, text=reshape_arabic("مكان الكلام في الستيكر"), font=("Tajawal", 14),
                     text_color=COLORS["text_white"]).pack(anchor="w")
        self._valign = ctk.CTkSegmentedButton(valign_row, values=list(_VALIGN_DISP.values()),
                                              font=("Tajawal", 14),
                                              selected_color=COLORS["accent"],
                                              selected_hover_color=COLORS["accent_hover"],
                                              command=self._on_valign)
        self._valign.set(_VALIGN_DISP.get(self._cfg.get("v_align", "top"), _VALIGN_DISP["top"]))
        self._valign.pack(fill="x", pady=(4, 2))

        copy_row = ctk.CTkFrame(left, fg_color="transparent")
        copy_row.pack(fill="x", padx=18)
        ctk.CTkLabel(copy_row, text=reshape_arabic("عدد النسخ"), font=("Tajawal", 14),
                     text_color=COLORS["text_white"]).pack(side="left")
        self._copies = ctk.CTkEntry(copy_row, width=60, font=("Tajawal", 14), justify="center")
        self._copies.insert(0, str(self._cfg.get("copies", 1)))
        self._copies.pack(side="right")
        self._copies.bind("<KeyRelease>", self._on_change_any)

        btn = ctk.CTkButton(left, text=reshape_arabic("طباعة"), font=("Tajawal Bold", 17), height=50,
                            corner_radius=8, fg_color=COLORS["accent"],
                            hover_color=COLORS["accent_hover"], command=self._print)
        btn.pack(fill="x", padx=18, pady=(16, 6))

        self._status = ctk.CTkLabel(left, text="", font=("Tajawal", 13),
                                    text_color=COLORS["text_light"])
        self._status.pack(fill="x", padx=18, pady=(0, 12))

        right = ctk.CTkFrame(main, fg_color=COLORS["bg_card"], corner_radius=12)
        right.pack(side="left", fill="both", expand=True, pady=4)
        ctk.CTkLabel(right, text=reshape_arabic("المعاينة الحية"), font=("Tajawal", 15),
                     text_color=COLORS["text_light"]).pack(anchor="w", padx=14, pady=(10, 4))
        self._preview = ctk.CTkLabel(right, text="", image=None)
        self._preview.pack(expand=True, pady=12)

    def _build_line_block(self, parent, idx, el):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(fill="x", padx=18, pady=(10, 0))
        ctk.CTkLabel(box, text=reshape_arabic(el["label"]), font=("Tajawal Bold", 14),
                     text_color=COLORS["text_white"]).pack(anchor="w")
        self._txt = getattr(self, "_txt", [])
        entry = LabelEntry(box, placeholder=el["label"], font=("Tajawal", 15),
                           height=40, fg_color=COLORS["bg_input"],
                           border_color=COLORS["border"])
        entry.set_text(el.get("text", ""))
        entry.bind("<KeyRelease>", lambda e, i=idx: self._on_text(i, e), True)
        entry.pack(fill="x", pady=(4, 0))
        self._txt.append(entry)

        srow = ctk.CTkFrame(parent, fg_color="transparent")
        srow.pack(fill="x", padx=18, pady=(2, 0))
        self._font_scales = getattr(self, "_font_scales", [])
        scale = ctk.CTkSlider(srow, from_=10, to=50, number_of_steps=80, width=150,
                              command=lambda v, i=idx: self._on_font(i, v))
        scale.set(float(el.get("font_size_pt", 16)))
        scale.pack(side="left")
        self._font_scales.append(scale)
        self._font_lbls = getattr(self, "_font_lbls", [])
        lbl = ctk.CTkLabel(srow, text=f'{el.get("font_size_pt", 16)}pt', width=44,
                           font=("Tajawal", 12), text_color=COLORS["accent"])
        lbl.pack(side="left", padx=(6, 4))
        self._font_lbls.append(lbl)
        self._align_menus = getattr(self, "_align_menus", [])
        menu = ctk.CTkOptionMenu(srow, values=list(_ALIGN_DISP.values()), width=86,
                                 font=("Tajawal", 13), fg_color=COLORS["bg_input"],
                                 button_color=COLORS["accent"],
                                 command=lambda v, i=idx: self._on_align(i, v))
        menu.set(_ALIGN_DISP.get(el.get("align", "right"), _ALIGN_DISP["right"]))
        menu.pack(side="right")
        self._align_menus.append(menu)

    # ---------- تفاعلات ----------

    def _on_change_any(self, *_):
        self._schedule_refresh()

    def _on_text(self, idx, event=None):
        self._cfg["elements"][idx]["text"] = self._txt[idx].get()
        self._schedule_refresh()

    def _on_font(self, idx, value):
        self._cfg["elements"][idx]["font_size_pt"] = round(value, 1)
        self._font_lbls[idx].configure(text=f'{round(value, 1)}pt')
        self._schedule_refresh()

    def _on_align(self, idx, value):
        self._cfg["elements"][idx]["align"] = _ALIGN_REV.get(value, "right")
        self._schedule_refresh()

    def _on_gap(self, value):
        self._cfg["gap_mm"] = round(value, 2)
        self._gap_lbl.configure(text=f'{round(value, 2)}')
        self._schedule_refresh()

    def _on_valign(self, value):
        self._cfg["v_align"] = _VALIGN_REV.get(value, "top")
        self._schedule_refresh()

    def _schedule_refresh(self):
        if self._pending:
            self.after_cancel(self._pending)
        self._pending = self.after(180, self._refresh)

    def _refresh(self):
        self._pending = None
        try:
            self._cfg["copies"] = max(1, min(99, int(self._copies.get() or "1")))
        except ValueError:
            pass
        img, disp = render(self._cfg)
        self._preview.configure(image=ctk.CTkImage(light_image=disp, dark_image=disp,
                                                   size=disp.size))
        self._preview.image = self._preview.cget("image")

    # ---------- طباعة ----------

    def _print(self):
        def worker():
            try:
                if not printing.printer_available():
                    self.after(0, self._set_status,
                               "الطابعة مش متوصلة — تأكد من القابس والكابل", COLORS["danger"])
                    return
                img, _ = render(self._cfg)
                pcfg = printing._load_print_cfg()
                w = float(self._cfg["sticker_width_mm"])
                h = float(self._cfg["sticker_height_mm"])
                copies = self._cfg["copies"]
                mode = pcfg.get("printer_mode", "receipt")

                if mode == "label":
                    payload = printing._build_tspl(
                        img, w, h, float(pcfg.get("label_gap_mm", 2)),
                        copies=copies,
                        sensor_align=bool(pcfg.get("sensor_align", True)))
                else:
                    mirrored = bool(pcfg.get("mirror", False))
                    payload = printing._build_escpos(img, mirror=mirrored) * copies
                printing._send_payload(payload)
                self.after(0, self._set_status, f"تمت الطباعة ({copies} نسخة) ✓", COLORS["success"])
            except PermissionError:
                self.after(0, self._set_status,
                           "صلاحية الطابعة مرفوضة (شوف udev rules)", COLORS["danger"])
            except OSError as e:
                self.after(0, self._set_status, f"فشل الطباعة: {e}", COLORS["danger"])

        threading.Thread(target=worker, daemon=True).start()

    def _set_status(self, msg, color):
        self._status.configure(text=reshape_arabic(msg), text_color=color)

    def destroy(self):
        save_cfg(self._cfg)
        super().destroy()


if __name__ == "__main__":
    app = LabelEditor()
    app.mainloop()