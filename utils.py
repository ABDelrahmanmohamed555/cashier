# utils.py
import json
import os
import time
import arabic_reshaper
from bidi.algorithm import get_display
import re

_WINDOW_STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "window_state.json")

_CURSOR_BASE = [
    "1000000000000000",
    "1100000000000000",
    "1110000000000000",
    "1111000000000000",
    "1111100000000000",
    "1111110000000000",
    "1111111000000000",
    "1111111100000000",
    "1111111110000000",
    "1111111111000000",
    "1111111111100000",
    "1111111111110000",
    "1111111111111000",
    "1111110111111000",
    "1111100011111000",
    "1111000000110000",
]


def _dilate(rows):
    out = []
    for y in range(16):
        row = ""
        for x in range(16):
            val = "0"
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < 16 and 0 <= nx < 16 and rows[ny][nx] == "1":
                        val = "1"
            row += val
        out.append(row)
    return out


def _erode(rows):
    out = []
    for y in range(16):
        row = ""
        for x in range(16):
            if rows[y][x] != "1":
                row += "0"
                continue
            ok = True
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < 16 and 0 <= nx < 16 and rows[ny][nx] != "1":
                        ok = False
            row += "1" if ok else "0"
        out.append(row)
    return out


_cursor_obj = None
_cursor_created = False


def apply_gold_cursor(window, color=(0xC8, 0x94, 0x3A)):
    """تطبيق مؤشر ذهبي على نافذة (وكل نوافذها الفرعية تلقائيًا) — Linux/X11 فقط."""
    global _cursor_obj, _cursor_created
    if os.environ.get("XDG_SESSION_TYPE") == "wayland":
        return
    if os.name != "posix":
        return
    try:
        from Xlib import display, X
        d = display.Display()
        root = d.screen().root

        if not _cursor_created:
            mask_rows = _dilate(_CURSOR_BASE)
            src_rows = _erode(_CURSOR_BASE)

            pix = root.create_pixmap(16, 16, 1)
            mask_pix = root.create_pixmap(16, 16, 1)
            gc1 = pix.create_gc(foreground=1, background=0)
            gc0 = pix.create_gc(foreground=0, background=0)
            for y, row in enumerate(src_rows):
                for x, ch in enumerate(row):
                    if ch == "1":
                        pix.fill_rectangle(gc1, x, y, 1, 1)
                    else:
                        pix.fill_rectangle(gc0, x, y, 1, 1)
            for y, row in enumerate(mask_rows):
                for x, ch in enumerate(row):
                    if ch == "1":
                        mask_pix.fill_rectangle(gc1, x, y, 1, 1)
                    else:
                        mask_pix.fill_rectangle(gc0, x, y, 1, 1)
            d.sync()

            r, g, b = color
            _cursor_obj = pix.create_cursor(
                mask_pix, (r * 257, g * 257, b * 257), (0, 0, 0), 0, 0)
            _cursor_created = True

        window.update_idletasks()
        xid = window.winfo_id()
        win = d.create_resource_object("window", xid)
        win.change_attributes(cursor=_cursor_obj)
        d.sync()
    except Exception:
        pass


