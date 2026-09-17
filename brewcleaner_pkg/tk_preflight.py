"""
Preflight check for the "macOS 13 (1307) or later required, have
instead 13 (1306)" crash.

WHAT THIS ACTUALLY IS: it is not a BrewCleaner bug and not a Python
exception — it's a bug in Tcl/Tk (present in the 8.6.12 build that
ships inside most python.org and older Homebrew Python installs)
where Tk's Cocoa backend misreads certain macOS point releases and
calls abort() from its own C init code. Because it's a hard process
abort (SIGABRT) raised before Python's exception machinery is even
running, it CANNOT be caught with try/except in the same process —
that's why the original app just died with `zsh: abort` instead of
showing an error dialog.

The only reliable way to detect it is to try initializing Tk in a
short-lived *subprocess* first, so a crash there doesn't take the
whole app down. This module does that, and gives the user an actual
actionable message instead of a bare abort trace.

The durable fix lives in scripts/install.sh, which now checks for a
working Tk *before* wiring up the `brewcleaner` command, and prefers
a Homebrew Python + `python-tk` combination (Tcl/Tk 8.6.13+) known
not to have this bug. This module is the runtime safety net for
people who installed before that fix, or who point BrewCleaner at a
different Python manually.
"""

from __future__ import annotations

import subprocess
import sys

_PROBE_SRC = "import tkinter; r = tkinter.Tk(); r.destroy()"


def probe_tk(timeout: float = 8.0) -> tuple[bool, str]:
    """
    Try to create and destroy a Tk root window in a subprocess.
    Returns (ok, diagnostic_message). diagnostic_message is empty
    when ok is True.
    """
    try:
        r = subprocess.run(
            [sys.executable, "-c", _PROBE_SRC],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, (
            "Tk did not respond within a few seconds while starting up. "
            "This usually also indicates a broken Tcl/Tk install."
        )
    except Exception as exc:
        return False, f"Could not even launch a Python subprocess to test Tk: {exc}"

    if r.returncode == 0:
        return True, ""

    combined = (r.stdout or "") + (r.stderr or "")
    if "or later required" in combined or r.returncode < 0:
        # returncode < 0 on POSIX means it died from a signal (SIGABRT = -6)
        return False, (
            "Your Python's bundled Tcl/Tk has a known bug on this macOS "
            "version and aborts instead of starting.\n\n"
            "Fix (recommended): run this in Terminal, then reopen BrewCleaner:\n"
            "    brew install python-tk\n\n"
            "If that doesn't help, your Python's Tcl/Tk needs updating to "
            "8.6.13 or later — installing Python fresh via Homebrew "
            "(`brew install python`) alongside `python-tk` resolves it for "
            "almost everyone.\n\n"
            f"Raw error: {combined.strip()[-300:]}"
        )
    return False, f"Tk failed to start (exit code {r.returncode}):\n{combined.strip()[-500:]}"


def preflight_or_exit() -> None:
    """
    Call this at the very top of the entry point, before any
    `import tkinter` happens in the main process. Prints a clear
    message and exits(1) instead of letting Tk abort the process.
    """
    ok, msg = probe_tk()
    if ok:
        return
    print("🍺 BrewCleaner can't start: Tk failed a startup check.\n", file=sys.stderr)
    print(msg, file=sys.stderr)
    sys.exit(1)
