# admin_panel.py
import os
import threading
import customtkinter as ctk
from customtkinter import CTkImage
from PIL import Image
from datetime import datetime
from config import APP_NAME, FONT_ARABIC, FONT_ARABIC_BOLD, FONT_HEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, COLORS, BASE_DIR, ADMIN_PASSWORD, DEVICE_TYPES
from arabic_entry import ArabicEntry
from db.database import get_today_orders, update_order, delete_order, add_customer, add_order
from utils import reshape_arabic, save_window_state, restore_or_center, format_datetime, apply_gold_cursor, make_undecorated, enable_resize, make_optionmenu_values
from dropdown import AnimatedOptionMenu


class AdminPanel(ctk.CTk):
    def __init__(self, user):
        super().__init__()
        make_undecorated(self)
        self.user = user
        self.geometry("1000x700")
        self.minsize(900, 650)
        enable_resize(self, 900, 650)
        self.configure(fg_color=COLORS["bg_dark"])

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._clock_timer = None
        restore_or_center(self, "admin_window", 1200, 700)
        self.after(150, lambda: apply_gold_cursor(self))
        self._build_ui()
        self.bind("<Escape>", lambda e: self._logout())
        self.protocol("WM_DELETE_WINDOW", self._logout)

    def _build_ui(self):
        self._build_header()
        self._build_main_content()

    def _build_main_content(self):
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        left_frame = ctk.CTkFrame(main_container, fg_color=COLORS["bg_card"], corner_radius=10)
        left_frame.pack(side="right", fill="both", expand=True)

        right_frame = ctk.CTkFrame(main_container, fg_color=COLORS["bg_card"], corner_radius=10)
        right_frame.pack(side="left", fill="both", expand=True)

        self._build_today_orders(left_frame)
        self._build_right_panel(right_frame)

    def _build_header(self):
        _logo_path = os.path.join(BASE_DIR, "icon.png")
        logo_img = CTkImage(
            light_image=Image.open(_logo_path),
            dark_image=Image.open(_logo_path),
            size=(32, 32)
        )
        from titlebar import TitleBar
        TitleBar(self, APP_NAME, self._logout, logo_image=logo_img).pack(fill="x")

        toolbar = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], height=44, corner_radius=0)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        right_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        right_frame.pack(side="right", padx=20, fill="y")

        self.time_label = ctk.CTkLabel(
            right_frame,
            text="",
            font=FONT_BODY,
            text_color=COLORS["text_light"],
        )
        self.time_label.pack(side="right", padx=(0, 10), pady=10)
        self._clock_timer = None
        self._update_clock()

        date_str = datetime.now().strftime("%d / %m / %Y")
        ctk.CTkLabel(
            toolbar,
            text=date_str,
            font=FONT_BODY,
            text_color=COLORS["text_light"],
        ).place(relx=0.5, rely=0.5, anchor="center")

        left_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        left_frame.pack(side="left", padx=20, fill="y")

        user_text = reshape_arabic(f"المستخدم: {self.user['name']}")
        ctk.CTkLabel(
            left_frame,
            text=user_text,
            font=FONT_BODY,
            text_color=COLORS["text_light"],
        ).pack(side="left", pady=11)

        ctk.CTkButton(
            left_frame,
            text=reshape_arabic("بحث"),
            font=FONT_SMALL,
            width=70,
            height=30,
            corner_radius=6,
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_light"],
            command=self._open_search,
        ).pack(side="left", padx=(12, 0))

        ctk.CTkButton(
            left_frame,
            text=reshape_arabic("تغيير كلمة المرور"),
            font=FONT_SMALL,
            height=30,
            corner_radius=6,
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_light"],
            command=self._change_password,
        ).pack(side="left", padx=(10, 0))

        ctk.CTkButton(
            left_frame,
            text=reshape_arabic("خروج"),
            font=FONT_SMALL,
            width=80,
            height=30,
            corner_radius=6,
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_light"],
            command=self._logout,
        ).pack(side="left", padx=(10, 0))

    def _update_clock(self):
        now = datetime.now().strftime("%I:%M:%S %p")
        self.time_label.configure(text=now)
        self._clock_timer = self.after(1000, self._update_clock)

    def destroy(self):
        save_window_state("admin_window", self.geometry())
        if self._clock_timer:
            self.after_cancel(self._clock_timer)
        super().destroy()

    def _build_today_orders(self, parent):
        table_frame = ctk.CTkFrame(
            parent, fg_color="transparent", corner_radius=10
        )
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        header_bar = ctk.CTkFrame(
            table_frame, fg_color=COLORS["accent_dim"], height=48, corner_radius=0
        )
        header_bar.pack(fill="x")
        header_bar.pack_propagate(False)

        ctk.CTkLabel(
            header_bar,
            text=reshape_arabic("طلبات اليوم"),
            font=FONT_HEADER,
            text_color=COLORS["text_white"],
        ).pack(side="right", padx=15)

        ctk.CTkButton(
            header_bar,
            text=reshape_arabic("تحديث"),
            font=FONT_SMALL,
            width=90,
            height=30,
            corner_radius=6,
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border_light"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_white"],
            command=self._refresh_table,
        ).pack(side="left", padx=15)

        columns_frame = ctk.CTkFrame(
            table_frame, fg_color=COLORS["bg_input"], corner_radius=0
        )
        columns_frame.pack(fill="x", padx=10, pady=(10, 0))

        headers = [
            (reshape_arabic("تحكم"), 120),
            (reshape_arabic("ملاحظات"), 160),
            (reshape_arabic("الجهاز"), 100),
            (reshape_arabic("الهاتف"), 120),
            (reshape_arabic("الزبون"), 140),
            (reshape_arabic("رقم"), 60),
        ]
        for text, width in headers:
            ctk.CTkLabel(
                columns_frame, text=text,
                font=FONT_BODY_BOLD,
                text_color=COLORS["accent"],
                width=width,
            ).pack(side="right", padx=8, pady=10)

        self.orders_scroll = ctk.CTkScrollableFrame(
            table_frame, fg_color="transparent", corner_radius=0,
        )
        self.orders_scroll.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self._refresh_table()

    def _build_right_panel(self, parent):
        form_frame = ctk.CTkFrame(parent, fg_color="transparent")
        form_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            form_frame,
            text=reshape_arabic("إضافة طلب جديد"),
            font=FONT_HEADER,
            text_color=COLORS["accent"],
        ).pack(anchor="e", pady=(0, 20))

        # Date field
        ctk.CTkLabel(form_frame, text=reshape_arabic("التاريخ"), font=FONT_SMALL,
                     text_color=COLORS["text_light"], anchor="e").pack(fill="x", pady=(0, 4))

        self.date_entry = ctk.CTkEntry(
            form_frame, font=FONT_BODY, height=42, corner_radius=6,
            fg_color=COLORS["bg_input"], text_color=COLORS["text_white"],
            border_color=COLORS["border"], justify="center",
            placeholder_text="DD/MM/YYYY"
        )
        self.date_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.date_entry.pack(fill="x", pady=(0, 12))

        # Name field
        ctk.CTkLabel(form_frame, text=reshape_arabic("اسم الزبون"), font=FONT_SMALL,
                     text_color=COLORS["text_light"], anchor="e").pack(fill="x", pady=(0, 4))

        self.name_entry = ArabicEntry(form_frame, placeholder=reshape_arabic(" "), font=FONT_BODY, height=42, corner_radius=6,
                                      fg_color=COLORS["bg_input"], text_color=COLORS["text_white"],
                                      border_color=COLORS["border"])
        self.name_entry.pack(fill="x", pady=(0, 12))

        # Phone field
        ctk.CTkLabel(form_frame, text=reshape_arabic("رقم التلفون"), font=FONT_SMALL,
                     text_color=COLORS["text_light"], anchor="e").pack(fill="x", pady=(0, 4))

        self.phone_entry = ctk.CTkEntry(
            form_frame, font=FONT_BODY, height=42, corner_radius=6,
            fg_color=COLORS["bg_input"], text_color=COLORS["text_white"],
            border_color=COLORS["border"], justify="right",
            placeholder_text=reshape_arabic("01xxxxxxxxx")
        )
        self.phone_entry.pack(fill="x", pady=(0, 12))

        # Device type
        ctk.CTkLabel(form_frame, text=reshape_arabic("نوع الجهاز"), font=FONT_SMALL,
                     text_color=COLORS["text_light"], anchor="e").pack(fill="x", pady=(0, 4))

        self.dev_display, self.dev_map = make_optionmenu_values(DEVICE_TYPES)
        self.device_menu = AnimatedOptionMenu(
            form_frame, values=self.dev_display, font=FONT_BODY, dropdown_font=FONT_BODY,
            height=42, corner_radius=6,
            fg_color=COLORS["bg_input"], button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"], text_color=COLORS["text_white"],
        )
        self.device_menu.set(self.dev_display[0])
        self.device_menu.pack(fill="x", pady=(0, 12))

        # Address (optional)
        ctk.CTkLabel(form_frame, text=reshape_arabic("العنوان (اختياري)"), font=FONT_SMALL,
                     text_color=COLORS["text_light"], anchor="e").pack(fill="x", pady=(0, 4))

        self.address_entry = ArabicEntry(form_frame, placeholder=reshape_arabic(" "), font=FONT_BODY, height=42, corner_radius=6,
                                         fg_color=COLORS["bg_input"], text_color=COLORS["text_white"],
                                         border_color=COLORS["border"])
        self.address_entry.pack(fill="x", pady=(0, 12))

        # Notes (optional)
        ctk.CTkLabel(form_frame, text=reshape_arabic("ملاحظات (اختياري)"), font=FONT_SMALL,
                     text_color=COLORS["text_light"], anchor="e").pack(fill="x", pady=(0, 4))

        self.notes_entry = ArabicEntry(form_frame, placeholder=reshape_arabic(" "), font=FONT_BODY, height=42, corner_radius=6,
                                       fg_color=COLORS["bg_input"], text_color=COLORS["text_white"],
                                       border_color=COLORS["border"])
        self.notes_entry.pack(fill="x", pady=(0, 12))

        # --- سويتش طباعة سعر بحث (صلاحيات أدمن) ---
        self.price_var = ctk.BooleanVar(value=False)
        self.price_switch_row = ctk.CTkFrame(form_frame, fg_color="transparent")
        self.price_switch_row.pack(fill="x", pady=(6, 4))
        self.price_switch = ctk.CTkSwitch(
            self.price_switch_row,
            text=reshape_arabic("طباعة سعر بحث"),
            font=FONT_SMALL,
            variable=self.price_var,
            command=self._on_price_switch,
            progress_color=COLORS["accent"],
            button_color=COLORS["text_white"],
            button_hover_color=COLORS["text_light"],
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_light"],
        )
        self.price_switch.pack(side="right")

        self.price_entry_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        self.price_entry_frame.pack(fill="x", pady=(0, 8))
        # مخفي في البداية
        self.price_entry_frame.pack_forget()
        ctk.CTkLabel(
            self.price_entry_frame,
            text=reshape_arabic("السعر (جنيه)"),
            font=FONT_SMALL,
            text_color=COLORS["text_light"],
            anchor="e",
        ).pack(fill="x", pady=(0, 4))
        self.price_entry = ctk.CTkEntry(
            self.price_entry_frame,
            placeholder_text=reshape_arabic("مثال: 250"),
            font=FONT_BODY,
            height=42,
            corner_radius=6,
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_white"],
            placeholder_text_color=COLORS["text_light"],
            border_color=COLORS["border"],
            justify="center",
        )
        self.price_entry.pack(fill="x")
        self.price_entry.bind("<KeyRelease>", self._on_price_typed)

        # Status label
        self.status_label = ctk.CTkLabel(form_frame, text="", font=FONT_SMALL, text_color=COLORS["danger"])
        self.status_label.pack(pady=(10, 0))

        # Buttons frame
        btn_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(20, 0))

        # Save button
        self.save_btn = ctk.CTkButton(
            btn_frame,
            text=reshape_arabic("حفظ"),
            font=FONT_BODY_BOLD, height=42, corner_radius=6,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_white"],
            command=self._save_order
        )
        self.save_btn.pack(fill="x", pady=(0, 8))

        # Print and Save button
        self.print_save_btn = ctk.CTkButton(
            btn_frame,
            text=reshape_arabic("طباعة وحفظ"),
            font=FONT_BODY_BOLD, height=42, corner_radius=6,
            fg_color=COLORS["info"], hover_color=COLORS["info_hover"],
            text_color=COLORS["text_white"],
            command=self._print_and_save_order
        )
        self.print_save_btn.pack(fill="x", pady=(0, 8))

        # Send via WhatsApp button
        self.send_btn = ctk.CTkButton(
            btn_frame,
            text=reshape_arabic("إرسال واتساب"),
            font=FONT_BODY_BOLD, height=42, corner_radius=6,
            fg_color=COLORS["success"], hover_color=COLORS["success_hover"],
            text_color=COLORS["text_white"],
            command=self._send_whatsapp_order
        )
        self.send_btn.pack(fill="x")

    def _validate_form(self):
        name = self.name_entry.get().strip()
        phone = self.phone_entry.get().strip()
        date_str = self.date_entry.get().strip()

        if not name:
            self.status_label.configure(text=reshape_arabic("يرجى إدخال الاسم"))
            return False
        if not phone:
            self.status_label.configure(text=reshape_arabic("يرجى إدخال رقم التلفون"))
            return False
        if not date_str:
            self.status_label.configure(text=reshape_arabic("يرجى إدخال التاريخ"))
            return False

        # Validate date format
        try:
            day, month, year = date_str.split("/")
            datetime(int(year), int(month), int(day))
        except ValueError:
            self.status_label.configure(text=reshape_arabic("تنسيق التاريخ غير صحيح (DD/MM/YYYY)"))
            return False

        self.status_label.configure(text="")
        return True

    def _get_form_data(self):
        name = self.name_entry.get().strip()
        phone = self.phone_entry.get().strip()
        date_str = self.date_entry.get().strip()
        dev_disp = self.device_menu.get()
        device = self.dev_map.get(dev_disp, dev_disp)
        address = self.address_entry.get().strip()
        notes = self.notes_entry.get().strip()

        day, month, year = date_str.split("/")
        created_at = f"{year}-{month.zfill(2)}-{day.zfill(2)} {datetime.now().strftime('%H:%M:%S')}"

        full_notes = ""
        if address:
            full_notes += f"العنوان: {address}"
        if notes:
            if full_notes:
                full_notes += "\n"
            full_notes += notes

        return name, phone, device, full_notes, created_at

    def _save_order(self):
        if not self._validate_form():
            return

        name, phone, device, full_notes, created_at = self._get_form_data()

        try:
            cid = add_customer(name, phone)
            oid, onum = add_order(cid, self.user["id"], device, full_notes, created_at)
            self._refresh_table()
            self.status_label.configure(text=reshape_arabic(f"تم حفظ الطلب #{onum:04d}"), text_color=COLORS["success"])
            self._clear_form()
        except Exception as e:
            self.status_label.configure(text=reshape_arabic(f"خطأ: {e}"), text_color=COLORS["danger"])

    def _print_and_save_order(self):
        if not self._validate_form():
            return
        if self.price_var.get() and not self._get_price_value():
            self.status_label.configure(text=reshape_arabic("ادخل سعر البحث أولاً"), text_color=COLORS["warning"])
            self.price_entry.focus_set()
            return

        name, phone, device, full_notes, created_at = self._get_form_data()
        price_val = self._get_price_value()
        price_text = f"{price_val} جنيه" if price_val else ""

        try:
            cid = add_customer(name, phone)
            oid, onum = add_order(cid, self.user["id"], device, full_notes, created_at)
            self._refresh_table()
            self.status_label.configure(text=reshape_arabic(f"تم حفظ الطلب #{onum:04d} - جاري الطباعة..."), text_color=COLORS["success"])

            # Print the order مع السعر على السطر السفلي (+5% عن التاريخ)
            from printing import print_sticker
            order_data = {
                "order_number": f"{onum:04d}",
                "customer_name": name,
                "phone": phone,
                "device_type": device,
                "notes": full_notes,
            }
            if price_text:
                order_data["price"] = price_text

            def _do_print():
                ok, msg = print_sticker(order_data, copies=1)
                def _done():
                    if ok:
                        self.status_label.configure(text=reshape_arabic(f"تمت الطباعة #{onum:04d}"), text_color=COLORS["success"])
                    else:
                        self.status_label.configure(text=reshape_arabic(msg), text_color=COLORS["danger"])
                    self._reset_price_switch()
                try:
                    self.after(0, _done)
                except Exception:
                    pass
            threading.Thread(target=_do_print, daemon=True).start()

            self._clear_form()
        except Exception as e:
            self.status_label.configure(text=reshape_arabic(f"خطأ: {e}"), text_color=COLORS["danger"])

    def _send_whatsapp_order(self):
        if not self._validate_form():
            return

        name, phone, device, full_notes, created_at = self._get_form_data()

        try:
            cid = add_customer(name, phone)
            oid, onum = add_order(cid, self.user["id"], device, full_notes, created_at)
            self._refresh_table()
            self.status_label.configure(text=reshape_arabic("جاري الإرسال..."), text_color=COLORS["text_light"])
            self.send_btn.configure(state="disabled")

            # Build WhatsApp message
            address_part = ""
            if self.address_entry.get().strip():
                address_part = f"\nالعنوان: {self.address_entry.get().strip()}"
            notes_part = ""
            if self.notes_entry.get().strip():
                notes_part = f"\nملاحظات: {self.notes_entry.get().strip()}"

            msg = f"طلب خارجي #{onum:04d}\nالاسم: {name}\nالرقم: {phone}{address_part}\nالجهاز: {device}{notes_part}"

            def worker():
                try:
                    import wa_send
                    ok, err = wa_send.send_text_to_all(msg)
                    def done():
                        self.send_btn.configure(state="normal")
                        if ok:
                            self.status_label.configure(text=reshape_arabic("تم الإرسال ✓"), text_color=COLORS["success"])
                            self._clear_form()
                        else:
                            self.status_label.configure(text=reshape_arabic(f"فشل الإرسال: {err}"), text_color=COLORS["danger"])
                    self.after(0, done)
                except Exception as e:
                    self.after(0, lambda: (self.send_btn.configure(state="normal"),
                                           self.status_label.configure(text=reshape_arabic(f"خطأ: {e}"), text_color=COLORS["danger"])))

            threading.Thread(target=worker, daemon=True).start()
        except Exception as e:
            self.status_label.configure(text=reshape_arabic(f"خطأ: {e}"), text_color=COLORS["danger"])

    def _on_price_switch(self):
        if self.price_var.get():
            self.price_entry_frame.pack(fill="x", pady=(0, 8))
            self.after(100, lambda: self.price_entry.focus_set())
        else:
            self.price_entry_frame.pack_forget()
            self.price_entry.delete(0, "end")

    def _on_price_typed(self, *_):
        txt = self.price_entry.get()
        allowed = []
        for ch in txt:
            if ch.isdigit() or ch in ".,٫":
                allowed.append(ch)
        filtered = "".join(allowed)
        filtered = filtered.replace("٫", ".").replace(",", ".")
        if filtered.count(".") > 1:
            parts = filtered.split(".")
            filtered = parts[0] + "." + "".join(parts[1:])
        if len(filtered) > 10:
            filtered = filtered[:10]
        if filtered != txt:
            self.price_entry.delete(0, "end")
            if filtered:
                self.price_entry.insert(0, filtered)

    def _get_price_value(self):
        if not getattr(self, "price_var", None) or not self.price_var.get():
            return ""
        try:
            txt = self.price_entry.get().strip().replace(",", ".").replace("٫", ".")
        except Exception:
            return ""
        if not txt:
            return ""
        try:
            float(txt)
        except ValueError:
            return ""
        if "." in txt:
            txt = txt.rstrip("0").rstrip(".")
        return txt

    def _reset_price_switch(self):
        try:
            if hasattr(self, "price_var"):
                self.price_var.set(False)
            if hasattr(self, "price_switch"):
                self.price_switch.deselect()
            if hasattr(self, "price_entry_frame"):
                self.price_entry_frame.pack_forget()
            if hasattr(self, "price_entry"):
                self.price_entry.delete(0, "end")
        except Exception:
            pass

    def _clear_form(self):
        self.name_entry.delete(0, "end")
        self.phone_entry.delete(0, "end")
        self.address_entry.delete(0, "end")
        self.notes_entry.delete(0, "end")
        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.device_menu.set(self.dev_display[0])
        self._reset_price_switch()

    def _refresh_table(self):
        for widget in self.orders_scroll.winfo_children():
            widget.destroy()

        orders = get_today_orders()

        if not orders:
            ctk.CTkLabel(
                self.orders_scroll,
                text=reshape_arabic("لا توجد طلبات اليوم"),
                font=FONT_BODY,
                text_color=COLORS["text_light"],
            ).pack(pady=50)
            return

        for i, order in enumerate(orders):
            bg = COLORS["bg_hover"] if i % 2 == 0 else COLORS["bg_card"]
            row = ctk.CTkFrame(self.orders_scroll, fg_color=bg, corner_radius=6)
            row.pack(fill="x", pady=2)

            actions = ctk.CTkFrame(row, fg_color="transparent", width=120)
            actions.pack(side="right", padx=4, pady=6)
            actions.pack_propagate(False)

            edit_btn = ctk.CTkButton(
                actions,
                text=reshape_arabic("تعديل"),
                font=FONT_SMALL,
                width=50,
                height=28,
                corner_radius=4,
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"],
                text_color=COLORS["text_white"],
                command=lambda o=order: self._edit_order(o),
            )
            edit_btn.pack(side="right", padx=(2, 0))

            del_btn = ctk.CTkButton(
                actions,
                text=reshape_arabic("حذف"),
                font=FONT_SMALL,
                width=50,
                height=28,
                corner_radius=4,
                fg_color=COLORS["danger"],
                hover_color="#d94a4a",
                text_color=COLORS["text_white"],
                command=lambda o=order: self._delete_order(o),
            )
            del_btn.pack(side="right")

            notes = order["notes"] if order["notes"] else "-"
            ctk.CTkLabel(row, text=reshape_arabic(notes), font=FONT_BODY,
                         text_color=COLORS["text_light"], width=160).pack(side="right", padx=8, pady=11)
            ctk.CTkLabel(row, text=reshape_arabic(order["device_type"]), font=FONT_BODY,
                         text_color=COLORS["text_white"], width=100).pack(side="right", padx=8, pady=11)
            ctk.CTkLabel(row, text=order["phone"], font=FONT_BODY,
                         text_color=COLORS["text_light"], width=120).pack(side="right", padx=8, pady=11)
            ctk.CTkLabel(row, text=reshape_arabic(order["customer_name"]), font=FONT_BODY,
                         text_color=COLORS["text_white"], width=140).pack(side="right", padx=8, pady=11)
            ctk.CTkLabel(row, text=f"#{order['order_number']:04d}", font=FONT_BODY_BOLD,
                         text_color=COLORS["accent"], width=60).pack(side="right", padx=8, pady=11)

    def _delete_order(self, order):
        confirm = ctk.CTkToplevel(self)
        confirm.title("")
        confirm.geometry("360x180")
        confirm.configure(fg_color=COLORS["bg_dark"])
        make_undecorated(confirm)
        enable_resize(confirm, 320, 160)

        x = (self.winfo_screenwidth() - 360) // 2
        y = (self.winfo_screenheight() - 180) // 2
        confirm.geometry(f"360x180+{x}+{y}")
        confirm.bind("<Escape>", lambda e: confirm.destroy())

        ctk.CTkLabel(
            confirm,
            text=reshape_arabic("هل أنت متأكد من حذف هذا الطلب؟"),
            font=FONT_BODY_BOLD,
            text_color=COLORS["text_white"],
        ).pack(pady=(30, 10))

        ctk.CTkLabel(
            confirm,
            text=f"#{order['order_number']:04d} - {order['customer_name']}",
            font=FONT_BODY,
            text_color=COLORS["text_light"],
        ).pack()

        btn_frame = ctk.CTkFrame(confirm, fg_color="transparent")
        btn_frame.pack(pady=(20, 0))

        ctk.CTkButton(
            btn_frame,
            text=reshape_arabic("إلغاء"),
            font=FONT_BODY,
            width=100,
            height=38,
            corner_radius=6,
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_light"],
            command=confirm.destroy,
        ).pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            btn_frame,
            text=reshape_arabic("حذف"),
            font=FONT_BODY_BOLD,
            width=100,
            height=38,
            corner_radius=6,
            fg_color=COLORS["danger"],
            hover_color="#d94a4a",
            text_color=COLORS["text_white"],
            command=lambda: self._confirm_delete(order["id"], confirm),
        ).pack(side="right")

    def _confirm_delete(self, order_id, confirm):
        delete_order(order_id)
        confirm.destroy()
        self._refresh_table()

    def _edit_order(self, order):
        from config import DEVICE_TYPES
        from utils import make_optionmenu_values

        dialog = ctk.CTkToplevel(self)
        dialog.title("")
        dialog.geometry("480x500")
        dialog.configure(fg_color=COLORS["bg_dark"])
        make_undecorated(dialog)
        enable_resize(dialog, 420, 420)

        x = (self.winfo_screenwidth() - 480) // 2
        y = (self.winfo_screenheight() - 500) // 2
        dialog.geometry(f"480x500+{x}+{y}")

        from titlebar import TitleBar
        TitleBar(dialog, reshape_arabic(f"تعديل الطلب #{order['order_number']:04d}"), dialog.destroy).pack(fill="x")
        dialog.bind("<Escape>", lambda e: dialog.destroy())

        form = ctk.CTkFrame(dialog, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=30)

        ctk.CTkLabel(form, text=reshape_arabic("اسم الزبون"), font=FONT_SMALL,
                     text_color=COLORS["text_light"], anchor="e").pack(fill="x", pady=(0, 4))

        name_entry = ctk.CTkEntry(
            form, font=FONT_BODY, height=42, corner_radius=6,
            fg_color=COLORS["bg_input"], text_color=COLORS["text_white"],
            border_color=COLORS["border"], justify="right",
        )
        name_entry.insert(0, order["customer_name"])
        name_entry.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(form, text=reshape_arabic("رقم التلفون"), font=FONT_SMALL,
                     text_color=COLORS["text_light"], anchor="e").pack(fill="x", pady=(0, 4))

        phone_entry = ctk.CTkEntry(
            form, font=FONT_BODY, height=42, corner_radius=6,
            fg_color=COLORS["bg_input"], text_color=COLORS["text_white"],
            border_color=COLORS["border"], justify="right",
        )
        phone_entry.insert(0, order["phone"])
        phone_entry.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(form, text=reshape_arabic("نوع الجهاز"), font=FONT_SMALL,
                     text_color=COLORS["text_light"], anchor="e").pack(fill="x", pady=(0, 4))

        device_display, device_map = make_optionmenu_values(DEVICE_TYPES)
        device_menu = AnimatedOptionMenu(
            form, values=device_display, font=FONT_BODY, dropdown_font=FONT_BODY,
            height=42, corner_radius=6,
            fg_color=COLORS["bg_input"], button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"], text_color=COLORS["text_white"],
        )
        current_device = reshape_arabic(order["device_type"])
        if current_device in device_display:
            device_menu.set(current_device)
        device_menu.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(form, text=reshape_arabic("ملاحظات"), font=FONT_SMALL,
                     text_color=COLORS["text_light"], anchor="e").pack(fill="x", pady=(0, 4))

        notes_entry = ctk.CTkEntry(
            form, font=FONT_BODY, height=42, corner_radius=6,
            fg_color=COLORS["bg_input"], text_color=COLORS["text_white"],
            border_color=COLORS["border"], justify="right",
        )
        notes_entry.insert(0, order.get("notes", ""))
        notes_entry.pack(fill="x", pady=(0, 15))

        btn_frame = ctk.CTkFrame(form, fg_color="transparent")
        btn_frame.pack(fill="x")

        ctk.CTkButton(
            btn_frame,
            text=reshape_arabic("إلغاء"),
            font=FONT_BODY, width=100, height=40, corner_radius=6,
            fg_color="transparent", border_width=1, border_color=COLORS["border"],
            text_color=COLORS["text_light"], command=dialog.destroy,
        ).pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            btn_frame,
            text=reshape_arabic("حفظ"),
            font=FONT_BODY_BOLD, width=100, height=40, corner_radius=6,
            fg_color=COLORS["success"], hover_color=COLORS["success_hover"],
            text_color=COLORS["text_white"],
            command=lambda: self._save_edit(order["id"], name_entry, phone_entry, device_menu, device_map, notes_entry, dialog),
        ).pack(side="right")

    def _save_edit(self, order_id, name_entry, phone_entry, device_menu, device_map, notes_entry, dialog):
        name = name_entry.get().strip()
        phone = phone_entry.get().strip()
        device_display = device_menu.get()
        device = device_map.get(device_display, device_display)
        notes = notes_entry.get().strip()

        if not name or not phone:
            return

        update_order(order_id, name, phone, device, notes)
        dialog.destroy()
        self._refresh_table()

    def _open_search(self):
        from config import DEVICE_TYPES
        from db.database import search_orders
        from utils import make_optionmenu_values

        dialog = ctk.CTkToplevel(self)
        dialog.title("")
        dialog.geometry("820x600")
        dialog.configure(fg_color=COLORS["bg_dark"])
        make_undecorated(dialog)
        enable_resize(dialog, 600, 450)

        def save_and_destroy():
            save_window_state("search_admin", dialog.geometry())
            dialog.destroy()

        restore_or_center(dialog, "search_admin", 820, 600)
        dialog.protocol("WM_DELETE_WINDOW", save_and_destroy)

        from titlebar import TitleBar
        TitleBar(dialog, reshape_arabic("بحث عن طلب"), save_and_destroy).pack(fill="x")

        dialog.bind("<Escape>", lambda e: save_and_destroy())
        dialog.bind("<Return>", lambda e: do_search())

        # filters row
        filters = ctk.CTkFrame(dialog, fg_color="transparent")
        filters.pack(fill="x", padx=20)

        name_entry = ArabicEntry(filters, placeholder=reshape_arabic("الاسم"),
                                font=FONT_SMALL, height=36, width=140)
        name_entry.pack(side="right", padx=4)

        phone_entry = ctk.CTkEntry(filters, font=FONT_SMALL, height=36, width=140,
                                   corner_radius=6, fg_color=COLORS["bg_input"],
                                   text_color=COLORS["text_white"],
                                   border_color=COLORS["border"], justify="right",
                                   placeholder_text=reshape_arabic("رقم التلفون"))
        phone_entry.pack(side="right", padx=4)

        dev_display, dev_map = make_optionmenu_values(DEVICE_TYPES)
        all_text = reshape_arabic("الكل")
        dev_display = [all_text] + dev_display
        dev_map[all_text] = ""
        device_menu = AnimatedOptionMenu(filters, values=dev_display, font=FONT_SMALL,
                                        dropdown_font=FONT_SMALL, height=36, width=140,
                                        corner_radius=6, fg_color=COLORS["bg_input"],
                                        button_color=COLORS["accent"],
                                        button_hover_color=COLORS["accent_hover"],
                                        text_color=COLORS["text_white"])
        device_menu.set(all_text)
        device_menu.pack(side="right", padx=4)

        date_from = ctk.CTkEntry(filters, font=FONT_SMALL, height=36, width=100,
                                 corner_radius=6, fg_color=COLORS["bg_input"],
                                 text_color=COLORS["text_white"],
                                 border_color=COLORS["border"], justify="center",
                                 placeholder_text="DD/MM/YYYY")
        date_from.pack(side="right", padx=2)

        ctk.CTkLabel(filters, text=reshape_arabic("من"), font=FONT_SMALL,
                     text_color=COLORS["text_light"]).pack(side="right", padx=2)

        date_to = ctk.CTkEntry(filters, font=FONT_SMALL, height=36, width=100,
                               corner_radius=6, fg_color=COLORS["bg_input"],
                               text_color=COLORS["text_white"],
                               border_color=COLORS["border"], justify="center",
                               placeholder_text="DD/MM/YYYY")
        date_to.pack(side="right", padx=2)

        ctk.CTkLabel(filters, text=reshape_arabic("إلى"), font=FONT_SMALL,
                     text_color=COLORS["text_light"]).pack(side="right", padx=2)

        def fill_today():
            t = datetime.now().strftime("%d/%m/%Y")
            date_from.delete(0, "end")
            date_from.insert(0, t)
            date_to.delete(0, "end")
            date_to.insert(0, t)

        ctk.CTkButton(
            filters, text=reshape_arabic("اليوم"), font=FONT_SMALL,
            width=50, height=36, corner_radius=6,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_white"],
            command=fill_today,
        ).pack(side="right", padx=(4, 2))

        # results area
        results_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        results_frame.pack(fill="both", expand=True, padx=20, pady=(10, 15))

        result_count = ctk.CTkLabel(results_frame, text="", font=FONT_SMALL,
                                    text_color=COLORS["text_light"])
        result_count.pack(anchor="e", pady=(0, 4))

        # table header
        cols_frame = ctk.CTkFrame(results_frame, fg_color="transparent")
        cols_frame.pack(fill="x")

        col_widths = [
            (reshape_arabic("ملاحظات"), 160),
            (reshape_arabic("الجهاز"), 100),
            (reshape_arabic("الهاتف"), 120),
            (reshape_arabic("الزبون"), 140),
            (reshape_arabic("التاريخ"), 130),
            (reshape_arabic("رقم"), 60),
        ]
        for text, w in col_widths:
            ctk.CTkLabel(cols_frame, text=text, font=FONT_BODY_BOLD,
                         text_color=COLORS["text_light"], width=w,
                         anchor="e").pack(side="right", padx=8, pady=6)

        # separator
        ctk.CTkFrame(results_frame, height=1, fg_color=COLORS["border"]).pack(fill="x")

        scroll = ctk.CTkScrollableFrame(results_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        def do_search():
            for w in scroll.winfo_children():
                w.destroy()

            name_val = name_entry.get().strip()
            phone_val = phone_entry.get().strip()
            dev_val = dev_map.get(device_menu.get(), device_menu.get())
            df = date_from.get().strip()
            dt = date_to.get().strip()

            def _fix_date(s):
                if "/" in s:
                    parts = s.split("/")
                    if len(parts) == 3 and len(parts[2]) == 4:
                        return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                return s
            df = _fix_date(df)
            dt = _fix_date(dt)

            results = search_orders(name_val, phone_val, dev_val, df, dt)
            result_count.configure(text=reshape_arabic(f"النتائج: {len(results)}"))

            if not results:
                ctk.CTkLabel(scroll, text=reshape_arabic("لا توجد نتائج"),
                             font=FONT_BODY, text_color=COLORS["text_light"]).pack(pady=30)
                return

            for i, order in enumerate(results):
                bg = COLORS["bg_hover"] if i % 2 == 0 else COLORS["bg_card"]
                row = ctk.CTkFrame(scroll, fg_color=bg, corner_radius=6)
                row.pack(fill="x", pady=2)

                notes = order["notes"] if order["notes"] else "-"
                ctk.CTkLabel(row, text=reshape_arabic(notes), font=FONT_BODY,
                             text_color=COLORS["text_light"], width=160
                             ).pack(side="right", padx=8, pady=10)
                ctk.CTkLabel(row, text=reshape_arabic(order["device_type"]), font=FONT_BODY,
                             text_color=COLORS["text_white"], width=100
                             ).pack(side="right", padx=8, pady=10)
                ctk.CTkLabel(row, text=order["phone"], font=FONT_BODY,
                             text_color=COLORS["text_light"], width=120
                             ).pack(side="right", padx=8, pady=10)
                ctk.CTkLabel(row, text=reshape_arabic(order["customer_name"]), font=FONT_BODY,
                             text_color=COLORS["text_white"], width=140
                             ).pack(side="right", padx=8, pady=10)
                ctk.CTkLabel(row, text=format_datetime(order["created_at"]), font=FONT_BODY,
                             text_color=COLORS["text_light"], width=130
                             ).pack(side="right", padx=8, pady=10)
                ctk.CTkLabel(row, text=f"#{order['order_number']:04d}", font=FONT_BODY_BOLD,
                             text_color=COLORS["accent"], width=60
                             ).pack(side="right", padx=8, pady=10)

        ctk.CTkButton(
            filters,
            text=reshape_arabic("بحث"),
            font=FONT_BODY_BOLD, width=90, height=36, corner_radius=6,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_white"],
            command=do_search,
        ).pack(side="right", padx=(8, 0))

        self._search_filters = (name_entry, phone_entry, device_menu, dev_map, date_from, date_to, scroll, do_search)

        # run initial empty search
        do_search()

    def _change_password(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("")
        dialog.geometry("380x280")
        dialog.configure(fg_color=COLORS["bg_dark"])
        make_undecorated(dialog)
        enable_resize(dialog, 340, 260)

        x = (self.winfo_screenwidth() - 380) // 2
        y = (self.winfo_screenheight() - 280) // 2
        dialog.geometry(f"380x280+{x}+{y}")

        from titlebar import TitleBar
        TitleBar(dialog, reshape_arabic("تغيير كلمة المرور"), dialog.destroy).pack(fill="x")
        dialog.bind("<Escape>", lambda e: dialog.destroy())

        form = ctk.CTkFrame(dialog, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=30)

        ctk.CTkLabel(form, text=reshape_arabic("كلمة المرور الجديدة"), font=FONT_SMALL,
                     text_color=COLORS["text_light"], anchor="e").pack(fill="x", pady=(0, 4))

        new_pass_entry = ctk.CTkEntry(
            form, font=FONT_BODY, height=42, corner_radius=6,
            fg_color=COLORS["bg_input"], text_color=COLORS["text_white"],
            border_color=COLORS["border"], justify="right", show="*",
        )
        new_pass_entry.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(form, text=reshape_arabic("تأكيد كلمة المرور"), font=FONT_SMALL,
                     text_color=COLORS["text_light"], anchor="e").pack(fill="x", pady=(0, 4))

        confirm_entry = ctk.CTkEntry(
            form, font=FONT_BODY, height=42, corner_radius=6,
            fg_color=COLORS["bg_input"], text_color=COLORS["text_white"],
            border_color=COLORS["border"], justify="right", show="*",
        )
        confirm_entry.pack(fill="x", pady=(0, 15))

        btn_frame = ctk.CTkFrame(form, fg_color="transparent")
        btn_frame.pack(fill="x")

        ctk.CTkButton(
            btn_frame,
            text=reshape_arabic("إلغاء"),
            font=FONT_BODY, width=90, height=38, corner_radius=6,
            fg_color="transparent", border_width=1, border_color=COLORS["border"],
            text_color=COLORS["text_light"], command=dialog.destroy,
        ).pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            btn_frame,
            text=reshape_arabic("حفظ"),
            font=FONT_BODY_BOLD, width=90, height=38, corner_radius=6,
            fg_color=COLORS["success"], hover_color=COLORS["success_hover"],
            text_color=COLORS["text_white"],
            command=lambda: self._save_password(new_pass_entry, confirm_entry, dialog),
        ).pack(side="right")

    def _save_password(self, new_pass_entry, confirm_entry, dialog):
        new_pass = new_pass_entry.get().strip()
        confirm = confirm_entry.get().strip()

        if not new_pass or len(new_pass) < 3:
            return

        if new_pass != confirm:
            return

        from db.database import reset_admin
        try:
            with open(os.path.join(BASE_DIR, "config.py"), "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace(f'ADMIN_PASSWORD = "{ADMIN_PASSWORD}"', f'ADMIN_PASSWORD = "{new_pass}"')
            content = content.replace(f"ADMIN_PASSWORD = '{ADMIN_PASSWORD}'", f"ADMIN_PASSWORD = '{new_pass}'")
            with open(os.path.join(BASE_DIR, "config.py"), "w", encoding="utf-8") as f:
                f.write(content)

            import importlib
            import config as cfg
            importlib.reload(cfg)
            from config import ADMIN_PASSWORD as new_admpw
            reset_admin("codex", new_admpw)

            dialog.destroy()
        except Exception:
            pass

    def _logout(self):
        self.destroy()
        from login import LoginWindow
        app = LoginWindow()
        app.mainloop()
