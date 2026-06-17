"""
Shared HUD theme — dark panels, neon-purple accents, monospace.

Apply with theme.apply(widget) in each window's __init__ to give the whole app
a consistent futuristic look that matches the orb.
"""

# Palette (kept in sync with the orb / tray / app-icon accent)
BG        = "#0d0f17"
SURFACE   = "#161a26"
SURFACE_2 = "#1d2230"
BORDER    = "#2d3148"
ACCENT    = "#7c6cfc"
TEXT      = "#e8e9f0"
MUTED     = "#8a8fa8"
GREEN     = "#4ade80"

STYLESHEET = f"""
QDialog, QWidget {{
    background: {BG};
    color: {TEXT};
    font-family: "Menlo", "SF Mono", monospace;
    font-size: 12px;
}}
QLabel {{ color: {TEXT}; background: transparent; }}
QTextEdit, QListWidget {{
    background: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px;
    selection-background-color: {ACCENT};
}}
QLineEdit, QComboBox, QSpinBox {{
    background: {SURFACE_2};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 8px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 1px solid {ACCENT}; }}
QPushButton {{
    background: transparent;
    color: {TEXT};
    border: 1px solid {ACCENT};
    border-radius: 6px;
    padding: 6px 16px;
}}
QPushButton:hover {{ background: {ACCENT}; color: {BG}; }}
QPushButton:pressed {{ background: {SURFACE_2}; }}
QCheckBox {{ color: {TEXT}; spacing: 8px; background: transparent; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {BORDER}; border-radius: 4px; background: {SURFACE_2};
}}
QCheckBox::indicator:checked {{ background: {ACCENT}; border: 1px solid {ACCENT}; }}
QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 8px; top: -1px; }}
QTabBar::tab {{
    background: transparent;
    color: {MUTED};
    padding: 7px 16px;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom: 2px solid {ACCENT}; }}
QProgressBar {{ background: {SURFACE_2}; border: none; border-radius: 5px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 5px; }}
QScrollBar:vertical {{ background: {BG}; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
"""


def apply(widget):
    """Apply the HUD stylesheet to a top-level widget."""
    widget.setStyleSheet(STYLESHEET)
