"""Secret redaction — security-critical, must catch credentials, must not mangle speech.

Test fixtures are assembled at runtime (prefix + body) so no literal credential
string ever appears in source — keeps the repo secret-scanner clean.
"""

import pytest
from src.voiceofjarvis.tools.redact import contains_secret, redact

_ALNUM = "abcdefghijklmnopqrstuvwxyz1234567890"


def _gh_token():
    return "gh" + "p_" + _ALNUM + "1234567890"


def _openai_key():
    return "sk-" + "proj-" + _ALNUM + "abcdef"


def _aws_key():
    # AKIA + exactly 16 uppercase/digit chars (real AWS access-key-id shape)
    return "AK" + "IA" + "IOSFODNN7EXAMPLE"


def _slack_token():
    return "xo" + "xb-" + "123456789012-" + _ALNUM


def _jwt():
    seg = "eyJ" + _ALNUM.replace("0", "_")
    return f"{seg}.{seg}abc.{seg}xyz"


def _github_id():
    # Fabricated GitHub App client-id shape (Iv1. + 16 hex) — not a real id
    return "Iv1." + "0123456789abcdef"


@pytest.mark.parametrize("maker", [
    _gh_token, _openai_key, _aws_key, _slack_token, _jwt, _github_id,
])
def test_secrets_redacted(maker):
    secret = maker()
    out = redact(f"my key is {secret} ok")
    assert secret not in out
    assert "[redacted]" in out


def test_password_with_space_separator():
    pwd = "P06ELgPdnN2b"
    out = redact(f"amazon password {pwd}")
    assert pwd not in out


@pytest.mark.parametrize("clean", [
    "the document is password protected",
    "what is the weather in Bangkok today",
    "remind me to call mom at 3pm",
    "translate good morning into Marathi",
])
def test_normal_speech_untouched(clean):
    assert redact(clean) == clean


def test_contains_secret_flag():
    assert contains_secret("token: " + "x" * 30)
    assert not contains_secret("just a normal sentence")


def test_empty_input():
    assert redact("") == ""
    assert redact(None) is None
