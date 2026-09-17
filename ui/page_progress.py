"""
Progress page.

Part of the App class mixin split (v4.0) — see brewcleaner.py's App
class definition for how all these mixins are combined, and
ROADMAP.md for why this split was done as a second, isolated pass
after the v4.0 logic/bugfix pass rather than bundled with it.

This file only contains methods that were already in brewcleaner.py's
App class (v3.1.3/early v4.0) — moved here verbatim, unchanged, under
the "Progress page." section. No behavior was changed by this move.
"""

from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, PKGS, CASKS, etc.

class ProgressMixin:
    # ══════════════════════════════════════════════════════════
    #  PAGE — PROGRESS
    # ══════════════════════════════════════════════════════════

    def _pg_progress(self):
        p = ctk.CTkFrame(self._cf, fg_color="transparent")
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(4, weight=1)

        self._pr_title = ctk.CTkLabel(
            p, text="No Task Running",
            font=ctk.CTkFont(family=_SF, size=26, weight="bold"),
            text_color=C["text"])
        self._pr_title.grid(row=0, column=0, sticky="w")
        self._pr_sub = ctk.CTkLabel(
            p, text="Start a task from any page to see live progress here.",
            font=ctk.CTkFont(size=12), text_color=C["text2"])
        self._pr_sub.grid(row=1, column=0, sticky="w", pady=(2, 14))

        sp = ctk.CTkFrame(p, fg_color=C["panel"], corner_radius=12,
                          border_width=1, border_color=C["border"])
        sp.grid(row=2, column=0, sticky="ew")
        self._steps_f = ctk.CTkFrame(sp, fg_color="transparent")
        self._steps_f.pack(fill="x", padx=16, pady=12)
        self._steps_idle_lbl = ctk.CTkLabel(
            self._steps_f,
            text="Steps will appear here when a task is running.",
            font=ctk.CTkFont(size=12), text_color=C["text3"])
        self._steps_idle_lbl.pack(pady=8)

        self._pbar = ctk.CTkProgressBar(
            p, fg_color=C["border"], progress_color=C["accent"],
            height=7, corner_radius=4)
        self._pbar.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        self._pbar.set(0)

        self._pr_term = self._mk_term(p, 200)
        self._pr_term.grid(row=4, column=0, sticky="nsew", pady=(10, 0))

        self._done_btn = ctk.CTkButton(
            p, text="✓  Done — Return to Dashboard",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=C["ok"], hover_color="#16A34A",
            height=50, corner_radius=10,
            command=lambda: self._goto("home"))
        self._done_btn.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        self._done_btn.grid_remove()
        self._pages["progress"] = p

