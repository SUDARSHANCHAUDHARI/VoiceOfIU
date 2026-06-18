"""Settings window — configure LLM routing, audio, and MCP servers."""

import json
import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..config import config
from ..router import claude_client, codex_client, ollama_client
from ..tools.mcp_manager import CONFIG_PATH as MCP_CONFIG_PATH

_STYLE = "background:#1a1d27; color:#e8e9f0;"


class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("VoiceOfIU — Settings")
        self.setMinimumWidth(520)
        from . import theme
        theme.apply(self)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._general_tab(), "General")
        tabs.addTab(self._llm_tab(), "LLM / Routing")
        tabs.addTab(self._audio_tab(), "Audio")
        tabs.addTab(self._mcp_tab(), "MCP Servers")
        layout.addWidget(tabs)

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("background:#7c6cfc; color:white; padding:6px 20px; border-radius:4px;")
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignRight)

    # ── General ──────────────────────────────────────────────────────────────

    def _general_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(16, 16, 16, 16)

        self._name_edit = QLineEdit(config.wake_word.upper())
        self._name_edit.setPlaceholderText("IU")
        form.addRow("Assistant name (wake word):", self._name_edit)

        self._offline_cb = QCheckBox("Offline mode (Ollama only, no CLIs)")
        self._offline_cb.setChecked(config.offline_mode)
        form.addRow(self._offline_cb)

        self._ctx_spin = QSpinBox()
        self._ctx_spin.setRange(2, 30)
        self._ctx_spin.setValue(config.context_window)
        form.addRow("Context window (turns):", self._ctx_spin)

        # Permissions — OFF by default; nothing is opened/read until enabled
        form.addRow(QLabel(""))
        form.addRow(QLabel("Permissions (off = never accessed):"))
        self._allow_calendar = QCheckBox("Allow Calendar access")
        self._allow_calendar.setChecked(config.allow_calendar)
        form.addRow(self._allow_calendar)
        self._allow_mail = QCheckBox("Allow Mail access")
        self._allow_mail.setChecked(config.allow_mail)
        form.addRow(self._allow_mail)
        self._allow_notes = QCheckBox("Allow Notes access")
        self._allow_notes.setChecked(config.allow_notes)
        form.addRow(self._allow_notes)
        self._allow_files = QCheckBox("Allow local file reading (Documents/Desktop/Downloads)")
        self._allow_files.setChecked(config.allow_files)
        form.addRow(self._allow_files)

        # Dictation (Input Monitoring) — macOS-level permission, grant via button
        from ..dictation import dictation
        granted = dictation.has_permission()
        dict_btn = QPushButton("Enable dictation hotkey (Cmd+Shift+D)")
        dict_btn.setEnabled(not granted)
        dict_btn.setText("Dictation enabled ✅" if granted else "Enable dictation hotkey (Cmd+Shift+D)")
        dict_btn.clicked.connect(lambda: (dictation.request_permission(), dictation.open_settings()))
        form.addRow(dict_btn)

        # Status indicators
        form.addRow(QLabel(""))
        form.addRow(QLabel("Status:"))
        form.addRow("Claude CLI:", QLabel("✅ Found" if claude_client.is_available() else "❌ Not found"))
        form.addRow("Codex CLI:", QLabel("✅ Found" if codex_client.is_available() else "⚠️ Not installed (optional)"))
        form.addRow("Ollama:", QLabel("✅ Running" if ollama_client.is_running() else "⚠️ Not running"))

        return w

    # ── LLM / Routing ────────────────────────────────────────────────────────

    def _llm_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(16, 16, 16, 16)

        form.addRow(QLabel("Routing priority: Claude Code CLI → Codex (code tasks) → Ollama (offline)"))
        form.addRow(QLabel(""))

        self._ollama_model = QLineEdit(config.ollama_model)
        form.addRow("Ollama model (offline fallback):", self._ollama_model)

        form.addRow(QLabel(""))
        form.addRow(QLabel("CLI locations (auto-detected, read-only):"))
        import shutil
        claude_path = shutil.which("claude") or "not found"
        codex_path = shutil.which("codex") or "not installed"
        form.addRow("claude:", QLabel(claude_path))
        form.addRow("codex:", QLabel(codex_path))

        return w

    # ── Audio ─────────────────────────────────────────────────────────────────

    def _audio_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(16, 16, 16, 16)

        self._whisper_model = QComboBox()
        for m in ["tiny", "base", "small", "medium"]:
            self._whisper_model.addItem(m)
        self._whisper_model.setCurrentText(config.whisper_model)
        form.addRow("Whisper model:", self._whisper_model)

        form.addRow(QLabel("Note: larger = more accurate but slower. 'base' recommended for Apple Silicon."))

        # Voice ─ playful baby voice option (IU is named after the author's daughter)
        form.addRow(QLabel(""))
        self._baby_voice = QCheckBox("Baby voice 👶 — speak in a cute, high-pitched little-baby voice")
        self._baby_voice.setChecked(config.baby_voice)
        form.addRow(self._baby_voice)
        form.addRow(QLabel("Optional: turn this on any time you'd like IU to talk like a little baby."))

        return w

    # ── MCP ───────────────────────────────────────────────────────────────────

    def _mcp_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addWidget(QLabel(f"Config file: {MCP_CONFIG_PATH}"))
        layout.addWidget(QLabel("Edit JSON below to add MCP servers:"))

        self._mcp_edit = QTextEdit()
        self._mcp_edit.setFont(QFont("Menlo", 11))
        self._mcp_edit.setStyleSheet(_STYLE)
        if os.path.exists(MCP_CONFIG_PATH):
            with open(MCP_CONFIG_PATH) as f:
                self._mcp_edit.setPlainText(f.read())
        else:
            self._mcp_edit.setPlainText(json.dumps({
                "servers": [
                    {"name": "my-server", "command": "npx",
                     "args": ["-y", "@modelcontextprotocol/server-name"]}
                ]
            }, indent=2))
        layout.addWidget(self._mcp_edit)

        return w

    # ── Save ─────────────────────────────────────────────────────────────────

    def _save(self):
        from ..config import save as save_settings
        from ..listening import wake_word

        new_name = self._name_edit.text().strip() or "IU"
        config.wake_word = new_name.lower()
        wake_word.set_wake_word(config.wake_word)

        config.offline_mode = self._offline_cb.isChecked()
        config.context_window = self._ctx_spin.value()
        config.ollama_model = self._ollama_model.text().strip()
        config.whisper_model = self._whisper_model.currentText()
        config.baby_voice = self._baby_voice.isChecked()

        config.allow_calendar = self._allow_calendar.isChecked()
        config.allow_mail = self._allow_mail.isChecked()
        config.allow_notes = self._allow_notes.isChecked()
        config.allow_files = self._allow_files.isChecked()

        save_settings()  # persist to settings.json

        # Save MCP config
        mcp_text = self._mcp_edit.toPlainText().strip()
        if mcp_text:
            try:
                json.loads(mcp_text)  # validate
                os.makedirs(os.path.dirname(MCP_CONFIG_PATH), exist_ok=True)
                with open(MCP_CONFIG_PATH, "w") as f:
                    f.write(mcp_text)
            except json.JSONDecodeError:
                pass  # invalid JSON — don't save

        self.accept()
