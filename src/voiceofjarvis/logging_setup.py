"""
Centralized logging — console + rotating file in ~/Library/Logs/VoiceOfIU.

Call setup() once at startup. File logs survive across runs and are where you
look when the app runs headless under the LaunchAgent.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

_LOG_DIR = os.path.expanduser("~/Library/Logs/VoiceOfIU")
_LOG_FILE = os.path.join(_LOG_DIR, "voiceofiu.log")

_configured = False


def setup(level: int = logging.INFO):
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger()
    root.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-7s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
        file_handler = RotatingFileHandler(
            _LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8",
        )
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
    except Exception as e:
        root.warning(f"File logging unavailable: {e}")

    # Quiet noisy third-party loggers
    for noisy in ("httpx", "urllib3", "huggingface_hub", "PIL"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def log_path() -> str:
    return _LOG_FILE
