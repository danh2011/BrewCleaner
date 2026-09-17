"""
Dashboard/home page.

Part of the App class mixin split (v4.0) — see brewcleaner.py's App
class definition for how all these mixins are combined, and
ROADMAP.md for why this split was done as a second, isolated pass
after the v4.0 logic/bugfix pass rather than bundled with it.

This file only contains methods that were already in brewcleaner.py's
App class (v3.1.3/early v4.0) — moved here verbatim, unchanged, under
the "Dashboard/home page." section. No behavior was changed by this move.
"""

import subprocess
from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, PKGS, CASKS, etc.

class DashboardMixin:
    # ══════════════════════════════════════════════════════════
    #  PAGE — DASHBOARD
    # ══════════════════════════════════════════════════════════

    def _pg_home(self):
        p = ctk.CTkScrollableFrame(self._cf, fg_color="transparent",
                                   scrollbar_button_color=C["border"])
        self._section_hdr(p, "Dashboard", "Homebrew overview & quick actions")

        self._stat_cf = ctk.CTkFrame(p, fg_color="transparent")
        self._stat_cf.pack(fill="x", padx=8)
        for i in range(4):
            self._stat_cf.grid_columnconfigure(i, weight=1)
        self._s_brew  = self._stat_card(self._stat_cf, "🍺", "Homebrew",  "…", 0)
        self._s_pkgs  = self._stat_card(self._stat_cf, "📦", "Installed", "…", 1)
        self._s_cache = self._stat_card(self._stat_cf, "💾", "Cache",     "…", 2)
        self._s_out   = self._stat_card(self._stat_cf, "↑",  "Outdated",  "…", 3)

        self._brew_missing_banner = ctk.CTkFrame(
            p, fg_color="#FFF1F1", corner_radius=10,
            border_width=1, border_color="#FCA5A5")
        inner_b = ctk.CTkFrame(self._brew_missing_banner, fg_color="transparent")
        inner_b.pack(fill="x", padx=16, pady=14)
        ctk.CTkLabel(inner_b, text="🍺  Homebrew is not installed",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=C["err"]).pack(anchor="w")
        ctk.CTkLabel(inner_b,
                     text="Homebrew is the missing package manager for macOS. "
                          "Install it to use all BrewCleaner features.",
                     font=ctk.CTkFont(size=11), text_color=C["text2"],
                     wraplength=650, justify="left").pack(anchor="w", pady=(4, 10))
        ctk.CTkButton(inner_b, text="⬇  Install Homebrew",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      fg_color=C["accent"], hover_color=C["accent_h"],
                      height=38, corner_radius=8,
                      command=self._do_install_brew_fresh).pack(anchor="w")
        self._brew_missing_banner.pack_forget()

        # ── Xcode / CLT warning banner (hidden until probe confirms CLT missing) ──
        self._xcode_banner = ctk.CTkFrame(
            p, fg_color="#FFF8E1", corner_radius=10,
            border_width=1, border_color="#FFD54F")
        inner_x = ctk.CTkFrame(self._xcode_banner, fg_color="transparent")
        inner_x.pack(fill="x", padx=16, pady=14)
        ctk.CTkLabel(inner_x,
                     text="🛠️  Xcode Command Line Tools are not installed",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#7B5800").pack(anchor="w")
        self._xcode_banner_desc = ctk.CTkLabel(
            inner_x,
            text="Checking your macOS version for the compatible Xcode CLT…",
            font=ctk.CTkFont(size=11), text_color="#7B5800",
            wraplength=680, justify="left")
        self._xcode_banner_desc.pack(anchor="w", pady=(4, 10))
        xbf = ctk.CTkFrame(inner_x, fg_color="transparent")
        xbf.pack(anchor="w")
        self._xcode_install_btn = ctk.CTkButton(
            xbf, text="⬇  Install Command Line Tools",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#F59E0B", hover_color="#D97706",
            text_color="#FFFFFF", height=38, corner_radius=8,
            command=self._do_install_clt)
        self._xcode_install_btn.pack(side="left", padx=(0, 8))
        ctk.CTkButton(xbf, text="📥  Apple Developer Downloads",
                      font=ctk.CTkFont(size=11),
                      fg_color="transparent", text_color="#854D0E",
                      hover_color="#FEF3C7", height=38, corner_radius=8,
                      command=lambda: subprocess.Popen(
                          ["open", "https://developer.apple.com/download/all/"])
                      ).pack(side="left")
        self._xcode_banner.pack_forget()
        qf = ctk.CTkFrame(p, fg_color="transparent")
        qf.pack(fill="x", pady=(0, 22), padx=8)
        for i in range(4):
            qf.grid_columnconfigure(i, weight=1)
        self._quick_btns: List[ctk.CTkButton] = []
        for i, (lbl, cmd) in enumerate([
            ("🗑️  Clean Cache", "brew cleanup --prune=all"),
            ("🔄  Update Brew",  "brew update"),
            ("⬆️  Upgrade All",  "brew upgrade"),
            ("🩺  Doctor",       "brew doctor"),
        ]):
            b = ctk.CTkButton(
                qf, text=lbl, font=ctk.CTkFont(size=12),
                fg_color=C["panel"], text_color=C["accent"],
                hover_color=C["accent_bg"],
                border_width=1, border_color=C["border"],
                corner_radius=10, height=44,
                command=lambda c=cmd: self._quick(c))
            b.grid(row=0, column=i, padx=4, sticky="ew")
            self._quick_btns.append(b)

        out_frame = ctk.CTkFrame(p, fg_color="transparent")
        out_frame.pack(fill="x", padx=8)
        self._mini_hdr(out_frame, "Output")
        self._home_term = self._mk_term(out_frame, 200)
        self._home_term.pack(fill="x")
        self._tw(self._home_term, "Ready. Use quick actions above or the sidebar.\n")
        self._pages["home"] = p

    # NOTE: _show_xcode_banner and _hide_xcode_banner used to be defined
    # here a second time (v3.1.3) — since they're defined again later in
    # this class with more complete logic, the earlier copies were dead
    # code (Python silently keeps only the last definition of a method).
    # Removed in v4.0; see the real definitions further down.

    def _do_install_clt(self):
        """Trigger Xcode Command Line Tools install appropriate for user's macOS."""
        guidance = _xcode_install_guidance()
        major    = guidance["major"]
        if major >= 13:
            # Modern macOS: xcode-select --install opens the system dialog
            msg = (f"This will run:\n\n    xcode-select --install\n\n"
                   f"A system dialog will appear to install Xcode {guidance['xcode_name']} "
                   f"for macOS {guidance['macos_name']}.\n\n"
                   "Return to BrewCleaner once installation completes.")
            if messagebox.askyesno("Install Command Line Tools", msg, icon="info"):
                subprocess.Popen(["xcode-select", "--install"])
                messagebox.showinfo(
                    "Installation Started",
                    "Follow the system dialog to complete the install.\n"
                    "BrewCleaner will re-check CLT status on next launch.")
        else:
            # Older macOS: must download manually from Apple Developer
            msg = (f"Your Mac (macOS {major}.x) requires Xcode {guidance['xcode_name']}.\n\n"
                   "Apple only provides older Command Line Tools via download.\n\n"
                   "1.  Open developer.apple.com/download/all/\n"
                   "2.  Sign in with a free Apple ID\n"
                   "3.  Search for  'Command Line Tools'\n"
                   "4.  Download the version compatible with your macOS\n\n"
                   "Would you like to open the download page now?")
            if messagebox.askyesno("Download Command Line Tools", msg, icon="info"):
                subprocess.Popen(["open", "https://developer.apple.com/download/all/"])

    def _do_install_brew_fresh(self):
        if not messagebox.askyesno(
                "Install Homebrew",
                "This will download and run the official Homebrew install script.\n\n"
                "Your administrator password will be required once.", icon="info"):
            return
        if not self._acquire_sudo():
            return
        self._run_steps("Installing Homebrew", "Downloading official install script", [
            ("Install Homebrew",    self._op_install_brew),
            ("Verify installation", lambda: self._sh("brew --version"))])

