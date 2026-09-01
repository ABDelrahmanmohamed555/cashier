# arabic_entry.py
import customtkinter as ctk
from utils import reshape_arabic
import re


class ArabicEntry(ctk.CTkFrame):
    def __init__(self, master=None, placeholder="", font=None, height=44,
                 corner_radius=8, border_width=1, border_color="#1f2530",
                 fg_color="#11151c", text_color="#f0ece4",
                 placeholder_text_color="#8a8a8a", **kwargs):

        super().__init__(master, fg_color="transparent", height=height, **kwargs)
        self.pack_propagate(False)

        self._placeholder = placeholder
        self._font = font
        self._text_color = text_color
        self._placeholder_color = placeholder_text_color
        self._border_color = border_color
        self._raw_text = ""
        self._focused = False

        self._build(fg_color, border_color, border_width, corner_radius, height)

        self._bind_events()

    def _build(self, bg_color, border_color, border_width, corner_radius, height):
        self._frame = ctk.CTkFrame(
            self, fg_color=bg_color, height=height,
            corner_radius=corner_radius, border_width=border_width,
            border_color=border_color,
        )
        self._frame.pack(fill="both", expand=True)
        self._frame.pack_propagate(False)

        inner = ctk.CTkFrame(self._frame, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=12, pady=2)

        self._label = ctk.CTkLabel(
            inner, text=reshape_arabic(self._placeholder),
            font=self._font, text_color=self._placeholder_color,
            anchor="e", justify="right",
        )
        self._label.pack(fill="both", expand=True)

        self._cursor_visible = False

    def _bind_events(self):
        self._frame.bind("<Button-1>", self._on_click)
        self._label.bind("<Button-1>", self._on_click)

        self._frame.bind("<KeyPress>", self._on_keypress)
        self._label.bind("<KeyPress>", self._on_keypress)

        self._frame.bind("<FocusIn>", self._on_focusin)
        self._frame.bind("<FocusOut>", self._on_focusout)
        self._label.bind("<FocusIn>", self._on_focusin)
        self._label.bind("<FocusOut>", self._on_focusout)

    def _on_click(self, event):
        self._frame.focus_set()
        self._update_display()

    def _on_focusin(self, event):
        self._focused = True
        self._frame.configure(border_color="#c8943a")
        self._update_display()

    def _on_focusout(self, event):
        self._focused = False
        self._frame.configure(border_color=self._border_color)
        self._update_display()

    def _on_keypress(self, event):
        if event.char and event.char.isprintable():
            self._raw_text += event.char
            self._update_display()
            return "break"
        elif event.keysym == "BackSpace":
            self._raw_text = self._raw_text[:-1]
            self._update_display()
            return "break"
        elif event.keysym == "Return":
            self._raw_text += "\n"
            self._update_display()
            return "break"
        return "break"

    def _update_display(self):
        if self._raw_text:
            # كل سطر لوحده عشان الـ reshape ما يتداخلش بين السطور
            display = "\n".join(reshape_arabic(line) for line in self._raw_text.split("\n"))
            self._label.configure(text=display, text_color=self._text_color)
        else:
            self._label.configure(
                text=reshape_arabic(self._placeholder),
                text_color=self._placeholder_color,
            )
        self._auto_height()

    def _auto_height(self):
        n_lines = max(1, self._raw_text.count("\n") + 1)
        try:
            fs = self._font[1] if isinstance(self._font, (tuple, list)) else 14
        except (IndexError, TypeError):
            fs = 14
        h = max(44, n_lines * int(fs * 2) + 12)
        self.configure(height=h)
        self._frame.configure(height=h)

    def get(self):
        return self._raw_text

    def delete(self, first, last="end"):
        # يدعم delete(0,"end") و delete(0,tk.END) و أي نطاق عام
        try:
            is_clear = (str(first) in ("0", "0.0") and str(last) in ("end", "END", "tk.END", ""))
            if first == 0 and last == "end":
                is_clear = True
        except Exception:
            is_clear = False
        if is_clear or (str(first) == "0" and str(last) == "end"):
            self._raw_text = ""
            self._update_display()
            return
        # حالات عامة: حذف من first حتى last
        try:
            s = 0
            e = len(self._raw_text)
            if isinstance(first, int):
                s = max(0, min(e, first))
            elif isinstance(first, str) and first.isdigit():
                s = max(0, min(e, int(first)))
            elif str(first) == "end":
                s = e
            if isinstance(last, int):
                e = max(0, min(len(self._raw_text), last))
            elif isinstance(last, str) and last.isdigit():
                e = max(0, min(len(self._raw_text), int(last)))
            elif str(last) in ("end", "END"):
                e = len(self._raw_text)
            self._raw_text = self._raw_text[:s] + self._raw_text[e:]
            self._update_display()
        except Exception:
            self._raw_text = ""
            self._update_display()

    def insert(self, index, string):
        """إدخال نص برمجياً — يحاكي CTkEntry.insert(index, text)"""
        if not string:
            return
        s = str(string)
        try:
            # end / END -> إلحاق
            if str(index) in ("end", "END", "insert", "tk.END"):
                self._raw_text += s
            elif isinstance(index, int):
                idx = max(0, min(len(self._raw_text), index))
                self._raw_text = self._raw_text[:idx] + s + self._raw_text[idx:]
            elif isinstance(index, str):
                # "0" أو "0.0" أو رقم
                idx_str = index.split(".")[0] if "." in index else index
                try:
                    idx = int(idx_str)
                    idx = max(0, min(len(self._raw_text), idx))
                    self._raw_text = self._raw_text[:idx] + s + self._raw_text[idx:]
                except ValueError:
                    self._raw_text += s
            else:
                self._raw_text += s
        except Exception:
            self._raw_text += s
        self._update_display()

    def focus_set(self):
        try:
            self._frame.focus_set()
        except Exception:
            try:
                super().focus_set()
            except Exception:
                pass

    def focus(self):
        return self.focus_set()

    def icursor(self, *args, **kwargs):
        pass

    def configure(self, **kwargs):
        if "placeholder_text" in kwargs:
            self._placeholder = kwargs.pop("placeholder_text")
            self._update_display()
        super().configure(**kwargs)

    def bind(self, sequence=None, command=None, add=None):
        self._frame.bind(sequence, command, add)
        self._label.bind(sequence, command, add)
