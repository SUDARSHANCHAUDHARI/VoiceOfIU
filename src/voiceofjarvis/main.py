"""
VoiceOfIU — entry point.

Modes:
  python run.py          → full desktop app (system tray + GUI)
  python run.py --no-gui → CLI mode (terminal only, no GUI)
"""

import argparse
import logging
import signal
import sys

from .logging_setup import setup as setup_logging

setup_logging()
log = logging.getLogger(__name__)


def run():
    parser = argparse.ArgumentParser(description="VoiceOfIU")
    parser.add_argument("--no-gui", action="store_true", help="Run in terminal mode, no GUI")
    args = parser.parse_args()

    if args.no_gui:
        _run_cli()
    else:
        _run_gui()


def _run_cli():
    """Terminal-only loop — no Qt required."""
    from .config import config
    from .listening.audio import AudioStream
    from .listening.stt import transcribe
    from .listening.vad import VoiceActivityDetector
    from .listening.wake_word import detect as wake_detect
    from .memory import store
    from .output.echo_guard import EchoGuard
    from .output.tts import speak, stream_speak
    from .router.router import respond_stream
    from .tools.dispatcher import augment

    store.init()
    log.info("VoiceOfIU starting (CLI mode)...")

    audio = AudioStream()
    vad   = VoiceActivityDetector(aggressiveness=2)
    echo  = EchoGuard()

    from .config import display_name, spoken_name
    name = spoken_name()
    speak(f"{name} online. Say {name} to activate.", blocking=True)
    audio.start()
    log.info(f"Listening — say '{display_name()}' to activate")

    def _shutdown(sig=None, frame=None):
        log.info("Shutting down.")
        audio.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    while True:
        chunk = audio.read_chunk(timeout=0.1)
        if chunk is None:
            continue
        if echo.is_muted():
            continue

        segment = vad.process_chunk(chunk)
        if segment is None:
            continue

        log.info("Transcribing...")
        text = transcribe(segment, model_size=config.whisper_model)
        if not text:
            continue

        log.info(f"Heard: {text}")
        triggered, intent = wake_detect(text)
        if not triggered:
            continue

        log.info(f"Intent: {intent!r}")
        augmented = augment(intent or "")
        response = stream_speak(
            respond_stream(augmented),
            on_start=echo.on_tts_start,
            on_done=echo.on_tts_done,
        )
        log.info(f"Response: {response}")

        store.save_turn("user", intent or "")
        store.save_turn("assistant", response)


def _run_gui():
    from .gui.app import run_gui
    run_gui()
