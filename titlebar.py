# titlebar.py
import customtkinter as ctk
from config import COLORS, FONT_BODY_BOLD
from utils import reshape_arabic


class TitleBar(ctk.CTkFrame):
    """شريط علوي خاص بنوافذ بدون إطار: سحب + تصغير + إغلاق + تكبير بدبل كليك."""

    def __init__(self, master, title, on_close, height=48, logo_image=None):
        super().__init__(master, height=height, fg_color=COLORS["bg_card"],
                         corner_radius=0)
        self.pack_propagate(False)

        self._prev_geometry = None
        self._maximized = False
        self._dx = self._dy = 0

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="right", padx=14, fill="y")

        if logo_image is not None:
            self._logo = ctk.CTkLabel(right, text="", image=logo_image)
            self._logo.pack(side="right", pady=5)

        self.title_label = ctk.CTkLabel(
            right,
            text=reshape_arabic(title),
            font=FONT_BODY_BOLD,
            text_color=COLORS["text_white"],
        )
        self.title_label.pack(side="right", padx=(0, 10), pady=12)

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", padx=8, fill="y")

        self.close_btn = ctk.CTkButton(
            left,
            text="\u2715",
            width=36, height=32, corner_radius=6,
            font=(ctk.ThemeManager.theme["CTkFont"]["family"], 13),
            fg_color="transparent",
            border_width=1, border_color=COLORS["border"],
            hover_color=COLORS["danger"],
            text_color=COLORS["text_light"],
            command=on_close,
        )
        self.close_btn.pack(side="left", padx=3, pady=8)

        self.max_btn = ctk.CTkButton(
            left,
            text="\u25a1",
            width=36, height=32, corner_radius=6,
            font=(ctk.ThemeManager.theme["CTkFont"]["family"], 13),
            fg_color="transparent",
            border_width=1, border_color=COLORS["border"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_light"],
            command=self._toggle_maximize,
        )
        self.max_btn.pack(side="left", padx=3, pady=8)

        self.min_btn = ctk.CTkButton(
            left,
            text="\u2500",
            width=36, height=32, corner_radius=6,
            font=(ctk.ThemeManager.theme["CTkFont"]["family"], 13),
            fg_color="transparent",
            border_width=1, border_color=COLORS["border"],
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_light"],
            command=self._minimize,
        )
        self.min_btn.pack(side="left", padx=3, pady=8)

        ctk.CTkFrame(self, height=2, fg_color=COLORS["accent"]).place(
            relx=0, rely=1.0, relwidth=1, anchor="sw")

        for w in (self, right, left, self.title_label):
            self._bind_drag(w)

    def _bind_drag(self, widget):
        widget.bind("<Button-1>", self._on_press)
        widget.bind("<B1-Motion>", self._on_motion)
        widget.bind("<Double-Button-1>", lambda e: self._toggle_maximize())

    def _on_press(self, e):
        self._dx = e.x_root - self.master.winfo_x()
        self._dy = e.y_root - self.master.winfo_y()

    def _on_motion(self, e):
        self.master.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def _toggle_maximize(self):
        win = self.master
        if self._maximized:
            win.geometry(self._prev_geometry)
            self._maximized = False
            self.max_btn.configure(text="\u25a1")
        else:
            self._prev_geometry = win.geometry()
            sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
            win.geometry(f"{sw}x{sh}+0+0")
            self._maximized = True
            self.max_btn.configure(text="\u25a0")

    def _minimize(self):
        try:
            self.master.iconify()
        except Exception:
            pass