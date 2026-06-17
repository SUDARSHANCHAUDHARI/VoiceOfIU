"""
Sensitive-data redaction.

Strips credentials, API keys, tokens, and password lines from text before it
is spoken aloud (TTS) or sent to the LLM. Applied at the source where untrusted
content (notes, files, mail, screen OCR) enters the pipeline.

Conservative by design: masks high-confidence secret patterns only, so normal
speech is never mangled.
"""

import re

_MASK = "[redacted]"

# High-confidence secret patterns
_PATTERNS = [
    # Private key blocks
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
    # JWT (three base64url segments)
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    # GitHub tokens
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bIv1\.[A-Fa-f0-9]{12,}\b"),
    # OpenAI / Stripe style keys
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\b[ps]k_(live|test)_[A-Za-z0-9]{16,}\b"),
    # AWS access key id
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    # Slack tokens
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    # Bearer tokens
    re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{16,}\b", re.IGNORECASE),
    # password / pwd / passwd / secret / api_key / token = value
    re.compile(r"(?i)\b(password|passwd|pwd|secret|api[_-]?key|access[_-]?token|token)\b\s*[:=>]*\s*([^\s]*\d[^\s]*)"),
    # Long opaque hex/base64 blobs (≥ 28 chars) — likely a token/hash
    re.compile(r"\b[A-Za-z0-9+/_\-]{28,}={0,2}\b"),
]


def redact(text: str) -> str:
    """Return text with secret-like substrings replaced by [redacted]."""
    if not text:
        return text
    out = text
    for pat in _PATTERNS:
        if pat.groups:
            # keep the label, mask the value
            out = pat.sub(lambda m: f"{m.group(1)}: {_MASK}", out)
        else:
            out = pat.sub(_MASK, out)
    return out


def contains_secret(text: str) -> bool:
    """True if any secret pattern matches (used for logging/warnings)."""
    return any(pat.search(text) for pat in _PATTERNS)
