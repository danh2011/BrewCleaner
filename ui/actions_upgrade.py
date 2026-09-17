"""
Upgrade page actions.

Part of the App class mixin split (v4.0) — see brewcleaner.py's App
class definition for how all these mixins are combined, and
ROADMAP.md for why this split was done as a second, isolated pass
after the v4.0 logic/bugfix pass rather than bundled with it.

This file only contains methods that were already in brewcleaner.py's
App class (v3.1.3/early v4.0) — moved here verbatim, unchanged, under
the "Upgrade page actions." section. No behavior was changed by this move.
"""

from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, PKGS, CASKS, etc.

class UpgradeActionsMixin:
    # ══════════════════════════════════════════════════════════
    #  UPGRADE ACTIONS
    # ══════════════════════════════════════════════════════════

    def _do_upgrade_one(self, name: str, is_cask: bool):
        flag = "--cask" if is_cask else ""
        self._run_steps(f"Upgrading {name}", name, [
            ("Update Homebrew",   self._op_update_if_stale),
            (f"Upgrade {name}",   lambda n=name, f=flag:
             self._sh(f"brew upgrade {f} {n}".strip())),
            ("Refresh list",      self._refresh_upgrades)])

    def _do_upgrade_selected(self):
        if not self._upgrade_sel:
            messagebox.showinfo("Nothing Selected", "Tick at least one package to upgrade.")
            return
        pkgs = sorted(self._upgrade_sel)
        self._run_steps("Upgrading Selected", f"{len(pkgs)} package(s)", [
            ("Update Homebrew",            self._op_update_if_stale),
            (f"Upgrade {len(pkgs)} pkg(s)",lambda p=pkgs: self._sh("brew upgrade " + " ".join(p))),
            ("Refresh list",               self._refresh_upgrades)])

    def _do_upgrade_all(self):
        if not messagebox.askyesno("Upgrade All",
                                   "Upgrade all installed formulae and casks?\n"
                                   "This may take several minutes."):
            return
        self._run_steps("Upgrading All", "brew upgrade", [
            ("Update Homebrew",  self._op_update_if_stale),
            ("Upgrade formulae", lambda: self._sh("brew upgrade")),
            ("Upgrade casks",    lambda: self._sh("brew upgrade --cask")),
            ("Refresh list",     self._refresh_upgrades)])

