"""
Codex CLI client — calls `codex` as a subprocess.
No API key in our code. Uses your existing Codex subscription.
One-time auth: run `codex` once in terminal to log in.
Install: npm install -g @openai/codex
"""

import logging
import shutil
import subprocess

log = logging.getLogger(__name__)


def is_available() -> bool:
    return shutil.which("codex") is not None


def respond(intent: str) -> str:
    if not is_available():
        raise RuntimeError(
            "Codex CLI not found. "
            "Install with: npm install -g @openai/codex  then log in."
        )

    try:
        result = subprocess.run(
            # `exec` = non-interactive; skip-git-repo-check so it runs anywhere
            ["codex", "exec", "--skip-git-repo-check", intent],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("Codex CLI timed out after 120s") from e
    except FileNotFoundError as e:
        raise RuntimeError("codex command not found in PATH") from e

    if result.returncode != 0:
        err = result.stderr.strip()
        if "refresh token" in err or "Unauthorized" in err or "401" in err:
            raise RuntimeError("Codex login expired — run 'codex login' in a terminal.")
        raise RuntimeError(f"Codex CLI error: {err}")

    return result.stdout.strip()
