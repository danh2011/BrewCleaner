"""
Generic multi-step task runner + blocking shell helper.

Part of the App class mixin split (v4.0) — see brewcleaner.py's App
class definition for how all these mixins are combined, and
ROADMAP.md for why this split was done as a second, isolated pass
after the v4.0 logic/bugfix pass rather than bundled with it.

This file only contains methods that were already in brewcleaner.py's
App class (v3.1.3/early v4.0) — moved here verbatim, unchanged, under
the "Generic multi-step task runner + blocking shell helper." section. No behavior was changed by this move.
"""

import subprocess
import threading
from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, PKGS, CASKS, etc.

class StepRunnerMixin:
    # ══════════════════════════════════════════════════════════
    #  STEP RUNNER
    # ══════════════════════════════════════════════════════════

    def _run_steps(self, title: str, sub: str, steps: List[Tuple[str, Callable]]):
        self._task_running   = True
        self._task_title_str = title
        self._task_had_error = False  # v4.0: tracked for the completion notification
        self._pr_title.configure(text=title)
        self._pr_sub.configure(text=sub)
        self._pr_term.configure(state="normal")
        self._pr_term.delete("1.0", "end")
        self._pr_term.configure(state="disabled")
        for w in self._steps_f.winfo_children():
            w.destroy()
        self._step_rows = []
        for name, _ in steps:
            rf = ctk.CTkFrame(self._steps_f, fg_color="transparent")
            rf.pack(fill="x", pady=2)
            ind = ctk.CTkLabel(rf, text="○", font=ctk.CTkFont(size=14),
                               text_color=C["text3"], width=26)
            ind.pack(side="left")
            lbl = ctk.CTkLabel(rf, text=name, font=ctk.CTkFont(size=12),
                               text_color=C["text2"])
            lbl.pack(side="left", padx=8)
            self._step_rows.append((ind, lbl))
        self._pbar.set(0)
        self._done_btn.grid_remove()
        self._task_dot.configure(text_color=C["accent"])
        self._sb.configure(fg_color=C["accent"])
        self._sb_show(f"{title}  ·  starting…")

        def runner():
            for i, (name, fn) in enumerate(steps):
                self.after(0, lambda i=i, n=name: (
                    self._step_ui(i, "run"),
                    self._sb_update(f"{self._task_title_str}  ·  {n}")))
                try:
                    fn()
                    self.after(0, lambda i=i: self._step_ui(i, "ok"))
                except Exception as exc:
                    self._task_had_error = True
                    self.after(0, lambda i=i, e=exc: (
                        self._step_ui(i, "err"),
                        self._tw(self._pr_term, f"\n❌  {e}\n")))
                self.after(0, lambda v=(i+1)/len(steps): self._anim_progress(v))
            self.after(0, self._steps_done)

        threading.Thread(target=runner, daemon=True).start()

    def _step_ui(self, idx: int, state: str):
        if idx >= len(self._step_rows):
            return
        ind, lbl = self._step_rows[idx]
        if self._spin_job:
            self.after_cancel(self._spin_job)
            self._spin_job = None
        if state == "run":
            self._spin_idx = 0
            lbl.configure(text_color=C["accent"])
            def tick(w=ind):
                w.configure(text=_SPIN[self._spin_idx % len(_SPIN)],
                            text_color=C["accent"])
                self._spin_idx += 1
                self._spin_job = self.after(90, tick)
            tick()
        elif state == "ok":
            ind.configure(text="✓", text_color=C["ok"])
            lbl.configure(text_color=C["text"])
        elif state == "err":
            ind.configure(text="✗", text_color=C["err"])
            lbl.configure(text_color=C["err"])

    def _anim_progress(self, target: float):
        cur = self._pbar.get()
        if abs(target - cur) < 0.005:
            self._pbar.set(target)
            return
        self._pbar.set(cur + (target - cur) * 0.25)
        self.after(16, lambda: self._anim_progress(target))

    def _steps_done(self):
        if self._spin_job:
            self.after_cancel(self._spin_job)
            self._spin_job = None
        self._pbar.set(1.0)
        self._tw(self._pr_term, "\n✅  All operations complete.\n")
        self._done_btn.grid()
        self._task_running = False
        self._sudo_cached  = False
        self._task_dot.configure(text_color=C["text3"])
        self._sb_complete()

        # v4.0: native macOS notification so you know a task finished
        # even if you switched away from the app. Respects the
        # existing "notifications" preference.
        try:
            prefs = _load_prefs()
            if prefs.get("notifications", True):
                if getattr(self, "_task_had_error", False):
                    _notify_mod.send(
                        "BrewCleaner", f"{self._task_title_str} — finished with errors",
                        subtitle="Check the Progress tab for details.",
                        enabled=True)
                else:
                    _notify_mod.send(
                        "BrewCleaner", f"{self._task_title_str} — complete",
                        enabled=True)
        except Exception:
            pass  # a notification failure should never interrupt cleanup below

        
        # Reset caches so next page visit fetches fresh data
        self._pkg_state_loaded = False
        self._installed_set    = set()
        self._outdated_set     = set()
        self._outdated_loaded  = False
        self._services_loaded  = False
        self._taps_loaded      = False
        
        # Auto-refresh if the user is currently parked on a specific data-driven page
        if self._page == "pkgs":
            self._refresh_pkgs_action()
        elif self._page == "upgrades":
            self._refresh_upgrades()
        elif self._page == "services":
            self._refresh_services()
        elif self._page == "taps":
            self._refresh_taps()

        if self._prefs.get("notifications", True) and _MAC:
            subprocess.Popen(["osascript", "-e",
                              'display notification "All operations complete." '
                              'with title "BrewCleaner"'])
        threading.Thread(target=self._probe, daemon=True).start()

    # ══════════════════════════════════════════════════════════
    #  SHELL HELPER  (blocking — call only from worker threads)
    # ══════════════════════════════════════════════════════════

    def _sh(self, cmd: str, env: Optional[Dict] = None):
        use_env = env if env is not None else _BREW_ENV
        self.after(0, lambda: self._tw(self._pr_term, f"\n$ {cmd}\n"))
        buf: List[str] = []
        buf_lock = threading.Lock()

        def flush_buf():
            with buf_lock:
                if buf:
                    self._tw(self._pr_term, "".join(buf))
                    buf.clear()

        def schedule_flush():
            flush_buf()
            if self._task_running:
                self.after(50, schedule_flush)

        self.after(50, schedule_flush)
        try:
            proc = subprocess.Popen(cmd, shell=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    text=True, env=use_env, bufsize=1)
            for line in iter(proc.stdout.readline, ""):
                with buf_lock:
                    buf.append(line)
            proc.wait()
            self.after(0, flush_buf)
        except Exception as exc:
            self.after(0, lambda e=exc: self._tw(self._pr_term, f"  ❌  {e}\n"))

    def _log(self, msg: str):
        self.after(0, lambda m=msg: self._tw(self._pr_term, m + "\n"))

