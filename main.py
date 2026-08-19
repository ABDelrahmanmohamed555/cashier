# main.py
import os
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
)
from utils import reshape_arabic, make_optionmenu_values, save_window_state, restore_or_center, format_datetime, apply_gold_cursor, make_undecorated, enable_resize
from dropdown import AnimatedOptionMenu
from arabic_entry import ArabicEntry
from printing import print_sticker_async, printer_available
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

        ctk.CTkLabel(
            header_bar,
            text=reshape_arabic("اضافة جهاز"),
            font=FONT_HEADER,
            text_color=COLORS["text_white"],
        ).pack(expand=True)

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
            placeholder=reshape_arabic("اختياري"),
            font=FONT_BODY,
            height=48,
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_white"],
            placeholder_text_color=COLORS["text_light"],
        )
        self.notes_entry.grid(row=7, column=0, sticky="ew", pady=(0, 15))

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

        save_btn = ctk.CTkButton(
            btn_frame,
            text=reshape_arabic("حفظ و طباعة"),
            font=FONT_BODY_BOLD,
            width=160,
            height=48,
            corner_radius=8,
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
            text_color=COLORS["text_white"],
            command=self._save_order,
        )
        save_btn.pack(side="right")

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

        for i, order in enumerate(orders):
            bg = COLORS["bg_hover"] if i % 2 == 0 else COLORS["bg_card"]
            row = ctk.CTkFrame(self.orders_scroll, fg_color=bg, corner_radius=6)
            row.pack(fill="x", pady=2)

            notes = order["notes"] if order["notes"] else "-"
            ctk.CTkLabel(row, text=reshape_arabic(notes), font=FONT_BODY,
                         text_color=COLORS["text_light"], width=180).pack(side="right", padx=8, pady=11)
            ctk.CTkLabel(row, text=reshape_arabic(order["device_type"]), font=FONT_BODY,
                         text_color=COLORS["text_white"], width=100).pack(side="right", padx=8, pady=11)
            ctk.CTkLabel(row, text=order["phone"], font=FONT_BODY,
                         text_color=COLORS["text_light"], width=120).pack(side="right", padx=8, pady=11)
            ctk.CTkLabel(row, text=reshape_arabic(order["customer_name"]), font=FONT_BODY,
                         text_color=COLORS["text_white"], width=140).pack(side="right", padx=8, pady=11)
            ctk.CTkLabel(row, text=f"#{order['order_number']:04d}", font=FONT_BODY_BOLD,
                         text_color=COLORS["accent"], width=60).pack(side="right", padx=8, pady=11)

    def _save_order(self):
        name = self.customer_name.get().strip()
        phone = self.customer_phone.get().strip()
        device_display = self.device_type.get()
        device = self._device_map.get(device_display, device_display)
        notes = self.notes_entry.get().strip()

        if not name or not phone:
            self._show_toast(reshape_arabic("املأ اسم الزبون ورقم التلفون"), COLORS["danger"])
            return

        customer_id = add_customer(name, phone)
        order_id, order_number = add_order(
            customer_id, self.user["id"], device, notes
        )

        if printer_available():
            order_data = {
                "order_number": f"{order_number:04d}",
                "customer_name": name,
                "phone": phone,
                "device_type": device,
                "notes": notes,
            }
            print_sticker_async(
                order_data,
                callback=lambda ok, msg: self.after(0, lambda: self._show_toast(
                    reshape_arabic(f"تم الحفظ و{msg}  #{order_number:04d}"),
                    COLORS["success"] if ok else COLORS["danger"],
                )),
            )
        else:
            self._show_toast(
                reshape_arabic(f"تم الحفظ  #{order_number:04d}  (الطابعة غير متصلة)"),
                COLORS["warning"],
            )

        self._clear_form()
        self._refresh_orders_table()

    def _clear_form(self):
        self.customer_name.delete(0, "end")
        self.customer_phone.delete(0, "end")
        self.notes_entry.delete(0, "end")
        self.device_type.set(reshape_arabic(DEVICE_TYPES[0]))
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

        do_search()

    def _logout(self):
        self.destroy()
        from login import LoginWindow
        app = LoginWindow()
        app.mainloop()
