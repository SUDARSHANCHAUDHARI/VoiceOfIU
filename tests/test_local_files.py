"""Local file access — path extraction and the sandbox guard (security)."""

import os

from src.voiceofjarvis.tools import local_files


def test_blocks_outside_allowed_roots():
    assert not local_files._is_allowed("/etc/passwd")
    assert not local_files._is_allowed("/System/Library/whatever")


def test_allows_documents():
    p = os.path.expanduser("~/Documents/notes.txt")
    assert local_files._is_allowed(p)


def test_path_extraction():
    assert local_files._extract_path("read ~/Desktop/todo.txt please").endswith("todo.txt")
    assert local_files._extract_path("open notes.md").endswith("notes.md")
    assert local_files._extract_path("just talking") is None


def test_read_denies_traversal():
    msg = local_files._read_file("/etc/passwd", "read passwd")
    assert "denied" in msg.lower()
