import logging
import platform

import numpy as np

log = logging.getLogger(__name__)

_model = None
_backend: str | None = None


def warm_up(model_size: str = "base"):
    """
    Pre-load the model and run a tiny silent transcription so the FIRST real
    request isn't slow. Safe to call from a background thread at startup.
    """
    try:
        _load(model_size)
        silence = np.zeros(16000, dtype=np.int16).tobytes()  # 1s of silence
        transcribe(silence, model_size=model_size)
        log.info(f"Whisper '{model_size}' warmed up")
    except Exception as e:
        log.warning(f"Whisper warm-up skipped: {e}")


def _load(model_size: str = "base"):
    global _model, _backend
    if _model is not None:
        return

    is_apple_silicon = platform.system() == "Darwin" and platform.machine() == "arm64"

    if is_apple_silicon:
        try:
            import mlx_whisper  # noqa: F401 — just verify it imports
            _backend = "mlx"
            _model = f"mlx-community/whisper-{model_size}-mlx"
            return
        except ImportError:
            pass

    try:
        from faster_whisper import WhisperModel
        _backend = "faster_whisper"
        _model = WhisperModel(model_size, device="cpu", compute_type="int8")
        return
    except ImportError:
        pass

    raise RuntimeError(
        "No Whisper backend available. "
        "Run: pip install mlx-whisper  (Apple Silicon)  OR  pip install faster-whisper"
    )


def transcribe(audio_bytes: bytes, model_size: str = "base") -> str | None:
    """Transcribe raw 16kHz mono int16 PCM bytes → text string, or None if empty."""
    _load(model_size)

    audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    if _backend == "mlx":
        import mlx_whisper
        result = mlx_whisper.transcribe(
            audio_np,
            path_or_hf_repo=_model,
            language="en",
            initial_prompt="IU AI, are you AI, weather, temperature, time, reminder, search, code, write, open, close",
        )
        text = result.get("text", "").strip()

    elif _backend == "faster_whisper":
        # _model is a WhisperModel here (not the str repo path used by mlx)
        segments, _ = _model.transcribe(audio_np, beam_size=5, language="en")  # type: ignore[union-attr]
        text = " ".join(s.text for s in segments).strip()

    else:
        return None

    return text or None
