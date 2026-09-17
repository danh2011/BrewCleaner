"""
Taps page.

Part of the App class mixin split (v4.0) — see brewcleaner.py's App
class definition for how all these mixins are combined, and
ROADMAP.md for why this split was done as a second, isolated pass
after the v4.0 logic/bugfix pass rather than bundled with it.

This file only contains methods that were already in brewcleaner.py's
App class (v3.1.3/early v4.0) — moved here verbatim, unchanged, under
the "Taps page." section. No behavior was changed by this move.
"""

import subprocess
import threading
import json
from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, PKGS, CASKS, etc.

class TapsMixin:
    # ══════════════════════════════════════════════════════════
    #  PAGE — TAPS
    # ══════════════════════════════════════════════════════════

    def _pg_taps(self):
        p = ctk.CTkFrame(self._cf, fg_color="transparent")
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(2, weight=1)

        hdr = ctk.CTkFrame(p, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(hdr, text="Tap Manager",
                     font=ctk.CTkFont(family=_SF, size=26, weight="bold"),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(hdr, text="Add or remove third-party Homebrew formula repositories.",
                     font=ctk.CTkFont(size=12), text_color=C["text2"]).pack(anchor="w", pady=(2, 0))

        toolbar = ctk.CTkFrame(p, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkButton(toolbar, text="↻  Refresh",
                      fg_color=C["panel"], text_color=C["text2"],
                      hover_color=C["accent_bg"], border_width=1, border_color=C["border"],
                      height=36, width=100, corner_radius=8,
                      command=self._refresh_taps).pack(side="left", padx=(0, 8))
        add_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        add_frame.pack(side="right")
        self._tap_entry = ctk.CTkEntry(
            add_frame,
            placeholder_text="user/repo  (e.g. homebrew/cask-fonts)",
            font=ctk.CTkFont(size=12), height=36, width=280, corner_radius=8,
            fg_color=C["panel"], border_color=C["border"], text_color=C["text"])
        self._tap_entry.pack(side="left", padx=(0, 6))
        ctk.CTkButton(add_frame, text="+ Add Tap",
                      fg_color=C["accent"], hover_color=C["accent_h"],
                      height=36, width=100, corner_radius=8,
                      command=self._do_add_tap).pack(side="left")

        self._taps_list = ctk.CTkScrollableFrame(
            p, fg_color="transparent", scrollbar_button_color=C["border"])
        self._taps_list.grid(row=2, column=0, sticky="nsew")
        self._taps_list.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self._taps_list, text="Loading…",
                     font=ctk.CTkFont(size=12), text_color=C["text3"]
                     ).grid(row=0, column=0, pady=24)
        self._pages["taps"] = p

    def _refresh_taps(self):
        self._taps_loaded = False
        for w in self._taps_list.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._taps_list, text="Refreshing…",
                     font=ctk.CTkFont(size=12), text_color=C["text3"]
                     ).grid(row=0, column=0, pady=24)
        self._taps_loaded = True
        threading.Thread(target=self._load_taps_data, daemon=True).start()

    def _load_taps_data(self):
        try:
            r = subprocess.run(["brew", "tap-info", "--json", "--installed"],
                               capture_output=True, text=True, timeout=20, env=_BREW_ENV)
            taps_json = json.loads(r.stdout) if r.stdout.strip() else []
            self._taps_data = [
                {"name":     t.get("name","?"),
                 "count":    len(t.get("formula_names",[])) + len(t.get("cask_tokens",[])),
                 "remote":   t.get("remote",""),
                 "official": t.get("name","").startswith("homebrew/")}
                for t in taps_json
            ]
            self.after(0, self._render_taps)
        except Exception as exc:
            self.after(0, lambda e=exc: self._render_taps_error(str(e)))

    def _render_taps(self):
        for w in self._taps_list.winfo_children():
            w.destroy()
        if not self._taps_data:
            ctk.CTkLabel(self._taps_list, text="No taps found.",
                         font=ctk.CTkFont(size=12), text_color=C["text3"]
                         ).grid(row=0, column=0, pady=24)
            return
        ctk.CTkLabel(self._taps_list, text=f"{len(self._taps_data)} tap(s) installed",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C["text"]).grid(row=0, column=0, sticky="w", padx=12, pady=(4, 8))
        for i, tap in enumerate(self._taps_data):
            row = ctk.CTkFrame(self._taps_list, fg_color=C["panel"],
                               corner_radius=10, border_width=1, border_color=C["border"])
            row.grid(row=i+1, column=0, sticky="ew", pady=4, padx=8)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text="🍺" if tap["official"] else "🧪",
                         font=ctk.CTkFont(size=18), fg_color="transparent"
                         ).grid(row=0, column=0, padx=(14, 10), pady=12)
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.grid(row=0, column=1, sticky="ew", pady=10)
            ctk.CTkLabel(info, text=tap["name"],
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=C["text"], anchor="w").pack(anchor="w")
            n   = tap["count"]
            rem = tap["remote"]
            sub = f"{n} formula{'e' if n != 1 else ''}"
            if rem:
                sub += f"  •  {rem[:55]}{'…' if len(rem) > 55 else ''}"
            ctk.CTkLabel(info, text=sub, font=ctk.CTkFont(size=10),
                         text_color=C["text2"], anchor="w").pack(anchor="w")
            if not tap["official"]:
                ctk.CTkButton(row, text="Untap", width=78, height=28, corner_radius=6,
                              fg_color=C["err"], hover_color="#C62828",
                              font=ctk.CTkFont(size=11),
                              command=lambda n=tap["name"]: self._do_untap(n)
                              ).grid(row=0, column=2, padx=12)

    def _render_taps_error(self, msg: str):
        for w in self._taps_list.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._taps_list, text=f"⚠️  {msg}",
                     font=ctk.CTkFont(size=12), text_color=C["err"]
                     ).grid(row=0, column=0, pady=24)

    def _do_add_tap(self):
        name = self._tap_entry.get().strip()
        if not name:
            messagebox.showinfo("Add Tap", "Enter a tap name, e.g.  homebrew/cask-fonts")
            return
        self._tap_entry.delete(0, "end")
        self._run_steps("Adding Tap", f"brew tap {name}", [
            ("Add tap",      lambda: self._sh(f"brew tap {name}")),
            ("Refresh list", self._refresh_taps)])

    def _do_untap(self, name: str):
        if not messagebox.askyesno(
                "Untap", f"Remove tap  {name}?\n\n"
                "All formulae from this tap will become unavailable."):
            return
        self._run_steps("Removing Tap", f"brew untap {name}", [
            ("Untap",        lambda: self._sh(f"brew untap {name}")),
            ("Refresh list", self._refresh_taps)])

