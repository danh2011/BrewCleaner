"""
Packages page (formulae + casks).

Part of the App class mixin split (v4.0) — see brewcleaner.py's App
class definition for how all these mixins are combined, and
ROADMAP.md for why this split was done as a second, isolated pass
after the v4.0 logic/bugfix pass rather than bundled with it.

This file only contains methods that were already in brewcleaner.py's
App class (v3.1.3/early v4.0) — moved here verbatim, unchanged, under
the "Packages page (formulae + casks)." section. No behavior was changed by this move.
"""

import subprocess
import threading
from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, PKGS, CASKS, etc.

class PackagesMixin:
    # ══════════════════════════════════════════════════════════
    #  PAGE — PACKAGES  (formulae + casks)
    # ══════════════════════════════════════════════════════════

    def _pg_pkgs(self):
        p = ctk.CTkFrame(self._cf, fg_color="transparent")
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(3, weight=1)

        hdr = ctk.CTkFrame(p, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ctk.CTkLabel(hdr, text="Package Store",
                     font=ctk.CTkFont(family=_SF, size=26, weight="bold"),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(hdr, text="Curated formulae & casks + live Homebrew search  —  conflicts flagged before install.",
                     font=ctk.CTkFont(size=12), text_color=C["text2"]).pack(anchor="w", pady=(2, 0))

        # Tab row
        tab_row = ctk.CTkFrame(p, fg_color="transparent")
        tab_row.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        self._tab_formula_btn = ctk.CTkButton(
            tab_row, text="📦  Formulae",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=C["accent"], hover_color=C["accent_h"],
            text_color="#FFFFFF", height=34, width=140, corner_radius=8,
            command=lambda: self._set_pkg_tab("formulae"))
        self._tab_formula_btn.pack(side="left", padx=(0, 4))
        self._tab_cask_btn = ctk.CTkButton(
            tab_row, text="📱  Casks (Apps)",
            font=ctk.CTkFont(size=12),
            fg_color=C["panel"], hover_color=C["accent_bg"],
            text_color=C["text2"], border_width=1, border_color=C["border"],
            height=34, width=140, corner_radius=8,
            command=lambda: self._set_pkg_tab("casks"))
        self._tab_cask_btn.pack(side="left", padx=(0, 8))
        leg = ctk.CTkFrame(tab_row, fg_color="transparent")
        leg.pack(side="right")
        for bg, fg, lbl in [(C["bi"],C["bit"],"✓ Installed"),
                            (C["bo"],C["bot"],"↑ Update"),
                            (C["bn"],C["bnt"],"· Not installed")]:
            ctk.CTkLabel(leg, text=lbl, font=ctk.CTkFont(size=9),
                         fg_color=bg, text_color=fg,
                         corner_radius=4, padx=5, pady=2).pack(side="left", padx=2)

        # Toolbar
        toolbar = ctk.CTkFrame(p, fg_color="transparent")
        toolbar.grid(row=2, column=0, sticky="ew", pady=(0, 4))
        toolbar.grid_columnconfigure(0, weight=1)
        self._sq = tk.StringVar()
        self._sq.trace("w", self._on_search)
        ctk.CTkEntry(toolbar,
                     placeholder_text="🔍  Search packages — live Homebrew search after 600 ms…",
                     textvariable=self._sq,
                     font=ctk.CTkFont(size=13), height=40, corner_radius=10,
                     fg_color=C["panel"], border_color=C["border"],
                     text_color=C["text"]).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._inst_btn = ctk.CTkButton(
            toolbar, text="Install  (0)",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=C["accent"], hover_color=C["accent_h"],
            height=40, width=148, corner_radius=10,
            command=self._do_install)
        self._inst_btn.grid(row=0, column=1)

        self._refresh_pkgs_btn = ctk.CTkButton(
            toolbar, text="↻  Refresh",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=C["panel"], hover_color=C["accent_bg"],
            text_color=C["text2"], border_width=1, border_color=C["border"],
            height=40, width=100, corner_radius=10,
            command=self._refresh_pkgs_action)
        self._refresh_pkgs_btn.grid(row=0, column=2, padx=(8, 0))

        self._ps = ctk.CTkScrollableFrame(p, fg_color="transparent",
                                          scrollbar_button_color=C["border"])
        self._ps.grid(row=3, column=0, sticky="nsew", pady=(8,0))
        for i in range(3):
            self._ps.grid_columnconfigure(i, weight=1)
        self._refresh_grid()
        self._pages["pkgs"] = p

    def _set_pkg_tab(self, tab: str):
        self._pkg_tab = tab
        if tab == "formulae":
            self._tab_formula_btn.configure(fg_color=C["accent"], text_color="#FFFFFF")
            self._tab_cask_btn.configure(fg_color=C["panel"], text_color=C["text2"])
        else:
            self._tab_cask_btn.configure(fg_color=C["accent"], text_color="#FFFFFF")
            self._tab_formula_btn.configure(fg_color=C["panel"], text_color=C["text2"])
        self._brew_results = []
        self._refresh_grid()

    def _on_search(self, *_):
        if self._search_job:
            self.after_cancel(self._search_job)
        q = self._sq.get().strip()
        self._brew_results = []
        self._refresh_grid()
        if len(q) >= 2:
            self._search_job = self.after(
                600, lambda: threading.Thread(
                    target=self._live_brew_search, args=(q,), daemon=True).start())

    def _refresh_pkgs_action(self):
        self._set_search_status("↻  Refreshing package states…")
        self._pkg_state_loaded = True
        threading.Thread(target=self._load_pkg_state, daemon=True).start()

    def _live_brew_search(self, q: str):
        self.after(0, lambda: self._set_search_status("🔎  Searching Homebrew…"))
        try:
            flag = "--formula" if self._pkg_tab == "formulae" else "--cask"
            r = subprocess.run(["brew", "search", flag, q],
                               capture_output=True, text=True, timeout=25)
            catalogue = PKGS if self._pkg_tab == "formulae" else CASKS
            all_ids: set = {pk["id"] for pks in catalogue.values() for pk in pks}
            all_ids |= {pk["id"] for pk in self._custom_pkgs}
            results = [
                {"id": i, "label": i,
                 "desc": "Homebrew formula" if self._pkg_tab == "formulae" else "Homebrew cask",
                 "icon": "📦", "conflicts": []}
                for i in r.stdout.strip().splitlines()
                if i.strip() and i.strip() not in all_ids
            ][:24]
            self._brew_results = results
            self.after(0, lambda: (self._set_search_status(None), self._refresh_grid()))
        except Exception:
            self.after(0, lambda: self._set_search_status("⚠️  brew search unavailable"))

    def _set_search_status(self, msg: Optional[str]):
        if self._search_status and self._search_status.winfo_exists():
            self._search_status.destroy()
            self._search_status = None
        if msg:
            self._search_status = ctk.CTkLabel(
                self._ps, text=msg, font=ctk.CTkFont(size=12),
                text_color=C["text2"], fg_color="transparent", anchor="w")
            self._search_status.grid(row=0, column=0, columnspan=3,
                                     sticky="w", padx=6, pady=(6, 2))

    def _refresh_grid(self):
        q = self._sq.get().lower().strip()
        for w in self._ps.winfo_children():
            w.destroy()
        self._search_status = None
        for i in range(3):
            self._ps.grid_columnconfigure(i, weight=1)

        grid_row = 1
        catalogue = list((PKGS if self._pkg_tab == "formulae" else CASKS).items())
        if self._pkg_tab == "formulae" and self._custom_pkgs:
            catalogue.append(("Custom", self._custom_pkgs))
        if self._brew_results and q:
            catalogue.append(("🍺  Homebrew Results", self._brew_results))

        for cat, pkgs in catalogue:
            vis = [pk for pk in pkgs
                   if not q or q in pk["id"]
                   or q in pk["label"].lower()
                   or q in pk["desc"].lower()]
            if not vis:
                continue
            ctk.CTkLabel(self._ps, text=cat,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=C["text2"]).grid(
                row=grid_row, column=0, columnspan=3,
                sticky="w", padx=4, pady=(14, 4))
            grid_row += 1
            for j, pk in enumerate(vis):
                col = j % 3
                if col == 0:
                    pkg_row = grid_row
                    grid_row += 1
                self._pkg_card(pk, pkg_row, col)

        if q and len(q) >= 2 and self._pkg_tab == "formulae":
            hint = ctk.CTkFrame(self._ps, fg_color=C["accent_bg"],
                                corner_radius=10, border_width=1, border_color=C["accent"])
            hint.grid(row=grid_row, column=0, columnspan=3, sticky="ew", padx=4, pady=10)
            ctk.CTkLabel(hint, text=f"➕  Add \"{q}\" to your install list",
                         font=ctk.CTkFont(size=12),
                         text_color=C["accent"]).pack(side="left", padx=14, pady=10)
            ctk.CTkButton(hint, text="Add",
                          fg_color=C["accent"], hover_color=C["accent_h"],
                          width=72, height=30, corner_radius=8,
                          command=lambda q=q: self._add_custom(q)).pack(side="right", padx=14)

    def _pkg_card(self, pkg: Dict, row: int, col: int):
        pid       = pkg["id"]
        is_cask   = self._pkg_tab == "casks"
        vars_dict = self._cask_vars if is_cask else self._pkg_vars
        sel_set   = self._cask_sel  if is_cask else self._selected
        inst_set  = self._cask_installed if is_cask else self._installed_set
        outd_set  = self._cask_outdated  if is_cask else self._outdated_set

        if pid not in vars_dict:
            vars_dict[pid] = tk.BooleanVar(value=pid in sel_set)
        var = vars_dict[pid]

        base_id = pid.split("@")[0]
        if pid in outd_set or base_id in outd_set:
            bb, bt, bl = C["bo"], C["bot"], "↑ Update"
        elif pid in inst_set or base_id in inst_set:
            bb, bt, bl = C["bi"], C["bit"], "✓ Installed"
        else:
            bb, bt, bl = C["bn"], C["bnt"], "· Not installed"

        card = ctk.CTkFrame(self._ps, fg_color=C["panel"], corner_radius=10,
                            border_width=1,
                            border_color=C["accent"] if var.get() else C["border"])
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", padx=12, pady=10)

        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=pkg["icon"], font=ctk.CTkFont(size=20),
                     fg_color="transparent").pack(side="left")
        ctk.CTkLabel(top, text=bl, font=ctk.CTkFont(size=9),
                     fg_color=bb, text_color=bt,
                     corner_radius=4, padx=5, pady=1).pack(side="right")
        ctk.CTkLabel(inner, text=pkg["label"],
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C["text"], anchor="w").pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(inner, text=pkg["desc"],
                     font=ctk.CTkFont(size=10), text_color=C["text2"],
                     anchor="w", wraplength=160).pack(fill="x")
        ctk.CTkCheckBox(inner, text="Select", variable=var,
                        font=ctk.CTkFont(size=10),
                        fg_color=C["accent"], hover_color=C["accent_h"],
                        border_color=C["border"],
                        command=lambda p=pid, v=var, c=card: self._toggle_pkg(p, v, c)
                        ).pack(anchor="w", pady=(8, 0))

    def _toggle_pkg(self, pid: str, var: tk.BooleanVar, card: ctk.CTkFrame):
        is_cask = self._pkg_tab == "casks"
        sel_set = self._cask_sel if is_cask else self._selected
        if var.get():
            sel_set.add(pid)
            card.configure(border_color=C["accent"])
        else:
            sel_set.discard(pid)
            card.configure(border_color=C["border"])
        total = len(self._selected) + len(self._cask_sel)
        self._inst_btn.configure(text=f"Install  ({total})")

    def _add_custom(self, name: str):
        all_ids = {pk["id"] for pks in PKGS.values() for pk in pks}
        all_ids |= {pk["id"] for pk in self._custom_pkgs}
        if name not in all_ids:
            self._custom_pkgs.append({"id": name, "label": name,
                                      "desc": "Custom Homebrew formula",
                                      "icon": "📦", "conflicts": []})
        self._sq.set("")

    def _load_pkg_state(self):
        try:
            # Timeouts increased to allow slow Macs or heavy Homebrew setups to respond
            r1 = subprocess.run(["brew","list","--formula"], capture_output=True, text=True, timeout=45, env=_BREW_ENV)
            r2 = subprocess.run(["brew","outdated","--quiet"], capture_output=True, text=True, timeout=60, env=_BREW_ENV)
            r3 = subprocess.run(["brew","list","--cask"], capture_output=True, text=True, timeout=45, env=_BREW_ENV)
            r4 = subprocess.run(["brew","outdated","--cask","--quiet"], capture_output=True, text=True, timeout=60, env=_BREW_ENV)
            
            self._installed_set  = set(r1.stdout.strip().split())
            self._outdated_set   = set(r2.stdout.strip().split())
            self._cask_installed = set(r3.stdout.strip().split())
            self._cask_outdated  = set(r4.stdout.strip().split())
            
            n_out = len(self._outdated_set) + len(self._cask_outdated)
            self.after(0, lambda: (
                self._s_out.configure(text=str(n_out),
                                     text_color=C["warn"] if n_out else C["ok"]),
                self._refresh_grid()))
        except subprocess.TimeoutExpired as e:
            print(f"BrewCleaner background load timed out: {e}")
        except Exception as e:
            print(f"BrewCleaner background load error: {e}")
    # (_show_full_tree used to be defined right here too, out of place —
    # moved down next to _show_deps/_show_uses where it belongs, see below)


