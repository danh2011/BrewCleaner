"""
Settings page.

Part of the App class mixin split (v4.0) — see brewcleaner.py's App
class definition for how all these mixins are combined, and
ROADMAP.md for why this split was done as a second, isolated pass
after the v4.0 logic/bugfix pass rather than bundled with it.

This file only contains methods that were already in brewcleaner.py's
App class (v3.1.3/early v4.0) — moved here verbatim, unchanged, under
the "Settings page." section. No behavior was changed by this move.
"""

import subprocess
from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, PKGS, CASKS, etc.

class SettingsMixin:
    # ══════════════════════════════════════════════════════════
    #  PAGE — SETTINGS
    # ══════════════════════════════════════════════════════════

    def _pg_settings(self):
        p = ctk.CTkScrollableFrame(self._cf, fg_color="transparent",
                                   scrollbar_button_color=C["border"])
        self._section_hdr(p, "Settings")

        # Appearance
        opt_frame = ctk.CTkFrame(p, fg_color="transparent")
        opt_frame.pack(fill="x", padx=8)
        self._mini_hdr(opt_frame, "Appearance")
        theme_row = ctk.CTkFrame(opt_frame, fg_color=C["panel"], corner_radius=10,
                                 border_width=1, border_color=C["border"])
        theme_row.pack(fill="x", pady=4)
        lf = ctk.CTkFrame(theme_row, fg_color="transparent")
        lf.pack(side="left", fill="x", expand=True, padx=16, pady=14)
        ctk.CTkLabel(lf, text="🌙  Theme Mode",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=C["text"], anchor="w").pack(fill="x")
        ctk.CTkLabel(lf, text="Switch the app interface appearance",
                     font=ctk.CTkFont(size=11), text_color=C["text2"],
                     anchor="w").pack(fill="x")
                     
        self._theme_opt = ctk.CTkOptionMenu(
            theme_row,
            values=["System", "Light", "Dark"],
            fg_color=C["accent_bg"],
            button_color=C["accent"],
            button_hover_color=C["accent_h"],
            text_color=C["accent"],
            dropdown_fg_color=C["panel"],
            dropdown_text_color=C["text"],
            dropdown_hover_color=C["accent_bg"],
            command=self._change_theme
        )
        self._theme_opt.pack(side="right", padx=20)
        self._theme_opt.set(self._prefs.get("theme", "system").capitalize())

        # Behaviour
        self._mini_hdr(opt_frame, "Behaviour")
        for key, title, desc in [
            ("notifications", "🔔  Notifications",
             "Send a macOS notification when operations complete"),
            ("auto_refresh",  "↻  Auto-refresh on launch",
             "Re-check brew status every time BrewCleaner opens"),
        ]:
            var = tk.BooleanVar(value=self._prefs.get(key, True))
            r = ctk.CTkFrame(opt_frame, fg_color=C["panel"], corner_radius=10,
                             border_width=1, border_color=C["border"])
            r.pack(fill="x", pady=4)
            lf2 = ctk.CTkFrame(r, fg_color="transparent")
            lf2.pack(side="left", fill="x", expand=True, padx=16, pady=14)
            ctk.CTkLabel(lf2, text=title,
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=C["text"], anchor="w").pack(fill="x")
            ctk.CTkLabel(lf2, text=desc,
                         font=ctk.CTkFont(size=11), text_color=C["text2"],
                         anchor="w").pack(fill="x")
            ctk.CTkSwitch(r, text="", variable=var,
                          fg_color=C["border"], progress_color=C["accent"],
                          command=lambda k=key, v=var: self._save_setting(k, v.get())
                          ).pack(side="right", padx=20)

        # About
        self._mini_hdr(opt_frame, "About")
        ab = ctk.CTkFrame(opt_frame, fg_color=C["panel"], corner_radius=10,
                          border_width=1, border_color=C["border"])
        ab.pack(fill="x", pady=4)
        inn = ctk.CTkFrame(ab, fg_color="transparent")
        inn.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(inn, text=f"🍺  BrewCleaner  v{APP_VERSION}",
                     font=ctk.CTkFont(family=_SF, size=18, weight="bold"),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(inn,
                     text="The complete Homebrew manager for macOS.\n"
                          "Single Python file · open source · macOS 10.15+",
                     font=ctk.CTkFont(size=12), text_color=C["text2"],
                     justify="left").pack(anchor="w", pady=(6, 14))
        btn_row = ctk.CTkFrame(inn, fg_color="transparent")
        btn_row.pack(anchor="w")
        ctk.CTkButton(btn_row, text="⭐  Star on GitHub",
                      fg_color=C["accent_bg"], text_color=C["accent"],
                      hover_color=C["accent_bg"], border_width=1,
                      border_color=C["accent"], height=36, corner_radius=8,
                      font=ctk.CTkFont(size=12),
                      command=lambda: subprocess.Popen(["open", GITHUB_URL])
                      ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="📜  View TOS",
                      fg_color=C["panel"], text_color=C["text2"],
                      hover_color=C["accent_bg"], border_width=1,
                      border_color=C["border"], height=36, corner_radius=8,
                      font=ctk.CTkFont(size=12),
                      command=self._show_tos).pack(side="left")
        self._pages["settings"] = p

    def _show_tos(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Terms of Use")
        dlg.geometry("520x340")
        dlg.configure(fg_color=C["bg"])
        dlg.grab_set()
        dlg.resizable(False, False)
        dlg.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()  - 520) // 2
        y = self.winfo_y() + (self.winfo_height() - 340) // 2
        dlg.geometry(f"+{x}+{y}")
        ctk.CTkLabel(dlg, text="🍺  BrewCleaner  Terms of Use",
                     font=ctk.CTkFont(family=_SF, size=16, weight="bold"),
                     text_color=C["text"]).pack(pady=(22, 10))
        for line in TOS_LINES:
            fg = C["accent"] if line.startswith("     ") else (
                 C["text"] if line.endswith(":") else C["text2"])
            ctk.CTkLabel(dlg, text=line, font=ctk.CTkFont(size=12),
                         text_color=fg, anchor="w").pack(anchor="w", padx=40, pady=1)
        ctk.CTkButton(dlg, text="Close", height=36, corner_radius=8,
                      fg_color=C["accent"], hover_color=C["accent_h"],
                      command=dlg.destroy).pack(pady=(22, 0))

    def _change_theme(self, selection: str):
        if self._task_running:
            messagebox.showwarning("Task in Progress", "Cannot switch themes while a task is running.")
            self._theme_opt.set(self._prefs.get("theme", "system").capitalize())
            return
            
        new_theme = selection.lower()
        self._prefs["theme"] = new_theme
        _save_prefs(self._prefs)
        
        # Re-resolve colors and mode
        if new_theme == "system":
            ctk.set_appearance_mode("System")
            actual_mode = ctk.get_appearance_mode()
            C.update(_DARK if actual_mode == "Dark" else _LIGHT)
        else:
            ctk.set_appearance_mode(selection)
            C.update(_DARK if new_theme == "dark" else _LIGHT)
            
        # Rebuild UI
        page             = self._page
        selected         = set(self._selected)
        cask_sel         = set(self._cask_sel)
        custom_pkgs      = list(self._custom_pkgs)
        installed_set    = set(self._installed_set)
        outdated_set     = set(self._outdated_set)
        pkg_state_loaded = self._pkg_state_loaded
        
        for w in self.winfo_children():
            w.destroy()
            
        self._pages = {}
        self._build()
        
        self._selected         = selected
        self._cask_sel         = cask_sel
        self._custom_pkgs      = custom_pkgs
        self._installed_set    = installed_set
        self._outdated_set     = outdated_set
        self._pkg_state_loaded = pkg_state_loaded
        self._goto(page)

    def _save_setting(self, key: str, val):
        self._prefs[key] = val
        _save_prefs(self._prefs)

