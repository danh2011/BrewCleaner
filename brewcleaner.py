#!/usr/bin/env python3
# ══════════════════════════════════════════════════════════════
#  PRE-IMPORT CONSTANTS  (stdlib only — used before ctk loads)
# ══════════════════════════════════════════════════════════════

import sys, os, subprocess, importlib.util, time, json, threading, plistlib
import urllib.request, ast
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── v4.0: menu bar mode branches off BEFORE anything Tk-related is
# even imported — it doesn't need Tk at all (see menubar_app.py), and
# running it in the same process as the main Tk app would mean two
# things fighting over the event loop. `brewcleaner --menubar` is a
# fully separate, lightweight run mode.
if "--menubar" in sys.argv:
    import menubar_app
    menubar_app.run(os.path.abspath(__file__))
    sys.exit(0)

# ── v4.0: preflight check BEFORE anything imports tkinter ──────────
# See brewcleaner_pkg/tk_preflight.py for why this has to happen here,
# in a subprocess, before the real `import tkinter` below.
from brewcleaner_pkg.tk_preflight import preflight_or_exit
preflight_or_exit()

# ── v4.0: pure logic (version detection, prefs, catalogue, update,
# snapshots, disk reporting) now lives in brewcleaner_pkg/ where it's
# unit tested (see tests/). The names below are kept as-is so nothing
# elsewhere in this file has to change — they're just imports now
# instead of inline definitions. This also removes two real bugs that
# existed in v3.1.3: `_xcode_install_guidance` and `_show_xcode_banner`
# were each accidentally DEFINED TWICE in this file, so the first copy
# of each silently became dead code. There is exactly one copy of each
# now (see brewcleaner_pkg/system.py).
from brewcleaner_pkg.version import APP_VERSION, GITHUB_URL
from brewcleaner_pkg.prefs import load_prefs as _load_prefs, save_prefs as _save_prefs
from brewcleaner_pkg.prefs import PREFS_PATH as _PREFS_PATH, SNAPS_PATH as _SNAPS_PATH
from brewcleaner_pkg.system import (
    sys_is_dark as _sys_is_dark,
    get_macos_version as _get_macos_version,
    get_recommended_xcode as _get_recommended_xcode,
    clt_installed as _clt_installed,
    xcode_app_installed as _xcode_app_installed,
    xcode_install_guidance as _xcode_install_guidance,
)
from brewcleaner_pkg.brew_env import build_brew_env as _build_brew_env
from brewcleaner_pkg import update as _update_mod
from brewcleaner_pkg import snapshots as _snapshots_mod
from brewcleaner_pkg import disk as _disk_mod

_check_clt_installed = _clt_installed

TOS_LINES = [
    "By using BrewCleaner you accept the following:",
    "  •  This app runs privileged Homebrew commands on your Mac",
    "  •  Destructive operations (Full Reinstall, etc.) cannot be undone",
    "  •  The authors are NOT liable for data loss or system issues",
    "  •  You use this software entirely at your own risk",
    "  •  THIS PROGRAM IS PROVIDED AS IS",
    "  •  THIS PROGRAM IS PROVIDED UNDER THE GNU GENERAL PUBLIC LICENSE v3.0"
    "  •  Source code and full license is open-source and visible at:",
    f"     {GITHUB_URL}",
]


