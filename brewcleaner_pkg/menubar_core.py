"""
Menu bar mode — pure logic, testable without rumps or a display.

Menu bar mode (`brewcleaner --menubar`) runs as its own lightweight
process using rumps (an NSStatusBar wrapper), completely separate
from the main Tk app rather than alongside it in the same process —
Tk and rumps both want to own the run loop, so running both at once
in one process is the kind of thing that works in a demo and then
hangs intermittently for someone. Launching the full GUI from the
menu bar spawns brewcleaner.py as a normal subprocess instead.

Everything that can be tested without rumps/pyobjc (which only
install on macOS) lives here. menubar_app.py is the thin rumps.App
wrapper around these functions.
"""

from __future__ import annotations

import subprocess
import sys
from typing import List, Optional


def get_outdated_count(brew_env: dict, timeout: float = 15.0) -> Optional[int]:
    """
    Returns the number of outdated formulae + casks, or None if the
    check failed (network issue, brew missing, etc.) — callers should
    show that as "?" rather than 0, since 0 and "couldn't check" mean
    very different things to someone glancing at their menu bar.
    """
    try:
        r1 = subprocess.run(["brew", "outdated", "--quiet"],
                             capture_output=True, text=True, timeout=timeout, env=brew_env)
        r2 = subprocess.run(["brew", "outdated", "--cask", "--quiet"],
                             capture_output=True, text=True, timeout=timeout, env=brew_env)
        if r1.returncode != 0 and r2.returncode != 0:
            return None
        n1 = len([ln for ln in r1.stdout.splitlines() if ln.strip()])
        n2 = len([ln for ln in r2.stdout.splitlines() if ln.strip()])
        return n1 + n2
    except Exception:
        return None


def format_menu_title(count: Optional[int]) -> str:
    """What to show as the actual menu bar text."""
    if count is None:
        return "🍺 ?"
    if count == 0:
        return "🍺"
    return f"🍺 {count}"


def format_status_line(count: Optional[int]) -> str:
    """A slightly longer status description, for the dropdown menu."""
    if count is None:
        return "Couldn't check for updates"
    if count == 0:
        return "Everything up to date"
    if count == 1:
        return "1 package outdated"
    return f"{count} packages outdated"


def build_open_gui_command(script_path: str, python_exe: Optional[str] = None) -> List[str]:
    """
    The argv to launch the normal full-window app from the menu bar,
    deliberately WITHOUT --menubar (or it would just spawn another
    menu bar instance).
    """
    return [python_exe or sys.executable, script_path]


def build_quick_clean_command() -> str:
    """The exact command menu bar mode's 'Quick Clean' item runs."""
    return "brew cleanup -s --prune=all"
