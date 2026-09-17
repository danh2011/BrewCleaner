"""
Clean Brew page (options UI).

Part of the App class mixin split (v4.0) — see brewcleaner.py's App
class definition for how all these mixins are combined, and
ROADMAP.md for why this split was done as a second, isolated pass
after the v4.0 logic/bugfix pass rather than bundled with it.

This file only contains methods that were already in brewcleaner.py's
App class (v3.1.3/early v4.0) — moved here verbatim, unchanged, under
the "Clean Brew page (options UI)." section. No behavior was changed by this move.
"""

from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, PKGS, CASKS, etc.

class CleanPageMixin:
    # ══════════════════════════════════════════════════════════
    #  PAGE — CLEAN BREW
    # ══════════════════════════════════════════════════════════

    def _pg_clean(self):
        p = ctk.CTkScrollableFrame(self._cf, fg_color="transparent",
                                   scrollbar_button_color=C["border"])
        self._section_hdr(p, "Clean Brew",
                          "Remove cache, lock files, old versions — or a full reinstall")

        wb = ctk.CTkFrame(p, fg_color="#FFF8E1", corner_radius=10,
                          border_width=1, border_color="#FFD54F")
        wb.pack(fill="x", pady=(0, 20), padx=8)
        ctk.CTkLabel(wb, text="⚠️  Full Reinstall removes ALL packages and Homebrew itself. "
                     "Select packages to reinstall on the Packages page first.",
                     font=ctk.CTkFont(size=12), text_color="#7B5800",
                     wraplength=700).pack(padx=16, pady=12)

        # v4.0: disk space report — see brewcleaner_pkg/disk.py. Shows
        # what cleanup would actually free instead of asking people to
        # run it blind.
        disk_card = ctk.CTkFrame(p, fg_color=C["panel"], corner_radius=10,
                                  border_width=1, border_color=C["border"])
        disk_card.pack(fill="x", pady=(0, 16), padx=8)
        disk_row = ctk.CTkFrame(disk_card, fg_color="transparent")
        disk_row.pack(fill="x", padx=16, pady=12)
        self._disk_summary_lbl = ctk.CTkLabel(
            disk_row, text="📊  Estimating reclaimable disk space…",
            font=ctk.CTkFont(size=12), text_color=C["text2"], anchor="w")
        self._disk_summary_lbl.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(disk_row, text="Refresh", width=80, height=28,
                      fg_color="transparent", border_width=1, border_color=C["border"],
                      text_color=C["text2"], hover_color=C["panel2"],
                      command=self._refresh_disk_summary).pack(side="right")
        self._refresh_disk_summary()

        opt_frame = ctk.CTkFrame(p, fg_color="transparent")
        opt_frame.pack(fill="x", padx=8)
        self._mini_hdr(opt_frame, "Options")
        
        self._clean_vars: Dict[str, tk.BooleanVar] = {}
        OPTIONS = [
            ("locks",   "🔓  Remove Lock / In-Progress Files",
             "Unlock stuck brew operations and delete .lock files",                       True,  False),
            ("cache",   "🗑️  Clear Download Cache",
             "Free disk space from ~/Library/Caches/Homebrew",                           True,  False),
            ("old",     "♻️  Remove Old Package Versions",
             "Keep only the latest version of each formula",                              True,  False),
            ("orphans", "🔄  Remove Orphan Dependencies",
             "Remove installed packages no longer needed by anything (brew autoremove)", False, False),
            ("logs",    "📋  Clear Homebrew Logs",
             "Delete all files in ~/Library/Logs/Homebrew",                              False, False),
            ("full",    "💣  Full Reinstall  (destructive)",
             "Uninstall every package, remove Homebrew entirely, then reinstall fresh",  False, True),
        ]
        
        for key, title, desc, default, danger in OPTIONS:
            var = tk.BooleanVar(value=default)
            self._clean_vars[key] = var
            row = ctk.CTkFrame(opt_frame, fg_color=C["panel"], corner_radius=10,
                               border_width=1, border_color=C["border"])
            row.pack(fill="x", pady=4)
            lf = ctk.CTkFrame(row, fg_color="transparent")
            lf.pack(side="left", fill="x", expand=True, padx=16, pady=14)
            ctk.CTkLabel(lf, text=title,
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=C["err"] if danger else C["text"],
                         anchor="w").pack(fill="x")
            ctk.CTkLabel(lf, text=desc, font=ctk.CTkFont(size=11),
                         text_color=C["text2"], anchor="w").pack(fill="x")
            ctk.CTkCheckBox(row, text="", variable=var, width=30,
                            fg_color=C["err"] if danger else C["accent"],
                            hover_color=C["accent_h"],
                            border_color=C["border"]).pack(side="right", padx=18)

        ctk.CTkButton(p, text="Run Selected Actions",
                      font=ctk.CTkFont(size=14, weight="bold"),
                      fg_color=C["accent"], hover_color=C["accent_h"],
                      height=50, corner_radius=10,
                      command=self._do_clean).pack(fill="x", pady=(20, 4), padx=8)
        self._pages["clean"] = p

