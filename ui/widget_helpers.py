"""
Small shared widget-building helpers.

Part of the App class mixin split (v4.0) — see brewcleaner.py's App
class definition for how all these mixins are combined, and
ROADMAP.md for why this split was done as a second, isolated pass
after the v4.0 logic/bugfix pass rather than bundled with it.

This file only contains methods that were already in brewcleaner.py's
App class (v3.1.3/early v4.0) — moved here verbatim, unchanged, under
the "Small shared widget-building helpers." section. No behavior was changed by this move.
"""

from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, PKGS, CASKS, etc.

class WidgetHelpersMixin:
    # ══════════════════════════════════════════════════════════
    #  SHARED WIDGET HELPERS
    # ══════════════════════════════════════════════════════════

    def _section_hdr(self, parent, title: str, sub: str = ""):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", pady=(0, 20), padx=8)
        ctk.CTkLabel(f, text=title,
                     font=ctk.CTkFont(family=_SF, size=26, weight="bold"),
                     text_color=C["text"]).pack(anchor="w")
        if sub:
            ctk.CTkLabel(f, text=sub, font=ctk.CTkFont(size=12),
                         text_color=C["text2"]).pack(anchor="w", pady=(3, 0))

    def _mini_hdr(self, parent, text: str):
        ctk.CTkLabel(parent, text=text,
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=C["text2"]).pack(anchor="w", pady=(14, 4))

    def _stat_card(self, parent, icon: str, title: str, val: str,
                   col: int) -> ctk.CTkLabel:
        f = ctk.CTkFrame(parent, fg_color=C["panel"], corner_radius=12,
                         border_width=1, border_color=C["border"])
        f.grid(row=0, column=col, padx=4, sticky="nsew")
        ctk.CTkLabel(f, text=icon, font=ctk.CTkFont(size=24),
                     fg_color="transparent").pack(pady=(16, 4))
        lbl = ctk.CTkLabel(f, text=val,
                           font=ctk.CTkFont(size=20, weight="bold"),
                           text_color=C["text3"], fg_color="transparent")
        lbl.pack()
        ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=11),
                     text_color=C["text2"], fg_color="transparent").pack(pady=(2, 16))
        return lbl

    def _mk_term(self, parent, height: int = 160) -> ctk.CTkTextbox:
        return ctk.CTkTextbox(
            parent, height=height,
            fg_color=C["tbg"], text_color=C["tfg"],
            font=ctk.CTkFont(family=_MNO, size=11),
            corner_radius=10, state="disabled",
            scrollbar_button_color="#2E2E4E")

    def _tw(self, tb: ctk.CTkTextbox, text: str):
        tb.configure(state="normal")
        tb.insert("end", text)
        tb.see("end")
        tb.configure(state="disabled")

    def _fmt_sz(self, b: int) -> str:
        for unit in ("B","KB","MB","GB","TB"):
            if b < 1024:
                return f"{b:.1f} {unit}"
            b /= 1024
        return f"{b:.1f} PB"


