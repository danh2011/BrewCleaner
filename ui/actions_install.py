"""
Packages page install handler + conflict dialog.

Part of the App class mixin split (v4.0) — see brewcleaner.py's App
class definition for how all these mixins are combined, and
ROADMAP.md for why this split was done as a second, isolated pass
after the v4.0 logic/bugfix pass rather than bundled with it.

This file only contains methods that were already in brewcleaner.py's
App class (v3.1.3/early v4.0) — moved here verbatim, unchanged, under
the "Packages page install handler + conflict dialog." section. No behavior was changed by this move.
"""

import os
import subprocess
from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, PKGS, CASKS, etc.

class InstallActionMixin:
    # ══════════════════════════════════════════════════════════
    #  INSTALL ACTION
    # ══════════════════════════════════════════════════════════

    def _do_install(self):
        total = len(self._selected) + len(self._cask_sel)
        if not total:
            messagebox.showinfo("No Selection", "Select at least one package.")
            return
        # ── Xcode CLT warning ─────────────────────────────────────
        if not _check_clt_installed():
            guidance = _xcode_install_guidance()
            proceed = messagebox.askyesno(
                "Xcode Command Line Tools Missing",
                f"Xcode Command Line Tools are NOT installed.\n\n"
                f"{guidance['note']}\n\n"
                "Many formulae will fail to compile or install without them.\n\n"
                "Install CLT first (recommended), or continue anyway?",
                icon="warning")
            if not proceed:
                return
        conflicts: Dict[str, List[str]] = {}
        for pid in self._selected:
            pkg = self._find_pkg(pid)
            if not pkg:
                continue
            found = [n for spec, n in pkg.get("conflicts", [])
                     if self._chk_conflict(spec)]
            if found:
                conflicts[pkg["label"]] = found
        if conflicts:
            self._conflict_dlg(conflicts, self._actually_install)
        else:
            self._actually_install()

    def _actually_install(self):
        formulae = sorted(self._selected)
        casks    = sorted(self._cask_sel)
        steps: List[Tuple[str, Callable]] = [
            ("Update Homebrew", self._op_update_if_stale),
        ]
        if formulae:
            steps.append((f"Pre-fetch bottles  ({len(formulae)} formula)",
                          lambda f=formulae: self._op_prefetch(f)))
            steps.append((f"Install {len(formulae)} formula(e)",
                          lambda f=formulae: self._op_batch_install(f)))
        if casks:
            steps.append((f"Install {len(casks)} cask(s)",
                          lambda c=casks: self._sh("brew install --cask " + " ".join(c))))
        self._run_steps("Installing Packages",
                        f"{len(formulae)+len(casks)} package(s) queued", steps)

    def _find_pkg(self, pid: str) -> Optional[Dict]:
        for pks in PKGS.values():
            for p in pks:
                if p["id"] == pid:
                    return p
        for p in self._custom_pkgs:
            if p["id"] == pid:
                return p
        return None

    def _chk_conflict(self, spec: str) -> bool:
        if spec.startswith("cmd:"):
            try:
                return subprocess.run(
                    ["which", spec[4:]], capture_output=True, timeout=3
                ).returncode == 0
            except Exception:
                return False
        return os.path.exists(os.path.expanduser(spec))

    def _conflict_dlg(self, conflicts: Dict[str, List[str]], on_proceed: Callable):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Conflicts Detected")
        dlg.geometry("500x400")
        dlg.configure(fg_color=C["bg"])
        dlg.grab_set()
        dlg.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()  - 500) // 2
        y = self.winfo_y() + (self.winfo_height() - 400) // 2
        dlg.geometry(f"+{x}+{y}")
        ctk.CTkLabel(dlg, text="⚠️  Conflicts Detected",
                     font=ctk.CTkFont(family=_SF, size=18, weight="bold"),
                     text_color=C["text"]).pack(pady=(22, 4))
        ctk.CTkLabel(dlg,
                     text="Other installations of these packages exist on this Mac:",
                     font=ctk.CTkFont(size=12), text_color=C["text2"]).pack()
        sc = ctk.CTkScrollableFrame(dlg, fg_color=C["panel"],
                                    corner_radius=10, height=180)
        sc.pack(fill="x", padx=20, pady=14)
        for lbl, items in conflicts.items():
            ctk.CTkLabel(sc, text=f"  {lbl}",
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=C["text"]).pack(anchor="w", padx=8, pady=(8, 2))
            for item in items:
                ctk.CTkLabel(sc, text=f"    • {item} found",
                             font=ctk.CTkFont(size=11),
                             text_color=C["warn"]).pack(anchor="w", padx=8)
        bf = ctk.CTkFrame(dlg, fg_color="transparent")
        bf.pack(fill="x", padx=20, pady=(0, 20))
        bf.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(bf, text="Install Anyway",
                      fg_color=C["accent"], hover_color=C["accent_h"],
                      command=lambda: [dlg.destroy(), on_proceed()]
                      ).grid(row=0, column=0, padx=(0, 5), sticky="ew")
        ctk.CTkButton(bf, text="Cancel",
                      fg_color="transparent", text_color=C["text2"],
                      hover_color=C["border"], border_width=1, border_color=C["border"],
                      command=dlg.destroy
                      ).grid(row=0, column=1, padx=(5, 0), sticky="ew")

