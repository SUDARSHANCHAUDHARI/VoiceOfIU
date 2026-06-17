import os
import platform
import re
import subprocess
import threading
from collections.abc import Callable, Iterator

_stop_event = threading.Event()

# Sentence boundary — splits on . ! ? followed by space or end
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def stop():
    """Interrupt any currently playing TTS immediately."""
    _stop_event.set()
    if platform.system() == "Darwin":
        subprocess.run(["killall", "say"], capture_output=True)
    try:
        import sounddevice as sd
        sd.stop()
    except Exception:
        pass


def _clear_stop():
    _stop_event.clear()

_piper_checked = False
_piper_ok = False
_piper_model: str | None = None

_PIPER_MODEL_DIRS = [
    os.path.expanduser("~/.local/share/piper"),
    os.path.expanduser("~/Library/Application Support/VoiceOfIU/piper"),
]
_PIPER_MODEL_NAME = "en_US-ryan-medium.onnx"


def _find_piper_model() -> str | None:
    for d in _PIPER_MODEL_DIRS:
        p = os.path.join(d, _PIPER_MODEL_NAME)
        if os.path.exists(p):
            return p
    return None


def _check_piper() -> bool:
    global _piper_checked, _piper_ok, _piper_model
    if _piper_checked:
        return _piper_ok
    _piper_checked = True
    try:
        from piper import PiperVoice  # noqa: F401
        _piper_model = _find_piper_model()
        _piper_ok = _piper_model is not None
    except ImportError:
        _piper_ok = False
    return _piper_ok


def speak(
    text: str,
    on_start: Callable | None = None,
    on_done: Callable | None = None,
    blocking: bool = False,
) -> threading.Thread | None:
    """Synthesize and play text. Calls on_start before playback, on_done after."""
    if not text or not text.strip():
        return None

    safe_text = _redact(text)

    def _run():
        _clear_stop()
        if on_start:
            on_start()
        try:
            if _stop_event.is_set():
                return
            if _check_piper() and not _is_non_latin(safe_text):
                _play_piper(safe_text)
            else:
                _play_fallback(safe_text)
        finally:
            if on_done:
                on_done()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    if blocking:
        t.join()
    return t


def stream_speak(
    chunks: Iterator[str],
    on_start: Callable | None = None,
    on_done: Callable | None = None,
) -> str:
    """
    Speak text as it arrives. Consumes a generator of text deltas, splits into
    sentences, and speaks each complete sentence immediately. Returns full text.

    This is the latency win — first sentence plays while the LLM is still generating.
    """
    _clear_stop()
    if on_start:
        on_start()

    buffer = ""
    full = ""
    try:
        for delta in chunks:
            if _stop_event.is_set():
                break
            buffer += delta
            full += delta
            # Emit any complete sentences in the buffer
            parts = _SENTENCE_END.split(buffer)
            if len(parts) > 1:
                *complete, buffer = parts
                for sentence in complete:
                    if _stop_event.is_set():
                        break
                    _speak_blocking(sentence.strip())
        # Speak whatever remains
        if buffer.strip() and not _stop_event.is_set():
            _speak_blocking(buffer.strip())
    finally:
        if on_done:
            on_done()
    return full.strip()


def _speak_blocking(text: str):
    """Synthesize and play one chunk, blocking until done."""
    if not text:
        return
    text = _redact(text)
    if _check_piper() and not _is_non_latin(text):
        _play_piper(text)
    else:
        _play_fallback(text)


def _redact(text: str) -> str:
    """Safety net — strip any secrets before they're spoken aloud."""
    try:
        from ..tools import redact as _r
        return _r.redact(text)
    except Exception:
        return text


def _play_piper(text: str):
    import numpy as np
    import sounddevice as sd
    from piper import PiperVoice

    voice = PiperVoice.load(_piper_model)  # type: ignore[arg-type]  # guarded by _check_piper()
    chunks = [np.frombuffer(c, dtype=np.int16) for c in voice.synthesize_stream_raw(text)]  # type: ignore[attr-defined]  # piper ships no stubs
    if chunks:
        audio = np.concatenate(chunks).astype(np.float32) / 32768.0
        sd.play(audio, samplerate=22050, blocking=True)


def _is_non_latin(text: str) -> bool:
    """True if text contains significant non-Latin script (Devanagari, Arabic, CJK, etc.)."""
    non_latin = sum(1 for c in text if ord(c) > 0x036F)
    return non_latin > len(text) * 0.2


def _play_fallback(text: str):
    if platform.system() == "Darwin":
        if _is_non_latin(text):
            # macOS auto-selects voice — handles Devanagari/Marathi better than Samantha
            subprocess.run(["say", text], check=False)
        else:
            subprocess.run(["say", "-v", "Samantha", text], check=False)
    else:
        print(f"[TTS fallback] {text}")
