"""
Dependencies page.

Part of the App class mixin split (v4.0) — see brewcleaner.py's App
class definition for how all these mixins are combined, and
ROADMAP.md for why this split was done as a second, isolated pass
after the v4.0 logic/bugfix pass rather than bundled with it.

This file only contains methods that were already in brewcleaner.py's
App class (v3.1.3/early v4.0) — moved here verbatim, unchanged, under
the "Dependencies page." section. No behavior was changed by this move.
"""

import subprocess
import threading
from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, PKGS, CASKS, etc.

class DepsMixin:
    # ══════════════════════════════════════════════════════════
    #  PAGE — DEPENDENCIES
    # ══════════════════════════════════════════════════════════

    def _pg_deps(self):
        p = ctk.CTkFrame(self._cf, fg_color="transparent")
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(3, weight=1)

        hdr = ctk.CTkFrame(p, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(hdr, text="Dependencies",
                     font=ctk.CTkFont(family=_SF, size=26, weight="bold"),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(hdr, text="View what a formula depends on, or what depends on it.",
                     font=ctk.CTkFont(size=12), text_color=C["text2"]).pack(anchor="w", pady=(2, 0))

        search_row = ctk.CTkFrame(p, fg_color="transparent")
        search_row.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        search_row.grid_columnconfigure(0, weight=1)
        self._dep_entry = ctk.CTkEntry(
            search_row,
            placeholder_text="Enter a formula name, e.g. ffmpeg or postgresql@16",
            font=ctk.CTkFont(size=13), height=40, corner_radius=10,
            fg_color=C["panel"], border_color=C["border"], text_color=C["text"])
        self._dep_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(search_row, text="🔽  Dependencies",
                      fg_color=C["accent"], hover_color=C["accent_h"],
                      height=40, width=148, corner_radius=10,
                      command=self._show_deps).grid(row=0, column=1, padx=(0, 6))
        ctk.CTkButton(search_row, text="🔼  Used By",
                      fg_color=C["panel"], text_color=C["accent"],
                      border_width=1, border_color=C["accent"],
                      hover_color=C["accent_bg"], height=40, width=110, corner_radius=10,
                      command=self._show_uses).grid(row=0, column=2)

        ctk.CTkButton(p, text="🌳  Show full installed tree",
                      fg_color=C["panel"], text_color=C["text2"],
                      hover_color=C["accent_bg"], border_width=1,
                      border_color=C["border"], height=30,
                      font=ctk.CTkFont(size=11),
                      command=self._show_full_tree).grid(row=2, column=0, sticky="w", pady=(0, 4))

        self._deps_out = self._mk_term(p, 250)
        self._deps_out.grid(row=3, column=0, sticky="nsew")
        self._tw(self._deps_out, "Enter a formula name above and click 'Dependencies' or 'Used By'.\n")
        self._pages["deps"] = p

    def _show_deps(self):
        name = self._dep_entry.get().strip()
        if not name:
            return
        self._deps_out.configure(state="normal")
        self._deps_out.delete("1.0", "end")
        self._deps_out.configure(state="disabled")
        self._tw(self._deps_out, f"$ brew deps --tree {name}\n\n")
        def run():
            r = subprocess.run(["brew", "deps", "--tree", name],
                               capture_output=True, text=True, timeout=20, env=_BREW_ENV)
            out = r.stdout or r.stderr or "(no output)"
            self.after(0, lambda: self._tw(self._deps_out, out + "\n"))
        threading.Thread(target=run, daemon=True).start()

    def _show_uses(self):
        name = self._dep_entry.get().strip()
        if not name:
            return
        self._deps_out.configure(state="normal")
        self._deps_out.delete("1.0", "end")
        self._deps_out.configure(state="disabled")
        self._tw(self._deps_out, f"$ brew uses --installed {name}\n\n")
        def run():
            r = subprocess.run(["brew", "uses", "--installed", name],
                               capture_output=True, text=True, timeout=20, env=_BREW_ENV)
            out = r.stdout.strip() or "(nothing installed depends on this package)"
            self.after(0, lambda: self._tw(self._deps_out, out + "\n"))
        threading.Thread(target=run, daemon=True).start()

    def _show_full_tree(self):
        self._deps_out.configure(state="normal")
        self._deps_out.delete("1.0", "end")
        self._deps_out.configure(state="disabled")
        self._tw(self._deps_out, "$ brew deps --tree --installed\n\n"
                                  "(This can take a minute or two on systems with many packages...)\n\n")
        def run():
            try:
                r = subprocess.run(["brew", "deps", "--tree", "--installed"],
                                   capture_output=True, text=True, timeout=120, env=_BREW_ENV)
                out = r.stdout or r.stderr or "(no installed formulae with dependencies)"
                self.after(0, lambda: self._tw(self._deps_out, out + "\n"))
            except subprocess.TimeoutExpired:
                self.after(0, lambda: self._tw(
                    self._deps_out, "⚠️  Command timed out. Homebrew took too long to build the dependency tree.\n"))
            except Exception:
                self.after(0, lambda: self._tw(self._deps_out, f"⚠️  Error: {e}\n"))
        threading.Thread(target=run, daemon=True).start()

