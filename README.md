# VoiceOfIU

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![macOS](https://img.shields.io/badge/macOS-Apple%20Silicon-000000?logo=apple)
![No API keys](https://img.shields.io/badge/API%20keys-none-4ade80)
![License](https://img.shields.io/badge/License-Apache%202.0-7c6cfc)

A private, **local** voice assistant for macOS — wake word, speech-to-text, LLM reasoning, and text-to-speech, all running on your machine. No API keys, no per-request billing: it drives the **Claude Code CLI**, **Codex CLI**, and **Ollama** as subprocesses using your existing logins.

> Default wake word is **“IU”** — fully renameable on first launch (e.g. “Hey Jarvis”, “Nova”).

---

## Features

- **Wake word** — say the name anywhere in a sentence (configurable). Whisper-mishearing aliases built in.
- **Audio-reactive orb HUD** — a floating, translucent reactor orb that pulses with your voice, draws a live waveform, shifts colour by state (listening → thinking → speaking), and shows a typewriter caption of the conversation. Three satellite nodes open Logs / Memory / Settings.
- **Streaming responses** — starts speaking the first sentence while the LLM is still generating.
- **Live transcription** — your words appear as you speak (toggleable).
- **Smart LLM routing** — Claude Code CLI (default brain) → Codex CLI (code tasks) → Ollama (offline). Ollama auto-picks the best installed model per task type.
- **Multi-step requests** — "check the weather and then remind me to call mom" is split into ordered sub-tasks.
- **Follow-up window** — keep talking for 15s after a reply without repeating the wake word.
- **Tools** — weather, web search, full-page fetch, screen OCR, nutrition logging, sandboxed file reading, and macOS **Calendar / Mail / Notes** (read + draft).
- **Dictation** — hold `Cmd+Shift+D`, speak, release → transcribed text pastes into the focused app.
- **Memory** — SQLite history, semantic recall (Ollama embeddings, FTS5 fallback), topic graph, and automatic old-conversation summarisation.
- **Privacy by default** — secret redaction at three chokepoints, and per-integration consent (Calendar/Mail/Notes/files stay OFF until you enable them).

## Requirements

- macOS on Apple Silicon (built/tested on M4, macOS 26)
- Python 3.11
- [Claude Code CLI](https://claude.com/claude-code) — logged in (`claude` runs in your terminal)
- Optional: [Ollama](https://ollama.com) running locally; Codex CLI (`codex login`)

## Install

```bash
cd VoiceOfIU
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Optional, for semantic memory search:

```bash
ollama pull nomic-embed-text
```

## Run

```bash
.venv/bin/python run.py            # full desktop app (orb + tray)
.venv/bin/python run.py --no-gui   # terminal-only mode
```

On first launch the **setup wizard** lets you name your assistant, checks your environment, and offers one-click enabling of the dictation hotkey.

Then just talk: **“IU, what’s the weather?”** · **“Hey IU, translate good morning to Marathi”** · say **“stop”** to interrupt.

## Interface

A frameless orb floats top-right of your screen:

- **Core** glows brighter with your voice level; **arcs** rotate continuously.
- **Colour = state:** 🟣 listening · 🟡 thinking · 🟢 speaking · 🔴 dictating · ⚪ paused.
- **Caption** below shows what you said and IU's reply (typewriter reveal, auto-fades).
- **Three dots** around the orb open Settings (top), Logs and Memory (bottom). Drag the orb to move it; double-click to hide.

## Permissions

macOS prompts the first time each is used — approve in **System Settings → Privacy & Security**. The setup wizard and Settings can take you straight to the right pane:

| Feature | macOS permission |
|---------|------------------|
| Listening | Microphone |
| Dictation hotkey | Input Monitoring |
| Calendar / Mail / Notes | Automation |
| Screen OCR | Screen Recording |

In-app, Calendar / Mail / Notes / file access are **off by default** and enabled per-integration under **Settings → Permissions** — nothing on your Mac is opened or read without your explicit opt-in.

## Configuration

- Change the assistant **name**, models, offline mode, permissions, and MCP servers in **Settings** or the setup wizard.
- Persisted to `~/.config/VoiceOfIU/settings.json`.
- Logs: `~/Library/Logs/VoiceOfIU/voiceofiu.log`.

## Auto-start (optional)

Run as a background agent that starts on login and restarts on crash:

```bash
scripts/install_autostart.sh     # enable
scripts/uninstall_autostart.sh   # disable
```

Build a double-clickable launcher app:

```bash
scripts/make_app.sh              # → dist/VoiceOfIU.app (ad-hoc signed)
```

## Architecture

```
mic → VAD → Whisper STT → wake word → planner → tool dispatch → LLM router → streaming TTS
                                                       │              │
                                                weather/web/files     ├─ Claude Code CLI
                                                calendar/mail/notes    ├─ Codex CLI
                                                screen OCR/nutrition    └─ Ollama (offline)
                                                       │
                                                 SQLite memory (history · semantic recall · topics)
```

| Layer | Module |
|-------|--------|
| Listening | `listening/` — audio, vad, stt, wake_word |
| Output | `output/` — tts (streaming, redacted), echo_guard |
| Routing | `router/` — claude_client, codex_client, ollama_client, router, planner |
| Tools | `tools/` — dispatcher, weather, web, screen, nutrition, local_files, macos_bridge, macos_*, consent, redact |
| Memory | `memory/` — store, search, embeddings, summariser, graph |
| GUI | `gui/` — app, orb_widget, theme, tray, logs_window, memory_viewer, settings_window, setup_wizard |

## Security & privacy

- **No API keys on disk.** LLMs are invoked as CLI subprocesses (your existing subscriptions) or local Ollama. The CLI runs isolated (clean persona, no project hooks) so IU stays a voice assistant.
- **Redaction** strips secrets (API keys, tokens, passwords) at three chokepoints: tool output → LLM, TTS output, and memory persistence.
- **Consent-gated access** — Calendar/Mail/Notes/files are never touched until you enable them in Settings.
- **File access is sandboxed** to Documents / Desktop / Downloads.
- **Mail is never auto-sent** — composing creates a draft for you to review.

## Development

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest          # 76 tests
.venv/bin/ruff check src/ tests/    # lint
.venv/bin/mypy src/voiceofiu/   # type check
```

## Author

Built by **Sudarshan Chaudhari** — [SudarshanTechLabs](https://github.com/SUDARSHANCHAUDHARI), Bangkok 🇹🇭

## License

Licensed under the **Apache License 2.0** — see [LICENSE](LICENSE). © 2026 Sudarshan Chaudhari (SudarshanTechLabs).

Bundled and runtime third-party components (e.g. PySide6 — LGPL; Whisper, Piper, Ollama models) retain their own respective licenses.
