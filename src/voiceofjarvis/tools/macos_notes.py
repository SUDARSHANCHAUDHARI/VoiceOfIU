"""macOS Notes integration via AppleScript. Read + create notes."""

from . import consent, macos_bridge

_APP = "Notes"
_DENIED = "I need Notes access. Enable it in System Settings, Privacy and Security, Automation."


def list_notes(count: int = 5) -> str | None:
    """List titles of the most recent `count` notes."""
    script = f'''
    set output to ""
    tell application "Notes"
        set theNotes to notes
        set n to count of theNotes
        if n > {count} then set n to {count}
        repeat with i from 1 to n
            set output to output & (name of item i of theNotes) & linefeed
        end repeat
    end tell
    return output
    '''
    result = macos_bridge.run(_APP, script, timeout=25)
    if result == macos_bridge.NOT_PERMITTED:
        return consent.denied_message("notes")
    if result == "PERMISSION_DENIED":
        return _DENIED
    if not result:
        return "You don't have any notes yet."
    return f"[Your notes]\n{result}"


def create_note(title: str, body: str = "") -> str:
    """Create a new note with title and optional body."""
    safe_title = title.replace('"', "'")
    safe_body = body.replace('"', "'")
    content = f"{safe_title}<br>{safe_body}" if safe_body else safe_title
    script = f'''
    tell application "Notes"
        make new note at folder "Notes" with properties {{body:"{content}"}}
    end tell
    return "created"
    '''
    result = macos_bridge.run(_APP, script)
    if result == macos_bridge.NOT_PERMITTED:
        return consent.denied_message("notes")
    if result == "PERMISSION_DENIED":
        return _DENIED
    if result == "created":
        return f"I've created a note titled '{title}'."
    return "I couldn't create the note."