def _check_xcode_boot():
    """
    Stdlib-only pre-flight that warns users if Xcode CLT is missing
    and offers to install it.  Called immediately after _boot().
    """
    if _clt_installed():
        return  # nothing to do

    import tkinter as _tk

    is_dark  = _sys_is_dark()
    bg_color = "#0D1117" if is_dark else "#FAFAFA"
    fg_color = "#E6EDF3" if is_dark else "#1A1A2E"
    fg_dim   = "#8B949E" if is_dark else "#475569"
    warn_col = "#D29922" if is_dark else "#92400E"
    sep_col  = "#30363D" if is_dark else "#E2E8F0"
    btn_bg   = "#21262D" if is_dark else "#E2E8F0"

    mac_major, mac_minor = _get_macos_version()
    xcode_ver, dl_url    = _get_recommended_xcode(mac_major, mac_minor)
    mac_str = f"{mac_major}.{mac_minor}" if mac_major else "unknown"

    W, H = 560, 316
    root = _tk.Tk()
    root.withdraw()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()

    w = _tk.Toplevel(root)
    w.title("BrewCleaner — Xcode Required")
    w.overrideredirect(True)
    w.configure(bg=bg_color)
    w.geometry(f"{W}x{H}+{(sw - W) // 2}+{(sh - H) // 2}")
    w.lift()
    w.attributes("-topmost", True)

    # ── header ───────────────────────────────────────────────
    _tk.Label(w, text="🍺  BrewCleaner",
              font=("Helvetica", 15, "bold"), bg=bg_color, fg=fg_color
              ).place(x=26, y=18)
    _tk.Frame(w, bg=sep_col, height=1).place(x=26, y=48, width=W - 52)

    # ── warning content ──────────────────────────────────────
    _tk.Label(w, text="⚠️  Xcode Tools Are Not Installed",
              font=("Helvetica", 13, "bold"), bg=bg_color, fg=warn_col
              ).place(x=26, y=58)

    body = (
        "Homebrew requires Xcode Command Line Tools to compile packages\n"
        "from source. Many formulae will fail to install without them.\n\n"
        f"Your macOS {mac_str} is compatible with Xcode {xcode_ver}.\n"
        "Click below to install the CLT (a system dialog will appear),\n"
        "or download the full Xcode from the link shown."
    )
    _tk.Label(w, text=body,
              font=("Helvetica", 11), bg=bg_color, fg=fg_dim,
              anchor="w", justify="left"
              ).place(x=26, y=86)

    _tk.Label(w, text=f"Full Xcode download:  {dl_url}",
              font=("Helvetica", 9), bg=bg_color, fg="#2F81F7"
              ).place(x=26, y=212)

    status_lbl = _tk.Label(w, text="", font=("Helvetica", 10),
                           bg=bg_color, fg="#3FB950" if is_dark else "#15803D")
    status_lbl.place(x=26, y=238)

    # ── buttons ──────────────────────────────────────────────
    def do_install_clt():
        try:
            subprocess.Popen(["xcode-select", "--install"])
            status_lbl.configure(
                text="System dialog opened — follow the prompts, then relaunch BrewCleaner.")
        except Exception as exc:
            status_lbl.configure(text=f"⚠️  Could not launch installer: {exc}", fg="#F85149")

    _tk.Button(w, text="🔧  Install Xcode CLT",
               font=("Helvetica", 12, "bold"),
               command=do_install_clt).place(x=26, y=264)

    _tk.Button(w, text="Continue Without Xcode →",
               font=("Helvetica", 11),
               command=w.destroy).place(x=220, y=264)

    w.update()
    while w.winfo_exists():
        try:
            root.update()
        except Exception:
            break
        time.sleep(0.02)

    try:
        root.destroy()
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════
#  PHASE 1 BOOTSTRAP: install customtkinter + TOS acceptance
#  Pure stdlib only — ctk not yet imported
# ══════════════════════════════════════════════════════════════

