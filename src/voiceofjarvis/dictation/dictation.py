"""
Dictation mode — hold Cmd+Shift+D, speak, release → text pastes into active app.
Free offline alternative to WisprFlow.

Uses a native macOS Quartz CGEventTap (works on macOS 26 Tahoe, unlike pynput).
Requires Input Monitoring / Accessibility permission for the running process.
"""

import logging
import platform
import subprocess
import threading

log = logging.getLogger(__name__)

# Cmd+Shift+D.  Key code 2 == 'd' on US layout.
_HOTKEY_KEYCODE = 2
_recording = False


def is_supported() -> bool:
    """Native Quartz event tap works on all macOS versions when pyobjc is present."""
    if platform.system() != "Darwin":
        return False
    try:
        import Quartz  # noqa: F401
        return True
    except ImportError:
        return False


def has_permission() -> bool:
    """True if Input Monitoring is granted (needed for the global hotkey)."""
    try:
        import Quartz
        return bool(Quartz.CGPreflightListenEventAccess())
    except Exception:
        return False


def request_permission():
    """Trigger the macOS Input Monitoring prompt (first time only)."""
    try:
        import Quartz
        Quartz.CGRequestListenEventAccess()
    except Exception:
        pass


def open_settings():
    """Deep-link straight to System Settings → Privacy → Input Monitoring."""
    subprocess.run(
        ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"],
        check=False,
    )


def start(stt_fn, on_status=None):
    """
    Start the global hotkey listener on a daemon thread.
    stt_fn: callable(audio_bytes) -> str — the STT function to use
    on_status: optional callable(str) for UI updates
    """
    if not is_supported():
        log.warning("Dictation unavailable: pyobjc/Quartz not installed")
        return
    threading.Thread(target=_run_tap, args=(stt_fn, on_status), daemon=True).start()


def _run_tap(stt_fn, on_status):
    from Quartz import (
        CFMachPortCreateRunLoopSource,
        CFRunLoopAddSource,
        CFRunLoopGetCurrent,
        CFRunLoopRun,
        CGEventGetFlags,
        CGEventGetIntegerValueField,
        CGEventTapCreate,
        kCFRunLoopCommonModes,
        kCGEventFlagMaskCommand,
        kCGEventFlagMaskShift,
        kCGEventKeyDown,
        kCGEventKeyUp,
        kCGEventTapOptionListenOnly,
        kCGHeadInsertEventTap,
        kCGKeyboardEventKeycode,
        kCGSessionEventTap,
    )

    from ..listening.audio import AudioStream
    held = threading.Event()
    state = {"chunks": [], "audio": None}

    def _start_recording():
        if held.is_set():
            return
        held.set()
        if on_status:
            on_status("dictating")
        log.info("Dictation: recording")
        state["audio"] = AudioStream()
        state["chunks"] = []
        state["audio"].start()

        def _record():
            while held.is_set():
                chunk = state["audio"].read_chunk(timeout=0.05)
                if chunk:
                    state["chunks"].append(chunk)
            state["audio"].stop()
            audio_bytes = b"".join(state["chunks"])
            if audio_bytes:
                text = stt_fn(audio_bytes)
                if text:
                    log.info(f"Dictation: pasting {text!r}")
                    _paste(text)
            if on_status:
                on_status("listening")

        threading.Thread(target=_record, daemon=True).start()

    def _stop_recording():
        held.clear()

    def _callback(proxy, etype, event, refcon):
        try:
            keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            if keycode != _HOTKEY_KEYCODE:
                return event
            flags = CGEventGetFlags(event)
            has_mods = (flags & kCGEventFlagMaskCommand) and (flags & kCGEventFlagMaskShift)
            if etype == kCGEventKeyDown and has_mods:
                _start_recording()
            elif etype == kCGEventKeyUp:
                _stop_recording()
        except Exception as e:
            log.warning(f"Dictation tap error: {e}")
        return event

    mask = (1 << kCGEventKeyDown) | (1 << kCGEventKeyUp)
    tap = CGEventTapCreate(
        kCGSessionEventTap, kCGHeadInsertEventTap,
        kCGEventTapOptionListenOnly, mask, _callback, None,
    )
    if not tap:
        log.warning("Dictation: event tap not created — grant Input Monitoring "
                    "permission in System Settings, Privacy and Security.")
        return

    source = CFMachPortCreateRunLoopSource(None, tap, 0)
    CFRunLoopAddSource(CFRunLoopGetCurrent(), source, kCFRunLoopCommonModes)
    log.info("Dictation ready — hold Cmd+Shift+D to dictate")
    CFRunLoopRun()


def _paste(text: str):
    """Paste text into the currently focused app via clipboard + Cmd+V."""
    try:
        import pyperclip
        pyperclip.copy(text)
        subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to keystroke "v" using command down'],
            check=False,
        )
    except Exception as e:
        log.warning(f"Paste failed: {e}")
