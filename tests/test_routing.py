"""Router task-type detection, stop command, URL extraction, Ollama model selection."""

import pytest
from src.voiceofjarvis.router import ollama_client
from src.voiceofjarvis.router.router import _detect_task_type, _is_coding_task
from src.voiceofjarvis.tools.dispatcher import _extract_url, is_stop_command


@pytest.mark.parametrize("intent,expected", [
    ("write a python function to sort a list", "coding"),
    ("debug this error in my code", "coding"),
    ("translate hello into french", "translation"),
    ("calculate 15 percent of 3500", "math"),
    ("explain how photosynthesis works", "reasoning"),
    ("what is the weather today", "general"),
])
def test_task_type_detection(intent, expected):
    assert _detect_task_type(intent) == expected


def test_is_coding_task():
    assert _is_coding_task("refactor this kotlin class")
    assert not _is_coding_task("what time is it")


@pytest.mark.parametrize("text", [
    "stop", "stop it", "shut up", "cancel", "never mind", "STOP.",
])
def test_stop_commands(text):
    assert is_stop_command(text)


@pytest.mark.parametrize("text", [
    "what is the weather", "tell me about stops on the train",
])
def test_non_stop(text):
    assert not is_stop_command(text)


def test_url_extraction():
    assert _extract_url("fetch https://example.com/page now") == "https://example.com/page"
    assert _extract_url("no url here") is None


def test_ollama_model_selection(monkeypatch):
    # Pretend these models are installed
    monkeypatch.setattr(ollama_client, "_installed_cache",
                        ["llama3.2:latest", "deepseek-coder:6.7b"])
    assert ollama_client.best_model_for("coding").startswith("deepseek-coder")
    assert ollama_client.best_model_for("general").startswith("llama3.2")


def test_ollama_fallback_when_empty(monkeypatch):
    monkeypatch.setattr(ollama_client, "_installed_cache", [])
    assert ollama_client.best_model_for("coding") == ollama_client.DEFAULT_MODEL
