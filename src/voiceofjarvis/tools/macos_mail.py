"""macOS Mail integration via AppleScript. Read-only inbox + draft compose (never auto-sends)."""

from . import consent, macos_bridge

_APP = "Mail"
_DENIED = "I need Mail access. Enable it in System Settings, Privacy and Security, Automation."


def read_inbox(count: int = 5) -> str | None:
    """Read subject + sender of the latest `count` inbox messages."""
    script = f'''
    set output to ""
    tell application "Mail"
        set msgs to messages 1 thru {count} of inbox
        repeat with m in msgs
            set output to output & "From " & (sender of m) & ": " & (subject of m) & linefeed
        end repeat
    end tell
    return output
    '''
    result = macos_bridge.run(_APP, script, timeout=25)
    if result == macos_bridge.NOT_PERMITTED:
        return consent.denied_message("mail")
    if result == "PERMISSION_DENIED":
        return _DENIED
    if not result:
        return "Your inbox looks empty."
    return f"[Latest emails]\n{result}"


def compose_draft(to: str, subject: str, body: str) -> str:
    """Create a draft email (does NOT send — opens for review). Privacy-safe."""
    safe_subject = subject.replace('"', "'")
    safe_body = body.replace('"', "'")
    script = f'''
    tell application "Mail"
        set newMsg to make new outgoing message with properties {{subject:"{safe_subject}", content:"{safe_body}", visible:true}}
        tell newMsg
            make new to recipient at end of to recipients with properties {{address:"{to}"}}
        end tell
        activate
    end tell
    return "drafted"
    '''
    result = macos_bridge.run(_APP, script)
    if result == macos_bridge.NOT_PERMITTED:
        return consent.denied_message("mail")
    if result == "PERMISSION_DENIED":
        return _DENIED
    if result == "drafted":
        return f"I've drafted an email to {to}. Review it and send when ready."
    return "I couldn't create the draft."
