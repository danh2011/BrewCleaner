"""
Native macOS notifications — new in v4.0.

Previously the only way to know a task had finished was to have the
BrewCleaner window open and visible. This lets a long-running task
(installs, upgrades, cleanup) notify you even if you've switched
away to another app.

Uses `osascript -e 'display notification ...'` — no extra
dependencies, works on every supported macOS version. Respects the
existing `notifications` preference (see prefs.py); callers should
check that themselves before calling send(), but send() also takes
an `enabled` flag as a belt-and-braces guard so a caller can't
forget.
"""

from __future__ import annotations

import subprocess


def _escape(s: str) -> str:
    # AppleScript string literal: escape backslashes and double quotes.
    return s.replace("\\", "\\\\").replace('"', '\\"')


def build_command(title: str, message: str, subtitle: str = "") -> list:
    """
    Returns the argv list for the osascript call. Split out from
    send() so it's testable without actually running a subprocess or
    needing to be on macOS.
    """
    script = f'display notification "{_escape(message)}" with title "{_escape(title)}"'
    if subtitle:
        script += f' subtitle "{_escape(subtitle)}"'
    return ["osascript", "-e", script]


def send(title: str, message: str, subtitle: str = "", enabled: bool = True) -> bool:
    """
    Best-effort: returns True if the notification command was run
    without raising, False otherwise (e.g. not on macOS, osascript
    missing, or `enabled` is False). Never raises — a failed
    notification should never be allowed to interrupt a real task.
    """
    if not enabled:
        return False
    try:
        subprocess.run(build_command(title, message, subtitle),
                        capture_output=True, timeout=5)
        return True
    except Exception:
        return False