def save_window_state(key, geometry):
    os.makedirs(os.path.dirname(_WINDOW_STATE_PATH), exist_ok=True)
    state = {}
    if os.path.exists(_WINDOW_STATE_PATH):
        try:
            with open(_WINDOW_STATE_PATH, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            pass
    state[key] = geometry
    with open(_WINDOW_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f)


def load_window_state(key):
    if not os.path.exists(_WINDOW_STATE_PATH):
        return None
    try:
        with open(_WINDOW_STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
        return state.get(key)
    except Exception:
        return None


_ARABIC_RANGE = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')


def _has_arabic(text):
    return bool(_ARABIC_RANGE.search(text))


def reshape_arabic(text):
    if not text:
        return text
    if not _has_arabic(text):
        return text
    try:
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except Exception:
        return text


def make_optionmenu_values(original_list):
    display_values = [reshape_arabic(item) for item in original_list]
    mapping = {}
    for display, original in zip(display_values, original_list):
        mapping[display] = original
    return display_values, mapping


def restore_or_center(window, key, default_w, default_h):
    geom = load_window_state(key)
    if geom:
        try:
            size = geom.split("+")[0]
            w, h = size.split("x")
            if int(w) >= 100 and int(h) >= 60:
                window.geometry(geom)
                return
        except Exception:
            pass
    # center
    ws = window.winfo_screenwidth()
    hs = window.winfo_screenheight()
    x = (ws - default_w) // 2
    y = (hs - default_h) // 2
    window.geometry(f"{default_w}x{default_h}+{x}+{y}")


def _set_gold_cursor(window):
    """إعادة تطبيق المؤشر الذهبي على نافذة (بعد ما مؤشر تغيير الحجم يشيلوه)."""
    try:
        if _cursor_obj is None:
            window.config(cursor="")
            return
        from Xlib import display
        d = display.Display()
        window.update_idletasks()
        xid = int(window.winfo_id())
        w = d.create_resource_object("window", xid)
        w.change_attributes(cursor=_cursor_obj)
        d.sync()
    except Exception:
        try:
            window.config(cursor="")
        except Exception:
            pass


_RESIZE_CURSORS = {
    "nw": "top_left_corner",
    "ne": "top_right_corner",
    "sw": "bottom_left_corner",
    "se": "bottom_right_corner",
    "w": "left_side",
    "e": "right_side",
    "n": "top_side",
    "s": "bottom_side",
}


def enable_resize(window, min_w=400, min_h=300, edge=6):
    """تغيير حجم النافذة بالفأرة بحوافها وزواياها (لأننا شالنا إطار النظام).
    min_w/min_h: أصغر مقاس مسموح. edge: سُمك المنطقة القابلة للسحب بالبكسل."""
    state = {"zone": None, "gx": 0, "gy": 0, "gw": 0, "gh": 0, "px": 0, "py": 0}
    hover = {"z": None}

    def zone_at(e):
        if window.state() != "normal":
            return None
        try:
            w = window.winfo_width()
            h = window.winfo_height()
        except Exception:
            return None
        if w < 10 or h < 10:
            return None
        x = e.x_root - window.winfo_rootx()
        y = e.y_root - window.winfo_rooty()
        west = x <= edge
        east = x >= w - 1 - edge
        north = y <= edge
        south = y >= h - 1 - edge
        if north and west:
            return "nw"
        if north and east:
            return "ne"
        if south and west:
            return "sw"
        if south and east:
            return "se"
        if west:
            return "w"
        if east:
            return "e"
        if north:
            return "n"
        if south:
            return "s"
        return None

    def on_press(e):
        z = zone_at(e)
        if not z:
            return
        state["zone"] = z
        state["gx"] = window.winfo_x()
        state["gy"] = window.winfo_y()
        state["gw"] = window.winfo_width()
        state["gh"] = window.winfo_height()
        state["px"] = e.x_root
        state["py"] = e.y_root
        # لو النافذة كانت مكبرة للمسح (زر التكبير في الـ TitleBar) —
        # أول سحب حجم بيشيل التكبير ويرجع النافذة عادية
        try:
            sw = window.winfo_screenwidth()
            if state["gw"] >= sw - 2:
                for child in window.winfo_children():
                    if hasattr(child, "_maximized"):
                        child._maximized = False
                        try:
                            child.max_btn.configure(text="\u25a1")
                        except Exception:
                            pass
        except Exception:
            pass
        try:
            window.config(cursor=_RESIZE_CURSORS[z])
        except Exception:
            pass

    def on_drag(e):
        z = state["zone"]
        if not z:
            return
        dx = e.x_root - state["px"]
        dy = e.y_root - state["py"]
        nx, ny = state["gx"], state["gy"]
        nw, nh = state["gw"], state["gh"]
        if "e" in z:
            nw = state["gw"] + dx
        if "s" in z:
            nh = state["gh"] + dy
        if "w" in z:
            nw = state["gw"] - dx
            nx = state["gx"] + dx
        if "n" in z:
            nh = state["gh"] - dy
            ny = state["gy"] + dy
        nw = max(min_w, nw)
        nh = max(min_h, nh)
        window.geometry(f"{int(nw)}x{int(nh)}+{int(nx)}+{int(ny)}")

    def on_release(e):
        if state["zone"]:
            state["zone"] = None
            _set_gold_cursor(window)

    def on_motion(e):
        if state["zone"]:
            return
        z = zone_at(e)
        if z == hover["z"]:
            return
        hover["z"] = z
        if z:
            try:
                window.config(cursor=_RESIZE_CURSORS[z])
            except Exception:
                pass
        else:
            _set_gold_cursor(window)

    window.bind("<ButtonPress-1>", on_press, add="+")
    window.bind("<B1-Motion>", on_drag, add="+")
    window.bind("<ButtonRelease-1>", on_release, add="+")
    window.bind("<Motion>", on_motion, add="+")
    return window


def make_undecorated(window):
    """حل جذري بديل عن overrideredirect: النافذة تفضل مُدارة من الـ WM (فالـ
    stacking والقوائم المنسدلة والكيبورد والمينيمايز يشتغلوا طبيعي) لكن بدون أي
    إطار/تزيين خارجي عبر _MOTIF_WM_HINTS — فالشكل يفضل زي نوافذنا المخصصة بالظبط.
    ملحوظة مهمة: Xfwm بيقرا الخاصية بالـ type = _MOTIF_WM_HINTS نفسه (مش INTEGER)
    فينبغي نكتبها بنفس الـ type — وبيطبّقها فورًا على PropertyNotify."""
    try:
        from Xlib import display
        d = display.Display()
        atom = d.intern_atom("_MOTIF_WM_HINTS")
        # flags = MWM_HINTS_DECORATIONS(2), decorations = 0
        hints = (2, 0, 0, 0, 0)

        def apply_hints():
            try:
                if not window.winfo_exists():
                    return
                xid = int(window.winfo_id())
                client = None
                seen = set()
                for _ in range(10):
                    if xid in seen:
                        break
                    seen.add(xid)
                    try:
                        w = d.create_resource_object("window", xid)
                        wm = w.get_wm_class()
                        if wm and wm[0]:
                            client = xid
                            break
                        xid = w.query_tree().parent.id
                    except Exception:
                        break
                if client is None:
                    return
                d.create_resource_object("window", client).change_property(atom, atom, 32, hints)
                d.sync()
            except Exception:
                pass

        apply_hints()
        try:
            for delay in (150, 600):
                window.after(delay, apply_hints)
        except Exception:
            pass
    except Exception:
        pass


def format_datetime(dt_str):
    """Convert '2026-07-27 18:21:08' to '2026-07-27 06:21 PM' (12-hour)"""
    if not dt_str or len(dt_str) < 16:
        return dt_str or ""
    try:
        from datetime import datetime as dt
        parsed = dt.strptime(dt_str[:19], "%Y-%m-%d %H:%M:%S")
        return parsed.strftime("%Y-%m-%d %I:%M %p")
    except Exception:
        return dt_str[:16]


def fade_out(window, on_complete, alpha=1.0, step=0.1):
    if alpha <= 0:
        window.withdraw()
        on_complete()
        return
    window.attributes("-alpha", alpha)
    window.after(20, lambda: fade_out(window, on_complete, alpha - step, step))


def fade_in(window, alpha=0.0, step=0.1):
    if alpha >= 1.0:
        window.attributes("-alpha", 1.0)
        return
    window.attributes("-alpha", alpha)
    window.after(20, lambda: fade_in(window, alpha + step, step))
