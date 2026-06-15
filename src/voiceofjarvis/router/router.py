"""
LLM Router

Priority:
  1. Offline mode → Ollama only
  2. Codex CLI + coding task → Codex
  3. Claude Code CLI → default brain
  4. Ollama fallback
  5. Nothing available → helpful error
"""

import logging
from collections.abc import Iterator

from ..config import config
from ..memory import search as mem_search
from . import claude_client, codex_client, ollama_client

log = logging.getLogger(__name__)


def respond(intent: str) -> str:
    if not intent or not intent.strip():
        return "I didn't catch that. Could you say that again?"

    # Recall relevant memory to enrich context
    context = mem_search.format_recent(limit=config.context_window)
    memory_snippet = mem_search.recall(intent)

    return _route(intent, context, memory_snippet)


def respond_stream(intent: str) -> Iterator[str]:
    """
    Stream a response when possible (Claude CLI, default brain). Falls back to
    a single-chunk yield of respond() for Codex/Ollama paths.
    """
    if not intent or not intent.strip():
        yield "I didn't catch that. Could you say that again?"
        return

    context = mem_search.format_recent(limit=config.context_window)
    memory_snippet = mem_search.recall(intent)

    # Streaming only applies to the default Claude brain (not offline/coding)
    can_stream = (
        not config.offline_mode
        and not (codex_client.is_available() and _is_coding_task(intent))
        and claude_client.is_available()
    )

    if can_stream:
        try:
            log.info("Streaming from Claude Code CLI")
            enriched = intent
            if memory_snippet:
                enriched = f"{memory_snippet}\n\nCurrent request: {intent}"
            yield from claude_client.respond_stream(enriched, context=context)
            return
        except Exception as e:
            log.warning(f"Claude streaming failed: {e} — falling back")

    # Non-streaming fallback (Codex / Ollama / errors)
    yield _route(intent, context, memory_snippet)


def _route(intent: str, context: list[dict], memory_snippet: str) -> str:
    if config.offline_mode:
        return _try_ollama(intent) or "Ollama is not running. Start it with: ollama serve"

    if codex_client.is_available() and _is_coding_task(intent):
        try:
            log.info("Routing to Codex CLI")
            return codex_client.respond(intent)
        except Exception as e:
            log.warning(f"Codex failed: {e} — falling back to Claude")

    if claude_client.is_available():
        try:
            log.info("Routing to Claude Code CLI")
            # Enrich context with memory if available
            enriched = intent
            if memory_snippet:
                enriched = f"{memory_snippet}\n\nCurrent request: {intent}"
            return claude_client.respond(enriched, context=context)
        except Exception as e:
            log.warning(f"Claude CLI failed: {e} — falling back to Ollama")

    result = _try_ollama(intent)
    if result:
        return result

    return (
        "I'm not connected to any AI. "
        "Make sure Claude Code is installed and logged in, or start Ollama."
    )


def _try_ollama(intent: str) -> str | None:
    if not ollama_client.is_running():
        return None
    try:
        task = _detect_task_type(intent)
        model = ollama_client.best_model_for(task)
        log.info(f"Routing to Ollama [{task}] → {model}")
        return ollama_client.respond(intent, model=model)
    except Exception as e:
        log.warning(f"Ollama failed: {e}")
        return None


def _is_coding_task(intent: str) -> bool:
    return _detect_task_type(intent) == "coding"


def _detect_task_type(intent: str) -> str:
    lower = intent.lower()
    if any(k in lower for k in {"write", "code", "function", "script", "implement", "debug",
                                  "fix", "refactor", "class", "method", "algorithm", "program",
                                  "python", "javascript", "kotlin", "swift", "sql", "bash"}):
        return "coding"
    if any(k in lower for k in {"translate", "translation", "in french", "in hindi",
                                  "in marathi", "in spanish", "in japanese", "in thai",
                                  "in chinese", "in arabic", "language"}):
        return "translation"
    if any(k in lower for k in {"calculate", "math", "equation", "solve", "integral",
                                  "derivative", "percentage", "formula"}):
        return "math"
    if any(k in lower for k in {"explain", "reason", "analyse", "analyze", "compare",
                                  "pros and cons", "difference between", "why does"}):
        return "reasoning"
    return "general"
