import queue

import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_MS = 30
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_MS / 1000)  # 480 samples


class AudioStream:
    def __init__(self):
        self._queue: queue.Queue[bytes] = queue.Queue()
        self._stream = None
        self._running = False

    def start(self):
        self._running = True
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype='int16',
            blocksize=CHUNK_SAMPLES,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self):
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()

    def _callback(self, indata, frames, time, status):
        if self._running:
            self._queue.put(bytes(indata))

    def read_chunk(self, timeout: float = 0.1) -> bytes | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None
