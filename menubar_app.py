"""
Menu bar mode's actual NSStatusBar wrapper.

Deliberately thin — every decision (what the title says, what the
quick-clean command is, how to launch the full GUI) is delegated to
brewcleaner_pkg/menubar_core.py, which is unit tested. This file is
just the rumps glue, which can't be tested outside real macOS (rumps
wraps pyobjc, which only installs on macOS) so it's kept as small as
possible on purpose.

Run via:  brewcleaner --menubar
"""

from __future__ import annotations

import subprocess
import sys
import threading

from brewcleaner_pkg import menubar_core
from brewcleaner_pkg.brew_env import build_brew_env
from brewcleaner_pkg.notify import send as notify_send
from brewcleaner_pkg.prefs import load_prefs

REFRESH_INTERVAL_SECONDS = 30 * 60  # 30 minutes — matches brew's own update cadence assumptions


def _require_rumps():
    try:
        import rumps
        return rumps
    except ImportError:
        print(
            "Menu bar mode needs the 'rumps' package, which isn't installed.\n"
            "Install it with:\n"
            "    pip3 install rumps\n"
            "then run `brewcleaner --menubar` again.",
            file=sys.stderr,
        )
        sys.exit(1)


def run(script_path: str) -> None:
    rumps = _require_rumps()
    brew_env = build_brew_env()

    class BrewCleanerMenuBar(rumps.App):
        def __init__(self):
            super().__init__(menubar_core.format_menu_title(None), quit_button=None)
            self.menu = [
                rumps.MenuItem("Checking…", callback=None),
                None,  # separator
                rumps.MenuItem("Open BrewCleaner", callback=self.open_gui),
                rumps.MenuItem("Quick Clean", callback=self.quick_clean),
                rumps.MenuItem("Check Now", callback=self.check_now),
                None,
                rumps.MenuItem("Quit", callback=self.quit_app),
            ]
            self._status_item = self.menu["Checking…"]

        # ── actions ──────────────────────────────────────────
        def open_gui(self, _sender=None):
            cmd = menubar_core.build_open_gui_command(script_path)
            subprocess.Popen(cmd)

        def quick_clean(self, _sender=None):
            self._status_item.title = "Cleaning…"

            def work():
                try:
                    subprocess.run(menubar_core.build_quick_clean_command(),
                                    shell=True, env=brew_env, timeout=300,
                                    capture_output=True)
                    prefs = load_prefs()
                    notify_send("BrewCleaner", "Quick Clean complete",
                                enabled=prefs.get("notifications", True))
                finally:
                    self.refresh(None)
            threading.Thread(target=work, daemon=True).start()

        def check_now(self, _sender=None):
            self.refresh(None)

        def quit_app(self, _sender=None):
            rumps.quit_application()

        # ── periodic refresh ─────────────────────────────────
        def refresh(self, _sender):
            self._status_item.title = "Checking…"

            def work():
                count = menubar_core.get_outdated_count(brew_env)
                self.title = menubar_core.format_menu_title(count)
                self._status_item.title = menubar_core.format_status_line(count)
            threading.Thread(target=work, daemon=True).start()

        @rumps.timer(REFRESH_INTERVAL_SECONDS)
        def periodic_refresh(self, _sender):
            self.refresh(None)

    app = BrewCleanerMenuBar()
    app.refresh(None)
    app.run()
