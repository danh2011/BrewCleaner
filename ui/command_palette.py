"""
Command palette (⌘K) — new in v4.0.

Scoped deliberately to page navigation only, not arbitrary actions —
see ROADMAP.md. A palette that can fuzzy-match its way into running a
destructive brew command is a much bigger, riskier feature than one
that jumps to a page; this is the safe, self-contained version of
that idea. Extending it to actions later is a natural follow-up.
"""

from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, NAV_ITEMS, etc.


class CommandPaletteMixin:
    # ══════════════════════════════════════════════════════════
    #  COMMAND PALETTE
    # ══════════════════════════════════════════════════════════

    def _open_command_palette(self, event=None):
        # Toggle: if it's already open, close it instead of stacking
        # a second one (e.g. if the shortcut fires twice quickly).
        existing = getattr(self, "_palette_win", None)
        if existing is not None and existing.winfo_exists():
            existing.destroy()
            self._palette_win = None
            return "break"

        win = ctk.CTkToplevel(self)
        self._palette_win = win
        win.title("")
        win.geometry("480x360")
        win.transient(self)
        win.attributes("-topmost", True)
        win.configure(fg_color=C["panel"])
        try:
            win.overrideredirect(False)
        except Exception:
            pass

        # Center over the main window.
        try:
            self.update_idletasks()
            x = self.winfo_x() + (self.winfo_width() - 480) // 2
            y = self.winfo_y() + 100
            win.geometry(f"480x360+{max(x, 0)}+{max(y, 0)}")
        except Exception:
            pass

        entry = ctk.CTkEntry(
            win, placeholder_text="Jump to a page…", font=ctk.CTkFont(size=15),
            height=40, fg_color=C["panel2"], border_color=C["border"],
            text_color=C["text"])
        entry.pack(fill="x", padx=12, pady=(12, 6))
        entry.focus_set()

        results_frame = ctk.CTkScrollableFrame(win, fg_color="transparent")
        results_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        state = {"items": list(NAV_ITEMS), "selected": 0}

        def close(_=None):
            if win.winfo_exists():
                win.destroy()
            self._palette_win = None
            return "break"

        def go(pid):
            close()
            self._goto(pid)

        def render():
            for w in results_frame.winfo_children():
                w.destroy()
            query = entry.get().strip().lower()
            items = [it for it in NAV_ITEMS if query in it[2].lower()] if query else list(NAV_ITEMS)
            state["items"] = items
            state["selected"] = 0 if items else -1
            for i, (pid, icon, label) in enumerate(items):
                row = ctk.CTkButton(
                    results_frame, text=f"  {icon}   {label}",
                    font=ctk.CTkFont(size=13), anchor="w", height=36,
                    fg_color=C["accent_bg"] if i == 0 else "transparent",
                    text_color=C["accent"] if i == 0 else C["text"],
                    hover_color=C["accent_bg"],
                    command=lambda p=pid: go(p))
                row.pack(fill="x", pady=1)

        def move_selection(delta):
            if not state["items"]:
                return
            state["selected"] = (state["selected"] + delta) % len(state["items"])
            render()
            # re-highlight the newly selected row
            children = results_frame.winfo_children()
            for i, child in enumerate(children):
                is_sel = i == state["selected"]
                child.configure(
                    fg_color=C["accent_bg"] if is_sel else "transparent",
                    text_color=C["accent"] if is_sel else C["text"])

        def on_key(e):
            if e.keysym == "Escape":
                return close()
            if e.keysym == "Return":
                if state["items"] and 0 <= state["selected"] < len(state["items"]):
                    go(state["items"][state["selected"]][0])
                return "break"
            if e.keysym == "Down":
                move_selection(1)
                return "break"
            if e.keysym == "Up":
                move_selection(-1)
                return "break"

        entry.bind("<KeyRelease>", lambda e: render() if e.keysym not in
                   ("Escape", "Return", "Down", "Up") else None)
        entry.bind("<Escape>", on_key)
        entry.bind("<Return>", on_key)
        entry.bind("<Down>", on_key)
        entry.bind("<Up>", on_key)
        win.bind("<FocusOut>", lambda e: None)  # deliberately no auto-close on blur

        render()
        return "break"
