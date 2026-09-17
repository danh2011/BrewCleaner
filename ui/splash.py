"""
The startup splash screen (v4.0: moved out of brewcleaner.py so it
lives alongside its ui/*.py sibling mixins). Owns the self-update
check too (see brewcleaner_pkg/update.py for the hardened download
logic this calls into).
"""

from __future__ import annotations

import os
import sys
import threading
import time
from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, APP_VERSION, _update_mod, etc.

TIPS = [
    ("💡", "Select multiple packages at once — they all install in a single fast brew call"),
    ("🚀", "Bottles are pre-compiled binaries — they are a lot easier to manage & update"),
    ("⏩", "brew update is skipped automatically if it ran less than an hour ago"),
    ("🧹", "Remove Orphans cleans up unused dependency packages in one click"),
    ("🔐", "Your sudo password is asked once per session and kept alive silently for up to a minute"),
    ("📊", "The Progress tab stays live even while you navigate other pages"),
    ("⚡", "7 speed env-vars are set on every brew call — skipping unnecessary pings"),
    ("📸", "Use Snapshots to back up your package list before big changes"),
    ("🔒", "Pin a package to prevent it from being upgraded accidentally"),
    ("🧪", "Untap stale taps to keep brew update fast and free of clutter"),
    ("🔀", "Use Dependencies to see what a package needs before installing it"),
    ("🩺", "Run Brew Health regularly to catch configuration issues early"),
    ("🏎", "The speed of BrewCleaner is highly dependent on your system & its internet connection"),
    ("💻", "An SSD is always faster than a HDD for BrewCleaner"),
]


class _Splash(ctk.CTkToplevel):
    def __init__(self, master, on_done: Callable, loading_event: threading.Event):
        super().__init__(master)
        self._on_done       = on_done
        self._loading_event = loading_event
        self._tip_idx       = 0
        self._tip_job: Optional[str] = None
        self._updating      = False          # True while downloading an update
        self._start_time    = time.time()
        self._MIN_SECS      = 3.5            # minimum splash display seconds

        self.overrideredirect(True)
        self.configure(fg_color="#0D1117")
        self.resizable(False, False)

        W, H = 520, 280
        self.geometry(f"{W}x{H}")
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{W}x{H}+{(sw - W) // 2}+{(sh - H) // 2}")
        self.lift()
        self.attributes("-topmost", True)

        self._build_ui(W)
        self._rotate_tip()
        self._check_for_updates()

    def _build_ui(self, W: int):
        ctk.CTkLabel(self, text="🍺", font=ctk.CTkFont(size=40),
                     fg_color="transparent").pack(pady=(22, 2))
        ctk.CTkLabel(self, text="BrewCleaner",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="#E6EDF3", fg_color="transparent").pack()
        ctk.CTkLabel(self, text=f"v{APP_VERSION}  •  The Homebrew Manager",
                     font=ctk.CTkFont(size=10),
                     text_color="#8B949E", fg_color="transparent").pack()

        ctk.CTkFrame(self, fg_color="#30363D", height=1).pack(fill="x", padx=44, pady=(10, 6))

        tip_row = ctk.CTkFrame(self, fg_color="transparent")
        tip_row.pack(fill="x", padx=40, pady=4)
        self._tip_icon = ctk.CTkLabel(
            tip_row, text=TIPS[0][0], font=ctk.CTkFont(size=18),
            fg_color="transparent", width=28)
        self._tip_icon.pack(side="left")
        self._tip_text = ctk.CTkLabel(
            tip_row, text=TIPS[0][1],
            font=ctk.CTkFont(size=11), text_color="#8B949E",
            fg_color="transparent", wraplength=420,
            anchor="w", justify="left")
        self._tip_text.pack(side="left", padx=(8, 0), fill="x", expand=True)

        self._pbar = ctk.CTkProgressBar(
            self, fg_color="#30363D", progress_color="#2F81F7",
            height=3, corner_radius=2)
        self._pbar.pack(fill="x", padx=44, pady=(12, 0))
        self._pbar.set(0)
        self.after(80, self._poll_ready)   # real-load-aware progress

    def _rotate_tip(self):
        self._tip_idx = (self._tip_idx + 1) % len(TIPS)
        icon, text = TIPS[self._tip_idx]
        if self.winfo_exists():
            self._tip_icon.configure(text=icon)
            self._tip_text.configure(text=text)
            self._tip_job = self.after(2500, self._rotate_tip)   # slow — was 700

    def _poll_ready(self):
        """
        Drive the progress bar based on actual loading state, then close
        when both the loading event is set AND the minimum display time
        has elapsed.  Called every 80 ms via after().
        """
        if not self.winfo_exists():
            return
        if self._updating:
            return   # update download in progress — don't interfere

        elapsed = time.time() - self._start_time

        if self._loading_event.is_set():
            if elapsed >= self._MIN_SECS:
                # Loading complete + min time served → fill bar and close
                self._pbar.set(1.0)
                self.after(1200, self._close)
                return
            else:
                # Done loading but haven't shown splash long enough yet
                frac = elapsed / self._MIN_SECS
                self._pbar.set(0.97 + frac * 0.03)   # creep to 1.0
        else:
            # Still loading — animate in two phases
            if elapsed < 2.0:
                # Fast phase: 0 → 68% over the first 2 s
                self._pbar.set(min(elapsed / 2.0 * 0.68, 0.68))
            else:
                # Slow crawl: 68% → 95%, waiting for real work
                t = elapsed - 2.0
                self._pbar.set(min(0.68 + t * 0.014, 0.95))

        self.after(80, self._poll_ready)

    def _check_for_updates(self):
        """
        v4.0: delegates to brewcleaner_pkg.update, which stages the
        download, validates it (parses as Python, version matches,
        checksum if published), and swaps it in atomically — it never
        writes over the running file directly. See update.py's module
        docstring for the three bugs this replaces (dead duplicate
        except handler, UnboundLocalError on early failure, and no
        integrity checking of any kind).
        """
        def run_check():
            try:
                info = _update_mod.check_for_update(APP_VERSION)
                if info is None:
                    return

                self._updating = True
                self.after(0, lambda: self._tip_text.configure(
                    text=f"✨  Downloading update v{info.version}…", text_color="#3FB950"))
                self.after(0, lambda: self._pbar.set(0.0))

                def progress(p):
                    self.after(0, lambda: self._pbar.set(p))

                _update_mod.download_and_apply(info, os.path.abspath(__file__), on_progress=progress)

                self.after(0, lambda: self._tip_text.configure(
                    text="✅  Update complete — restarting…"))
                time.sleep(1.2)
                os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)] + sys.argv[1:])

            except Exception as exc:
                # Any failure (network, validation, checksum mismatch,
                # etc.) just cancels the update quietly — the original
                # file was never touched, so there's nothing to recover.
                print(f"BrewCleaner: self-update skipped ({exc})")
                self._updating = False

        threading.Thread(target=run_check, daemon=True).start()

    def _close(self):
        if self._tip_job:
            try:
                self.after_cancel(self._tip_job)
            except Exception:
                pass
        try:
            self._on_done(self)
        except Exception:
            pass
