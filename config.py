import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "db", "cashier.db")
FONTS_DIR = os.path.join(BASE_DIR, "assets", "fonts")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

FONT_ARABIC = "Cairo"
FONT_ARABIC_BOLD = "Cairo"

FONT_SIZE_TITLE = 32
FONT_SIZE_HEADER = 18
FONT_SIZE_BODY = 16
FONT_SIZE_SMALL = 15

FONT_TITLE = (FONT_ARABIC_BOLD, FONT_SIZE_TITLE)
FONT_HEADER = (FONT_ARABIC_BOLD, FONT_SIZE_HEADER)
FONT_BODY = (FONT_ARABIC, FONT_SIZE_BODY)
FONT_BODY_BOLD = (FONT_ARABIC_BOLD, FONT_SIZE_BODY, "bold")
FONT_SMALL = (FONT_ARABIC, FONT_SIZE_SMALL)

APP_NAME = "مركز الصيانة - نظام الكاشير"

DEVICE_TYPES = [
    "ثلاجة",
    "فريزر",
    "غسالة",
    "صاروخ",
    "هيلتي",
    "شنيور",
    "مبرد مياه",
    "مكواة",
    "مكنسة",
    "خلاط",
    "كاتل",
    "تكييف",
    "سخان مياه",
    "ميكروويف",
    "مروحة",
    "أخرى",
]



ADMIN_USERNAME = "codex"
ADMIN_PASSWORD = "010100"

EMPLOYEE_USERNAME = "0000"
EMPLOYEE_PASSWORD = "0000"



COLORS = {
    "bg_dark": "#0d1117",
    "bg_card": "#151b23",
    "bg_input": "#1c2333",
    "bg_hover": "#252d3d",
    "accent": "#c8943a",
    "accent_hover": "#dbaa55",
    "accent_dim": "#a8782e",
    "text_white": "#f5f0e3",
    "text_light": "#9e9e9e",
    "success": "#2d8a4e",
    "success_hover": "#3aa05e",
    "danger": "#c73e3e",
    "warning": "#c8943a",
    "info": "#3a86c8",
    "info_hover": "#5aa0e0",
    "border": "#2d3543",
    "border_light": "#3d4758",
}
