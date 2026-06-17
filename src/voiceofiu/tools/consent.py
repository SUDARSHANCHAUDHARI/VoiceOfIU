"""
Access consent gate.

VoiceOfIU must NOT open apps or read private data without explicit permission.
Each integration (Calendar, Mail, Notes, local files) is OFF by default and
only runs once the user enables it in Settings. This is the in-app guard that
stops silent access to personal data.
"""

from ..config import config

# Integration key → config flag + spoken label
_INTEGRATIONS = {
    "calendar": ("allow_calendar", "Calendar"),
    "mail":     ("allow_mail", "Mail"),
    "notes":    ("allow_notes", "Notes"),
    "files":    ("allow_files", "your files"),
}


def is_allowed(integration: str) -> bool:
    flag, _ = _INTEGRATIONS.get(integration, (None, None))
    return bool(flag and getattr(config, flag, False))


def denied_message(integration: str) -> str:
    _, label = _INTEGRATIONS.get(integration, (None, integration))
    return (f"I don't have permission to access {label}. "
            f"You can enable it in Settings under Permissions.")
