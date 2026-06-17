"""Real-time logs window — shows transcript, routing decisions, tool calls."""

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class LogsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("VoiceOfIU — Live Logs")
        self.resize(700, 450)
        from . import theme
        theme.apply(self)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFont(QFont("Menlo", 12))
        self._log.setStyleSheet(
            "background:#0f1117; color:#e8e9f0; border:none; padding:8px;"
        )
        layout.addWidget(self._log)

        # Volume meter — live mic level
        meter_row = QHBoxLayout()
        meter_row.addWidget(QLabel("🎤"))
        self._meter = QProgressBar()
        self._meter.setRange(0, 100)
        self._meter.setTextVisible(False)
        self._meter.setFixedHeight(10)
        self._meter.setStyleSheet(
            "QProgressBar { background:#1a1d27; border:none; border-radius:5px; }"
            "QProgressBar::chunk { background:#7c6cfc; border-radius:5px; }"
        )
        meter_row.addWidget(self._meter)
        layout.addLayout(meter_row)

        btn_row = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._log.clear)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def set_level(self, level: float):
        """Update the volume meter (0.0–1.0)."""
        self._meter.setValue(int(level * 100))

    def append(self, text: str, color: str = "#e8e9f0"):
        self._log.append(f'<span style="color:{color}">{text}</span>')
        self._log.verticalScrollBar().setValue(
            self._log.verticalScrollBar().maximum()
        )

    def log_heard(self, text: str):
        self.append(f"🎙️ Heard: {text}", "#8a8fa8")

    def log_intent(self, intent: str):
        self.append(f"🎯 Intent: {intent}", "#7c6cfc")

    def log_response(self, response: str):
        from ..config import display_name
        self.append(f"🤖 {display_name()}: {response}", "#4ade80")

    def log_status(self, status: str):
        self.append(f"   [{status}]", "#fbbf24")
