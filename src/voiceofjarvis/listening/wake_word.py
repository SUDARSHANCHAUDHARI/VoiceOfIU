"""
Wake word detection. The name is user-configurable (default "IU").

Triggers are built dynamically from the chosen name:
  "{name}", "hey {name}", "{name} ai", "listen {name}", "hey {name} listen"

For the default "iu" we add hand-tuned phonetic aliases because Whisper mishears
it as "are you" / "hey you". Custom names rely on Whisper transcribing them
correctly (real-word names usually work fine).
"""

import re

# Whisper mishearings specific to "IU" — only added when the name is IU.
_IU_ALIASES = [
    "iu ai", "are you ai", "are you a i", "i you ai", "iu a i",
    "hey iu", "hey, iu", "hey you", "hey, you",
    "hey iu listen", "hey you listen",
    "listen iu ai", "listen are you ai", "listen iu", "listen, iu",
]

WAKE_WORD = "iu"
_PATTERN: re.Pattern | None = None


def _build_triggers(name: str) -> list[str]:
    name = name.lower().strip()
    triggers = {
        name,
        f"hey {name}",
        f"{name} ai",
        f"listen {name}",
        f"hey {name} listen",
    }
    if name in ("iu", "iu ai"):
        triggers.update(_IU_ALIASES)
    # longest first so multi-word triggers match before bare name
    return sorted(triggers, key=len, reverse=True)


def set_wake_word(name: str):
    """(Re)build the trigger pattern for a new wake-word name."""
    global WAKE_WORD, _PATTERN
    WAKE_WORD = name.lower().strip() or "iu"
    triggers = _build_triggers(WAKE_WORD)
    _PATTERN = re.compile(
        r"\b(?:" + "|".join(re.escape(t) for t in triggers) + r")\b[,\.\?!]?",
        re.IGNORECASE,
    )


def detect(transcript: str) -> tuple[bool, str | None]:
    """
    Returns (triggered, intent). Matches any trigger phrase for the configured
    name; intent is the transcript with the trigger stripped out.
    """
    if _PATTERN is None:
        set_wake_word(WAKE_WORD)
    assert _PATTERN is not None  # set_wake_word always assigns it

    lower = transcript.lower().strip()
    if not _PATTERN.search(lower):
        return False, None

    intent = _PATTERN.sub("", transcript)
    intent = re.sub(r"\s+", " ", intent).strip().strip(".,!?").strip()
    return True, intent or None


# Initialise from persisted config at import
try:
    from ..config import config
    set_wake_word(config.wake_word)
except Exception:
    set_wake_word("iu")
