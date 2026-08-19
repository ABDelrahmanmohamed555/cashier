# dropdown.py
import customtkinter as ctk
from config import COLORS
from utils import make_undecorated

ROW_HEIGHT = 38
OPEN_STEPS = 12
OPEN_DELAY = 10
CLOSE_STEPS = 10
CLOSE_DELAY = 8


class AnimatedDropdown(ctk.CTkToplevel):
    """قائمة منسدلة مخصصة بأنيميشن: تنزلق لفوق/تحت مع fade، وعلى الـ hover
    يظهر إطار ذهبي حول التصنيف. نافذة مُدارة من الـ WM بدون إطار خارجي."""

    def __init__(self, anchor, values, font, on_select, on_closed=None):
        super().__init__(anchor.winfo_toplevel())
        self.withdraw()
        self._values = values
        self._font = font
        self._on_select = on_select
        self._host = anchor.winfo_toplevel()  # النافذة الأم (مش الدروب-داون نفسه)
        self._on_closed = on_closed
        self._closing = False
        self._hover_index = -1
        self._rows = []
        self._escape_id = None
        self._outside_id = None
        self._destroy_id = None

        self.title("")
        self.configure(fg_color=COLORS["bg_card"])
        make_undecorated(self)

        self._x = anchor.winfo_rootx()
        self._y = anchor.winfo_rooty() + anchor.winfo_height() + 4
        self._width = max(anchor.winfo_width(), 180)

        container = ctk.CTkFrame(
            self, fg_color=COLORS["bg_card"], corner_radius=8,
            border_width=1, border_color=COLORS["border"],
        )
        container.pack(fill="both", expand=True, padx=1, pady=1)

        full_height = len(values) * ROW_HEIGHT + 12
        available = anchor.winfo_screenheight() - self._y - 24
        self._scroll = ctk.CTkScrollableFrame(
            container, fg_color="transparent", corner_radius=6,
        )
        self._scroll.pack(fill="both", expand=True, padx=3, pady=3)
        self._full_height = min(full_height, available)

        for i, value in enumerate(values):
            self._build_row(i, value)

        self._bind_outside_close()
        self.geometry(f"{self._width}x0+{self._x}+{self._y}")
        self.attributes("-alpha", 0.0)
        self.deiconify()
        self._animate_open()

    def _build_row(self, index, value):
        row = ctk.CTkFrame(
            self._scroll, fg_color="transparent", corner_radius=6,
            height=ROW_HEIGHT - 6, border_width=1,
            border_color=COLORS["bg_card"],
        )
        row.pack(fill="x", pady=2)
        row.pack_propagate(False)

        label = ctk.CTkLabel(
            row, text=value, font=self._font,
            text_color=COLORS["text_white"], anchor="e",
        )
        label.pack(fill="both", padx=14)

        def on_enter(e, i=index):
            self._set_hover(i)

        def on_leave(e, i=index):
            if not self._closing:
                self._clear_hover(i)

        def on_click(e, v=value):
            self._choose(v)

        for w in (row, label):
            w.bind("<Enter>", on_enter)
            w.bind("<Button-1>", on_click)
        label.bind("<Leave>", on_leave)
        row.bind("<Leave>", on_leave)

        self._rows.append({"frame": row, "label": label, "value": value})

    def _set_hover(self, index):
        if self._closing:
            return
        if self._hover_index >= 0 and self._hover_index < len(self._rows):
            self._clear_hover(self._hover_index)
        self._hover_index = index
        row = self._rows[index]["frame"]
        row.configure(border_color=COLORS["accent"], fg_color=COLORS["bg_hover"])

    def _clear_hover(self, index):
        if self._closing:
            return
        row = self._rows[index]["frame"]
        row.configure(border_color=COLORS["bg_card"], fg_color="transparent")

    def _choose(self, value):
        if self._closing:
            return
        self._close(select_value=value)

    def _bind_outside_close(self):
        root = self._host
        self._escape_id = self.bind_all("<Escape>", lambda e: self._close(), add=True)
        self._outside_id = root.bind("<Button-1>", self._on_outside_click, add="+")
        self._destroy_id = root.bind("<Destroy>", self._on_root_destroy, add="+")

    def _on_outside_click(self, event):
        if self._closing:
            return
        try:
            under = self.winfo_containing(event.x_root, event.y_root)
        except Exception:
            under = None
        if under is None:
            return
        in_self = False
        w = under
        while w is not None:
            if w is self:
                in_self = True
                break
            try:
                w = w.master
            except Exception:
                break
        if not in_self:
            self._close()

    def _on_root_destroy(self, event):
        if event.widget is self._host:
            self._close(skip_animation=True)

    def _animate_open(self):
        target = max(self._full_height, 1)

        def step(i):
            if self._closing or not self.winfo_exists():
                return
            progress = i / OPEN_STEPS
            eased = 1 - (1 - progress) ** 2  # ease-out
            h = max(int(target * eased), 1)
            self.geometry(f"{self._width}x{h}+{self._x}+{self._y}")
            self.attributes("-alpha", progress)
            if i < OPEN_STEPS:
                self.after(OPEN_DELAY, lambda: step(i + 1))
            else:
                self.focus_force()

        self.after(OPEN_DELAY, lambda: step(1))

    def _close(self, select_value=None, skip_animation=False):
        if self._closing:
            return
        self._closing = True

        if select_value is not None:
            try:
                self._on_select(select_value)
            except Exception:
                pass

        if skip_animation:
            self._cleanup_and_destroy()
            return

        def step(i):
            if not self.winfo_exists():
                return
            progress = i / CLOSE_STEPS  # من 1 لـ 0
            h = max(int(self._full_height * progress), 1)
            self.geometry(f"{self._width}x{h}+{self._x}+{self._y}")
            self.attributes("-alpha", max(0.0, progress))
            if i > 0:
                self.after(CLOSE_DELAY, lambda: step(i - 1))
            else:
                self._cleanup_and_destroy()

        self.after(CLOSE_DELAY, lambda: step(CLOSE_STEPS - 1))

    def _cleanup_and_destroy(self):
        try:
            if self._escape_id is not None:
                self.unbind_all("<Escape>")
            root = self._host
            if root is not None and root.winfo_exists():
                if self._outside_id is not None:
                    root.unbind("<Button-1>", self._outside_id)
                if self._destroy_id is not None:
                    root.unbind("<Destroy>", self._destroy_id)
        except Exception:
            pass
        if self._on_closed is not None:
            try:
                self._on_closed()
            except Exception:
                pass
        try:
            self.destroy()
        except Exception:
            pass


class AnimatedOptionMenu(ctk.CTkOptionMenu):
    """نفس CTkOptionMenu لكن القائمة المنسدلة مخصصة: انيميشن فتح/قفل
    وإطار ذهبي عند الـ hover. الواجهة نفسها (get/set/values/command)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._custom_menu = None

    def _open_dropdown_menu(self):
        if self._custom_menu is not None:
            try:
                if self._custom_menu.winfo_exists():
                    self._custom_menu._close()
                    return
            except Exception:
                pass
            self._custom_menu = None

        self._custom_menu = AnimatedDropdown(
            anchor=self,
            values=list(self._values),
            font=self._dropdown_menu.cget("font"),
            on_select=self._on_custom_select,
            on_closed=self._on_custom_closed,
        )

    def _on_custom_select(self, value):
        if value in self._values:
            self._dropdown_callback(value)

    def _on_custom_closed(self):
        self._custom_menu = None
