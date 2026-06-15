"""
PyQt6 application shell.
Audio pipeline runs in VoiceThread (QThread).
GUI runs in main thread via QApplication event loop.
"""

import logging
import sys
import time

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication

from ..config import config
from ..listening.audio import AudioStream
from ..listening.stt import transcribe, warm_up
from ..listening.vad import VoiceActivityDetector
from ..listening.wake_word import detect as wake_detect
from ..memory import store, summariser
from ..output.echo_guard import EchoGuard
from ..output.tts import speak, stream_speak
from ..output.tts import stop as tts_stop
from ..router.planner import plan
from ..router.router import respond_stream
from ..tools.dispatcher import augment, is_stop_command

log = logging.getLogger(__name__)


def _chunk_level(chunk: bytes) -> float:
    """RMS amplitude of int16 PCM chunk, normalized to 0.0–1.0."""
    try:
        samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
        if samples.size == 0:
            return 0.0
        rms = np.sqrt(np.mean(samples ** 2))
        # 32768 is int16 max; scale up so normal speech fills the bar
        return float(min(1.0, rms / 8000.0))
    except Exception:
        return 0.0


class VoiceThread(QThread):
    """Audio pipeline running in background thread."""
    transcript_received = pyqtSignal(str)
    intent_detected     = pyqtSignal(str)
    response_ready      = pyqtSignal(str)
    status_changed      = pyqtSignal(str)
    audio_level         = pyqtSignal(float)   # 0.0–1.0 mic level for volume meter
    partial_transcript  = pyqtSignal(str)     # live interim text while speaking

    def __init__(self):
        super().__init__()
        self._paused = False
        self._running = True
        self._partial_count = 0

    def _emit_partial(self, vad):
        """Transcribe the in-progress speech buffer and emit it as interim text."""
        buf = vad.partial()
        if not buf:
            return
        try:
            text = transcribe(buf, model_size=config.whisper_model)
        except Exception:
            return
        if text and len(text.strip()) > 1:
            self.partial_transcript.emit(text.strip())

    def pause(self):
        self._paused = True
        self.status_changed.emit("paused")

    def resume(self):
        self._paused = False
        self.status_changed.emit("listening")

    def stop(self):
        self._running = False

    def run(self):
        FOLLOWUP_SECONDS = 15  # stay active after a response

        audio = AudioStream()
        vad   = VoiceActivityDetector(aggressiveness=2)
        echo  = EchoGuard()
        followup_until = 0.0  # epoch time until which wake word is not required

        # Announce BEFORE mic starts — prevents echo triggering wake word
        from ..config import spoken_name
        name = spoken_name()
        speak(f"{name} online. Say {name} to activate.", blocking=True)

        audio.start()
        self.status_changed.emit("listening")
        log.info("VoiceThread started — listening")

        while self._running:
            if self._paused:
                self.msleep(100)
                continue

            chunk = audio.read_chunk(timeout=0.05)
            if chunk is None:
                continue

            if echo.is_muted():
                continue

            # Emit mic level for the volume meter (RMS of int16 PCM → 0–1)
            self.audio_level.emit(_chunk_level(chunk))

            segment = vad.process_chunk(chunk)
            if segment is None:
                # Live preview: transcribe the in-progress buffer ~every 0.6s
                if config.live_transcription:
                    self._partial_count += 1
                    if self._partial_count >= 20:
                        self._partial_count = 0
                        self._emit_partial(vad)
                continue
            self._partial_count = 0

            try:
                followup_until = self._handle_segment(
                    segment, echo, followup_until, FOLLOWUP_SECONDS)
            except Exception:
                # One bad turn (LLM timeout, mic glitch, tool error) must never
                # kill the listener — log, recover, keep listening.
                log.exception("Error handling voice segment — recovering")
                followup_until = 0.0
                self.status_changed.emit("listening")

        audio.stop()
        log.info("VoiceThread stopped")

    def _handle_segment(self, segment, echo, followup_until, followup_seconds):
        """Process one captured speech segment. Returns the updated followup_until."""
        self.status_changed.emit("transcribing")
        text = transcribe(segment, model_size=config.whisper_model)
        if not text:
            self.status_changed.emit("listening")
            return followup_until

        # Drop noise: punctuation-only or fewer than 2 real words
        clean = text.strip(".,!? ")
        if len(clean.split()) < 2:
            self.status_changed.emit("listening")
            return followup_until

        # Stop command — works anytime, no wake word needed
        if is_stop_command(clean):
            tts_stop()
            self.status_changed.emit("listening")
            return 0.0

        self.transcript_received.emit(text)
        triggered, intent = wake_detect(text)

        # In follow-up window: treat any speech as intent (no wake word needed)
        if not triggered and time.time() < followup_until:
            triggered = True
            intent = clean

        if not triggered:
            self.status_changed.emit("listening")
            return followup_until

        if not intent or len(intent.split()) < 2:
            speak("Yes? What can I do for you?",
                  on_start=echo.on_tts_start, on_done=echo.on_tts_done, blocking=True)
            self.status_changed.emit("listening")
            return time.time() + followup_seconds

        self.intent_detected.emit(intent)
        self.status_changed.emit("thinking")

        # Split multi-step requests ("do X and then Y") into ordered sub-tasks
        steps = plan(intent)

        store.save_turn("user", intent or "")
        for step in steps:
            augmented = augment(step)
            self.status_changed.emit("speaking")
            reply = stream_speak(
                respond_stream(augmented),
                on_start=echo.on_tts_start,
                on_done=echo.on_tts_done,
            )
            self.response_ready.emit(reply)
            store.save_turn("assistant", reply)

        self.status_changed.emit("listening")
        return time.time() + followup_seconds


