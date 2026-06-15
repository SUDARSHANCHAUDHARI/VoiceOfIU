import webrtcvad

SAMPLE_RATE = 16000
CHUNK_MS = 30
CHUNK_BYTES = int(SAMPLE_RATE * CHUNK_MS / 1000) * 2  # int16 = 2 bytes/sample

SILENCE_THRESHOLD_MS = 700   # end speech after 700ms silence
MIN_SPEECH_MS = 250          # ignore segments shorter than this


class VoiceActivityDetector:
    def __init__(self, aggressiveness: int = 2):
        self._vad = webrtcvad.Vad(aggressiveness)
        self._speech_chunks: list[bytes] = []
        self._silence_count = 0
        self._in_speech = False
        self._silence_limit = SILENCE_THRESHOLD_MS // CHUNK_MS
        self._min_chunks = MIN_SPEECH_MS // CHUNK_MS

    def process_chunk(self, chunk: bytes) -> bytes | None:
        """
        Feed one 30ms audio chunk. Returns the full speech segment bytes
        when a complete utterance has ended, otherwise None.
        """
        if len(chunk) != CHUNK_BYTES:
            return None

        is_speech = self._vad.is_speech(chunk, SAMPLE_RATE)

        if is_speech:
            self._in_speech = True
            self._silence_count = 0
            self._speech_chunks.append(chunk)
        elif self._in_speech:
            self._speech_chunks.append(chunk)
            self._silence_count += 1
            if self._silence_count >= self._silence_limit:
                return self._flush()

        return None

    def _flush(self) -> bytes | None:
        chunks = self._speech_chunks
        self._speech_chunks = []
        self._silence_count = 0
        self._in_speech = False
        if len(chunks) < self._min_chunks:
            return None
        return b"".join(chunks)

    def partial(self) -> bytes | None:
        """In-progress speech bytes while the user is still talking (for live preview)."""
        if self._in_speech and len(self._speech_chunks) >= self._min_chunks:
            return b"".join(self._speech_chunks)
        return None

    def reset(self):
        self._speech_chunks = []
        self._silence_count = 0
        self._in_speech = False
