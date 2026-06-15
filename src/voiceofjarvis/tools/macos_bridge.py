"""
Shared AppleScript bridge for macOS app integrations.

Ensures the target app is running in the background (via `open -g -a`, which
does NOT steal focus) before executing the script, then runs osascript.
Returns "PERMISSION_DENIED" sentinel on Automation permission errors.
"""

import logging
import subprocess
import time

from . import consent

log = logging.getLogger(__name__)

_launched: set[str] = set()

# osascript app name → consent integration key
_APP_CONSENT = {"Calendar": "calendar", "Mail": "mail", "Notes": "notes"}

# Sentinel returned when the user hasn't granted this integration
NOT_PERMITTED = "NOT_PERMITTED"


def _ensure_running(app: str):
    """Launch app in background without bringing it to foreground."""
    if app in _launched:
        return
    try:
        subprocess.run(["open", "-g", "-a", app], capture_output=True, timeout=5)
        time.sleep(1.0)  # give scripting interface time to come up
        _launched.add(app)
    except Exception as e:
        log.warning(f"Could not launch {app}: {e}")


def run(app: str, script: str, timeout: int = 20) -> str | None:
    """Run an AppleScript against `app`, launching it first if needed.

    Consent gate: if the integration isn't enabled in Settings, the app is NEVER
    launched and NOT_PERMITTED is returned — nothing is opened without permission.
    """
    integration = _APP_CONSENT.get(app)
    if integration and not consent.is_allowed(integration):
        log.info(f"Blocked {app} access — '{integration}' not permitted")
        return NOT_PERMITTED

    _ensure_running(app)
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            err = result.stderr.strip()
            if "Not authorized" in err or "-1743" in err or "1743" in err:
                return "PERMISSION_DENIED"
            log.warning(f"AppleScript error ({app}): {err}")
            return None
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
