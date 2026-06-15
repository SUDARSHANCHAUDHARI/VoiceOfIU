"""Shared pytest fixtures."""

import os
import sys
import tempfile

import pytest

# Make `src` importable as a package root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture
def temp_db(monkeypatch):
    """Point the store at a throwaway SQLite file and initialise it."""
    from src.voiceofjarvis.memory import store
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr(store, "DB_PATH", path)
    store.init()
    yield store
    os.unlink(path)
