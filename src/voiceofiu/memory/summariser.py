"""
Conversation summariser — condenses old turns to prevent DB bloat.

Runs in the background (never blocks the voice loop). Turns older than a
threshold are summarised via the Claude CLI into a single digest row, and the
raw turns are removed. Keeps memory searchable without unbounded growth.
"""

import logging
import threading
from datetime import datetime, timedelta

from . import store

log = logging.getLogger(__name__)

_DAYS_BEFORE_SUMMARISE = 7
_MIN_TURNS_TO_SUMMARISE = 20


def maybe_summarise_async():
    """Kick off summarisation in a daemon thread if there's enough old history."""
    t = threading.Thread(target=_run, daemon=True)
    t.start()


def _run():
    try:
        old = store.get_turns_older_than(days=_DAYS_BEFORE_SUMMARISE)
        if len(old) < _MIN_TURNS_TO_SUMMARISE:
            return

        log.info(f"Summarising {len(old)} old turns")
        transcript = "\n".join(
            f"{t['role']}: {t['content']}" for t in old
        )
        summary = _summarise(transcript)
        if not summary:
            return

        cutoff = (datetime.now() - timedelta(days=_DAYS_BEFORE_SUMMARISE)).isoformat()
        store.save_turn("summary", summary)
        store.delete_turns_before(cutoff, keep_summaries=True)
        log.info("Old turns summarised and compacted")
    except Exception as e:
        log.warning(f"Summarisation failed: {e}")


def _summarise(transcript: str) -> str | None:
    """Use Claude CLI to compress a transcript into a durable digest."""
    from ..router import claude_client
    if not claude_client.is_available():
        return None
    prompt = (
        "Summarise the key facts, preferences, and decisions from this "
        "conversation history into a compact digest of bullet points. "
        "Keep only what would be useful to remember long-term "
        "(names, preferences, recurring topics, important facts). "
        "Be concise.\n\n" + transcript[:8000]
    )
    try:
        return claude_client.respond(prompt)
    except Exception:
        return None
