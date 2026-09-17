"""
Brew Health page.

Part of the App class mixin split (v4.0) — see brewcleaner.py's App
class definition for how all these mixins are combined, and
ROADMAP.md for why this split was done as a second, isolated pass
after the v4.0 logic/bugfix pass rather than bundled with it.

This file only contains methods that were already in brewcleaner.py's
App class (v3.1.3/early v4.0) — moved here verbatim, unchanged, under
the "Brew Health page." section. No behavior was changed by this move.
"""

import subprocess
import threading
from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, PKGS, CASKS, etc.

class HealthMixin:
    # ══════════════════════════════════════════════════════════
    #  PAGE — BREW HEALTH
    # ══════════════════════════════════════════════════════════

    def _pg_health(self):
        p = ctk.CTkFrame(self._cf, fg_color="transparent")
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(2, weight=1)

        hdr = ctk.CTkFrame(p, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(hdr, text="Brew Health",
                     font=ctk.CTkFont(family=_SF, size=26, weight="bold"),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(hdr, text="Run brew doctor and brew missing to spot configuration problems.",
                     font=ctk.CTkFont(size=12), text_color=C["text2"]).pack(anchor="w", pady=(2, 0))

        toolbar = ctk.CTkFrame(p, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkButton(toolbar, text="🩺  Run brew doctor",
                      fg_color=C["accent"], hover_color=C["accent_h"],
                      height=36, corner_radius=8,
                      command=self._run_doctor).pack(side="left", padx=(0, 6))
        ctk.CTkButton(toolbar, text="🔍  Check Missing Deps",
                      fg_color=C["panel"], text_color=C["text2"],
                      hover_color=C["accent_bg"], border_width=1, border_color=C["border"],
                      height=36, corner_radius=8,
                      command=self._run_missing).pack(side="left", padx=(0, 6))
        ctk.CTkButton(toolbar, text="🔧  brew cleanup --prune=all",
                      fg_color=C["panel"], text_color=C["warn"],
                      hover_color=C["accent_bg"], border_width=1, border_color=C["warn"],
                      height=36, corner_radius=8,
                      command=lambda: self._run_steps(
                          "Clean All", "Pruning all old downloads",
                          [("brew cleanup --prune=all",
                            lambda: self._sh("brew cleanup --prune=all"))])
                      ).pack(side="left")

        self._health_out = self._mk_term(p, 300)
        self._health_out.grid(row=2, column=0, sticky="nsew")
        self._tw(self._health_out, "Click a button above to check your Homebrew installation.\n")
        self._pages["health"] = p

    def _run_doctor(self):
        self._health_out.configure(state="normal")
        self._health_out.delete("1.0", "end")
        self._health_out.configure(state="disabled")
        self._tw(self._health_out, "$ brew doctor\n\n")
        def run():
            r = subprocess.run(["brew", "doctor"],
                               capture_output=True, text=True, timeout=60, env=_BREW_ENV)
            output = r.stdout + r.stderr
            if not output.strip():
                output = "Your system is ready to brew! ✓"
            self.after(0, lambda: (
                self._tw(self._health_out, output + "\n"),
                self._tw(self._health_out,
                         "\n✅  All checks passed.\n" if r.returncode == 0
                         else "\n⚠️  Issues found. Review the warnings above.\n")))
        threading.Thread(target=run, daemon=True).start()

    def _run_missing(self):
        self._health_out.configure(state="normal")
        self._health_out.delete("1.0", "end")
        self._health_out.configure(state="disabled")
        self._tw(self._health_out, "$ brew missing\n\n")
        def run():
            r = subprocess.run(["brew", "missing"],
                               capture_output=True, text=True, timeout=30, env=_BREW_ENV)
            output = r.stdout + r.stderr
            if not output.strip():
                output = "No missing dependencies found. ✓"
            self.after(0, lambda: self._tw(self._health_out, output + "\n"))
        threading.Thread(target=run, daemon=True).start()