def run_gui():
    """Start the full desktop app with system tray."""
    from .logs_window import LogsWindow
    from .memory_viewer import MemoryViewer
    from .settings_window import SettingsWindow
    from .tray import TrayIcon

    store.init()
    summariser.maybe_summarise_async()  # compact old memory in background

    # Warm up Whisper in the background so the first response isn't slow
    import threading
    threading.Thread(target=warm_up, args=(config.whisper_model,), daemon=True).start()

    app = QApplication(sys.argv)
    app.setApplicationName("VoiceOfIU")
    app.setQuitOnLastWindowClosed(False)  # keep running when windows close

    # First-run setup wizard
    from .setup_wizard import SetupWizard, should_show
    if should_show():
        SetupWizard().exec()

    # Windows
    logs_win     = LogsWindow()
    memory_win   = MemoryViewer()
    settings_win = SettingsWindow()

    # Audio-reactive orb HUD
    from .orb_widget import OrbWidget
    orb = OrbWidget()

    # Voice thread
    voice = VoiceThread()
    voice.transcript_received.connect(logs_win.log_heard)
    voice.intent_detected.connect(logs_win.log_intent)
    voice.response_ready.connect(logs_win.log_response)
    voice.status_changed.connect(logs_win.log_status)
    voice.audio_level.connect(logs_win.set_level)
    voice.audio_level.connect(orb.set_level)
    voice.status_changed.connect(orb.set_state)
    voice.transcript_received.connect(orb.set_heard)
    voice.response_ready.connect(orb.set_reply)
    voice.partial_transcript.connect(orb.set_partial)

    # Tray
    tray = TrayIcon()
    voice.status_changed.connect(tray.set_status)

    _paused = [False]

    def toggle_listen():
        if _paused[0]:
            voice.resume()
            _paused[0] = False
            tray.set_paused(False)
        else:
            voice.pause()
            _paused[0] = True
            tray.set_paused(True)

    def toggle_orb():
        orb.hide() if orb.isVisible() else (orb.show(), orb.raise_())

    # Orb satellite nodes open the windows
    orb.open_logs.connect(lambda: (logs_win.show(), logs_win.raise_()))
    orb.open_memory.connect(lambda: (memory_win.refresh(), memory_win.show(), memory_win.raise_()))
    orb.open_settings.connect(lambda: settings_win.show())

    tray.show_logs_requested.connect(lambda: (logs_win.show(), logs_win.raise_()))
    tray.show_memory_requested.connect(lambda: (memory_win.refresh(), memory_win.show(), memory_win.raise_()))
    tray.show_settings_requested.connect(lambda: settings_win.show())
    tray.toggle_listen_requested.connect(toggle_listen)
    tray.toggle_orb_requested.connect(toggle_orb)
    tray.quit_requested.connect(lambda: (voice.stop(), app.quit()))

    # Position the orb near the top-right of the primary screen and show it
    screen = app.primaryScreen().availableGeometry()
    orb.move(screen.right() - orb.width() - 40, screen.top() + 60)
    orb.show()

    # Dictation — hold Cmd+Shift+D to transcribe into the focused app
    from ..dictation import dictation
    if dictation.is_supported():
        dictation.start(
            stt_fn=lambda audio: transcribe(audio, model_size=config.whisper_model),
            on_status=voice.status_changed.emit,
        )

    # Logs stay hidden — the orb shows the live caption; open Logs via the ≡ node
    voice.start()  # announcement now happens inside VoiceThread before mic opens
    sys.exit(app.exec())
