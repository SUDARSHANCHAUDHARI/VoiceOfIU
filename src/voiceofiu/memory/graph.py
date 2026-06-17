"""
Knowledge graph (v1, simplified) — groups conversation history by topic.

Extracts salient keywords across all turns, picks the most frequent as topics,
and clusters turns under the topics they mention. No external deps; uses simple
stopword-filtered term frequency. This is the lightweight version the plan
called for — a full embedding/graph DB is deferred.
"""

import re
from collections import Counter

from . import store

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "be", "been",
    "to", "of", "in", "on", "at", "for", "with", "by", "from", "up", "about", "into",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "them", "my",
    "your", "his", "its", "our", "their", "this", "that", "these", "those", "what",
    "which", "who", "whom", "when", "where", "why", "how", "can", "could", "would",
    "should", "will", "shall", "may", "might", "must", "do", "does", "did", "have",
    "has", "had", "not", "no", "yes", "so", "if", "then", "than", "as", "just",
    "okay", "ok", "iu", "ai", "please", "tell", "give", "want", "need", "get", "got",
    "now", "today", "like", "know", "think", "going", "make", "really", "thing",
    "user", "asked", "naturally", "redacted",
}

_WORD = re.compile(r"[a-zA-Z][a-zA-Z'-]{2,}")


def build_topics(max_topics: int = 8, per_topic: int = 5) -> dict[str, list[dict]]:
    """
    Return {topic_word: [ {timestamp, role, content}, ... ]} grouping recent
    turns by the salient topics they mention. Empty dict if no history.
    """
    turns = store.get_recent_turns(limit=300)
    if not turns:
        return {}

    # Count keyword frequency across all turns
    freq: Counter = Counter()
    for t in turns:
        for w in _keywords(t["content"]):
            freq[w] += 1

    topics = [w for w, c in freq.most_common(max_topics) if c >= 2]
    if not topics:
        return {}

    graph: dict[str, list[dict]] = {t: [] for t in topics}
    for turn in turns:
        words = set(_keywords(turn["content"]))
        for topic in topics:
            if topic in words and len(graph[topic]) < per_topic:
                graph[topic].append(turn)

    # Drop topics that ended up empty
    return {k: v for k, v in graph.items() if v}


def _keywords(text: str) -> list[str]:
    return [
        w.lower() for w in _WORD.findall(text or "")
        if w.lower() not in _STOPWORDS
    ]
