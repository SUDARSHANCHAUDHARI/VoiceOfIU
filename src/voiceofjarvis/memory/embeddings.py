"""
Semantic memory search via Ollama embeddings + numpy cosine similarity.

Reuses the local Ollama install (no extra Python deps, no model downloads
beyond pulling an embed model). Falls back gracefully to FTS5 keyword search
when Ollama or the embed model isn't available.

Why not FAISS: for a personal assistant's history (hundreds–low thousands of
turns) brute-force cosine over numpy is just as fast and avoids index
build/persist/sync complexity. Revisit if history grows to 100k+ turns.
"""

import logging

import numpy as np
import requests

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"

log = logging.getLogger(__name__)

_available: bool | None = None


def is_available() -> bool:
    """True if Ollama is running and the embed model is pulled."""
    global _available
    if _available is not None:
        return _available
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        models = [m["name"] for m in r.json().get("models", [])]
        _available = any(m.startswith(EMBED_MODEL) for m in models)
    except Exception:
        _available = False
    return _available


def embed(text: str) -> np.ndarray | None:
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=10,
        )
        r.raise_for_status()
        vec = np.array(r.json()["embedding"], dtype=np.float32)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec
    except Exception as e:
        log.warning(f"Embedding failed: {e}")
        return None


def rank(query: str, candidates: list[dict], top_k: int = 4) -> list[dict]:
    """
    Rank candidate turns by semantic similarity to query.
    Each candidate is a dict with at least a 'content' key.
    Returns top_k most similar. Empty list if embeddings unavailable.
    """
    if not is_available() or not candidates:
        return []

    q = embed(query)
    if q is None:
        return []

    scored = []
    for c in candidates:
        v = embed(c["content"])
        if v is None:
            continue
        sim = float(np.dot(q, v))  # both normalized → cosine similarity
        scored.append((sim, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for sim, c in scored[:top_k] if sim > 0.3]
