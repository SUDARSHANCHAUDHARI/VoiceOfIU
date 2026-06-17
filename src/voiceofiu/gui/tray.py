"""System tray icon and menu."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

# State → accent colour for the tray glyph
_STATE_COLORS = {
    "listening":    "#7c6cfc",
    "transcribing": "#fbbf24",
    "thinking":     "#fbbf24",
    "speaking":     "#4ade80",
    "dictating":    "#f87171",
    "paused":       "#8a8fa8",
}


def _make_icon(state: str = "listening") -> QIcon:
    """Draw a soundwave glyph tinted by state — matches the app icon, no asset file."""
    size = 64
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    color = QColor(_STATE_COLORS.get(state, "#7c6cfc"))
    p.setBrush(color)
    p.setPen(Qt.PenStyle.NoPen)

    # Five rounded bars forming a soundwave (shorter when paused)
    heights = [0.30, 0.55, 0.85, 0.55, 0.30]
    if state == "paused":
        heights = [0.25, 0.25, 0.25, 0.25, 0.25]
    bar_w = size * 0.10
    gap = size * 0.07
    total = len(heights) * bar_w + (len(heights) - 1) * gap
    x = (size - total) / 2
    for h in heights:
        bar_h = size * h
        y0 = (size - bar_h) / 2
        p.drawRoundedRect(int(x), int(y0), int(bar_w), int(bar_h), int(bar_w / 2), int(bar_w / 2))
        x += bar_w + gap
    p.end()
    return QIcon(px)


class TrayIcon(QSystemTrayIcon):
    show_logs_requested = pyqtSignal()
    show_memory_requested = pyqtSignal()
    show_settings_requested = pyqtSignal()
    toggle_listen_requested = pyqtSignal()
    toggle_orb_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._listening = True
        self.setIcon(_make_icon("listening"))
        self.setToolTip("VoiceOfIU — Listening")
        self._build_menu()
        self.show()

    def _build_menu(self):
        menu = QMenu()

        self._status_action = QAction("● Listening", menu)
        self._status_action.setEnabled(False)
        menu.addAction(self._status_action)
        menu.addSeparator()

        self._toggle_action = QAction("Pause", menu)
        self._toggle_action.triggered.connect(self.toggle_listen_requested)
        menu.addAction(self._toggle_action)
        menu.addSeparator()

        logs_action = QAction("Live Logs", menu)
        logs_action.triggered.connect(self.show_logs_requested)
        menu.addAction(logs_action)

        mem_action = QAction("Memory Viewer", menu)
        mem_action.triggered.connect(self.show_memory_requested)
        menu.addAction(mem_action)

        settings_action = QAction("Settings", menu)
        settings_action.triggered.connect(self.show_settings_requested)
        menu.addAction(settings_action)

        orb_action = QAction("Show/Hide Orb", menu)
        orb_action.triggered.connect(self.toggle_orb_requested)
        menu.addAction(orb_action)
        menu.addSeparator()

        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.quit_requested)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    def set_status(self, status: str):
        labels = {
            "listening":     "● Listening",
            "transcribing":  "⏳ Transcribing",
            "thinking":      "🧠 Thinking",
            "speaking":      "🔊 Speaking",
            "dictating":     "🎙️ Dictating",
            "paused":        "⏸ Paused",
        }
        label = labels.get(status, "● Listening")
        self._status_action.setText(label)
        self.setIcon(_make_icon(status))
        self.setToolTip(f"VoiceOfIU — {label}")

    def set_paused(self, paused: bool):
        self._toggle_action.setText("Resume" if paused else "Pause")
        self.set_status("paused" if paused else "listening")
