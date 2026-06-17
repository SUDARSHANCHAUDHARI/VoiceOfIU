"""Ollama local LLM client — offline fallback."""

import json
import logging

import requests

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2"

log = logging.getLogger(__name__)

# Preference order per task type — first match that's installed wins
_MODEL_PREFS: dict[str, list[str]] = {
    "coding":      ["deepseek-coder-v2", "deepseek-coder", "codellama", "qwen2.5-coder", "llama3.2"],
    "reasoning":   ["llama3.1:70b", "llama3.1:8b", "llama3.2", "mistral"],
    "translation": ["llama3.2", "llama3.1:8b", "mistral", "qwen2.5"],
    "math":        ["qwen2.5", "llama3.1:8b", "llama3.2"],
    "general":     ["llama3.2", "llama3.1:8b", "mistral", "gemma2"],
}

_installed_cache: list[str] | None = None


def installed_models() -> list[str]:
    global _installed_cache
    if _installed_cache is not None:
        return _installed_cache
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        _installed_cache = [m["name"] for m in r.json().get("models", [])]
        return _installed_cache
    except Exception:
        return []


def best_model_for(task: str) -> str:
    """Pick best installed model for task type. Falls back to DEFAULT_MODEL."""
    available = installed_models()
    prefs = _MODEL_PREFS.get(task, _MODEL_PREFS["general"])
    for preferred in prefs:
        for installed in available:
            # match by prefix so "llama3.2:3b" matches "llama3.2"
            if installed.startswith(preferred) or preferred.startswith(installed.split(":")[0]):
                log.info(f"Ollama model selected for {task}: {installed}")
                return installed
    return DEFAULT_MODEL


def is_running() -> bool:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def respond(
    intent: str,
    context: list[dict] | None = None,
    system_prompt: str | None = None,
    model: str = DEFAULT_MODEL,
) -> str:
    messages = list(context or [])
    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + messages
    messages.append({"role": "user", "content": intent})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"num_ctx": 4096},
    }
    r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=30)  # type: ignore[arg-type]
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def classify_intent(text: str, model: str = "llama3.2:1b") -> dict:
    """
    Fast intent classification — returns {"coding": bool, "confidence": "high"|"medium"|"low"}.
    Uses smallest available model for speed.
    """
    prompt = (
        "Classify this voice command. Reply ONLY with valid JSON: "
        '{"coding": true/false, "confidence": "high"/"medium"/"low"}\n\n'
        f'Command: "{text}"'
    )
    try:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_ctx": 512, "temperature": 0},
        }
        r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=5)  # type: ignore[arg-type]
        r.raise_for_status()
        raw = r.json()["message"]["content"].strip()
        # Extract JSON from response (model may add surrounding text)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {"coding": False, "confidence": "low"}
