"""Task planner — multi-step request splitting."""

import pytest
from src.voiceofjarvis.router.planner import is_multi_step, plan


def test_single_step_passthrough():
    assert plan("what is the weather today") == ["what is the weather today"]


def test_empty():
    assert plan("") == []
    assert plan("   ") == []


@pytest.mark.parametrize("text,n", [
    ("what's the weather and then remind me to call mom", 2),
    ("check my email then add milk to notes then what's the time", 3),
    ("tell me a joke, and also what's the date", 2),
])
def test_multi_step_split(text, n):
    steps = plan(text)
    assert len(steps) == n
    assert all(len(s.split()) >= 2 for s in steps)


def test_is_multi_step():
    assert is_multi_step("play music and then set a timer")
    assert not is_multi_step("what time is it")


def test_caps_at_max_steps():
    text = "do a then do b then do c then do d then do e then do f"
    assert len(plan(text)) <= 4
