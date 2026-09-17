"""
Sudo credential caching/prompting.

Part of the App class mixin split (v4.0) — see brewcleaner.py's App
class definition for how all these mixins are combined, and
ROADMAP.md for why this split was done as a second, isolated pass
after the v4.0 logic/bugfix pass rather than bundled with it.

This file only contains methods that were already in brewcleaner.py's
App class (v3.1.3/early v4.0) — moved here verbatim, unchanged, under
the "Sudo credential caching/prompting." section. No behavior was changed by this move.
"""

import subprocess
import threading
import time
from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, PKGS, CASKS, etc.

class SudoMixin:
    # ══════════════════════════════════════════════════════════
    #  SUDO CREDENTIAL CACHING
    # ══════════════════════════════════════════════════════════

    def _acquire_sudo(self) -> bool:
        if self._sudo_cached:
            return True
        result: List[Optional[bool]] = [None]
        pw_var = tk.StringVar()
        dlg = ctk.CTkToplevel(self)
        dlg.title("Administrator Password")
        dlg.geometry("400x260")
        dlg.configure(fg_color=C["bg"])
        dlg.grab_set()
        dlg.resizable(False, False)
        dlg.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()  - 400) // 2
        y = self.winfo_y() + (self.winfo_height() - 260) // 2
        dlg.geometry(f"+{x}+{y}")
        ctk.CTkLabel(dlg, text="🔐", font=ctk.CTkFont(size=36)).pack(pady=(22, 4))
        ctk.CTkLabel(dlg, text="Administrator Access Required",
                     font=ctk.CTkFont(family=_SF, size=15, weight="bold"),
                     text_color=C["text"]).pack()
        ctk.CTkLabel(dlg,
                     text="Your password is used once to authorise this task.\nIt is never stored.",
                     font=ctk.CTkFont(size=11), text_color=C["text2"],
                     justify="center").pack(pady=(4, 12))
        pw_entry = ctk.CTkEntry(dlg, textvariable=pw_var, show="•",
                                placeholder_text="Password",
                                font=ctk.CTkFont(size=13), height=38,
                                width=320, corner_radius=8,
                                fg_color=C["panel"], border_color=C["border"],
                                text_color=C["text"])
        pw_entry.pack()
        pw_entry.focus_set()
        err_lbl = ctk.CTkLabel(dlg, text="", font=ctk.CTkFont(size=11),
                               text_color=C["err"])
        err_lbl.pack(pady=(4, 0))

        def attempt():
            pw = pw_var.get()
            if not pw:
                return
            try:
                r = subprocess.run(
                    ["sudo", "-S", "-v", "-p", ""],
                    input=pw + "\n", text=True,
                    capture_output=True, timeout=10)
                if r.returncode == 0:
                    self._sudo_cached = True
                    pw_var.set("")
                    result[0] = True
                    dlg.destroy()
                    threading.Thread(target=self._sudo_keepalive, daemon=True).start()
                else:
                    err_lbl.configure(text="Incorrect password — try again.")
                    pw_var.set("")
                    pw_entry.focus_set()
            except Exception as exc:
                err_lbl.configure(text=f"Error: {exc}")

        ctk.CTkButton(dlg, text="Authorise",
                      font=ctk.CTkFont(size=13, weight="bold"),
                      fg_color=C["accent"], hover_color=C["accent_h"],
                      height=38, width=320, corner_radius=8,
                      command=attempt).pack(pady=(10, 4))
        ctk.CTkButton(dlg, text="Cancel",
                      fg_color="transparent", text_color=C["text2"],
                      hover_color=C["border"], width=320, height=34,
                      command=lambda: [setattr(result, '__setitem__',
                                               lambda i, v: None), dlg.destroy()]
                      ).pack()
        pw_entry.bind("<Return>", lambda _: attempt())
        self.wait_window(dlg)
        return bool(result[0])

    def _sudo_keepalive(self):
        while self._task_running or self._sudo_cached:
            time.sleep(50)
            if not self._sudo_cached:
                break
            try:
                subprocess.run(["sudo", "-n", "-v"], capture_output=True, timeout=5)
            except Exception:
                pass

    def _sh_sudo(self, cmd: str):
        full = f"sudo -n {cmd}"
        self.after(0, lambda: self._tw(self._pr_term, f"\n$ {full}\n"))
        try:
            proc = subprocess.Popen(full, shell=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True)
            for line in iter(proc.stdout.readline, ""):
                self.after(0, lambda l=line: self._tw(self._pr_term, l))
            proc.wait()
        except Exception as exc:
            self.after(0, lambda e=exc: self._tw(self._pr_term, f"  ❌  {e}\n"))

