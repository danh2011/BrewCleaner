"""
Upgrades page.

Part of the App class mixin split (v4.0) — see brewcleaner.py's App
class definition for how all these mixins are combined, and
ROADMAP.md for why this split was done as a second, isolated pass
after the v4.0 logic/bugfix pass rather than bundled with it.

This file only contains methods that were already in brewcleaner.py's
App class (v3.1.3/early v4.0) — moved here verbatim, unchanged, under
the "Upgrades page." section. No behavior was changed by this move.
"""

import subprocess
import threading
import json
from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, PKGS, CASKS, etc.

class UpgradesPageMixin:
    # ══════════════════════════════════════════════════════════
    #  PAGE — UPGRADES
    # ══════════════════════════════════════════════════════════

    def _pg_upgrades(self):
        p = ctk.CTkFrame(self._cf, fg_color="transparent")
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(2, weight=1)

        hdr = ctk.CTkFrame(p, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(hdr, text="Upgrades",
                     font=ctk.CTkFont(family=_SF, size=26, weight="bold"),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(hdr, text="Upgrade individual packages and pin versions to prevent accidental upgrades.",
                     font=ctk.CTkFont(size=12), text_color=C["text2"]).pack(anchor="w", pady=(2, 0))

        toolbar = ctk.CTkFrame(p, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkButton(toolbar, text="↻  Refresh",
                      fg_color=C["panel"], text_color=C["text2"],
                      hover_color=C["accent_bg"], border_width=1, border_color=C["border"],
                      height=36, width=100, corner_radius=8,
                      command=self._refresh_upgrades).pack(side="left", padx=(0, 8))
        self._upgrade_sel_btn = ctk.CTkButton(
            toolbar, text="⬆  Upgrade Selected  (0)",
            fg_color=C["accent"], hover_color=C["accent_h"],
            height=36, width=210, corner_radius=8,
            command=self._do_upgrade_selected)
        self._upgrade_sel_btn.pack(side="left", padx=(0, 6))
        ctk.CTkButton(toolbar, text="⬆⬆  Upgrade All",
                      fg_color=C["panel"], text_color=C["warn"],
                      hover_color=C["accent_bg"], border_width=1, border_color=C["warn"],
                      height=36, width=150, corner_radius=8,
                      command=self._do_upgrade_all).pack(side="left")

        self._upgrades_list = ctk.CTkScrollableFrame(
            p, fg_color="transparent", scrollbar_button_color=C["border"])
        self._upgrades_list.grid(row=2, column=0, sticky="nsew")
        self._upgrades_list.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self._upgrades_list, text="Loading…",
                     font=ctk.CTkFont(size=12), text_color=C["text3"]
                     ).grid(row=0, column=0, pady=24)
        self._pages["upgrades"] = p

    def _refresh_upgrades(self):
        self._outdated_loaded = False
        for w in self._upgrades_list.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._upgrades_list, text="Refreshing…",
                     font=ctk.CTkFont(size=12), text_color=C["text3"]
                     ).grid(row=0, column=0, pady=24)
        self._outdated_loaded = True
        threading.Thread(target=self._load_outdated_data, daemon=True).start()

    def _load_outdated_data(self):
        try:
            r1 = subprocess.run(["brew","outdated","--json=v2"],
                                capture_output=True, text=True, timeout=25, env=_BREW_ENV)
            r2 = subprocess.run(["brew","list","--pinned"],
                                capture_output=True, text=True, timeout=10, env=_BREW_ENV)
            data = json.loads(r1.stdout) if r1.stdout.strip() else {}
            formulae = data.get("formulae", [])
            casks    = [dict(c, _is_cask=True) for c in data.get("casks", [])]
            self._outdated_data = formulae + casks
            self._pinned_set    = set(r2.stdout.strip().split())
            self.after(0, self._render_upgrades)
        except Exception as exc:
            self.after(0, lambda e=exc: self._render_upgrades_error(str(e)))

    def _render_upgrades(self):
        for w in self._upgrades_list.winfo_children():
            w.destroy()
        self._upgrade_vars = {}
        self._upgrade_sel  = set()
        self._upgrade_sel_btn.configure(text="⬆  Upgrade Selected  (0)")

        if not self._outdated_data:
            ctk.CTkLabel(self._upgrades_list,
                         text="✓  All packages are up to date",
                         font=ctk.CTkFont(size=13), text_color=C["ok"]
                         ).grid(row=0, column=0, pady=32)
            return

        ctk.CTkLabel(self._upgrades_list,
                     text=f"{len(self._outdated_data)} update(s) available",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C["text"]).grid(row=0, column=0, sticky="w", padx=12, pady=(4, 8))

        for i, pkg in enumerate(self._outdated_data):
            name    = pkg.get("name", "?")
            curr    = ", ".join(pkg.get("installed_versions", ["?"])) or "?"
            new_v   = pkg.get("current_version", "?")
            is_cask = pkg.get("_is_cask", False)
            pinned  = name in self._pinned_set

            var = tk.BooleanVar(value=False)
            self._upgrade_vars[name] = var

            row = ctk.CTkFrame(self._upgrades_list, fg_color=C["panel"],
                               corner_radius=10, border_width=1, border_color=C["border"])
            row.grid(row=i+1, column=0, sticky="ew", pady=4, padx=8)
            row.grid_columnconfigure(2, weight=1)

            ctk.CTkCheckBox(row, text="", variable=var, width=30,
                            fg_color=C["accent"], hover_color=C["accent_h"],
                            border_color=C["border"],
                            command=lambda n=name, v=var: self._toggle_upgrade(n, v)
                            ).grid(row=0, column=0, padx=(12, 4), pady=12)
            ctk.CTkLabel(row, text="📱" if is_cask else "📦",
                         font=ctk.CTkFont(size=16), fg_color="transparent"
                         ).grid(row=0, column=1, padx=(0, 10))
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.grid(row=0, column=2, sticky="ew", pady=10)
            name_txt = name + ("  📌 pinned" if pinned else "")
            ctk.CTkLabel(info, text=name_txt,
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=C["warn"] if pinned else C["text"],
                         anchor="w").pack(anchor="w")
            ctk.CTkLabel(info, text=f"{curr}  →  {new_v}",
                         font=ctk.CTkFont(size=11), text_color=C["warn"],
                         anchor="w").pack(anchor="w")

            bf = ctk.CTkFrame(row, fg_color="transparent")
            bf.grid(row=0, column=3, padx=12)
            if not is_cask:
                ctk.CTkButton(
                    bf,
                    text="Unpin" if pinned else "📌 Pin",
                    width=76, height=28, corner_radius=6,
                    fg_color=C["warn"] if pinned else C["panel"],
                    text_color=C["text"], border_width=1,
                    border_color=C["warn"] if pinned else C["border"],
                    hover_color=C["accent_bg"], font=ctk.CTkFont(size=11),
                    command=lambda n=name, pn=pinned: self._toggle_pin(n, pn)
                ).pack(side="left", padx=(0, 4))
            ctk.CTkButton(
                bf, text="⬆ Upgrade", width=90, height=28, corner_radius=6,
                fg_color=C["accent"] if not pinned else C["panel2"],
                hover_color=C["accent_h"],
                text_color="#FFFFFF" if not pinned else C["text3"],
                state="normal" if not pinned else "disabled",
                font=ctk.CTkFont(size=11),
                command=lambda n=name, cask=is_cask: self._do_upgrade_one(n, cask)
            ).pack(side="left")

    def _render_upgrades_error(self, msg: str = ""):
        for w in self._upgrades_list.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._upgrades_list, text=f"⚠️  {msg or 'Could not load upgrade data.'}",
                     font=ctk.CTkFont(size=12), text_color=C["err"]
                     ).grid(row=0, column=0, pady=24)

    def _toggle_upgrade(self, name: str, var: tk.BooleanVar):
        if var.get():
            self._upgrade_sel.add(name)
        else:
            self._upgrade_sel.discard(name)
        self._upgrade_sel_btn.configure(
            text=f"⬆  Upgrade Selected  ({len(self._upgrade_sel)})")

    def _toggle_pin(self, name: str, currently_pinned: bool):
        def run():
            cmd = f"brew {'unpin' if currently_pinned else 'pin'} {name}"
            subprocess.run(cmd, shell=True, capture_output=True, env=_BREW_ENV)
            self._outdated_loaded = False
            self.after(0, self._refresh_upgrades)
        threading.Thread(target=run, daemon=True).start()

