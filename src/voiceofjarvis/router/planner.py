"""
Task planner — splits a multi-step voice request into ordered sub-tasks.

Most requests are single-step and pass straight through. When the user chains
several asks ("what's the weather AND remind me to call mom THEN add milk to
notes"), this splits them on connectors so each part can be dispatched and
answered in turn, instead of the LLM half-handling a run-on request.
"""

import re

# Connectors that usually separate distinct asks in speech
_SPLIT = re.compile(
    r"\b(?:and then|then|after that|also|and also|, and |;)\b",
    re.IGNORECASE,
)

_MAX_STEPS = 4
_MIN_STEP_WORDS = 2


def plan(intent: str) -> list[str]:
    """
    Return ordered sub-tasks. A single-step request returns a 1-item list, so
    callers can always iterate the result uniformly.
    """
    if not intent or not intent.strip():
        return []

    parts = [p.strip(" ,.;") for p in _SPLIT.split(intent)]
    steps = [p for p in parts if len(p.split()) >= _MIN_STEP_WORDS]

    # Fall back to the whole intent if splitting produced nothing useful
    if len(steps) <= 1:
        return [intent.strip()]
    return steps[:_MAX_STEPS]


def is_multi_step(intent: str) -> bool:
    return len(plan(intent)) > 1
