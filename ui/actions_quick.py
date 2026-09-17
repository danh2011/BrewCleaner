"""
Dashboard quick-action buttons.

Part of the App class mixin split (v4.0) — see brewcleaner.py's App
class definition for how all these mixins are combined, and
ROADMAP.md for why this split was done as a second, isolated pass
after the v4.0 logic/bugfix pass rather than bundled with it.

This file only contains methods that were already in brewcleaner.py's
App class (v3.1.3/early v4.0) — moved here verbatim, unchanged, under
the "Dashboard quick-action buttons." section. No behavior was changed by this move.
"""

import subprocess
import threading
from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, PKGS, CASKS, etc.

class QuickActionsMixin:
    # ══════════════════════════════════════════════════════════
    #  QUICK ACTIONS
    # ══════════════════════════════════════════════════════════

    def _quick(self, cmd: str):
        def run():
            self.after(0, lambda: self._tw(self._home_term, f"\n$ {cmd}\n"))
            buf: List[str] = []
            buf_lock = threading.Lock()

            def flush():
                with buf_lock:
                    if buf:
                        self._tw(self._home_term, "".join(buf))
                        buf.clear()

            def sched():
                flush()
                if not getattr(self, "_quick_running", False):
                    return
                self.after(50, sched)

            self._quick_running = True
            self.after(50, sched)
            try:
                proc = subprocess.Popen(
                    cmd, shell=True,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, env=_BREW_ENV, bufsize=1)
                for line in iter(proc.stdout.readline, ""):
                    with buf_lock:
                        buf.append(line)
                proc.wait()
                self._quick_running = False
                self.after(0, flush)
                self.after(0, lambda rc=proc.returncode: self._tw(
                    self._home_term,
                    f"\n{'✅' if rc == 0 else '⚠️'}  Done (exit {rc})\n"))
            except Exception as exc:
                self._quick_running = False
                self.after(0, lambda e=exc: self._tw(self._home_term, f"\n❌  {e}\n"))
            threading.Thread(target=self._probe, daemon=True).start()

        threading.Thread(target=run, daemon=True).start()

