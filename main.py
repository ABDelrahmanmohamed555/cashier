# main.py
import os
import threading
import time
import customtkinter as ctk
from customtkinter import CTkImage
from PIL import Image
from datetime import datetime
from config import APP_NAME, FONT_ARABIC, FONT_ARABIC_BOLD, FONT_TITLE, FONT_HEADER, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, COLORS, DEVICE_TYPES, BASE_DIR
from db.database import (
    add_customer,
    add_order,
    get_next_order_number,
    get_today_orders,
    search_orders,
    update_order,
)
from utils import reshape_arabic, make_optionmenu_values, save_window_state, restore_or_center, format_datetime, apply_gold_cursor, make_undecorated, enable_resize
from dropdown import AnimatedOptionMenu
from arabic_entry import ArabicEntry
from printing import print_sticker, print_sticker_async, printer_available
from titlebar import TitleBar


class MainWindow(ctk.CTk):
    def __init__(self, user):
        super().__init__()
        make_undecorated(self)
        self.user = user
        self.title(f"Cashier - {user['name']}")
        self.geometry("1100x750")
        self.minsize(950, 650)
        enable_resize(self, 950, 650)
        self.configure(fg_color=COLORS["bg_dark"])

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._clock_timer = None
        self._editing_order_id = None
        self._edit_save_btn = None
        self._edit_cancel_btn = None
        restore_or_center(self, "main_window", 1100, 750)
        self.after(150, lambda: apply_gold_cursor(self))
        self._build_ui()
        self._refresh_orders_table()
        self.bind("<Escape>", lambda e: self._logout())
        self.protocol("WM_DELETE_WINDOW", self._logout)

    def _build_ui(self):
        self._build_header()
        self._build_content()

    def _build_header(self):
        _logo_path = os.path.join(BASE_DIR, "icon.png")
        logo_img = CTkImage(
            light_image=Image.open(_logo_path),
            dark_image=Image.open(_logo_path),
            size=(32, 32),
        )

        titlebar = TitleBar(self, APP_NAME, self._logout, logo_image=logo_img)
        titlebar.pack(fill="x")

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
        save_window_state("main_window", self.geometry())
        if self._clock_timer:
            self.after_cancel(self._clock_timer)
        super().destroy()

    def _build_content(self):
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=15)

        left_panel = ctk.CTkFrame(content, fg_color="transparent", width=450)
        left_panel.pack(side="right", fill="y", padx=(10, 0))
        left_panel.pack_propagate(False)

        right_panel = ctk.CTkFrame(content, fg_color="transparent")
        right_panel.pack(side="left", fill="both", expand=True)

        self._build_order_form(left_panel)
        self._build_orders_table(right_panel)

    def _build_order_form(self, parent):
        form_frame = ctk.CTkFrame(
            parent, fg_color=COLORS["bg_card"], corner_radius=10
        )
        form_frame.pack(fill="both", expand=True)

        header_bar = ctk.CTkFrame(
            form_frame, fg_color=COLORS["accent_dim"], height=48, corner_radius=0
        )
        header_bar.pack(fill="x")
        header_bar.pack_propagate(False)

        self._form_header_label = ctk.CTkLabel(
            header_bar,
            text=reshape_arabic("اضافة جهاز"),
            font=FONT_HEADER,
            text_color=COLORS["text_white"],
        )
        self._form_header_label.pack(expand=True)

        form_body = ctk.CTkFrame(form_frame, fg_color="transparent")
        form_body.pack(fill="both", expand=True, padx=20, pady=15)

        self._create_field(form_body, "اسم الزبون", 0)
        self.customer_name = ArabicEntry(
            form_body,
            placeholder=reshape_arabic(" "),
            font=FONT_BODY,
            height=48,
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_white"],
            placeholder_text_color=COLORS["text_light"],
        )
        self.customer_name.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        self._create_field(form_body, "رقم التلفون", 2)
        self.customer_phone = ctk.CTkEntry(
            form_body,
            placeholder_text="01xxxxxxxxx",
            font=FONT_BODY,
            height=48,
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_white"],
            placeholder_text_color=COLORS["text_light"],
            justify="right",
        )
        self.customer_phone.grid(row=3, column=0, sticky="ew", pady=(0, 12))

        self._create_field(form_body, "نوع الجهاز", 4)
        device_display, self._device_map = make_optionmenu_values(DEVICE_TYPES)
        self.device_type = AnimatedOptionMenu(
            form_body,
            values=device_display,
            font=FONT_BODY,
            dropdown_font=FONT_BODY,
            height=48,
            corner_radius=8,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_white"],
        )
        self.device_type.grid(row=5, column=0, sticky="ew", pady=(0, 12))

        self._create_field(form_body, "ملاحظات", 6)
        self.notes_entry = ArabicEntry(
            form_body,
            placeholder=reshape_arabic(" "),
            font=FONT_BODY,
            height=48,
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_white"],
            placeholder_text_color=COLORS["text_light"],
        )
        self.notes_entry.grid(row=7, column=0, sticky="ew", pady=(0, 12))

        self._create_field(form_body, "عدد نسخ الطباعة", 8)
        copies_row = ctk.CTkFrame(form_body, fg_color="transparent", height=48)
        copies_row.grid(row=9, column=0, sticky="ew", pady=(0, 6))
        copies_row.grid_propagate(False)
        copies_row.columnconfigure(0, weight=1)

        self.copies_entry = ctk.CTkEntry(
            copies_row,
            width=90,
            height=48,
            justify="center",
            font=FONT_BODY,
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_white"],
        )
        self.copies_entry.insert(0, "1")
        self.copies_entry.grid(row=0, column=0, sticky="e")
        self.copies_entry.bind("<KeyRelease>", self._on_copies_typed)

        arrows = ctk.CTkFrame(copies_row, fg_color="transparent", width=40)
        arrows.grid(row=0, column=1, sticky="ns", padx=(6, 8))
        up_btn = ctk.CTkButton(
            arrows, text="\u25b2", width=40, height=22, corner_radius=6,
            font=(ctk.ThemeManager.theme["CTkFont"]["family"], 11),
            fg_color=COLORS["bg_input"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_light"],
            command=lambda: self._step_copies(1),
        )
        up_btn.pack(side="top", fill="x")
        down_btn = ctk.CTkButton(
            arrows, text="\u25bc", width=40, height=22, corner_radius=6,
            font=(ctk.ThemeManager.theme["CTkFont"]["family"], 11),
            fg_color=COLORS["bg_input"], hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_light"],
            command=lambda: self._step_copies(-1),
        )
        down_btn.pack(side="top", fill="x", pady=(2, 0))

        # --- سويتش طباعة سعر بحث ---
        self.price_var = ctk.BooleanVar(value=False)
        self.price_switch_row = ctk.CTkFrame(form_body, fg_color="transparent")
        self.price_switch_row.grid(row=10, column=0, sticky="ew", pady=(6, 4))
        self.price_switch = ctk.CTkSwitch(
            self.price_switch_row,
            text=reshape_arabic("طباعة سعر "),
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
        # صلاحيات أدمن: السويتش متاح فقط للأدمن — الموظف يراه معطّل
        # لو أردت إخفاءه تماما للموظف استبدل pass بـ self.price_switch_row.grid_remove()
        is_admin = self.user.get("role") == "admin"
        if not is_admin:
            # حاليا يظل ظاهر للكل لكن يمكنك تعطيله:
            # self.price_switch.configure(state="disabled")
            pass

        self.price_entry_frame = ctk.CTkFrame(form_body, fg_color="transparent")
        self.price_entry_frame.grid(row=11, column=0, sticky="ew", pady=(0, 8))
        self.price_entry_frame.grid_remove()
        self.price_entry_frame.columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self.price_entry_frame,
            text=reshape_arabic("السعر (جنيه)"),
            font=FONT_SMALL,
            text_color=COLORS["text_light"],
            anchor="e",
        ).grid(row=0, column=0, sticky="e", pady=(0, 4))
        self.price_entry = ctk.CTkEntry(
            self.price_entry_frame,
            placeholder_text=reshape_arabic(" "),
            font=FONT_BODY,
            height=42,
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_white"],
            placeholder_text_color=COLORS["text_light"],
            justify="center",
        )
        self.price_entry.grid(row=1, column=0, sticky="ew")
        self.price_entry.bind("<KeyRelease>", self._on_price_typed)

        form_body.columnconfigure(0, weight=1)

        order_num_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        order_num_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.order_number_label = ctk.CTkLabel(
            order_num_frame,
            text=reshape_arabic(f"رقم الطلب:  #{get_next_order_number():04d}"),
            font=FONT_BODY_BOLD,
            text_color=COLORS["accent"],
        )
        self.order_number_label.pack(side="right")

        save_btn = ctk.CTkButton(
            form_frame,
            text=reshape_arabic("حفظ و طباعة"),
            font=FONT_BODY_BOLD,
            height=48,
            corner_radius=8,
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
            text_color=COLORS["text_white"],
            command=self._save_order,
        )
        save_btn.pack(fill="x", padx=20, pady=(0, 10))

        # --- أزرار التعديل (تظهر فقط عند تفعيل وضع التعديل بقلم التعديل) ---
        self._edit_buttons_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        self._edit_buttons_frame.pack(fill="x", padx=20, pady=(0, 10))
        self._edit_buttons_frame.pack_forget()  # مخفية افتراضياً

        self._edit_save_btn = ctk.CTkButton(
            self._edit_buttons_frame,
            text=reshape_arabic("حفظ التعديل"),
            font=FONT_BODY_BOLD,
            height=48,
            corner_radius=8,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_white"],
            command=self._save_edit,
        )
        self._edit_save_btn.pack(fill="x", pady=(0, 8))

        self._edit_cancel_btn = ctk.CTkButton(
            self._edit_buttons_frame,
            text=reshape_arabic("إلغاء التعديل"),
            font=FONT_BODY,
            height=40,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_light"],
            command=self._cancel_edit,
        )
        self._edit_cancel_btn.pack(fill="x")

        btn_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 15))

        clear_btn = ctk.CTkButton(
            btn_frame,
            text=reshape_arabic("مسح"),
            font=FONT_BODY,
            width=120,
            height=48,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_light"],
            command=self._clear_form,
        )
        clear_btn.pack(side="right", padx=(8, 0))

        external_btn = ctk.CTkButton(
            btn_frame,
            text=reshape_arabic("خارجي"),
            font=FONT_BODY_BOLD,
            width=230,
            height=48,
            corner_radius=8,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_white"],
            command=self._open_external_window,
        )
        external_btn.pack(side="right")

    def _create_field(self, parent, text, row):
        label = ctk.CTkLabel(
            parent,
            text=reshape_arabic(text),
            font=FONT_SMALL,
            text_color=COLORS["text_light"],
            anchor="e",
        )
        label.grid(row=row, column=0, sticky="e", pady=(0, 4))

    def _build_orders_table(self, parent):
        table_frame = ctk.CTkFrame(
            parent, fg_color=COLORS["bg_card"], corner_radius=10
        )
        table_frame.pack(fill="both", expand=True)

        header_bar = ctk.CTkFrame(
            table_frame, fg_color=COLORS["accent_dim"], height=48, corner_radius=0
        )
        header_bar.pack(fill="x")
        header_bar.pack_propagate(False)

        ctk.CTkLabel(
            header_bar,
            text=reshape_arabic("شغل اليوم"),
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
            command=self._refresh_orders_table,
        ).pack(side="left", padx=15)

        columns_frame = ctk.CTkFrame(
            table_frame, fg_color=COLORS["bg_input"], corner_radius=0
        )
        columns_frame.pack(fill="x", padx=10, pady=(10, 0))

        headers = [
            (reshape_arabic("ملاحظات"), 180),
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

    def _refresh_orders_table(self):
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

        # تكبير خط قائمة الطلبات 15% فقط (الريزولوشن متناسق مع زيادة ارتفاع الصف)
        _base_sz = FONT_BODY[1] if isinstance(FONT_BODY, tuple) and len(FONT_BODY) > 1 else 16
        _scaled_sz = int(round(_base_sz * 1.15))
        _font_body_15 = (FONT_ARABIC, _scaled_sz)
        _font_body_bold_15 = (FONT_ARABIC_BOLD, _scaled_sz, "bold")
        # ارتفاع الصف يزيد مع الخط لتجنب التداخل
        _row_pady = int(round(11 * 1.15))  # 11 → 13

        for i, order in enumerate(orders):
            bg = COLORS["bg_hover"] if i % 2 == 0 else COLORS["bg_card"]
            row = ctk.CTkFrame(self.orders_scroll, fg_color=bg, corner_radius=6)
            row.pack(fill="x", pady=2)

            # إخفاء العنوان من عمود الملاحظات — يظهر فقط في نافذة التفاصيل
            raw_notes = order["notes"] if order["notes"] else ""
            display_notes = raw_notes
            if raw_notes.strip().startswith("العنوان:"):
                _parts = raw_notes.split("\n", 1)
                display_notes = _parts[1].strip() if len(_parts) > 1 else ""
            elif "العنوان:" in raw_notes:
                _lines = raw_notes.split("\n")
                _filtered = [l for l in _lines if not l.strip().startswith("العنوان:")]
                display_notes = "\n".join(_filtered).strip()
            if not display_notes.strip():
                display_notes = "-"
            ctk.CTkLabel(row, text=reshape_arabic(display_notes), font=_font_body_15,
                         text_color=COLORS["text_light"], width=180).pack(side="right", padx=8, pady=_row_pady)
            ctk.CTkLabel(row, text=reshape_arabic(order["device_type"]), font=_font_body_15,
                         text_color=COLORS["text_white"], width=100).pack(side="right", padx=8, pady=_row_pady)
            ctk.CTkLabel(row, text=order["phone"], font=_font_body_15,
                         text_color=COLORS["text_light"], width=120).pack(side="right", padx=8, pady=_row_pady)
            ctk.CTkLabel(row, text=reshape_arabic(order["customer_name"]), font=_font_body_15,
                         text_color=COLORS["text_white"], width=140).pack(side="right", padx=8, pady=_row_pady)
            ctk.CTkLabel(row, text=f"#{order['order_number']:04d}", font=_font_body_bold_15,
                         text_color=COLORS["accent"], width=60).pack(side="right", padx=8, pady=_row_pady)

            # أزرار التحكم — في أقصى اليسار
            # زر تعديل ذهبي (قلم واضح) + زر إعادة طباعة أخضر (سهم دائري)
            edit_btn = ctk.CTkButton(
                row,
                text="✏",  # U+270F قلم أوضح وأسمك من ✎
                font=("DejaVu Sans", 17, "bold"),
                width=34,
                height=34,
                corner_radius=6,
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"],
                text_color=COLORS["text_white"],
                command=lambda o=order: self._start_edit(o),
            )
            edit_btn.pack(side="left", padx=(8, 2), pady=6)

            reprint_btn = ctk.CTkButton(
                row,
                text="↻",  # U+21BB سهم دائري لإعادة الطباعة
                font=("DejaVu Sans", 18, "bold"),
                width=34,
                height=34,
                corner_radius=6,
                fg_color=COLORS["success"],
                hover_color=COLORS["success_hover"],
                text_color=COLORS["text_white"],
                command=lambda o=order: self._reprint_order(o),
            )
            reprint_btn.pack(side="left", padx=(2, 8), pady=6)

            # 2 كليك شمال → نافذة تفاصيل بانيميشن سحب (بدون هوفر يسبب جليتش)
            try:
                row.bind("<Double-Button-1>", lambda e, o=order: self._show_order_details(o))
                for ch in row.winfo_children():
                    ch.bind("<Double-Button-1>", lambda e, o=order: (self._show_order_details(o), "break")[1])
            except Exception:
                pass
            # منع الدبل كليك من فتح التفاصيل عند الضغط على أزرار التحكم
            try:
                edit_btn.bind("<Double-Button-1>", lambda e: "break")
                reprint_btn.bind("<Double-Button-1>", lambda e: "break")
            except Exception:
                pass

    def _reprint_order(self, order):
        """إعادة طباعة نفس الطلب بنفس البيانات — زر أخضر بجانب التعديل."""
        try:
            order_data = {
                "order_number": f"{order.get('order_number', 0):04d}",
                "customer_name": order.get("customer_name") or "",
                "phone": order.get("phone") or "",
                "device_type": order.get("device_type") or "",
                "notes": order.get("notes") or "",
            }

            if not printer_available():
                self._show_toast(reshape_arabic("الطابعة غير متصلة"), COLORS["warning"])
                return

            self._show_toast(reshape_arabic(f"جاري إعادة الطباعة  #{order_data['order_number']}"), COLORS["info"])

            def _do_print():
                ok, msg = print_sticker(order_data, copies=1)
                try:
                    self.after(0, lambda: self._show_toast(
                        reshape_arabic(f"{'تمت إعادة الطباعة' if ok else 'فشلت الطباعة'}  #{order_data['order_number']}"),
                        COLORS["success"] if ok else COLORS["danger"],
                    ))
                except Exception:
                    pass

            threading.Thread(target=_do_print, daemon=True).start()
        except Exception as e:
            try:
                self._show_toast(reshape_arabic(f"خطأ إعادة الطباعة: {e}"), COLORS["danger"])
            except Exception:
                pass

    def _show_order_details(self, order):
        """نافذة تفاصيل الطلب بانيميشن سحب جذاب (2 كليك شمال)."""
        # --- تحليل البيانات ---
        raw_notes = order.get("notes") or ""
        address = ""
        pure_notes = raw_notes
        # العنوان محفوظ كـ "العنوان: ...\nباقي الملاحظات"
        if raw_notes.strip().startswith("العنوان:"):
            parts = raw_notes.split("\n", 1)
            address = parts[0].replace("العنوان:", "").strip()
            pure_notes = parts[1].strip() if len(parts) > 1 else ""
        elif "العنوان:" in raw_notes:
            try:
                idx = raw_notes.index("العنوان:")
                end = raw_notes.find("\n", idx)
                if end != -1:
                    address = raw_notes[idx + len("العنوان:"):end].strip()
                    pure_notes = (raw_notes[:idx] + raw_notes[end + 1:]).strip()
                else:
                    address = raw_notes[idx + len("العنوان:"):].strip()
                    pure_notes = raw_notes[:idx].strip()
            except Exception:
                address = ""
        display_address = address if address else ""
        display_notes = pure_notes.strip() if pure_notes.strip() else ""

        created = order.get("created_at") or ""
        date_str, time_str = "", ""
        try:
            dt = datetime.strptime(created[:19], "%Y-%m-%d %H:%M:%S")
            date_str = dt.strftime("%Y/%m/%d")
            time_str = dt.strftime("%I:%M %p")
        except Exception:
            try:
                date_str = created[:10]
                time_str = created[11:16]
            except Exception:
                date_str = created
        order_no = f"#{order.get('order_number', 0):04d}"
        cust = order.get("customer_name") or "-"
        phone = order.get("phone") or "-"
        device = order.get("device_type") or "-"

        # --- إنشاء النافذة ---
        win = ctk.CTkToplevel(self)
        win.title("")
        win.configure(fg_color=COLORS["bg_dark"])
        make_undecorated(win)
        enable_resize(win, 440, 500)
        win.transient(self)
        win.attributes("-topmost", True)
        try:
            win.attributes("-alpha", 0.0)
        except Exception:
            pass

        W, H = 480, 560
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - W) // 2
        y_final = (sh - H) // 2
        # ابدأ بارتفاع صغير (سحب من الأعلى)
        win.geometry(f"{W}x80+{x}+{y_final + H//2 - 40}")
        win.update_idletasks()

        # TitleBar (لا نعمل reshape هنا لأن TitleBar يعملها داخليا — تجنب عكس النص)
        from titlebar import TitleBar
        TitleBar(win, f"تفاصيل الطلب {order_no}", win.destroy).pack(fill="x")
        win.bind("<Escape>", lambda e: win.destroy())
        win.protocol("WM_DELETE_WINDOW", win.destroy)

        container = ctk.CTkFrame(win, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=14)

        # بطاقة علوية برقم الطلب
        top_card = ctk.CTkFrame(container, fg_color=COLORS["accent_dim"], corner_radius=10)
        top_card.pack(fill="x", pady=(6, 12))
        ctk.CTkLabel(top_card, text=order_no, font=(FONT_ARABIC_BOLD, 22, "bold"),
                     text_color=COLORS["text_white"]).pack(pady=12)
        ctk.CTkLabel(top_card, text=reshape_arabic(f"{date_str}  •  {time_str}"),
                     font=FONT_SMALL, text_color=COLORS["text_white"]).pack(pady=(0, 10))

        scroll = ctk.CTkScrollableFrame(container, fg_color="transparent", corner_radius=8,
                                            scrollbar_fg_color=COLORS["bg_dark"],
                                            scrollbar_button_color=COLORS["border"],
                                            scrollbar_button_hover_color=COLORS["accent"])
        scroll.pack(fill="both", expand=True)
        # تحسين سلاسة السكرول: تخفيف الحركة ومنع القفز المباشر
        try:
            _canvas = scroll._parent_canvas
            # تقليل مقدار القفزة الافتراضية
            try:
                _canvas.configure(yscrollincrement=8)
            except Exception:
                pass
            _smooth = {"job": None}
            def _smooth_to(target):
                if _smooth.get("job"):
                    try:
                        win.after_cancel(_smooth["job"])
                    except Exception:
                        pass
                start = _canvas.yview()[0]
                target = max(0.0, min(1.0, target))
                delta = target - start
                if abs(delta) < 0.002:
                    _canvas.yview_moveto(target)
                    return
                steps = 14
                def _step(i=0):
                    t = (i + 1) / steps
                    eased = 1 - pow(1 - t, 3)
                    pos = start + delta * eased
                    try:
                        _canvas.yview_moveto(pos)
                    except Exception:
                        return
                    if i + 1 < steps:
                        _smooth["job"] = win.after(10, lambda: _step(i + 1))
                    else:
                        _smooth["job"] = None
                _step(0)
            def _on_wheel(e):
                try:
                    if hasattr(e, "delta") and e.delta:
                        d = -1 * (e.delta / 120)
                    elif getattr(e, "num", None) == 4:
                        d = -1
                    elif getattr(e, "num", None) == 5:
                        d = 1
                    else:
                        d = 0
                    if d == 0:
                        return "break"
                    cur = _canvas.yview()[0]
                    # كل لفة ~ 9.1% (7.9% +15% حساسية إضافية)
                    target = cur + d * 0.091
                    _smooth_to(target)
                except Exception:
                    pass
                return "break"
            # ربط على الكانفاس والفريم الداخلي (يغطي كل المحتوى)
            _canvas.bind("<MouseWheel>", _on_wheel, add=True)
            _canvas.bind("<Button-4>", _on_wheel, add=True)
            _canvas.bind("<Button-5>", _on_wheel, add=True)
            scroll.bind("<MouseWheel>", _on_wheel, add=True)
            scroll.bind("<Button-4>", _on_wheel, add=True)
            scroll.bind("<Button-5>", _on_wheel, add=True)
            # حماية: عند اغلاق النافذة الغاء الانيميشن
            win.bind("<Destroy>", lambda e: _smooth.update({"job": None}), add="+")
        except Exception:
            pass

        detail_frames = []
        # تكبير خط التفاصيل 20% إجمالي (10% +10% إضافية — الفريم الذهبي يبقى كما هو)
        _d_small_sz = int(round(FONT_SMALL[1] * 1.20)) if isinstance(FONT_SMALL, tuple) and len(FONT_SMALL) > 1 else 18
        _d_body_sz = int(round(FONT_BODY[1] * 1.20)) if isinstance(FONT_BODY, tuple) and len(FONT_BODY) > 1 else 19
        _font_small_10 = (FONT_ARABIC, _d_small_sz)
        _font_body_10 = (FONT_ARABIC, _d_body_sz)

        def add_row(icon, label, value):
            f = ctk.CTkFrame(scroll, fg_color=COLORS["bg_card"], corner_radius=8)
            f.pack(fill="x", pady=5)
            # label +10%
            ctk.CTkLabel(f, text=reshape_arabic(label), font=_font_small_10,
                         text_color=COLORS["text_light"], anchor="e").pack(fill="x", padx=12, pady=(8, 2))
            # value +10%
            val = value if (value and str(value).strip() and str(value).strip() != "-") else reshape_arabic("لا يوجد")
            # لو القيمة عربية نشكلها
            if any("\u0600" <= c <= "\u06FF" for c in str(val)):
                val = reshape_arabic(str(val))
            lbl = ctk.CTkLabel(f, text=val, font=_font_body_10, text_color=COLORS["text_white"],
                               anchor="e", justify="right", wraplength=420)
            lbl.pack(fill="x", padx=12, pady=(0, 10))
            detail_frames.append(f)
            return f

        add_row("👤", "اسم الزبون", cust)
        add_row("📞", "رقم التلفون", phone)
        add_row("📍", "العنوان", display_address if display_address else "لا يوجد")
        add_row("🔧", "نوع الجهاز", device)
        add_row("📅", "التاريخ", date_str)
        add_row("⏰", "الوقت", time_str)
        add_row("🆔", "رقم الطلب", order_no)
        add_row("📝", "ملاحظات", display_notes if display_notes else "لا يوجد")

        # اخفاء التفاصيل مبدئيا لسحب متتالي
        for f in detail_frames:
            f.pack_forget()

        # --- انيميشن سحب ---
        win.grab_set()
        win.after(150, lambda: win.attributes("-topmost", False))

        def ease_out_cubic(t):
            return 1 - pow(1 - t, 3)

        def animate_win(step=0, steps=18):
            t = step / steps
            eased = ease_out_cubic(t)
            h = int(80 + (H - 80) * eased)
            y = int(y_final + (H - h) // 2 * (1 - eased))
            alpha = 0.0 + 1.0 * eased
            try:
                win.geometry(f"{W}x{h}+{x}+{y}")
                win.attributes("-alpha", alpha)
            except Exception:
                pass
            if step < steps:
                win.after(14, lambda: animate_win(step + 1, steps))
            else:
                # بعد انتهاء سحب النافذة — اسحب الصفوف واحد واحد
                def show_rows(idx=0):
                    if idx < len(detail_frames):
                        detail_frames[idx].pack(fill="x", pady=5)
                        # نبضة خفيفة
                        try:
                            f = detail_frames[idx]
                            orig = f.cget("fg_color")
                            f.configure(fg_color=COLORS["bg_hover"])
                            win.after(120, lambda f=f, c=orig: f.configure(fg_color=c))
                        except Exception:
                            pass
                        win.after(55, lambda: show_rows(idx + 1))
                show_rows(0)

        win.after(30, animate_win)

    def _save_order(self, external=False):
        # لو في وضع التعديل، نوجه المستخدم لزر "حفظ التعديل"
        if self._editing_order_id:
            self._show_toast(reshape_arabic("أنت في وضع التعديل — استخدم زر «حفظ التعديل»"), COLORS["warning"])
            return

        name = self.customer_name.get().strip()
        phone = self.customer_phone.get().strip()
        if external:
            device = "خارجي"
        else:
            device_display = self.device_type.get()
            device = self._device_map.get(device_display, device_display)
        notes = self.notes_entry.get().strip()

        if not name or not phone:
            self._show_toast(reshape_arabic("املأ اسم الزبون ورقم التلفون"), COLORS["danger"])
            return

        copies = self._copies_value()
        # سعر البحث (لو السويتش شغال)
        price_val = self._get_price_value()
        if self.price_var.get() and not price_val:
            self._show_toast(reshape_arabic("ادخل سعر البحث أولاً"), COLORS["warning"])
            self.price_entry.focus_set()
            return
        price_text = f"{price_val} جنيه" if price_val else ""
        customer_id = add_customer(name, phone)

        order_numbers = []
        order_datas = []
        for _ in range(copies):
            order_id, order_number = add_order(
                customer_id, self.user["id"], device, notes
            )
            order_numbers.append(order_number)
            od = {
                "order_number": f"{order_number:04d}",
                "customer_name": name,
                "phone": phone,
                "device_type": device,
                "notes": notes,
            }
            if price_text:
                od["price"] = price_text
            order_datas.append(od)

        if printer_available():
            # كل نسخة طلب مستقل برقم مختلف — نطبعهم واحدة واحدة
            # بفاصل للحساس (نفس القيمة في sticker_config.json)
            def _print_all():
                # نقرأ الفاصل من الإعدادات (1000ms افتراضي)
                try:
                    import json as _js
                    from config import BASE_DIR as _BD
                    with open(os.path.join(_BD, "assets", "sticker_config.json"), encoding="utf-8") as _f:
                        _pcfg = _js.load(_f).get("print", {})
                    _delay = float(_pcfg.get("inter_copy_delay_ms", 1000)) / 1000.0
                except Exception:
                    _delay = 1.0
                for idx, od in enumerate(order_datas):
                    ok, msg = print_sticker(od, copies=1)
                    try:
                        self.after(0, lambda ok=ok, msg=msg, num=od["order_number"]: self._show_toast(
                            reshape_arabic(f"تم الحفظ و{msg}  #{num}"),
                            COLORS["success"] if ok else COLORS["danger"],
                        ))
                    except Exception:
                        pass
                    if idx < len(order_datas) - 1:
                        time.sleep(_delay)
                # بعد انتهاء الطباعة: السويتش يتقفل تلقائي
                try:
                    self.after(0, self._reset_price_switch)
                except Exception:
                    pass

            threading.Thread(target=_print_all, daemon=True).start()

            # رسالة فورية مختصرة للنسخ المتعددة
            if copies > 1:
                self._show_toast(
                    reshape_arabic(f"جاري طباعة {copies} طلبات  #{order_numbers[0]:04d}–#{order_numbers[-1]:04d}"),
                    COLORS["success"],
                )
        else:
            if copies == 1:
                self._show_toast(
                    reshape_arabic(f"تم الحفظ  #{order_numbers[0]:04d}  (الطابعة غير متصلة)"),
                    COLORS["warning"],
                )
            else:
                self._show_toast(
                    reshape_arabic(f"تم الحفظ {copies} طلبات  #{order_numbers[0]:04d}–#{order_numbers[-1]:04d}  (الطابعة غير متصلة)"),
                    COLORS["warning"],
                )

        self._clear_form()
        self._refresh_orders_table()

    def _open_external_window(self):
        win = ctk.CTkToplevel(self)
        win.title("")
        win.geometry("480x650")
        win.configure(fg_color=COLORS["bg_dark"])
        make_undecorated(win)
        enable_resize(win, 420, 560)
        restore_or_center(win, "external_order", 480, 650)
        win.protocol("WM_DELETE_WINDOW", lambda: (save_window_state("external_order", win.geometry()), win.destroy()))
        win.bind("<Escape>", lambda e: (save_window_state("external_order", win.geometry()), win.destroy()))

        TitleBar(win, reshape_arabic(" "), lambda: (save_window_state("external_order", win.geometry()), win.destroy()), height=48).pack(fill="x")
        win.attributes("-topmost", True)
        win.after(200, lambda: win.attributes("-topmost", False))
        win.grab_set()

        container = ctk.CTkFrame(win, fg_color="transparent")
        container.pack(expand=True, fill="both", padx=30, pady=20)

        def _field_label(text):
            lbl = ctk.CTkLabel(container, text=reshape_arabic(text), font=FONT_SMALL, text_color=COLORS["text_light"], anchor="e")
            lbl.pack(fill="x", pady=(10, 4))
            return lbl

        _field_label("اسم الزبون")
        name_entry = ArabicEntry(container, placeholder=reshape_arabic(" "), font=FONT_BODY, height=48, corner_radius=8, border_width=1, border_color=COLORS["border"], fg_color=COLORS["bg_input"], text_color=COLORS["text_white"], placeholder_text_color=COLORS["text_light"])
        name_entry.pack(fill="x")

        _field_label("رقم التلفون")
        phone_entry = ctk.CTkEntry(container, placeholder_text="01xxxxxxxxx", font=FONT_BODY, height=48, corner_radius=8, border_width=1, border_color=COLORS["border"], fg_color=COLORS["bg_input"], text_color=COLORS["text_white"], placeholder_text_color=COLORS["text_light"], justify="right")
        phone_entry.pack(fill="x")

        _field_label("العنوان")
        address_entry = ArabicEntry(container, placeholder=reshape_arabic(" "), font=FONT_BODY, height=48, corner_radius=8, border_width=1, border_color=COLORS["border"], fg_color=COLORS["bg_input"], text_color=COLORS["text_white"], placeholder_text_color=COLORS["text_light"])
        address_entry.pack(fill="x")

        _field_label("نوع الجهاز")
        dev_display, dev_map = make_optionmenu_values(DEVICE_TYPES)
        device_menu = AnimatedOptionMenu(container, values=dev_display, font=FONT_BODY, dropdown_font=FONT_BODY, height=48, corner_radius=8, fg_color=COLORS["bg_input"], button_color=COLORS["accent"], button_hover_color=COLORS["accent_hover"], text_color=COLORS["text_white"])
        device_menu.pack(fill="x")
        device_menu.set(dev_display[0] if dev_display else "")

        _field_label("ملاحظات")
        notes_entry = ArabicEntry(container, placeholder=reshape_arabic(" "), font=FONT_BODY, height=48, corner_radius=8, border_width=1, border_color=COLORS["border"], fg_color=COLORS["bg_input"], text_color=COLORS["text_white"], placeholder_text_color=COLORS["text_light"])
        notes_entry.pack(fill="x")

        status_label = ctk.CTkLabel(container, text="", font=FONT_SMALL, text_color=COLORS["danger"])
        status_label.pack(pady=(10, 0))

        def do_send():
            name = name_entry.get().strip()
            phone = phone_entry.get().strip()
            address = address_entry.get().strip()
            dev_disp = device_menu.get()
            device = dev_map.get(dev_disp, dev_disp)
            notes = notes_entry.get().strip()
            if not name or not phone or not address:
                status_label.configure(text=reshape_arabic("املأ الاسم والرقم والعنوان"), text_color=COLORS["danger"])
                return
            # حفظ كطلب خارجي + إرسال واتس مباشر
            full_notes = f"العنوان: {address}" + (f"\n{notes}" if notes else "")
            try:
                cid = add_customer(name, phone)
                oid, onum = add_order(cid, self.user["id"], device, full_notes)
                self._refresh_orders_table()
            except Exception:
                pass
            # صياغة رسالة واتس
            msg = f"طلب خارجي #{onum:04d}\nالاسم: {name}\nالرقم: {phone}\nالعنوان: {address}\nالجهاز: {device}\nملاحظات: {notes if notes else '-'}"
            status_label.configure(text=reshape_arabic("جاري الإرسال..."), text_color=COLORS["text_light"])
            send_btn.configure(state="disabled")

            def worker():
                try:
                    import wa_send
                    ok, err = wa_send.send_text_to_all(msg)
                    def done():
                        send_btn.configure(state="normal")
                        if ok:
                            status_label.configure(text=reshape_arabic("تم الإرسال ✓"), text_color=COLORS["success"])
                            self._show_toast(reshape_arabic(f"تم إرسال الطلب الخارجي #{onum:04d}"), COLORS["success"])
                            win.after(900, lambda: (save_window_state("external_order", win.geometry()), win.destroy()))
                        else:
                            status_label.configure(text=reshape_arabic(f"فشل الإرسال: {err}"), text_color=COLORS["danger"])
                            self._show_toast(reshape_arabic("فشل إرسال الواتس"), COLORS["danger"])
                    self.after(0, done)
                except Exception as e:
                    self.after(0, lambda: (send_btn.configure(state="normal"), status_label.configure(text=reshape_arabic(f"خطأ: {e}"), text_color=COLORS["danger"])))

            threading.Thread(target=worker, daemon=True).start()

        send_btn = ctk.CTkButton(container, text=reshape_arabic("إرسال"), font=FONT_BODY_BOLD, height=52, corner_radius=8, fg_color=COLORS["success"], hover_color=COLORS["success_hover"], text_color=COLORS["text_white"], command=do_send)
        send_btn.pack(fill="x", pady=(20, 0))

        name_entry._frame.focus_set()
        win.bind("<Return>", lambda e: do_send())

    def _copies_value(self):
        """عدد النسخ من الخانة مع تقييد آمن (1..15)."""
        try:
            return max(1, min(15, int(self.copies_entry.get() or "1")))
        except ValueError:
            return 1

    def _step_copies(self, delta):
        val = self._copies_value() + delta
        self.copies_entry.delete(0, "end")
        self.copies_entry.insert(0, str(max(1, min(15, val))))

    def _on_copies_typed(self, *_):
        txt = self.copies_entry.get()
        digits = "".join(ch for ch in txt if ch.isdigit())[:2]
        if digits != txt:
            self.copies_entry.delete(0, "end")
            if digits:
                self.copies_entry.insert(0, digits)
        try:
            val = int(digits)
        except ValueError:
            return
        if val > 15:
            self.copies_entry.delete(0, "end")
            self.copies_entry.insert(0, "15")

    def _on_price_switch(self):
        """إظهار/إخفاء خانة السعر بانيميشن سحب + نبضة السويتش."""
        # إلغاء انيميشن سابق لو موجود
        if not hasattr(self, "_price_anim_job"):
            self._price_anim_job = None
        if self._price_anim_job:
            try:
                self.after_cancel(self._price_anim_job)
            except Exception:
                pass
            self._price_anim_job = None

        if self.price_var.get():
            # سويتش بانيميشن (CTkSwitch يحرك الزر تلقائيا) + نبضة لون
            try:
                self.price_switch.configure(progress_color=COLORS["accent_hover"])
                self.after(180, lambda: self.price_switch.configure(progress_color=COLORS["accent"]))
            except Exception:
                pass
            # إظهار بانيميشن سحب لأسفل
            self.price_entry_frame.grid()
            self.price_entry_frame.update_idletasks()
            target_h = self.price_entry_frame.winfo_reqheight() or 78
            try:
                self.price_entry_frame.grid_propagate(False)
                self.price_entry_frame.configure(height=0)
            except Exception:
                pass

            def _anim_show(step=0, steps=12):
                t = (step + 1) / steps
                eased = 1 - pow(1 - t, 3)
                h = int(target_h * eased)
                try:
                    self.price_entry_frame.configure(height=h)
                except Exception:
                    return
                if step + 1 < steps:
                    self._price_anim_job = self.after(11, lambda: _anim_show(step + 1))
                else:
                    try:
                        self.price_entry_frame.grid_propagate(True)
                        self.price_entry_frame.configure(height=target_h)
                        self.price_entry.focus_set()
                    except Exception:
                        pass
                    self._price_anim_job = None
            _anim_show()
        else:
            cur_h = 0
            try:
                cur_h = self.price_entry_frame.winfo_height() or self.price_entry_frame.winfo_reqheight() or 78
                self.price_entry_frame.grid_propagate(False)
                self.price_entry_frame.configure(height=cur_h)
            except Exception:
                pass

            def _anim_hide(step=0, steps=12):
                t = (step + 1) / steps
                eased = 1 - pow(1 - t, 3)
                h = int(cur_h * (1 - eased))
                try:
                    self.price_entry_frame.configure(height=max(0, h))
                except Exception:
                    return
                if step + 1 < steps:
                    self._price_anim_job = self.after(11, lambda: _anim_hide(step + 1))
                else:
                    try:
                        self.price_entry_frame.grid_remove()
                        self.price_entry_frame.grid_propagate(True)
                        self.price_entry.delete(0, "end")
                        self.price_switch.configure(progress_color=COLORS["accent"])
                    except Exception:
                        pass
                    self._price_anim_job = None
            _anim_hide()

    def _on_price_typed(self, *_):
        """السماح بأرقام ونقطة واحدة فقط."""
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
        # حد أقصى 7 خانات (مثال 9999999 أو 9999.99)
        if len(filtered) > 10:
            filtered = filtered[:10]
        if filtered != txt:
            self.price_entry.delete(0, "end")
            if filtered:
                self.price_entry.insert(0, filtered)

    def _get_price_value(self):
        """إرجاع السعر كنص رقمي إذا السويتش مفعل وإلا فارغ."""
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
        """إقفال السويتش تلقائي بعد الطباعة — بانيميشن."""
        try:
            if hasattr(self, "price_var"):
                self.price_var.set(False)
            if hasattr(self, "price_switch"):
                try:
                    self.price_switch.deselect()
                    self.price_switch.configure(progress_color=COLORS["accent"])
                except Exception:
                    pass
            # لو الفريم ظاهر اعمل انيميشن اخفاء
            if hasattr(self, "price_entry_frame") and self.price_entry_frame.winfo_manager():
                try:
                    if hasattr(self, "_price_anim_job") and self._price_anim_job:
                        try:
                            self.after_cancel(self._price_anim_job)
                        except Exception:
                            pass
                    cur_h = self.price_entry_frame.winfo_height() or self.price_entry_frame.winfo_reqheight() or 78
                    self.price_entry_frame.grid_propagate(False)
                    self.price_entry_frame.configure(height=cur_h)

                    def _anim_reset(step=0, steps=12):
                        t = (step + 1) / steps
                        eased = 1 - pow(1 - t, 3)
                        h = int(cur_h * (1 - eased))
                        try:
                            self.price_entry_frame.configure(height=max(0, h))
                        except Exception:
                            return
                        if step + 1 < steps:
                            self._price_anim_job = self.after(11, lambda: _anim_reset(step + 1))
                        else:
                            try:
                                self.price_entry_frame.grid_remove()
                                self.price_entry_frame.grid_propagate(True)
                                self.price_entry.delete(0, "end")
                            except Exception:
                                pass
                            self._price_anim_job = None
                    _anim_reset()
                    return
                except Exception:
                    pass
            if hasattr(self, "price_entry_frame"):
                try:
                    self.price_entry_frame.grid_remove()
                    self.price_entry_frame.grid_propagate(True)
                except Exception:
                    pass
            if hasattr(self, "price_entry"):
                self.price_entry.delete(0, "end")
        except Exception:
            pass

    def _clear_form(self):
        self.customer_name.delete(0, "end")
        self.customer_phone.delete(0, "end")
        self.notes_entry.delete(0, "end")
        self.copies_entry.delete(0, "end")
        self.copies_entry.insert(0, "1")
        self.device_type.set(reshape_arabic(DEVICE_TYPES[0]))
        self._reset_price_switch()
        self.order_number_label.configure(
            text=reshape_arabic(f"رقم الطلب:  #{get_next_order_number():04d}")
        )
        self._exit_edit_mode()

    # ---------- وضع التعديل ----------

    def _start_edit(self, order):
        """تحميل بيانات الطلب في الخانات وتفعيل وضع التعديل."""
        self._editing_order_id = order["id"]

        # تحميل البيانات في الخانات
        self.customer_name.delete(0, "end")
        self.customer_name.insert(0, order["customer_name"])

        self.customer_phone.delete(0, "end")
        self.customer_phone.insert(0, order["phone"])

        # ضبط نوع الجهاز (لو مش موجود في القائمة نضيفه مؤقتاً)
        dev_display = reshape_arabic(order["device_type"])
        if dev_display not in self.device_type._values:
            self.device_type.configure(values=list(self.device_type._values) + [dev_display])
            self._device_map[dev_display] = order["device_type"]
        self.device_type.set(dev_display)

        # الملاحظات: نعرضها كاملة (بما فيها العنوان لو موجود)
        self.notes_entry.delete(0, "end")
        self.notes_entry.insert(0, order["notes"] or "")

        # إظهار أزرار التعديل
        if self._edit_buttons_frame is not None:
            self._edit_buttons_frame.pack(fill="x", padx=20, pady=(0, 10))

        # تحديث عنوان النموذج
        try:
            header_bar = self._form_header_label
            header_bar.configure(text=reshape_arabic(f"تعديل الطلب #{order['order_number']:04d}"))
        except Exception:
            pass

        self.order_number_label.configure(
            text=reshape_arabic(f"تعديل الطلب:  #{order['order_number']:04d}")
        )

        self._show_toast(reshape_arabic(f"جاري تعديل الطلب #{order['order_number']:04d}"), COLORS["info"])
        self.customer_name.focus_set()

    def _save_edit(self):
        """حفظ التعديلات بدون طباعة."""
        if not self._editing_order_id:
            return

        name = self.customer_name.get().strip()
        phone = self.customer_phone.get().strip()
        if not name or not phone:
            self._show_toast(reshape_arabic("املأ اسم الزبون ورقم التلفون"), COLORS["danger"])
            return

        device_display = self.device_type.get()
        device = self._device_map.get(device_display, device_display)
        notes = self.notes_entry.get().strip()

        try:
            ok = update_order(self._editing_order_id, name, phone, device, notes)
            if ok:
                self._show_toast(reshape_arabic("تم حفظ التعديل بنجاح"), COLORS["success"])
            else:
                self._show_toast(reshape_arabic("فشل حفظ التعديل"), COLORS["danger"])
        except Exception as e:
            self._show_toast(reshape_arabic(f"خطأ في الحفظ: {e}"), COLORS["danger"])
            return

        self._exit_edit_mode()
        self._clear_form()
        self._refresh_orders_table()

    def _cancel_edit(self):
        """إلغاء وضع التعديل والعودة لوضع الإضافة."""
        self._exit_edit_mode()
        self._clear_form()
        self._show_toast(reshape_arabic("تم إلغاء التعديل"), COLORS["text_light"])

    def _exit_edit_mode(self):
        """إخفاء أزرار التعديل وإعادة النموذج لوضع الإضافة."""
        self._editing_order_id = None
        if self._edit_buttons_frame is not None:
            try:
                self._edit_buttons_frame.pack_forget()
            except Exception:
                pass
        # إعادة عنوان النموذج
        try:
            header_bar = self._form_header_label
            header_bar.configure(text=reshape_arabic("اضافة جهاز"))
        except Exception:
            pass
        self.order_number_label.configure(
            text=reshape_arabic(f"رقم الطلب:  #{get_next_order_number():04d}")
        )

    def _show_toast(self, message, color):
        toast = ctk.CTkToplevel(self)
        make_undecorated(toast)
        toast.configure(fg_color=color)
        toast.attributes("-topmost", True)

        w, h = 340, 55
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = self.winfo_screenheight() - 80
        toast.geometry(f"{w}x{h}+{x}+{y}")

        ctk.CTkLabel(
            toast,
            text=message,
            font=FONT_BODY_BOLD,
            text_color="white",
        ).pack(expand=True)

        toast.after(2000, toast.destroy)

    def _open_search(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("")
        dialog.geometry("820x600")
        dialog.configure(fg_color=COLORS["bg_dark"])
        make_undecorated(dialog)
        enable_resize(dialog, 600, 450)

        def save_and_destroy():
            save_window_state("search_main", dialog.geometry())
            dialog.destroy()

        restore_or_center(dialog, "search_main", 820, 600)
        dialog.protocol("WM_DELETE_WINDOW", save_and_destroy)

        from titlebar import TitleBar
        TitleBar(dialog, reshape_arabic("بحث عن طلب"), save_and_destroy).pack(fill="x")

        dialog.bind("<Escape>", lambda e: save_and_destroy())
        dialog.bind("<Return>", lambda e: do_search())

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
        device_menu = ctk.CTkOptionMenu(filters, values=dev_display, font=FONT_SMALL,
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

        results_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        results_frame.pack(fill="both", expand=True, padx=20, pady=(10, 15))

        result_count = ctk.CTkLabel(results_frame, text="", font=FONT_SMALL,
                                    text_color=COLORS["text_light"])
        result_count.pack(anchor="e", pady=(0, 4))

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

                raw_notes = order["notes"] if order["notes"] else ""
                _dn = raw_notes
                if raw_notes.strip().startswith("العنوان:"):
                    _p = raw_notes.split("\n", 1)
                    _dn = _p[1].strip() if len(_p) > 1 else ""
                elif "العنوان:" in raw_notes:
                    _ln = raw_notes.split("\n")
                    _dn = "\n".join([l for l in _ln if not l.strip().startswith("العنوان:")]).strip()
                if not _dn.strip():
                    _dn = "-"
                ctk.CTkLabel(row, text=reshape_arabic(_dn), font=FONT_BODY,
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

        do_search()

    def _logout(self):
        self.destroy()
        from login import LoginWindow
        app = LoginWindow()
        app.mainloop()