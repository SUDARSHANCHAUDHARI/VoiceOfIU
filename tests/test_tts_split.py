"""Sentence splitting for streaming TTS."""

from src.voiceofiu.output.tts import _SENTENCE_END, _is_non_latin


def test_sentence_split():
    parts = _SENTENCE_END.split("Hello there. How are you? I am fine.")
    assert parts == ["Hello there.", "How are you?", "I am fine."]


def test_no_split_mid_sentence():
    parts = _SENTENCE_END.split("This is one sentence with no breaks")
    assert len(parts) == 1


def test_non_latin_detection():
    assert _is_non_latin("सुप्रभात नमस्ते")          # Marathi/Devanagari
    assert _is_non_latin("こんにちは世界")              # Japanese
    assert not _is_non_latin("Good morning everyone")  # English
