"""macOS Calendar integration via AppleScript. No API key needed."""

from . import consent, macos_bridge

_APP = "Calendar"
_DENIED = "I need Calendar access. Enable it in System Settings, Privacy and Security, Automation."


def list_events(days: int = 1) -> str | None:
    """List events from today through `days` ahead."""
    script = f'''
    set output to ""
    set today to current date
    set endDate to today + ({days} * days)
    tell application "Calendar"
        repeat with cal in calendars
            set evts to (every event of cal whose start date ≥ today and start date ≤ endDate)
            repeat with e in evts
                set output to output & (summary of e) & " at " & (start date of e as string) & linefeed
            end repeat
        end repeat
    end tell
    return output
    '''
    result = macos_bridge.run(_APP, script, timeout=25)
    if result == macos_bridge.NOT_PERMITTED:
        return consent.denied_message("calendar")
    if result == "PERMISSION_DENIED":
        return _DENIED
    if not result:
        return "You have no events scheduled."
    return f"[Calendar events]\n{result}"


def create_event(title: str, hours_from_now: float = 1.0, duration_minutes: int = 60) -> str:
    """Create a calendar event starting `hours_from_now`."""
    safe_title = title.replace('"', "'")
    script = f'''
    tell application "Calendar"
        set startDate to (current date) + ({hours_from_now} * hours)
        set endDate to startDate + ({duration_minutes} * minutes)
        tell calendar 1
            make new event with properties {{summary:"{safe_title}", start date:startDate, end date:endDate}}
        end tell
    end tell
    return "created"
    '''
    result = macos_bridge.run(_APP, script)
    if result == macos_bridge.NOT_PERMITTED:
        return consent.denied_message("calendar")
    if result == "PERMISSION_DENIED":
        return _DENIED
    if result == "created":
        return f"Event '{title}' added to your calendar."
    return "I couldn't create the event."
