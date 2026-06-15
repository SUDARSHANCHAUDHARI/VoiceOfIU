"""Memory viewer — browse conversation history and meal log."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..memory import store


class MemoryViewer(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("VoiceOfIU — Memory")
        self.resize(750, 550)
        from . import theme
        theme.apply(self)
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        tabs = QTabWidget()
        tabs.addTab(self._build_conversation_tab(), "Conversations")
        tabs.addTab(self._build_topics_tab(), "Topics")
        tabs.addTab(self._build_meals_tab(), "Meals")
        layout.addWidget(tabs)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _build_conversation_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self._conv_list = QListWidget()
        self._conv_list.setFont(QFont("Menlo", 11))
        layout.addWidget(self._conv_list)
        return widget

    def _build_topics_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self._topics_text = QTextEdit()
        self._topics_text.setReadOnly(True)
        self._topics_text.setFont(QFont("Menlo", 11))
        layout.addWidget(self._topics_text)
        return widget

    def _build_meals_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self._meals_text = QTextEdit()
        self._meals_text.setReadOnly(True)
        self._meals_text.setFont(QFont("Menlo", 11))
        layout.addWidget(self._meals_text)
        return widget

    def refresh(self):
        self._load_conversations()
        self._load_topics()
        self._load_meals()

    def _load_topics(self):
        from ..memory import graph
        topics = graph.build_topics()
        if not topics:
            self._topics_text.setPlainText("Not enough conversation history yet to extract topics.")
            return
        lines = []
        for topic, turns in topics.items():
            lines.append(f"━━ {topic.upper()} ({len(turns)}) ━━")
            for t in turns:
                ts = t["timestamp"][:16].replace("T", " ")
                snippet = t["content"][:70] + ("…" if len(t["content"]) > 70 else "")
                lines.append(f"  [{ts}] {snippet}")
            lines.append("")
        self._topics_text.setPlainText("\n".join(lines))

    def _load_conversations(self):
        from ..config import display_name
        ai_name = display_name()
        self._conv_list.clear()
        turns = store.get_recent_turns(limit=100)
        for t in turns:
            ts = t["timestamp"][:16].replace("T", " ")
            role = "You" if t["role"] == "user" else ai_name
            text = t["content"][:80] + ("..." if len(t["content"]) > 80 else "")
            item = QListWidgetItem(f"[{ts}] {role}: {text}")
            if t["role"] == "assistant":
                item.setForeground(Qt.GlobalColor.green)
            self._conv_list.addItem(item)
        self._conv_list.scrollToBottom()

    def _load_meals(self):
        summary = store.get_meals(days=30)
        if not summary:
            from ..config import display_name
            self._meals_text.setPlainText(f"No meals logged yet.\nSay '{display_name()}, I ate...' to log a meal.")
            return
        lines = []
        total = 0
        for m in summary:
            ts = m["timestamp"][:16].replace("T", " ")
            cal = f"  ({m['calories']} kcal)" if m["calories"] else ""
            lines.append(f"[{ts}]{cal}  {m['description']}")
            if m["calories"]:
                total += m["calories"]
        if total:
            lines.append(f"\nTotal logged: {total} kcal")
        self._meals_text.setPlainText("\n".join(lines))
