"""
Background brew/xcode system probe on startup.

Part of the App class mixin split (v4.0) — see brewcleaner.py's App
class definition for how all these mixins are combined, and
ROADMAP.md for why this split was done as a second, isolated pass
after the v4.0 logic/bugfix pass rather than bundled with it.

This file only contains methods that were already in brewcleaner.py's
App class (v3.1.3/early v4.0) — moved here verbatim, unchanged, under
the "Background brew/xcode system probe on startup." section. No behavior was changed by this move.
"""

import subprocess
from pathlib import Path
from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, PKGS, CASKS, etc.

class ProbeMixin:
    # ══════════════════════════════════════════════════════════
    #  SYSTEM PROBE
    # ══════════════════════════════════════════════════════════

    def _probe(self):
        try:
            # Added env=_BREW_ENV so it has the right PATH
            r = subprocess.run(["brew", "--version"],
                               capture_output=True, text=True, timeout=8, env=_BREW_ENV)
            if r.returncode == 0:
                ver = r.stdout.splitlines()[0].replace("Homebrew", "").strip()
                self._brew_ok = True
                self.after(0, lambda v=ver: self._on_brew_found(v))
            else:
                raise RuntimeError
        except Exception:
            self._brew_ok = False
            self.after(0, self._on_brew_missing)
            self._probe_done.set()
            return
        try:
            r = subprocess.run(["brew","list","--formula"],
                               capture_output=True, text=True, timeout=10, env=_BREW_ENV)
            n = len([x for x in r.stdout.strip().splitlines() if x])
            self.after(0, lambda n=n: self._s_pkgs.configure(
                text=str(n), text_color=C["accent"]))
        except Exception:
            pass
        try:
            cache = Path.home() / "Library" / "Caches" / "Homebrew"
            if cache.exists():
                r = subprocess.run(["du", "-sh", str(cache)],
                                   capture_output=True, text=True, timeout=8)
                sz = r.stdout.split()[0]
                self.after(0, lambda s=sz: self._s_cache.configure(
                    text=s, text_color=C["warn"]))
        except Exception:
            pass

        # ── Xcode / CLT check ────────────────────────────────
        try:
            clt_ok  = _clt_installed()
            xapp_ok = _xcode_app_installed()
            if not clt_ok:
                mac_maj, mac_min = _get_macos_version()
                xver, dl         = _get_recommended_xcode(mac_maj, mac_min)
                self.after(0, lambda v=xver, u=dl, a=xapp_ok:
                           self._show_xcode_banner(v, u, a))
            else:
                self.after(0, self._hide_xcode_banner)
        except Exception:
            pass

        # Signal splash that real work is done
        self._probe_done.set()

    def _on_brew_found(self, ver: str):
        if not self._s_brew.winfo_exists():
            return
        self._brew_lbl.configure(text=f"v{ver}", text_color=C["ok"])
        self._s_brew.configure(text="Installed", text_color=C["ok"])
        self._brew_missing_banner.pack_forget()
        for b in self._quick_btns:
            if b.winfo_exists():
                b.configure(state="normal", text_color=C["accent"], fg_color=C["panel"])

    def _on_brew_missing(self):
        if not self._s_brew.winfo_exists():
            return
        self._brew_lbl.configure(text="Not installed", text_color=C["err"])
        self._s_brew.configure(text="Missing", text_color=C["err"])
        self._s_pkgs.configure(text="—",  text_color=C["text3"])
        self._s_cache.configure(text="—", text_color=C["text3"])
        self._s_out.configure(text="—",   text_color=C["text3"])
        self._brew_missing_banner.pack(fill="x", pady=(10, 0), after=self._stat_cf)
        for b in self._quick_btns:
            if b.winfo_exists():
                b.configure(state="disabled", text_color=C["text3"], fg_color=C["panel2"])

    def _show_xcode_banner(self, xcode_ver: str = "", dl_url: str = "",
                           full_xcode: bool = False):
        """Show the Xcode CLT warning banner with version-specific text."""
        if not self._xcode_banner.winfo_exists():
            return
        if not xcode_ver:
            g = _xcode_install_guidance()
            xcode_ver = g["xcode_name"]
        mac_major, mac_minor = _get_macos_version()
        mac_str = f"{mac_major}.{mac_minor}"
        desc = (
            f"Homebrew needs Xcode Command Line Tools to compile packages.\n"
            f"Your macOS {mac_str} is compatible with Xcode {xcode_ver}."
        )
        if full_xcode:
            desc += "\n(Full Xcode.app found — CLT should work; run  xcode-select --install  if brew fails.)"
        try:
            self._xcode_banner_desc.configure(text=desc)
        except Exception:
            pass
        self._xcode_banner.pack(fill="x", pady=(6, 0), after=self._stat_cf)

    def _hide_xcode_banner(self):
        """Hide the Xcode CLT warning banner."""
        try:
            self._xcode_banner.pack_forget()
        except Exception:
            pass

