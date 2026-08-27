# login.py
import os
import customtkinter as ctk
from customtkinter import CTkImage
from PIL import Image
from config import APP_NAME, FONT_ARABIC, FONT_ARABIC_BOLD, FONT_TITLE, FONT_BODY, FONT_BODY_BOLD, FONT_SMALL, COLORS, BASE_DIR
from db.database import authenticate
from utils import reshape_arabic, save_window_state, restore_or_center, apply_gold_cursor, make_undecorated, enable_resize

LOGO_PATH = os.path.join(BASE_DIR, "icon.png")


class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        make_undecorated(self)
        self.geometry("480x650")
        enable_resize(self, 420, 560)
        self.configure(fg_color=COLORS["bg_dark"])

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        restore_or_center(self, "login", 480, 650)
        from titlebar import TitleBar
        titlebar = TitleBar(self, APP_NAME, self.destroy, height=48)
        titlebar.pack(fill="x")
        self.update_idletasks()
        w, h = (int(x) for x in self.geometry().split("+")[0].split("x"))
        if h < 690:
            self.geometry(f"{w}x{h + 48}")
        self.after(150, lambda: apply_gold_cursor(self))
        self._build_ui()
        self.bind("<Escape>", lambda e: self.destroy())

    def destroy(self):
        save_window_state("login", self.geometry())
        super().destroy()

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"])
        container.pack(expand=True, fill="both", padx=50, pady=25)

        top_section = ctk.CTkFrame(container, fg_color="transparent")
        top_section.pack(fill="x", pady=(20, 0))

        logo_img = CTkImage(
            light_image=Image.open(LOGO_PATH),
            dark_image=Image.open(LOGO_PATH),
            size=(110, 110)
        )

        logo_label = ctk.CTkLabel(
            top_section,
            text="",
            image=logo_img,
        )
        logo_label.pack(pady=(0, 10))

        title = ctk.CTkLabel(
            top_section,
            text=reshape_arabic("المركز الفني للصيانة"),
            font=FONT_TITLE,
            text_color=COLORS["text_white"],
        )
        title.pack()
        self._title_width = title.winfo_reqwidth() + 8  # عرض ثابت عشان الكتابة متزحزحش
        title.configure(text="")                        # مخفي أول ما النافذة تفتح

        subtitle = ctk.CTkLabel(
            top_section,
            text=reshape_arabic("نظام إدارة الصيانة"),
            font=FONT_BODY,
            text_color=COLORS["text_light"],
        )
        subtitle.pack(pady=(5, 0))
        subtitle.configure(text_color=COLORS["bg_dark"])  # مخفي أول ما النافذة تفتح

        form_section = ctk.CTkFrame(container, fg_color="transparent")
        form_section.pack(fill="x", pady=(25, 0))

        username_label = ctk.CTkLabel(
            form_section,
            text=reshape_arabic("اسم المستخدم"),
            font=FONT_BODY,
            text_color=COLORS["text_light"],
            anchor="e",
        )
        username_label.pack(fill="x", pady=(0, 8))

        self.username_entry = ctk.CTkEntry(
            form_section,
            placeholder_text=reshape_arabic("ادخل اسم المستخدم"),
            font=FONT_BODY,
            height=50,
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_white"],
            placeholder_text_color=COLORS["text_light"],
            justify="right",
        )
        self.username_entry.pack(fill="x", pady=(0, 15))
        self.username_entry.bind("<Return>", lambda e: self.password_entry.focus_set())

        password_label = ctk.CTkLabel(
            form_section,
            text=reshape_arabic("كلمة المرور"),
            font=FONT_BODY,
            text_color=COLORS["text_light"],
            anchor="e",
        )
        password_label.pack(fill="x", pady=(0, 8))

        self.password_entry = ctk.CTkEntry(
            form_section,
            placeholder_text=reshape_arabic("ادخل كلمة المرور"),
            font=FONT_BODY,
            height=50,
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_white"],
            placeholder_text_color=COLORS["text_light"],
            show="●",
            justify="right",
        )
        self.password_entry.pack(fill="x")

        self.error_label = ctk.CTkLabel(
            form_section,
            text="",
            font=FONT_SMALL,
            text_color=COLORS["danger"],
        )
        self.error_label.pack(pady=(10, 0))

        bottom_section = ctk.CTkFrame(container, fg_color="transparent")
        bottom_section.pack(fill="x", pady=(20, 0))

        login_btn = ctk.CTkButton(
            bottom_section,
            text=reshape_arabic("دخول"),
            font=FONT_BODY_BOLD,
            height=52,
            corner_radius=8,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_white"],
            command=self._login,
        )
        login_btn.pack(fill="x")

        self.password_entry.bind("<Return>", lambda e: self._login())

        footer = ctk.CTkLabel(
            container,
            text=reshape_arabic("مركز الصيانة - نظام الكاشير"),
            font=FONT_SMALL,
            text_color=COLORS["border_light"],
        )
        footer.pack(side="bottom", pady=(20, 0))

        # أزرار ومدخلات مخفية بصريًا في البداية — هتظهر بالأنيميشن
        self._intro_queue = []
        self._intro_queue.append((username_label, "text_color", COLORS["bg_dark"], COLORS["text_light"]))
        self._intro_queue.append((self.username_entry, "fg_color", COLORS["bg_dark"], COLORS["bg_input"]))
        self._intro_queue.append((self.username_entry, "border_color", COLORS["bg_dark"], COLORS["border"]))
        self._intro_queue.append((password_label, "text_color", COLORS["bg_dark"], COLORS["text_light"]))
        self._intro_queue.append((self.password_entry, "fg_color", COLORS["bg_dark"], COLORS["bg_input"]))
        self._intro_queue.append((self.password_entry, "border_color", COLORS["bg_dark"], COLORS["border"]))
        self._intro_queue.append((login_btn, "fg_color", COLORS["bg_dark"], COLORS["accent"]))
        self._intro_queue.append((login_btn, "text_color", COLORS["bg_dark"], COLORS["text_white"]))
        self._apply_intro_hidden()

        self.logo_label = logo_label
        self.title_label = title
        self.subtitle_label = subtitle
        self.logo_label.configure(image=self._transparent_logo(110))  # اللوجو مش باين أول ما النافذة تفتح
        self.after(150, self._play_intro)
        self.after(300, lambda: self.username_entry.focus_set())

    # ---------- أنيميشن الدخول ----------

    @staticmethod
    def _hex_rgb(color):
        color = color.lstrip("#")
        return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))

    def _transparent_logo(self, size):
        layer = Image.open(LOGO_PATH).convert("RGBA")
        layer.putalpha(0)
        comp = Image.new("RGBA", layer.size, self._hex_rgb(COLORS["bg_dark"]) + (255,))
        comp.alpha_composite(layer)
        return CTkImage(light_image=comp.convert("RGB"), dark_image=comp.convert("RGB"),
                        size=(size, size))

    def _mix_hex(self, c1, c2, t):
        a, b = self._hex_rgb(c1), self._hex_rgb(c2)
        return "#" + "".join(f"{int(x + (y - x) * t):02x}" for x, y in zip(a, b))

    def _ramp(self, widget, prop, c_from, c_to, steps=6, ms=35, on_done=None):
        def tick(i=0):
            if i > steps:
                widget.configure(**{prop: c_to})
                if on_done:
                    on_done()
                return
            widget.configure(**{prop: self._mix_hex(c_from, c_to, i / steps) if 0 < i < steps else (c_from if i == 0 else c_to)})
            widget.after(ms, lambda: tick(i + 1))
        tick(0)

    def _apply_intro_hidden(self):
        for widget, prop, c_from, _c_to in self._intro_queue:
            widget.configure(**{prop: c_from})

    def _play_intro(self):
        self._fade_logo()
        self.after(750, self._type_title)      # بعد ما اللوجو يخلص
        self.after(2230, self._reveal_subtitle)
        self.after(2400, self._reveal_form)    # بعد ما العنوان يخلص ويستقر بلونه الأبيض

    def _reveal_subtitle(self):
        self._ramp(self.subtitle_label, "text_color", COLORS["bg_dark"],
                   COLORS["text_light"], steps=8, ms=30)

    def _fade_logo(self, steps=16, ms=40):
        """اللوجو يظهر بتلاشي تدريجي (من لون الخلفية للصورة الكاملة)."""
        base = Image.open(LOGO_PATH).convert("RGBA")
        bg = self._hex_rgb(COLORS["bg_dark"]) + (255,)
        size = (110, 110)

        def tick(i=0):
            if i > steps:
                full = CTkImage(light_image=Image.open(LOGO_PATH), dark_image=Image.open(LOGO_PATH), size=size)
                self.logo_label.configure(image=full)
                return
            layer = base.copy()
            layer.putalpha(int(255 * i / steps))
            comp = Image.new("RGBA", layer.size, bg)
            comp.alpha_composite(layer)
            img = CTkImage(light_image=comp.convert("RGB"), dark_image=comp.convert("RGB"), size=size)
            self.logo_label.configure(image=img)
            self.after(ms, lambda: tick(i + 1))

        tick(0)

    def _type_title(self, on_done=None):
        """العنوان بيتكتب حرف حرف بلون ذهبي وبعد ما يخلص يبقى أبيض."""
        raw = "المركز الفني للصيانة"
        full = reshape_arabic(raw)
        self.title_label.configure(text=full, text_color=COLORS["accent"])
        self.title_label.configure(width=self._title_width, text="")

        def tick(i=0):
            if i >= len(raw):
                self.title_label.configure(text=full)
                self.after(250, lambda: self.title_label.configure(text_color=COLORS["text_white"]))
                if on_done:
                    on_done()
                return
            self.title_label.configure(text=reshape_arabic(raw[:i + 1]))
            self.after(70, lambda: tick(i + 1))

        tick(0)

    def _reveal_form(self):
        """خانات الاسم وكلمة المرور وزر الدخول يظهروا ورا بعض بسرعة (أسرع 15% من قبل)."""
        ramp_ms = 25
        gap_ms = 63

        def start(idx=0):
            if idx >= len(self._intro_queue):
                return
            widget, prop, c_from, c_to = self._intro_queue[idx]
            self._ramp(widget, prop, c_from, c_to, steps=6, ms=ramp_ms,
                       on_done=lambda: done(idx))

        def done(idx):
            nxt = idx + 1
            if nxt >= len(self._intro_queue):
                self.after(100, lambda: self.username_entry.focus_set())
                return
            same = self._intro_queue[nxt][0] is self._intro_queue[idx][0]
            if same:
                start(nxt)                     # نفس الخانة (لون ولون حدود) — كمّل فورًا
            else:
                self.after(gap_ms, start, nxt) # خانة جديدة — فاصل بسيط

        start()

    def _login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            self.error_label.configure(
                text=reshape_arabic("من فضلك املأ جميع الحقول")
            )
            return

        user = authenticate(username, password)
        if user:
            self.error_label.configure(text="")
            self._open_next(user)
        else:
            self.error_label.configure(
                text=reshape_arabic("بيانات الدخول غير صحيحة")
            )

    def _open_next(self, user):
        self.destroy()
        if user["role"] == "admin":
            from admin_panel import AdminPanel
            app = AdminPanel(user)
            app.mainloop()
        else:
            from main import MainWindow
            app = MainWindow(user)
            app.mainloop()
