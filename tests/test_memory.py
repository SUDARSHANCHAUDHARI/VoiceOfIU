"""Memory store, redaction-on-save, topic graph, and summariser thresholds."""

from src.voiceofiu.memory import graph, search


def test_save_and_recent(temp_db):
    temp_db.save_turn("user", "I love hiking in the mountains")
    temp_db.save_turn("assistant", "Mountains are great for hiking")
    recent = temp_db.get_recent_turns(limit=10)
    assert len(recent) == 2
    assert recent[0]["content"] == "I love hiking in the mountains"


def test_save_redacts_secrets(temp_db):
    temp_db.save_turn("user", "my token is " + "gh" + "p_" + "x" * 36)
    recent = temp_db.get_recent_turns(limit=1)
    assert "[redacted]" in recent[0]["content"]


def test_topic_graph(temp_db):
    for _ in range(3):
        temp_db.save_turn("user", "tell me about hiking trails and mountains")
        temp_db.save_turn("user", "what about hiking gear for mountains")
    topics = graph.build_topics(max_topics=5)
    assert any("hiking" in t or "mountains" in t for t in topics)


def test_topic_graph_empty(temp_db):
    assert graph.build_topics() == {}


def test_fts_search_handles_punctuation(temp_db):
    temp_db.save_turn("user", "what's the weather, today?")
    # must not raise on FTS5 special chars
    results = temp_db.search_turns("weather, today?")
    assert isinstance(results, list)


def test_recall_returns_string(temp_db):
    temp_db.save_turn("user", "my favorite color is blue")
    out = search.recall("favorite color")
    assert isinstance(out, str)
