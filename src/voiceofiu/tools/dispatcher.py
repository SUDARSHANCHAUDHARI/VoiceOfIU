"""
Tool dispatcher — detects what data an intent needs, fetches it, and
returns an augmented prompt. Falls through cleanly if no tool matches.
"""

import logging
import re

from . import (
    local_files,
    macos_calendar,
    macos_mail,
    macos_notes,
    nutrition,
    redact,
    screen,
    weather,
    web,
)

log = logging.getLogger(__name__)

_WEATHER_KW   = {"weather", "temperature", "forecast", "rain", "sunny", "hot", "cold", "humid"}
_SEARCH_KW    = {"search", "find", "look up", "news", "latest", "who is", "what is", "when did"}
_SCREEN_KW    = {"screen", "read my screen", "what's on", "what do you see", "read this"}
_NUTRITION_KW = {"ate", "eating", "calories", "meal", "food", "nutrition", "diet", "weight"}
_FILE_KW      = {"read file", "open file", "show file", "list files", "files in", "contents of",
                  "what's in", "my documents", "my desktop", "my downloads"}
_FETCH_KW     = {"fetch", "read the page", "open the url", "go to", "read url", "summarize url",
                  "what does this page say", "read this link"}
_CALENDAR_KW  = {"calendar", "schedule", "my events", "appointment", "meeting", "what's on today",
                  "add event", "create event", "remind me to", "what do i have"}
_MAIL_KW      = {"email", "emails", "inbox", "mail", "check my mail", "read my email",
                  "compose", "send an email", "draft an email"}
_NOTES_KW     = {"note", "notes", "make a note", "create a note", "write a note", "my notes"}

_STOP_WORDS   = {"stop", "stop it", "stop talking", "shut up", "be quiet", "cancel", "never mind"}


def is_stop_command(text: str) -> bool:
    return text.lower().strip().rstrip(".,!?") in _STOP_WORDS


def augment(intent: str) -> str:
    """
    Check intent for tool triggers, fetch data, prepend to prompt.
    Returns the original intent unchanged if no tool fires.
    """
    lower = intent.lower()

    # Nutrition: log first, query second
    meal_logged = nutrition.detect_meal_log(intent)
    if meal_logged:
        return f"User just logged a meal. Tell them it was saved: {meal_logged}"

    if _matches(lower, _NUTRITION_KW):
        data = nutrition.get_summary()
        if data:
            return f"[Nutrition data]\n{data}\n\nUser asked: {intent}"

    if _matches(lower, _WEATHER_KW):
        city = _extract_city(intent)
        data = weather.get_weather(city)
        if data:
            return f"[Current weather: {data}]\n\nUser asked: {intent}"

    if _matches(lower, _SCREEN_KW):
        data = screen.read_screen()
        if data:
            return f"[Screen content]\n{redact.redact(data)}\n\nUser asked: {intent}"
        return "I tried to read the screen but couldn't capture it. Do you have screen recording permission enabled?"

    if _matches(lower, _FILE_KW):
        result = local_files.detect_file_intent(intent)
        if result:
            return redact.redact(result)

    if _matches(lower, _FETCH_KW):
        url = _extract_url(intent)
        if url:
            data = web.fetch_page(url)
            if data:
                return f"[Page content from {url}]\n{redact.redact(data)}\n\nUser asked: {intent}"

    if _matches(lower, _CALENDAR_KW):
        if any(k in lower for k in ("add", "create", "schedule", "remind me to", "new event")):
            title = re.sub(r"\b(add|create|schedule|an?|new|event|to my|in my|calendar|remind me to)\b",
                           "", intent, flags=re.IGNORECASE).strip()
            result = macos_calendar.create_event(title or "Reminder")
        else:
            result = macos_calendar.list_events()
        return f"Tell the user naturally: {result}"

    if _matches(lower, _MAIL_KW):
        if any(k in lower for k in ("compose", "send", "draft", "write an email")):
            return ("The user wants to send an email but I should not send mail automatically. "
                    "Ask them for the recipient, subject, and message, then tell them to use "
                    f"the Mail app to send it. User said: {intent}")
        result = macos_mail.read_inbox()
        return f"{redact.redact(result or '')}\n\nUser asked: {intent}"

    if _matches(lower, _NOTES_KW):
        if any(k in lower for k in ("make", "create", "write", "add", "new")):
            m = re.search(r"note\b[:,]?\s*(.+)", intent, flags=re.IGNORECASE)
            content = m.group(1).strip() if m else ""
            if content:
                result = macos_notes.create_note(content[:50], content)
            else:
                result = macos_notes.list_notes()
        else:
            result = macos_notes.list_notes()
        return f"Tell the user naturally: {redact.redact(result or '')}"

    if _matches(lower, _SEARCH_KW):
        data = web.search(intent)
        if data:
            return f"[Web search results: {data}]\n\nUser asked: {intent}"

    return intent


def _matches(text: str, keywords: set) -> bool:
    return any(kw in text for kw in keywords)


def _extract_url(text: str) -> str | None:
    m = re.search(r"https?://[^\s]+", text)
    return m.group(0) if m else None


def _extract_city(text: str) -> str | None:
    m = re.search(r"in ([A-Z][a-zA-Z\s]+?)(?:\?|$|,|\s+today|\s+now|\s+like)", text)
    return m.group(1).strip() if m else None
