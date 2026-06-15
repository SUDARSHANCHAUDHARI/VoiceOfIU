"""
Memory recall — finds relevant past turns for a given query.
Uses SQLite FTS5 as primary search (always available).
Falls back to recent turns if no FTS match.
"""

from . import embeddings, store


def recall(query: str, limit: int = 4) -> str:
    """
    Return a formatted string of relevant past turns to inject into the LLM prompt.
    Tries semantic search (Ollama embeddings) first, falls back to FTS5 keyword.
    Returns empty string if nothing relevant found.
    """
    hits = _semantic_hits(query, limit) or store.search_turns(query, limit=limit)
    if not hits:
        return ""

    lines = ["[Relevant past conversation:]"]
    for h in hits:
        ts = h["timestamp"][:16].replace("T", " ")
        lines.append(f"  [{ts}] {h['role'].capitalize()}: {h['content']}")
    return "\n".join(lines)


def _semantic_hits(query: str, limit: int) -> list[dict]:
    """Semantic ranking over a window of recent turns. Empty if unavailable."""
    if not embeddings.is_available():
        return []
    candidates = store.get_recent_turns(limit=60)
    return embeddings.rank(query, candidates, top_k=limit)


def format_recent(limit: int = 6) -> list[dict]:
    """Return recent turns as role/content dicts for LLM context injection."""
    turns = store.get_recent_turns(limit=limit)
    return [{"role": t["role"], "content": t["content"]} for t in turns]
