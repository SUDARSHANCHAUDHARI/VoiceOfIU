"""Configurable assistant name — wake word rebuilds, display/spoken forms."""

import pytest
from src.voiceofiu import config as cfg
from src.voiceofiu.listening import wake_word


@pytest.fixture(autouse=True)
def restore_name():
    original = wake_word.WAKE_WORD
    yield
    wake_word.set_wake_word(original)


def test_default_iu_still_triggers_with_aliases():
    wake_word.set_wake_word("iu")
    assert wake_word.detect("are you AI what is the time")[0]
    assert wake_word.detect("hey IU what's up")[0]


def test_custom_name_jarvis():
    wake_word.set_wake_word("jarvis")
    assert wake_word.detect("jarvis what is the weather")[0]
    assert wake_word.detect("hey jarvis play music")[0]
    triggered, intent = wake_word.detect("jarvis what time is it")
    assert triggered and "time" in intent.lower()


def test_custom_name_does_not_use_iu_aliases():
    wake_word.set_wake_word("nova")
    # "are you" is an IU-specific alias — must NOT trigger for a different name
    assert not wake_word.detect("are you there")[0]
    assert wake_word.detect("nova tell me a joke")[0]


def test_empty_name_falls_back_to_iu():
    wake_word.set_wake_word("")
    assert wake_word.WAKE_WORD == "iu"


def test_display_and_spoken_forms(monkeypatch):
    monkeypatch.setattr(cfg.config, "wake_word", "iu")
    assert cfg.display_name() == "IU"
    assert cfg.spoken_name() == "I U"
    monkeypatch.setattr(cfg.config, "wake_word", "jarvis")
    assert cfg.display_name() == "Jarvis"
    assert cfg.spoken_name() == "Jarvis"
