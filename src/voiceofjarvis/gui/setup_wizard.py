"""
First-run setup wizard.

Checks the runtime environment (Claude CLI, Codex, Ollama, Piper voice model,
embedding model) and shows what's ready vs missing. Offers a one-click pull of
the optional embedding model. Shown once; a marker file suppresses it afterwards.
"""

import logging
import os
import subprocess

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

log = logging.getLogger(__name__)

_MARKER = os.path.expanduser("~/.config/VoiceOfIU/.setup_done")


def should_show() -> bool:
    return not os.path.exists(_MARKER)


def _mark_done():
    os.makedirs(os.path.dirname(_MARKER), exist_ok=True)
    with open(_MARKER, "w") as f:
        f.write("ok")


class _PullThread(QThread):
    """Pulls the Ollama embedding model in the background."""
    done = pyqtSignal(bool)

    def run(self):
        try:
            r = subprocess.run(
                ["ollama", "pull", "nomic-embed-text"],
                capture_output=True, text=True, timeout=600,
            )
            self.done.emit(r.returncode == 0)
        except Exception as e:
            log.warning(f"Embed model pull failed: {e}")
            self.done.emit(False)


class SetupWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("VoiceOfIU — Setup")
        self.setMinimumWidth(480)
        self.setStyleSheet("background:#0f1117; color:#e8e9f0;")
        self._pull_thread = None
        self._setup_ui()
        self._run_checks()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title = QLabel("Welcome to VoiceOfIU")
        title.setStyleSheet("font-size:20px; font-weight:bold; color:#7c6cfc;")
        layout.addWidget(title)

        # Name picker — what the user calls their assistant
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("What should I call your assistant?"))
        self._name_edit = QLineEdit()
        from ..config import config
        self._name_edit.setText(config.wake_word.upper())
        self._name_edit.setPlaceholderText("IU")
        self._name_edit.setMaximumWidth(160)
        self._name_edit.setStyleSheet(
            "background:#1a1d27; color:#e8e9f0; padding:6px; border-radius:4px;")
        name_row.addWidget(self._name_edit)
        layout.addLayout(name_row)

        hint = QLabel("You'll say this name to wake it — e.g. “Hey IU” or “IU what's the weather”.")
        hint.setStyleSheet("color:#8a8fa8; font-size:11px;")
        layout.addWidget(hint)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color:#2d3148;")
        layout.addWidget(line)

        self._rows: dict[str, QLabel] = {}
        for key, name in [
            ("claude", "Claude Code CLI (primary brain)"),
            ("codex", "Codex CLI (code tasks, optional)"),
            ("ollama", "Ollama (offline fallback)"),
            ("piper", "Piper voice (TTS, optional)"),
            ("embed", "Embedding model (semantic memory, optional)"),
        ]:
            row = QHBoxLayout()
            label = QLabel(name)
            status = QLabel("checking…")
            status.setStyleSheet("color:#8a8fa8;")
            self._rows[key] = status
            row.addWidget(label)
            row.addStretch()
            row.addWidget(status)
            layout.addLayout(row)

        self._pull_btn = QPushButton("Download embedding model (recommended)")
        self._pull_btn.setStyleSheet(
            "background:#7c6cfc; color:white; padding:8px; border-radius:5px;")
        self._pull_btn.clicked.connect(self._pull_embed)
        self._pull_btn.setVisible(False)
        layout.addWidget(self._pull_btn)

        # Dictation permission (Input Monitoring) — grant from here
        dict_row = QHBoxLayout()
        dict_row.addWidget(QLabel("Dictation hotkey (Cmd+Shift+D)"))
        dict_row.addStretch()
        self._dict_status = QLabel("checking…")
        self._dict_status.setStyleSheet("color:#8a8fa8;")
        dict_row.addWidget(self._dict_status)
        self._dict_btn = QPushButton("Enable")
        self._dict_btn.setStyleSheet(
            "background:#7c6cfc; color:white; padding:4px 12px; border-radius:5px;")
        self._dict_btn.clicked.connect(self._grant_dictation)
        dict_row.addWidget(self._dict_btn)
        layout.addLayout(dict_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        done_btn = QPushButton("Get Started")
        done_btn.setStyleSheet(
            "background:#4ade80; color:#0f1117; padding:8px 24px; "
            "border-radius:5px; font-weight:bold;")
        done_btn.clicked.connect(self._finish)
        btn_row.addWidget(done_btn)
        layout.addLayout(btn_row)

    def _set(self, key: str, ok: bool, optional: bool = False):
        s = self._rows[key]
        if ok:
            s.setText("✅ ready")
            s.setStyleSheet("color:#4ade80;")
        elif optional:
            s.setText("⚠️ not set up")
            s.setStyleSheet("color:#fbbf24;")
        else:
            s.setText("❌ missing")
            s.setStyleSheet("color:#f87171;")

    def _run_checks(self):
        from ..memory import embeddings
        from ..output import tts
        from ..router import claude_client, codex_client, ollama_client

        self._set("claude", claude_client.is_available())
        self._set("codex", codex_client.is_available(), optional=True)
        self._set("ollama", ollama_client.is_running(), optional=True)
        self._set("piper", tts._check_piper(), optional=True)

        embed_ok = embeddings.is_available()
        self._set("embed", embed_ok, optional=True)
        # Offer the pull only if Ollama is up but the model is missing
        if not embed_ok and ollama_client.is_running():
            self._pull_btn.setVisible(True)

        self._refresh_dictation()

    def _refresh_dictation(self):
        from ..dictation import dictation
        granted = dictation.has_permission()
        if granted:
            self._dict_status.setText("✅ enabled")
            self._dict_status.setStyleSheet("color:#4ade80;")
            self._dict_btn.setVisible(False)
        else:
            self._dict_status.setText("⚠️ off")
            self._dict_status.setStyleSheet("color:#fbbf24;")
            self._dict_btn.setVisible(True)

    def _grant_dictation(self):
        from ..dictation import dictation
        dictation.request_permission()   # fires the macOS prompt (first time)
        dictation.open_settings()        # and opens the exact Settings pane
        self._dict_status.setText("grant in System Settings, then reopen")
        self._dict_status.setStyleSheet("color:#8a8fa8;")

    def _pull_embed(self):
        self._pull_btn.setEnabled(False)
        self._pull_btn.setText("Downloading… this can take a few minutes")
        self._pull_thread = _PullThread()
        self._pull_thread.done.connect(self._pull_finished)
        self._pull_thread.start()

    def _pull_finished(self, ok: bool):
        from ..memory import embeddings
        embeddings._available = None  # reset cache
        self._set("embed", embeddings.is_available(), optional=True)
        self._pull_btn.setVisible(False)

    def _finish(self):
        from ..config import config, save
        from ..listening import wake_word

        name = self._name_edit.text().strip() or "IU"
        config.wake_word = name.lower()
        save()
        wake_word.set_wake_word(config.wake_word)

        _mark_done()
        self.accept()
