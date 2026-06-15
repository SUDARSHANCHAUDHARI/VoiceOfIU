"""Wake word detection — the most failure-prone piece (Whisper mishears 'IU AI')."""

import pytest
from src.voiceofjarvis.listening.wake_word import detect


@pytest.mark.parametrize("phrase", [
    "IU AI what is the weather",
    "are you AI what is the weather",   # Whisper's common mishearing
    "are you a i tell me the time",
    "hey IU what's up",
    "hey you listen play music",
    "listen IU AI translate this",
])
def test_triggers_fire(phrase):
    triggered, intent = detect(phrase)
    assert triggered, f"should trigger on: {phrase}"
    assert intent, "intent should be extracted"


@pytest.mark.parametrize("phrase", [
    "what is the weather today",
    "the weather is nice",
    "tell me a joke",
    "",
])
def test_non_triggers(phrase):
    triggered, intent = detect(phrase)
    assert not triggered


def test_intent_strips_wake_word():
    _, intent = detect("IU AI what is the weather")
    assert "iu" not in intent.lower()
    assert "weather" in intent.lower()


def test_punctuation_after_wake_word():
    # "Are you AI?" with trailing question mark must still trigger
    triggered, intent = detect("Are you AI? what time is it")
    assert triggered
    assert "time" in intent.lower()


def test_wake_word_only_returns_empty_intent():
    triggered, intent = detect("IU AI")
    assert triggered
    assert intent is None
