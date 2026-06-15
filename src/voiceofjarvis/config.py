"""Runtime config. Persisted user settings live in a JSON overlay; no secrets on disk."""

import json
import logging
import os

log = logging.getLogger(__name__)

_SETTINGS_PATH = os.path.expanduser("~/.config/VoiceOfIU/settings.json")

# Keys persisted to / loaded from settings.json
_PERSISTED = (
    "wake_word", "whisper_model", "ollama_model", "offline_mode", "context_window",
    "allow_calendar", "allow_mail", "allow_notes", "allow_files",
)


class Config:
    # LLM routing
    offline_mode: bool = False          # True → always use Ollama
    default_llm: str = "claude"         # "claude" | "ollama"
    claude_model: str = "fast"          # "fast" | "balanced" | "powerful"
    ollama_model: str = "llama3.2"

    # STT
    whisper_model: str = "medium"        # "tiny" | "base" | "small" | "medium" | "large"

    # Behaviour
    wake_word: str = "iu"               # user-chosen AI name; default "IU"
    context_window: int = 10            # turns to keep in rolling context
    live_transcription: bool = True     # show words as you speak (set False if it lags)

    # Access consent — OFF by default. Nothing on your Mac is opened/read until
    # you explicitly enable it in Settings. Prevents silent access to private data.
    allow_calendar: bool = False
    allow_mail: bool = False
    allow_notes: bool = False
    allow_files: bool = False


config = Config()


def display_name() -> str:
    """Name for UI labels — uppercase for short acronyms, title-case otherwise."""
    n = config.wake_word.strip()
    return n.upper() if len(n.replace(" ", "")) <= 3 else n.title()


def spoken_name() -> str:
    """Name for TTS — short acronyms are spelled out ('iu' → 'I U') so TTS says them right."""
    n = config.wake_word.strip()
    if len(n) <= 3 and n.replace(" ", "").isalpha():
        return " ".join(n.upper())
    return n.title()


def save():
    """Persist user-configurable settings to the JSON overlay."""
    try:
        os.makedirs(os.path.dirname(_SETTINGS_PATH), exist_ok=True)
        data = {k: getattr(config, k) for k in _PERSISTED}
        with open(_SETTINGS_PATH, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log.warning(f"Could not save settings: {e}")


def _load():
    """Overlay persisted settings onto the defaults at startup."""
    if not os.path.exists(_SETTINGS_PATH):
        return
    try:
        with open(_SETTINGS_PATH) as f:
            data = json.load(f)
        for k in _PERSISTED:
            if k in data:
                setattr(config, k, data[k])
    except Exception as e:
        log.warning(f"Could not load settings: {e}")


_load()
