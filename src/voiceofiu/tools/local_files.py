"""Local file access — read files and list directories by voice."""

import logging
import os
import re

from . import consent

log = logging.getLogger(__name__)

_ALLOWED_ROOTS = [
    os.path.expanduser("~/Documents"),
    os.path.expanduser("~/Desktop"),
    os.path.expanduser("~/Downloads"),
]

_READ_KW  = {"read", "open", "show", "contents of", "what's in", "what is in"}
_LIST_KW  = {"list", "files in", "what files", "show files", "folder"}

_TEXT_EXTS = {".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
              ".csv", ".log", ".sh", ".swift", ".kt", ".html", ".css"}


def detect_file_intent(intent: str) -> str | None:
    """
    Returns augmented prompt if a file/folder operation is detected.
    Returns None if no file intent found.
    """
    lower = intent.lower()

    # Consent gate — no file access until the user enables it in Settings
    if (any(kw in lower for kw in _READ_KW) or any(kw in lower for kw in _LIST_KW)) \
            and not consent.is_allowed("files"):
        return consent.denied_message("files")

    if any(kw in lower for kw in _READ_KW):
        path = _extract_path(intent)
        if path:
            return _read_file(path, intent)

    if any(kw in lower for kw in _LIST_KW):
        path = _extract_path(intent) or os.path.expanduser("~/Desktop")
        return _list_dir(path, intent)

    return None


def _read_file(path: str, original: str) -> str:
    path = os.path.expanduser(path)
    if not _is_allowed(path):
        return f"Access denied: {path} is outside allowed folders (Documents, Desktop, Downloads)"
    if not os.path.exists(path):
        return f"File not found: {path}"
    ext = os.path.splitext(path)[1].lower()
    if ext not in _TEXT_EXTS:
        return f"Cannot read {ext} files — only text files are supported"
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            content = f.read(4000)
        return f"[File: {path}]\n{content}\n\nUser asked: {original}"
    except Exception as e:
        return f"Could not read file: {e}"


def _list_dir(path: str, original: str) -> str:
    path = os.path.expanduser(path)
    if not _is_allowed(path):
        return f"Access denied: {path} is outside allowed folders"
    if not os.path.isdir(path):
        return f"Not a directory: {path}"
    try:
        entries = os.listdir(path)[:30]
        listing = "\n".join(entries)
        return f"[Files in {path}]\n{listing}\n\nUser asked: {original}"
    except Exception as e:
        return f"Could not list directory: {e}"


def _is_allowed(path: str) -> bool:
    path = os.path.realpath(path)
    return any(path.startswith(os.path.realpath(root)) for root in _ALLOWED_ROOTS)


def _extract_path(text: str) -> str | None:
    # Match ~/... or /Users/... paths
    m = re.search(r"(~/[\w/\.\-]+|/Users/[\w/\.\-]+)", text)
    if m:
        return m.group(1)
    # Match "file.txt" or "notes.md" patterns
    m = re.search(r"([\w\-]+\.(txt|md|py|js|json|csv|log|sh|swift|kt))", text, re.IGNORECASE)
    if m:
        return os.path.expanduser(f"~/Desktop/{m.group(1)}")
    return None
