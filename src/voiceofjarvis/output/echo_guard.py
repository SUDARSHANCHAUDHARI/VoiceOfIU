import threading
import time


class EchoGuard:
    """
    Tracks TTS playback state so the STT loop can ignore IU AI's own voice.
    Call on_tts_start() before playback begins, on_tts_done() after it ends.
    is_muted() returns True during playback + a short buffer after.
    """

    def __init__(self, buffer_seconds: float = 0.6):
        self._lock = threading.Lock()
        self._playing = False
        self._mute_until = 0.0
        self._buffer = buffer_seconds

    def on_tts_start(self):
        with self._lock:
            self._playing = True

    def on_tts_done(self):
        with self._lock:
            self._playing = False
            self._mute_until = time.monotonic() + self._buffer

    def is_muted(self) -> bool:
        with self._lock:
            return self._playing or time.monotonic() < self._mute_until
