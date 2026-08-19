# neon.py
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
import customtkinter as ctk
from customtkinter import CTkImage
from config import FONTS_DIR, COLORS

_FONT_PATH = os.path.join(FONTS_DIR, "Cairo.ttf")
_font_cache = {}


def _pil_font(font):
    """تحويل font tuple لوحة الألوان (مثل ("Cairo", 16, "bold")) لخط PIL."""
    size = font[1] if isinstance(font, (tuple, list)) else font
    key = (size, font[2] if isinstance(font, (tuple, list)) and len(font) > 2 else "")
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(_FONT_PATH, int(size * 1.33))
    return _font_cache[key]


def _display_text(text):
    return get_display(arabic_reshaper.reshape(str(text)))


def glow_image(size, radius, color, blur, alpha=230):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=color + (alpha,))
    return img.filter(ImageFilter.GaussianBlur(blur))


class NeonButton(ctk.CTkFrame):
    """زر عادي لكن خلفه هالة متوهجة (نيون) — يتحمل التمدد (fill) بسلاسة."""

    def __init__(self, master, text="", command=None, width=160, height=48,
                 corner_radius=8, glow_pad=8, glow_blur=12,
                 glow_color=(200, 148, 58), fg_color=None, hover_color=None,
                 text_color=None, font=None, border_width=1, border_color=None):
        self._n_corner_radius = corner_radius
        self._n_glow_pad = glow_pad
        self._n_glow_blur = glow_blur
        self._n_glow_color = _rgb(glow_color)
        self._n_fg = fg_color or COLORS["accent"]
        self._n_hover = hover_color or COLORS["accent_hover"]
        self._n_text_color = text_color or COLORS["text_white"]
        self._n_font = font
        self._n_border_width = border_width
        self._n_border_color = border_color or COLORS["accent"]
        self._n_text = text
        self._n_command = command
        self._n_size = (0, 0)

        super().__init__(master, fg_color="transparent",
                         width=width + glow_pad * 2, height=height + glow_pad * 2)
        self.pack_propagate(False)

        self._glow_label = ctk.CTkLabel(self, text="")
        self._glow_label.place(x=0, y=0, relwidth=1, relheight=1)

        self.button = ctk.CTkButton(
            self,
            text=text,
            command=command,
            font=font,
            fg_color=self._n_fg,
            hover_color=self._n_hover,
            text_color=self._n_text_color,
            corner_radius=corner_radius,
            border_width=border_width,
            border_color=self._n_border_color,
        )
        self.button.place(relx=0.5, rely=0.5, anchor="center")

        self.configure(cursor="hand2")
        self.bind("<Configure>", self._on_resize)

    def _apply_size(self, w, h):
        self._n_size = (w, h)
        img = glow_image((w, h), self._n_corner_radius + self._n_glow_pad,
                         self._n_glow_color, self._n_glow_blur)
        ctk_img = CTkImage(light_image=img, dark_image=img, size=(w, h))
        self._glow_label.configure(image=ctk_img)
        bw = w - self._n_glow_pad * 2
        bh = h - self._n_glow_pad * 2
        if bw < 20 or bh < 20:
            return
        self.button.configure(width=bw, height=bh)
        self.button.place(relx=0.5, rely=0.5, anchor="center")

    def _on_resize(self, event=None):
        w, h = self.winfo_width(), self.winfo_height()
        if w < 10 or h < 10:
            return
        if (w, h) != self._n_size:
            self._apply_size(w, h)

    def configure_button(self, **kwargs):
        self.button.configure(**kwargs)


def _rgb(color):
    """تحويل لون hex أو tuple إلى (r, g, b)."""
    if isinstance(color, str):
        color = color.lstrip("#")
        return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(int(c) for c in color)


class NeonLabel(ctk.CTkLabel):
    """نص مع توهج نيون خلفه (PIL) — يقبل تغيير النص بـ set_text()."""

    def __init__(self, master, text="", font=None, fill=COLORS["text_white"],
                 glow=COLORS["accent"], blur=6, pad=6):
        self._n_font = font or ("Cairo", 16)
        self._n_fill = _rgb(fill)
        self._n_glow = _rgb(glow)
        self._n_blur = blur
        self._n_pad = pad
        super().__init__(master, text="")
        self.set_text(text)

    def _render(self, text):
        display = _display_text(text)
        pil_font = _pil_font(self._n_font)

        probe = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
        bbox = probe.textbbox((0, 0), display, font=pil_font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

        img = Image.new("RGBA", (w + self._n_pad * 2, h + self._n_pad * 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.text((self._n_pad - bbox[0], self._n_pad - bbox[1]), display,
               font=pil_font, fill=self._n_glow + (255,))
        img = img.filter(ImageFilter.GaussianBlur(self._n_blur))
        d2 = ImageDraw.Draw(img)
        d2.text((self._n_pad - bbox[0], self._n_pad - bbox[1]), display,
                font=pil_font, fill=self._n_fill + (255,))

        ctk_img = CTkImage(light_image=img, dark_image=img,
                           size=(w + self._n_pad * 2, h + self._n_pad * 2))
        self.configure(text="", image=ctk_img)

    def set_text(self, text):
        self._render(text)


def neon_label(master, text, font, fill=COLORS["text_white"],
               glow=COLORS["accent"], blur=6, pad=6):
    """دالة مساعدة (ترجع NeonLabel)."""
    return NeonLabel(master, text, font, fill, glow, blur, pad)