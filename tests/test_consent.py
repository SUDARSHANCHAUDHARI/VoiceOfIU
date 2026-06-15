"""Consent gate — apps/files must not be accessed without explicit permission."""

import pytest
from src.voiceofjarvis import config as cfg
from src.voiceofjarvis.tools import consent, local_files, macos_calendar, macos_notes


@pytest.fixture(autouse=True)
def reset_consent():
    saved = (cfg.config.allow_calendar, cfg.config.allow_mail,
             cfg.config.allow_notes, cfg.config.allow_files)
    cfg.config.allow_calendar = cfg.config.allow_mail = False
    cfg.config.allow_notes = cfg.config.allow_files = False
    yield
    (cfg.config.allow_calendar, cfg.config.allow_mail,
     cfg.config.allow_notes, cfg.config.allow_files) = saved


def test_default_denies_everything():
    assert not consent.is_allowed("calendar")
    assert not consent.is_allowed("mail")
    assert not consent.is_allowed("notes")
    assert not consent.is_allowed("files")


def test_enabling_grants_only_that_one():
    cfg.config.allow_notes = True
    assert consent.is_allowed("notes")
    assert not consent.is_allowed("calendar")


def test_calendar_blocked_without_consent():
    # Must NOT launch Calendar or return data — returns the denied message
    out = macos_calendar.list_events()
    assert "permission" in out.lower()


def test_notes_blocked_without_consent():
    out = macos_notes.list_notes()
    assert "permission" in out.lower()


def test_file_read_blocked_without_consent():
    out = local_files.detect_file_intent("read my notes.txt")
    assert out is not None and "permission" in out.lower()


def test_file_read_allowed_after_consent():
    # With consent granted the gate opens — we get past it (no "permission" denial).
    cfg.config.allow_files = True
    out = local_files.detect_file_intent("read ~/Desktop/nonexistent_xyz.txt")
    assert out is not None
    assert "permission" not in out.lower()  # gate passed; reaches file logic


def test_unknown_integration_is_denied():
    assert not consent.is_allowed("contacts")
