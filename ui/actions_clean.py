"""
Clean page 'Run Selected Actions' handler.

Part of the App class mixin split (v4.0) — see brewcleaner.py's App
class definition for how all these mixins are combined, and
ROADMAP.md for why this split was done as a second, isolated pass
after the v4.0 logic/bugfix pass rather than bundled with it.

This file only contains methods that were already in brewcleaner.py's
App class (v3.1.3/early v4.0) — moved here verbatim, unchanged, under
the "Clean page 'Run Selected Actions' handler." section. No behavior was changed by this move.
"""

import threading
from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, PKGS, CASKS, etc.

class CleanActionMixin:
    # ══════════════════════════════════════════════════════════
    #  CLEAN ACTION
    # ══════════════════════════════════════════════════════════

    def _refresh_disk_summary(self):
        """v4.0: populate the Clean page's disk-space estimate (see disk.py)."""
        def run():
            try:
                report = _disk_mod.get_disk_report()
                text = (f"📊  Cleanup could free ~{_disk_mod.format_bytes(report.total_bytes)}  "
                        f"(old versions {_disk_mod.format_bytes(report.old_versions_bytes)} · "
                        f"cache {_disk_mod.format_bytes(report.cache_bytes)} · "
                        f"downloads {_disk_mod.format_bytes(report.downloads_bytes)} · "
                        f"logs {_disk_mod.format_bytes(report.logs_bytes)})")
            except Exception as exc:
                text = f"📊  Couldn't estimate disk usage: {exc}"
            self.after(0, lambda: self._disk_summary_lbl.configure(text=text))
        threading.Thread(target=run, daemon=True).start()

    def _do_clean(self):
        opts = {k: v.get() for k, v in self._clean_vars.items()}
        if opts["full"] and not messagebox.askyesno(
                "Confirm Full Reinstall",
                "This will UNINSTALL every package and REMOVE Homebrew entirely,\n"
                "then reinstall Homebrew fresh.\n\nThis cannot be undone. Proceed?",
                icon="warning"):
            return
        steps: List[Tuple[str, Callable]] = []
        if opts["locks"]:
            steps.append(("Remove Lock Files",    self._op_rm_locks))
        if opts["cache"]:
            steps.append(("Clear Cache",          lambda: self._sh("brew cleanup --prune=all")))
        if opts["old"]:
            steps.append(("Remove Old Versions",  lambda: self._sh("brew cleanup")))
        if opts["orphans"]:
            steps.append(("Remove Orphans",       lambda: self._sh("brew autoremove")))
        if opts["logs"]:
            steps.append(("Clear Logs",           self._op_rm_logs))
        if opts["full"]:
            steps += [
                ("Uninstall All Packages", self._op_uninstall_all),
                ("Remove Homebrew",        self._op_rm_brew),
                ("Install Homebrew",       self._op_install_brew),
                ("Update Homebrew",        lambda: self._sh("brew update")),
            ]
        if not steps:
            messagebox.showinfo("Nothing Selected", "Tick at least one option.")
            return
        needs_sudo = opts["locks"] or opts["full"]
        if needs_sudo and not self._acquire_sudo():
            return
        steps.append(("Refresh disk estimate", self._refresh_disk_summary))
        self._run_steps("Cleaning Brew", f"{len(steps)} operation(s) queued", steps)