def _boot() -> bool:
    """
    Ensure customtkinter is available and TOS has been accepted.
    Shows a plain-tkinter window for install progress and/or TOS.
    Returns False only if the user explicitly declined TOS.
    """
    prefs     = _load_prefs()
    needs_ctk = not importlib.util.find_spec("customtkinter")
    needs_tos = prefs.get("tos_accepted_version") != APP_VERSION

    if not needs_ctk and not needs_tos:
        return True  # fast path

    import tkinter as _tk

    root = _tk.Tk()
    root.withdraw()

    W, H = 560, 380
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()

    is_dark = _sys_is_dark()
    bg_color = "#0D1117" if is_dark else "#EEF2FF"
    fg_color = "#E6EDF3" if is_dark else "#1A1A2E"
    fg_dim   = "#8B949E" if is_dark else "#475569"
    line_col = "#30363D" if is_dark else "#E2E8F0"

    w = _tk.Toplevel(root)
    w.title("BrewCleaner")
    w.overrideredirect(True)
    w.configure(bg=bg_color)
    w.geometry(f"{W}x{H}+{(sw - W) // 2}+{(sh - H) // 2}")
    w.lift()
    w.attributes("-topmost", True)

    # Header
    _tk.Label(w, text="🍺", font=("Helvetica", 38),
              bg=bg_color, fg="#2F81F7").place(x=W//2, y=26, anchor="n")
    _tk.Label(w, text="BrewCleaner",
              font=("Helvetica", 22, "bold"),
              bg=bg_color, fg=fg_color).place(x=W//2, y=74, anchor="n")
    _tk.Label(w, text=f"v{APP_VERSION}  •  The Homebrew Manager",
              font=("Helvetica", 10),
              bg=bg_color, fg=fg_dim).place(x=W//2, y=100, anchor="n")
    _tk.Frame(w, bg=line_col, height=1).place(x=40, y=122, width=W - 80)

    content_y = 136
    accepted  = [True]

    # ── Phase A: install customtkinter ────────────────────────
    if needs_ctk:
        accepted[0] = False
        status_lbl = _tk.Label(
            w, text="Installing customtkinter…",
            font=("Helvetica", 12), bg=bg_color, fg=fg_dim)
        status_lbl.place(x=W//2, y=content_y + 8, anchor="n")

        prog_bg  = _tk.Frame(w, bg=line_col, height=5)
        prog_bg.place(x=40, y=content_y + 44, width=W - 80)
        prog_bar = _tk.Frame(prog_bg, bg="#2F81F7", height=5, width=1)
        prog_bar.place(x=0, y=0)
        w.update()

        installed = [False]
        def do_install():
            for extra in (["--break-system-packages"], []):
                try:
                    subprocess.check_call(
                        [sys.executable, "-m", "pip", "install",
                         "customtkinter", "--quiet"] + extra,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    installed[0] = True
                    break
                except Exception:
                    pass

        t = threading.Thread(target=do_install, daemon=True)
        t.start()
        bar_w = W - 80
        step  = [0]

        def animate():
            if t.is_alive():
                step[0] = min(step[0] + 1, 90)
                prog_bar.place(width=int(step[0] / 100 * bar_w))
                w.after(35, animate)

        animate()
        while t.is_alive():
            try:
                root.update()
            except Exception:
                break
            time.sleep(0.03)

        prog_bar.place(width=bar_w)
        if installed[0]:
            status_lbl.configure(text="✓  customtkinter installed", fg="#3FB950" if is_dark else "#15803D")
        else:
            status_lbl.configure(
                text="⚠️  Install failed — run:  pip install customtkinter", fg="#F85149" if is_dark else "#EF4444")
            w.update()
            time.sleep(3)
            try:
                w.destroy()
                root.destroy()
            except Exception:
                pass
            return True

        w.update()
        time.sleep(0.5)
        content_y += 72

    # ── Phase B: TOS acceptance ───────────────────────────────
    if needs_tos:
        accepted[0] = False

        for i, line in enumerate(TOS_LINES):
            is_url  = line.startswith("     ")
            is_head = i == 0
            fg  = "#2F81F7" if is_url else (fg_color if is_head else fg_dim)
            fnt = ("Helvetica", 11, "bold") if is_head else ("Helvetica", 10)
            _tk.Label(w, text=line, font=fnt,
                      bg=bg_color, fg=fg,
                      anchor="w", justify="left"
                      ).place(x=44, y=content_y + i * 20)

        btn_y = content_y + len(TOS_LINES) * 20 + 16

        def on_accept():
            accepted[0] = True
            w.destroy()

        def on_decline():
            accepted[0] = False
            w.destroy()

        # Using default Tkinter buttons to ensure clear visibility across OS themes
        _tk.Button(w, text="✓  I Accept & Continue",
                   font=("Helvetica", 12, "bold"),
                   command=on_accept).place(x=44, y=btn_y)
        _tk.Button(w, text="Decline",
                   font=("Helvetica", 11),
                   command=on_decline).place(x=248, y=btn_y)

        w.update()
        while w.winfo_exists():
            try:
                root.update()
            except Exception:
                break
            time.sleep(0.02)
    else:
        try:
            w.destroy()
        except Exception:
            pass

    try:
        root.destroy()
    except Exception:
        pass

    if accepted[0]:
        prefs["tos_accepted_version"] = APP_VERSION
        _save_prefs(prefs)

    return accepted[0]


# ── Run bootstrap before any ctk import ──────────────────────
if not _boot():
    sys.exit(0)

_check_xcode_boot()   # warn if Xcode CLT missing (stdlib-only, safe to call here)


# ══════════════════════════════════════════════════════════════
#  IMPORTS  (ctk now guaranteed to exist)
# ══════════════════════════════════════════════════════════════
# v4.0: the ctk/tk imports, theme, and package catalogue moved to
# ui/_shared.py so the App class mixins (ui/*.py) can share them too
# without re-defining anything. See that file's docstring for why
# this is safe to import only here (after _boot()) and not earlier.

from ui._shared import (
    ctk, tk, messagebox, filedialog, Dict, List, Optional, Callable, Tuple,
    _LIGHT, _DARK, C, _MAC, _SF, _MNO, _SPIN, _BREW_ENV, PKGS, CASKS,
)

# v4.0: TIPS + the animated splash screen (_Splash) moved to ui/splash.py
# — imported by ui/core.py where it's actually used (App.__init__).

# ══════════════════════════════════════════════════════════════
#  MAIN APP  (v4.0: split into mixins — see ui/ and ROADMAP.md)
# ══════════════════════════════════════════════════════════════
# Every method that used to live directly in this class now lives in
# one of the mixins below, moved verbatim (no behavior changes) — see
# each ui/*.py file's docstring for which section it came from. This
# import happens here (not at the top of the file) because it's the
# first thing that needs ctk, and ctk is only guaranteed to exist
# after _boot() has run, above.

from ui.core import CoreMixin
from ui.page_dashboard import DashboardMixin
from ui.page_clean import CleanPageMixin
from ui.page_packages import PackagesMixin
from ui.page_upgrades import UpgradesPageMixin
from ui.page_services import ServicesMixin
from ui.page_taps import TapsMixin
from ui.page_snapshots import SnapshotsPageMixin
from ui.page_health import HealthMixin
from ui.page_deps import DepsMixin
from ui.page_progress import ProgressMixin
from ui.page_settings import SettingsMixin
from ui.widget_helpers import WidgetHelpersMixin
from ui.actions_quick import QuickActionsMixin
from ui.actions_upgrade import UpgradeActionsMixin
from ui.actions_clean import CleanActionMixin
from ui.actions_install import InstallActionMixin
from ui.sudo import SudoMixin
from ui.step_runner import StepRunnerMixin
from ui.probe import ProbeMixin
from ui.brew_ops import BrewOpsMixin
from ui.command_palette import CommandPaletteMixin


class App(
    # Mixins first, ctk.CTk last: CoreMixin.__init__ must be found
    # before ctk.CTk.__init__ in the MRO (it calls super().__init__()
    # itself to reach ctk.CTk's init). Order among the mixins doesn't
    # matter — none of them define overlapping method names.
    CoreMixin, DashboardMixin, CleanPageMixin, PackagesMixin,
    UpgradesPageMixin, ServicesMixin, TapsMixin, SnapshotsPageMixin,
    HealthMixin, DepsMixin, ProgressMixin, SettingsMixin,
    WidgetHelpersMixin, QuickActionsMixin, UpgradeActionsMixin,
    CleanActionMixin, InstallActionMixin, SudoMixin, StepRunnerMixin,
    ProbeMixin, BrewOpsMixin, CommandPaletteMixin,
    ctk.CTk,
):
    pass




# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = App()
    app.mainloop()
