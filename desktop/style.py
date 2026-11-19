"""Tema: sistem QPalette'inden açık/koyu algılayıp tek yerden stylesheet üretir."""
from PySide6.QtGui import QColor, QFont, QPalette

ACCENT = "#5b6cf0"
ACCENT_HOVER = "#4a5bdc"
FONT_FAMILIES = ["Inter", "Ubuntu", "Noto Sans", "Segoe UI", "sans-serif"]


def is_dark(pal: QPalette) -> bool:
    return pal.color(QPalette.Window).lightness() < 128


def colors(pal: QPalette) -> dict:
    dark = is_dark(pal)
    bg = pal.color(QPalette.Window)
    fg = pal.color(QPalette.WindowText)
    mix = lambda a, b, t: QColor(
        *(round(a.getRgb()[i] * (1 - t) + b.getRgb()[i] * t) for i in range(3))).name()
    return dict(
        dark=dark, bg=bg.name(), fg=fg.name(),
        surface=mix(bg, fg, 0.07), surface2=mix(bg, fg, 0.12),
        border=mix(bg, fg, 0.16), muted=mix(bg, fg, 0.55),
        sidebar=mix(bg, fg, 0.04), field=mix(bg, fg, 0.06),
        accent=ACCENT, accent_hover=ACCENT_HOVER, on_accent="#ffffff",
        dot=mix(bg, fg, 0.5))


def apply_font(app):
    f = QFont()
    f.setFamilies(FONT_FAMILIES)
    f.setPointSize(10)
    app.setFont(f)


def build_stylesheet(pal: QPalette) -> str:
    c = colors(pal)
    return f"""
QMainWindow, #root {{ background: {c['bg']}; }}
#sidebar {{ background: {c['sidebar']}; border-right: 1px solid {c['border']}; }}
#sidebar QLabel {{ color: {c['fg']}; }}
QLabel#section {{ color: {c['muted']}; font-size: 8pt; font-weight: 600; letter-spacing: 1px;
                  padding-top: 10px; }}
QLabel#muted {{ color: {c['muted']}; font-size: 9pt; }}
QLabel#appTitle {{ font-size: 13pt; font-weight: 700; }}
#sidebar QPushButton {{ background: transparent; border: none; border-radius: 8px;
                        padding: 7px 10px; text-align: left; color: {c['fg']}; }}
#sidebar QPushButton:hover {{ background: {c['surface2']}; }}
#sidebar QPushButton:disabled {{ color: {c['muted']}; }}
QListWidget {{ color: {c['fg']}; background: {c['surface']}; border: 1px solid {c['border']};
               border-radius: 8px; padding: 4px; outline: 0; }}
QListWidget::item {{ padding: 4px 6px; border-radius: 6px; }}
QListWidget::item:selected {{ background: {c['surface2']}; color: {c['fg']}; }}
QSpinBox {{ color: {c['fg']}; background: {c['surface']}; border: 1px solid {c['border']};
            border-radius: 8px; padding: 4px 8px; }}
QRadioButton {{ spacing: 6px; }}
QProgressBar {{ background: {c['surface2']}; border: none; border-radius: 3px; max-height: 6px; }}
QProgressBar::chunk {{ background: {c['accent']}; border-radius: 3px; }}
QStatusBar {{ background: {c['bg']}; color: {c['muted']}; }}

QScrollArea#chat, #chatInner {{ background: {c['bg']}; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {c['border']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

#bubbleUser {{ background: {c['accent']}; border-radius: 16px; border-bottom-right-radius: 4px; }}
#bubbleUser QLabel {{ color: {c['on_accent']}; background: transparent; }}
#bubbleBot {{ background: {c['surface']}; border: 1px solid {c['border']};
              border-radius: 16px; border-top-left-radius: 4px; }}
#bubbleBot QLabel {{ background: transparent; color: {c['fg']}; }}
QLabel#avatar {{ background: {c['accent']}; color: {c['on_accent']}; border-radius: 12px;
                 font-weight: 700; font-size: 9pt; }}
QLabel#who {{ color: {c['muted']}; font-size: 8pt; font-weight: 600; }}

QToolButton#chip {{ background: {c['surface2']}; border: 1px solid {c['border']};
                    border-radius: 12px; padding: 4px 10px; color: {c['fg']}; font-size: 9pt; }}
QToolButton#chip:hover {{ border-color: {c['accent']}; }}
QToolButton#chip:checked {{ border-color: {c['accent']}; }}
QPlainTextEdit#chunk {{ background: {c['field']}; border: 1px solid {c['border']};
                        border-radius: 10px; padding: 6px; color: {c['fg']}; }}

QPushButton#example {{ background: {c['surface']}; border: 1px solid {c['border']};
                       border-radius: 12px; padding: 10px 16px; color: {c['fg']}; }}
QPushButton#example:hover {{ border-color: {c['accent']}; background: {c['surface2']}; }}
QLabel#welcomeTitle {{ font-size: 20pt; font-weight: 700; }}

#inputBar {{ background: {c['bg']}; }}
#inputWrap {{ background: {c['field']}; border: 1px solid {c['border']}; border-radius: 22px; }}
#inputWrap:focus-within {{ border-color: {c['accent']}; }}
QLineEdit#input {{ background: transparent; border: none; padding: 8px 6px; color: {c['fg']}; }}
QPushButton#send {{ background: {c['accent']}; color: {c['on_accent']}; border: none;
                    border-radius: 18px; min-width: 36px; max-width: 36px;
                    min-height: 36px; max-height: 36px; font-size: 13pt; font-weight: 700; }}
QPushButton#send:hover {{ background: {c['accent_hover']}; }}
QPushButton#send:disabled {{ background: {c['surface2']}; color: {c['muted']}; }}
"""
