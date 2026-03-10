#!/usr/bin/env python3
"""
BrewCleaner v3.0  ─  The complete Homebrew manager for macOS
Single file · auto-bootstraps customtkinter · macOS 10.15+ · Python 3.8+

New in v3.0:
  • Animated splash screen with rotating tips on every launch
  • First-run TOS acceptance with GitHub source link
  • Upgrade Manager  — per-package upgrades, pin/unpin
  • Services Manager — start/stop/restart brew services
  • Tap Manager      — list taps, add, untap
  • Snapshots        — save/restore/Brewfile export+import
  • Brew Health      — parsed brew doctor output with fix hints
  • Dependencies     — dep tree + reverse lookup
  • Cask support     — formulae + casks in Package Store
  • Orphan removal   — brew autoremove in Clean Brew
  • System Cleaner removed (out of Homebrew scope)
"""

# ══════════════════════════════════════════════════════════════
#  PRE-IMPORT CONSTANTS  (stdlib only — used before ctk loads)
# ══════════════════════════════════════════════════════════════

import sys, os, subprocess, importlib.util, time, json, threading, plistlib
from pathlib import Path

APP_VERSION = "3.0"
GITHUB_URL  = "https://github.com/yourusername/BrewCleaner"

_PREFS_PATH = Path.home() / ".config" / "brewcleaner" / "prefs.json"
_SNAPS_PATH = Path.home() / ".config" / "brewcleaner" / "snapshots"

TOS_LINES = [
    "By using BrewCleaner you accept the following:",
    "  •  This app runs privileged Homebrew commands on your Mac",
    "  •  Destructive operations (Full Reinstall, etc.) cannot be undone",
    "  •  The authors are NOT liable for data loss or system issues",
    "  •  You use this software entirely at your own risk",
    "  •  Source code is fully open and visible at:",
    f"     {GITHUB_URL}",
]

TIPS = [
    ("💡", "Select multiple packages at once — they all install in a single fast brew call"),
    ("🚀", "Bottles are pre-compiled binaries — BrewCleaner always prefers them over source"),
    ("⏩", "brew update is skipped automatically if it ran less than an hour ago"),
    ("🧹", "Remove Orphans cleans up unused dependency packages in one click"),
    ("🔐", "Your sudo password is asked once per session and kept alive silently"),
    ("📊", "The Progress tab stays live even while you navigate other pages"),
    ("⚡", "7 speed env-vars are set on every brew call — skipping unnecessary pings"),
    ("📸", "Use Snapshots to back up your package list before big changes"),
    ("🔒", "Pin a package to prevent it from being upgraded accidentally"),
    ("🧪", "Untap stale taps to keep brew update fast and free of clutter"),
    ("🔀", "Use Dependencies to see what a package needs before installing it"),
    ("🩺", "Run Brew Health regularly to catch configuration issues early"),
]


# ══════════════════════════════════════════════════════════════
#  PREFERENCES
# ══════════════════════════════════════════════════════════════

def _load_prefs() -> dict:
    try:
        return json.loads(_PREFS_PATH.read_text())
    except Exception:
        return {"theme": "light", "notifications": True, "auto_refresh": True}


def _save_prefs(p: dict):
    _PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PREFS_PATH.write_text(json.dumps(p, indent=2))


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

    w = _tk.Toplevel(root)
    w.title("BrewCleaner")
    w.overrideredirect(True)
    w.configure(bg="#0D1117")
    w.geometry(f"{W}x{H}+{(sw - W) // 2}+{(sh - H) // 2}")
    w.lift()
    w.attributes("-topmost", True)

    # Header
    _tk.Label(w, text="🍺", font=("Helvetica", 38),
              bg="#0D1117", fg="#2F81F7").place(x=W//2, y=26, anchor="n")
    _tk.Label(w, text="BrewCleaner",
              font=("Helvetica", 22, "bold"),
              bg="#0D1117", fg="#E6EDF3").place(x=W//2, y=74, anchor="n")
    _tk.Label(w, text=f"v{APP_VERSION}  •  The Homebrew Manager",
              font=("Helvetica", 10),
              bg="#0D1117", fg="#8B949E").place(x=W//2, y=100, anchor="n")
    _tk.Frame(w, bg="#30363D", height=1).place(x=40, y=122, width=W - 80)

    content_y = 136
    accepted  = [True]

    # ── Phase A: install customtkinter ────────────────────────
    if needs_ctk:
        accepted[0] = False
        status_lbl = _tk.Label(
            w, text="Installing customtkinter…",
            font=("Helvetica", 12), bg="#0D1117", fg="#8B949E")
        status_lbl.place(x=W//2, y=content_y + 8, anchor="n")

        prog_bg  = _tk.Frame(w, bg="#30363D", height=5)
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
            status_lbl.configure(text="✓  customtkinter installed", fg="#3FB950")
        else:
            status_lbl.configure(
                text="⚠️  Install failed — run:  pip install customtkinter", fg="#F85149")
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
            fg  = "#2F81F7" if is_url else ("#E6EDF3" if is_head else "#8B949E")
            fnt = ("Helvetica", 11, "bold") if is_head else ("Helvetica", 10)
            _tk.Label(w, text=line, font=fnt,
                      bg="#0D1117", fg=fg,
                      anchor="w", justify="left"
                      ).place(x=44, y=content_y + i * 20)

        btn_y = content_y + len(TOS_LINES) * 20 + 16

        def on_accept():
            accepted[0] = True
            w.destroy()

        def on_decline():
            accepted[0] = False
            w.destroy()

        _tk.Button(w, text="✓  I Accept & Continue",
                   font=("Helvetica", 12, "bold"),
                   bg="#2F81F7", fg="white", activebackground="#1F6FEB",
                   relief="flat", padx=18, pady=7, cursor="hand2",
                   bd=0, command=on_accept).place(x=44, y=btn_y)
        _tk.Button(w, text="Decline",
                   font=("Helvetica", 11),
                   bg="#21262D", fg="#8B949E", activebackground="#30363D",
                   relief="flat", padx=14, pady=7, cursor="hand2",
                   bd=0, command=on_decline).place(x=248, y=btn_y)

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


# ══════════════════════════════════════════════════════════════
#  IMPORTS  (ctk now guaranteed to exist)
# ══════════════════════════════════════════════════════════════

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from typing import Dict, List, Optional, Callable, Tuple


# ══════════════════════════════════════════════════════════════
#  THEME
# ══════════════════════════════════════════════════════════════

_LIGHT: Dict[str, str] = dict(
    bg="#EEF2FF",        sidebar="#FFFFFF",     panel="#FFFFFF",
    panel2="#F8FAFF",    accent="#0078D4",      accent_h="#106EBE",
    accent_bg="#E3F0FF", border="#E2E8F0",      text="#1A1A2E",
    text2="#475569",     text3="#94A3B8",
    ok="#22C55E",        warn="#F59E0B",         err="#EF4444",
    tbg="#1E1E2E",       tfg="#CDD6F4",
    bi="#DCFCE7",        bit="#15803D",
    bo="#FEF9C3",        bot="#854D0E",
    bn="#F1F5F9",        bnt="#64748B",
)
_DARK: Dict[str, str] = dict(
    bg="#0D1117",        sidebar="#161B22",     panel="#21262D",
    panel2="#1C2128",    accent="#2F81F7",      accent_h="#1F6FEB",
    accent_bg="#0D2045", border="#30363D",      text="#E6EDF3",
    text2="#8B949E",     text3="#484F58",
    ok="#3FB950",        warn="#D29922",         err="#F85149",
    tbg="#010409",       tfg="#79C0FF",
    bi="#1A3A25",        bit="#3FB950",
    bo="#3A2E14",        bot="#D29922",
    bn="#21262D",        bnt="#8B949E",
)
C: Dict[str, str] = dict(_LIGHT)

_MAC  = sys.platform == "darwin"
_SF   = "SF Pro Display" if _MAC else "Helvetica"
_MNO  = "Menlo"          if _MAC else "Courier New"
_SPIN = ["⣾","⣽","⣻","⢿","⡿","⣟","⣯","⣷"]

_BREW_ENV: Dict[str, str] = {
    **dict(os.environ),
    "HOMEBREW_NO_AUTO_UPDATE":  "1",
    "HOMEBREW_NO_ANALYTICS":    "1",
    "HOMEBREW_NO_ENV_HINTS":    "1",
    "HOMEBREW_INSTALL_CLEANUP": "0",
    "HOMEBREW_MAKE_JOBS":       str(min(os.cpu_count() or 4, 8)),
    "HOMEBREW_CURL_RETRIES":    "3",
    "HOMEBREW_NO_GITHUB_API":   "1",
}


# ══════════════════════════════════════════════════════════════
#  PACKAGE CATALOGUES
# ══════════════════════════════════════════════════════════════

PKGS: Dict[str, List[Dict]] = {
    "Development": [
        {"id":"python@3.12","label":"Python 3.12","desc":"Python programming language","icon":"🐍",
         "conflicts":[("~/.pyenv","pyenv"),("~/anaconda3","Anaconda"),("~/miniconda3","Miniconda")]},
        {"id":"node","label":"Node.js","desc":"JavaScript runtime (LTS)","icon":"📦",
         "conflicts":[("~/.nvm","NVM"),("~/.volta","Volta"),("cmd:fnm","fnm")]},
        {"id":"git","label":"Git","desc":"Distributed version control","icon":"🌿","conflicts":[]},
        {"id":"gh","label":"GitHub CLI","desc":"GitHub from the terminal","icon":"🐙","conflicts":[]},
        {"id":"go","label":"Go","desc":"Go programming language","icon":"🔵","conflicts":[]},
        {"id":"rust","label":"Rust","desc":"Systems language","icon":"🦀","conflicts":[("cmd:rustup","rustup")]},
        {"id":"ruby","label":"Ruby","desc":"Ruby programming language","icon":"💎",
         "conflicts":[("~/.rbenv","rbenv"),("~/.rvm","RVM")]},
        {"id":"openjdk","label":"Java (OpenJDK)","desc":"Java 21 LTS","icon":"☕",
         "conflicts":[("/Library/Java/JavaVirtualMachines","System JDK")]},
        {"id":"vim","label":"Vim","desc":"Vi IMproved editor","icon":"✏️","conflicts":[]},
        {"id":"neovim","label":"Neovim","desc":"Hyperextensible Vim fork","icon":"✨","conflicts":[]},
        {"id":"tmux","label":"tmux","desc":"Terminal multiplexer","icon":"🖥️","conflicts":[]},
        {"id":"wget","label":"wget","desc":"Network file downloader","icon":"⬇️","conflicts":[]},
        {"id":"curl","label":"curl","desc":"Command-line HTTP client","icon":"🔗","conflicts":[]},
        {"id":"jq","label":"jq","desc":"Lightweight JSON processor","icon":"🔧","conflicts":[]},
        {"id":"make","label":"make","desc":"GNU Make build system","icon":"⚙️","conflicts":[]},
    ],
    "Database": [
        {"id":"postgresql@16","label":"PostgreSQL 16","desc":"Advanced open-source SQL","icon":"🐘","conflicts":[]},
        {"id":"mysql","label":"MySQL","desc":"Popular relational database","icon":"🐬","conflicts":[]},
        {"id":"redis","label":"Redis","desc":"In-memory data store","icon":"🔴","conflicts":[]},
        {"id":"sqlite","label":"SQLite","desc":"Self-contained SQL engine","icon":"🗄️","conflicts":[]},
        {"id":"mongodb-community","label":"MongoDB","desc":"NoSQL document database","icon":"🍃","conflicts":[]},
    ],
    "Media": [
        {"id":"ffmpeg","label":"FFmpeg","desc":"Complete media processing suite","icon":"🎬","conflicts":[]},
        {"id":"imagemagick","label":"ImageMagick","desc":"Image editing & conversion","icon":"🖼️","conflicts":[]},
        {"id":"yt-dlp","label":"yt-dlp","desc":"Download from 1000+ sites","icon":"📹","conflicts":[]},
        {"id":"exiftool","label":"ExifTool","desc":"Read/write media metadata","icon":"📷","conflicts":[]},
        {"id":"sox","label":"SoX","desc":"Audio processing toolbox","icon":"🎵","conflicts":[]},
    ],
    "DevOps": [
        {"id":"docker","label":"Docker","desc":"Container platform CLI","icon":"🐳","conflicts":[]},
        {"id":"kubectl","label":"kubectl","desc":"Kubernetes CLI","icon":"☸️","conflicts":[]},
        {"id":"terraform","label":"Terraform","desc":"Infrastructure as code","icon":"🏗️","conflicts":[]},
        {"id":"awscli","label":"AWS CLI","desc":"Amazon Web Services CLI","icon":"☁️","conflicts":[]},
        {"id":"helm","label":"Helm","desc":"Kubernetes package manager","icon":"⛵","conflicts":[]},
        {"id":"ansible","label":"Ansible","desc":"IT automation platform","icon":"🤖","conflicts":[]},
    ],
    "Security": [
        {"id":"gpg","label":"GPG","desc":"GNU Privacy Guard","icon":"🔐","conflicts":[]},
        {"id":"openssl@3","label":"OpenSSL 3","desc":"TLS/SSL cryptography toolkit","icon":"🔒","conflicts":[]},
        {"id":"nmap","label":"nmap","desc":"Network exploration tool","icon":"🕵️","conflicts":[]},
        {"id":"trivy","label":"Trivy","desc":"Container vulnerability scan","icon":"🛡️","conflicts":[]},
    ],
    "Productivity": [
        {"id":"tree","label":"tree","desc":"Directory tree visualiser","icon":"🌳","conflicts":[]},
        {"id":"htop","label":"htop","desc":"Interactive process viewer","icon":"📊","conflicts":[]},
        {"id":"bat","label":"bat","desc":"cat with syntax highlighting","icon":"🦇","conflicts":[]},
        {"id":"fd","label":"fd","desc":"Fast user-friendly find","icon":"🔍","conflicts":[]},
        {"id":"ripgrep","label":"ripgrep","desc":"Ultra-fast text search","icon":"⚡","conflicts":[]},
        {"id":"fzf","label":"fzf","desc":"Command-line fuzzy finder","icon":"🎯","conflicts":[]},
        {"id":"starship","label":"Starship","desc":"Cross-shell prompt","icon":"🚀","conflicts":[]},
        {"id":"zoxide","label":"zoxide","desc":"Smarter cd command","icon":"📍","conflicts":[]},
        {"id":"thefuck","label":"thefuck","desc":"Correct command typos","icon":"😤","conflicts":[]},
        {"id":"tldr","label":"tldr","desc":"Simplified man pages","icon":"📖","conflicts":[]},
    ],
}

CASKS: Dict[str, List[Dict]] = {
    "Browsers": [
        {"id":"google-chrome","label":"Chrome","desc":"Google Chrome browser","icon":"🌐","conflicts":[]},
        {"id":"firefox","label":"Firefox","desc":"Mozilla Firefox browser","icon":"🦊","conflicts":[]},
        {"id":"arc","label":"Arc","desc":"Arc browser by The Browser Company","icon":"🌈","conflicts":[]},
        {"id":"brave-browser","label":"Brave","desc":"Privacy-focused browser","icon":"🦁","conflicts":[]},
    ],
    "Development": [
        {"id":"visual-studio-code","label":"VS Code","desc":"Microsoft's code editor","icon":"💙","conflicts":[]},
        {"id":"iterm2","label":"iTerm2","desc":"Powerful macOS terminal","icon":"⬛","conflicts":[]},
        {"id":"tableplus","label":"TablePlus","desc":"Database GUI client","icon":"🗄️","conflicts":[]},
        {"id":"postman","label":"Postman","desc":"API development platform","icon":"📮","conflicts":[]},
        {"id":"github","label":"GitHub Desktop","desc":"GitHub's desktop app","icon":"🐙","conflicts":[]},
    ],
    "Productivity": [
        {"id":"raycast","label":"Raycast","desc":"Extendable launcher","icon":"🚀","conflicts":[]},
        {"id":"notion","label":"Notion","desc":"All-in-one workspace","icon":"📝","conflicts":[]},
        {"id":"obsidian","label":"Obsidian","desc":"Knowledge base & notes","icon":"🟣","conflicts":[]},
        {"id":"rectangle","label":"Rectangle","desc":"Window snap management","icon":"⬜","conflicts":[]},
    ],
    "Communication": [
        {"id":"slack","label":"Slack","desc":"Team communication","icon":"💬","conflicts":[]},
        {"id":"discord","label":"Discord","desc":"Communities & gaming","icon":"🎮","conflicts":[]},
        {"id":"zoom","label":"Zoom","desc":"Video conferencing","icon":"📹","conflicts":[]},
    ],
    "Utilities": [
        {"id":"the-unarchiver","label":"The Unarchiver","desc":"Archive extraction","icon":"📦","conflicts":[]},
        {"id":"vlc","label":"VLC","desc":"Versatile media player","icon":"🎬","conflicts":[]},
        {"id":"appcleaner","label":"AppCleaner","desc":"App removal utility","icon":"🧹","conflicts":[]},
        {"id":"stats","label":"Stats","desc":"System stats in menu bar","icon":"📊","conflicts":[]},
    ],
}



# ══════════════════════════════════════════════════════════════
#  ANIMATED SPLASH  (shown every startup for ~2.5 s)
# ══════════════════════════════════════════════════════════════

class _Splash(ctk.CTkToplevel):
    def __init__(self, master, on_done: Callable):
        super().__init__(master)
        self._on_done  = on_done
        self._tip_idx  = 0
        self._tip_job: Optional[str] = None

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
        self.after(2500, self._close)

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
        self._anim_bar(0.0)

    def _rotate_tip(self):
        self._tip_idx = (self._tip_idx + 1) % len(TIPS)
        icon, text = TIPS[self._tip_idx]
        if self.winfo_exists():
            self._tip_icon.configure(text=icon)
            self._tip_text.configure(text=text)
            self._tip_job = self.after(700, self._rotate_tip)

    def _anim_bar(self, v: float):
        if not self.winfo_exists():
            return
        self._pbar.set(min(v, 0.96))
        if v < 0.96:
            self.after(28, lambda: self._anim_bar(v + 0.013))

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


# ══════════════════════════════════════════════════════════════
#  APPLICATION
# ══════════════════════════════════════════════════════════════

class App(ctk.CTk):

    # ── init ─────────────────────────────────────────────────

    def __init__(self):
        super().__init__()
        self.withdraw()
        self.title("BrewCleaner")
        self.geometry("1160x740")
        self.minsize(980, 640)

        self._prefs = _load_prefs()
        theme = self._prefs.get("theme", "light")
        C.update(_DARK if theme == "dark" else _LIGHT)
        ctk.set_appearance_mode("Dark" if theme == "dark" else "Light")

        self._init_state()
        self._build()

        _Splash(self, on_done=self._on_splash_done)

        if self._prefs.get("auto_refresh", True):
            threading.Thread(target=self._probe, daemon=True).start()

    def _on_splash_done(self, splash):
        try:
            splash.destroy()
        except Exception:
            pass
        self.deiconify()
        self.lift()
        self._goto("home")

    def _init_state(self):
        self._page           = ""
        self._selected:   set              = set()
        self._cask_sel:   set              = set()
        self._custom_pkgs: List[Dict]      = []
        self._pkg_vars:   Dict[str, tk.BooleanVar] = {}
        self._cask_vars:  Dict[str, tk.BooleanVar] = {}
        self._installed_set: set           = set()
        self._outdated_set:  set           = set()
        self._cask_installed:set           = set()
        self._cask_outdated: set           = set()
        self._pkg_state_loaded             = False
        self._pkg_tab                      = "formulae"
        self._search_job: Optional[str]    = None
        self._brew_results: List[Dict]     = []
        self._search_status: Optional[ctk.CTkLabel] = None
        self._outdated_data: List[Dict]    = []
        self._outdated_loaded              = False
        self._pinned_set:  set             = set()
        self._upgrade_sel: set             = set()
        self._upgrade_vars: Dict[str, tk.BooleanVar] = {}
        self._services_data: List[Dict]    = []
        self._services_loaded              = False
        self._taps_data: List[Dict]        = []
        self._taps_loaded                  = False
        self._brew_ok                      = False
        self._step_rows: List[Tuple]       = []
        self._spin_job: Optional[str]      = None
        self._spin_idx                     = 0
        self._task_running                 = False
        self._task_title_str               = ""
        self._sudo_cached                  = False
        self._sudo_alive_job: Optional[str]= None
        self._sb_spin_job:    Optional[str]= None
        self._sb_spin_idx                  = 0
        self._sb_visible                   = False

    # ── scaffold ─────────────────────────────────────────────

    def _build(self):
        self.configure(fg_color=C["bg"])
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(0, minsize=0)
        self._mk_statusbar()
        self._mk_sidebar()
        self._cf = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        self._cf.grid(row=1, column=1, sticky="nsew")
        self._cf.grid_columnconfigure(0, weight=1)
        self._cf.grid_rowconfigure(0, weight=1)
        self._pages: Dict[str, ctk.CTkBaseClass] = {}
        self._pg_home()
        self._pg_clean()
        self._pg_pkgs()
        self._pg_upgrades()
        self._pg_services()
        self._pg_taps()
        self._pg_snapshots()
        self._pg_health()
        self._pg_deps()
        self._pg_progress()
        self._pg_settings()

    # ── global status bar ────────────────────────────────────

    def _mk_statusbar(self):
        self._sb = ctk.CTkFrame(self, fg_color=C["accent"], height=38, corner_radius=0)
        self._sb.grid_columnconfigure(2, weight=1)
        self._sb_spin_lbl = ctk.CTkLabel(
            self._sb, text=_SPIN[0], width=22,
            font=ctk.CTkFont(size=14), text_color="#FFFFFF", fg_color="transparent")
        self._sb_spin_lbl.grid(row=0, column=0, padx=(12, 0), pady=6)
        self._sb_step_lbl = ctk.CTkLabel(
            self._sb, text="", font=ctk.CTkFont(size=12),
            text_color="#FFFFFF", fg_color="transparent", anchor="w")
        self._sb_step_lbl.grid(row=0, column=2, sticky="ew", padx=(8, 0))
        ctk.CTkButton(
            self._sb, text="View Progress →",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="transparent", text_color="#FFFFFF",
            hover_color=C["accent_h"], width=130, height=26, corner_radius=6,
            command=lambda: self._goto("progress")
        ).grid(row=0, column=3, padx=(4, 2), pady=5)
        ctk.CTkButton(
            self._sb, text="✕",
            font=ctk.CTkFont(size=12), width=28, height=26,
            fg_color="transparent", text_color="#FFFFFF",
            hover_color=C["accent_h"], corner_radius=6,
            command=self._sb_dismiss
        ).grid(row=0, column=4, padx=(0, 8), pady=5)

    def _sb_show(self, text: str = ""):
        self._sb_visible = True
        self._sb_step_lbl.configure(text=text)
        self._sb.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.grid_rowconfigure(0, minsize=38)
        self._sb_spin_start()

    def _sb_update(self, text: str):
        if self._sb_visible:
            self._sb_step_lbl.configure(text=text)

    def _sb_complete(self):
        self._sb_spin_stop()
        self._sb.configure(fg_color=C["ok"])
        self._sb_spin_lbl.configure(text="✓")
        self._sb_step_lbl.configure(text="All operations complete  —  click View for details")
        self.after(4000, self._sb_dismiss)

    def _sb_dismiss(self):
        self._sb_spin_stop()
        self._sb_visible = False
        self._sb.grid_remove()
        self.grid_rowconfigure(0, minsize=0)
        self._sb.configure(fg_color=C["accent"])
        self._sb_spin_lbl.configure(text=_SPIN[0])

    def _sb_spin_start(self):
        self._sb_spin_stop()
        self._sb_spin_idx = 0
        def tick():
            if not self._sb_visible:
                return
            self._sb_spin_lbl.configure(text=_SPIN[self._sb_spin_idx % len(_SPIN)])
            self._sb_spin_idx += 1
            self._sb_spin_job = self.after(90, tick)
        tick()

    def _sb_spin_stop(self):
        if self._sb_spin_job:
            self.after_cancel(self._sb_spin_job)
            self._sb_spin_job = None

    # ── sidebar ──────────────────────────────────────────────

    def _mk_sidebar(self):
        sb = ctk.CTkFrame(self, fg_color=C["sidebar"], width=222, corner_radius=0)
        sb.grid(row=1, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_rowconfigure(3, weight=1)
        sb.grid_columnconfigure(0, weight=1)

        lg = ctk.CTkFrame(sb, fg_color="transparent", height=70)
        lg.grid(row=0, column=0, sticky="ew", padx=18, pady=(22, 4))
        lg.grid_propagate(False)
        lg.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(lg, text="🍺", font=ctk.CTkFont(size=30),
                     fg_color="transparent").grid(row=0, column=0, rowspan=2, padx=(0, 10))
        ctk.CTkLabel(lg, text="BrewCleaner",
                     font=ctk.CTkFont(family=_SF, size=15, weight="bold"),
                     text_color=C["text"], anchor="w",
                     fg_color="transparent").grid(row=0, column=1, sticky="ew")
        self._brew_lbl = ctk.CTkLabel(
            lg, text="checking…", font=ctk.CTkFont(size=10),
            text_color=C["text3"], fg_color="transparent", anchor="w")
        self._brew_lbl.grid(row=1, column=1, sticky="ew")

        ctk.CTkFrame(sb, fg_color=C["border"], height=1).grid(
            row=1, column=0, sticky="ew", padx=14, pady=2)

        nf = ctk.CTkFrame(sb, fg_color="transparent")
        nf.grid(row=2, column=0, sticky="ew", padx=8, pady=6)
        nf.grid_columnconfigure(0, weight=1)
        self._nav: Dict[str, ctk.CTkButton] = {}

        NAV_ITEMS = [
            ("home",      "🏠", "Dashboard"),
            ("clean",     "🧹", "Clean Brew"),
            ("pkgs",      "📦", "Packages"),
            ("upgrades",  "⬆️",  "Upgrades"),
            ("services",  "🔧", "Services"),
            ("taps",      "🧪", "Taps"),
            ("snapshots", "📸", "Snapshots"),
            ("health",    "🌿", "Brew Health"),
            ("deps",      "🔀", "Dependencies"),
            ("progress",  "📊", "Progress"),
            ("settings",  "⚙️",  "Settings"),
        ]
        for i, (pid, icon, label) in enumerate(NAV_ITEMS):
            b = ctk.CTkButton(
                nf, text=f"  {icon}   {label}",
                font=ctk.CTkFont(size=13),
                fg_color="transparent", text_color=C["text2"],
                hover_color=C["accent_bg"], anchor="w",
                height=40, corner_radius=8,
                command=lambda p=pid: self._goto(p))
            b.grid(row=i, column=0, sticky="ew", pady=1)
            self._nav[pid] = b

        self._task_dot = ctk.CTkLabel(
            nf, text="●", font=ctk.CTkFont(size=8),
            text_color=C["text3"], fg_color="transparent", width=12)
        self._task_dot.grid(row=9, column=0, sticky="e", padx=4)

        ctk.CTkLabel(sb, text=f"v{APP_VERSION}  •  open source",
                     font=ctk.CTkFont(size=10), text_color=C["text3"],
                     fg_color="transparent").grid(row=3, column=0, sticky="s", pady=(0, 14))

    # ── routing ──────────────────────────────────────────────

    def _goto(self, pid: str):
        for k, b in self._nav.items():
            b.configure(
                fg_color=C["accent_bg"] if k == pid else "transparent",
                text_color=C["accent"] if k == pid else C["text2"])
        if self._page and self._page in self._pages:
            self._pages[self._page].grid_remove()
        self._page = pid
        if pid in self._pages:
            self._pages[pid].grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        if pid == "pkgs" and not self._pkg_state_loaded:
            self._pkg_state_loaded = True
            threading.Thread(target=self._load_pkg_state, daemon=True).start()
        if pid == "upgrades" and not self._outdated_loaded:
            self._outdated_loaded = True
            threading.Thread(target=self._load_outdated_data, daemon=True).start()
        if pid == "services" and not self._services_loaded:
            self._services_loaded = True
            threading.Thread(target=self._load_services_data, daemon=True).start()
        if pid == "taps" and not self._taps_loaded:
            self._taps_loaded = True
            threading.Thread(target=self._load_taps_data, daemon=True).start()
        if pid == "snapshots":
            self.after(50, self._refresh_snapshots)


    # ══════════════════════════════════════════════════════════
    #  PAGE — DASHBOARD
    # ══════════════════════════════════════════════════════════

    def _pg_home(self):
        p = ctk.CTkScrollableFrame(self._cf, fg_color="transparent",
                                   scrollbar_button_color=C["border"])
        self._section_hdr(p, "Dashboard", "Homebrew overview & quick actions")

        self._stat_cf = ctk.CTkFrame(p, fg_color="transparent")
        self._stat_cf.pack(fill="x")
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

        self._mini_hdr(p, "Quick Actions")
        qf = ctk.CTkFrame(p, fg_color="transparent")
        qf.pack(fill="x", pady=(0, 22))
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

        self._mini_hdr(p, "Output")
        self._home_term = self._mk_term(p, 200)
        self._home_term.pack(fill="x")
        self._tw(self._home_term, "Ready. Use quick actions above or the sidebar.\n")
        self._pages["home"] = p

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

    # ══════════════════════════════════════════════════════════
    #  PAGE — CLEAN BREW
    # ══════════════════════════════════════════════════════════

    def _pg_clean(self):
        p = ctk.CTkScrollableFrame(self._cf, fg_color="transparent",
                                   scrollbar_button_color=C["border"])
        self._section_hdr(p, "Clean Brew",
                          "Remove cache, lock files, old versions — or a full reinstall")

        wb = ctk.CTkFrame(p, fg_color="#FFF8E1", corner_radius=10,
                          border_width=1, border_color="#FFD54F")
        wb.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(wb, text="⚠️  Full Reinstall removes ALL packages and Homebrew itself. "
                     "Select packages to reinstall on the Packages page first.",
                     font=ctk.CTkFont(size=12), text_color="#7B5800",
                     wraplength=700).pack(padx=16, pady=12)

        self._clean_vars: Dict[str, tk.BooleanVar] = {}
        OPTIONS = [
            ("locks",   "🔓  Remove Lock / In-Progress Files",
             "Unlock stuck brew operations and delete .lock files",                       True,  False),
            ("cache",   "🗑️  Clear Download Cache",
             "Free disk space from ~/Library/Caches/Homebrew",                           True,  False),
            ("old",     "♻️  Remove Old Package Versions",
             "Keep only the latest version of each formula",                              True,  False),
            ("orphans", "🔄  Remove Orphan Dependencies",
             "Remove installed packages no longer needed by anything (brew autoremove)", False, False),
            ("logs",    "📋  Clear Homebrew Logs",
             "Delete all files in ~/Library/Logs/Homebrew",                              False, False),
            ("full",    "💣  Full Reinstall  (destructive)",
             "Uninstall every package, remove Homebrew entirely, then reinstall fresh",  False, True),
        ]
        self._mini_hdr(p, "Options")
        for key, title, desc, default, danger in OPTIONS:
            var = tk.BooleanVar(value=default)
            self._clean_vars[key] = var
            row = ctk.CTkFrame(p, fg_color=C["panel"], corner_radius=10,
                               border_width=1, border_color=C["border"])
            row.pack(fill="x", pady=4)
            lf = ctk.CTkFrame(row, fg_color="transparent")
            lf.pack(side="left", fill="x", expand=True, padx=16, pady=14)
            ctk.CTkLabel(lf, text=title,
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=C["err"] if danger else C["text"],
                         anchor="w").pack(fill="x")
            ctk.CTkLabel(lf, text=desc, font=ctk.CTkFont(size=11),
                         text_color=C["text2"], anchor="w").pack(fill="x")
            ctk.CTkCheckBox(row, text="", variable=var, width=30,
                            fg_color=C["err"] if danger else C["accent"],
                            hover_color=C["accent_h"],
                            border_color=C["border"]).pack(side="right", padx=18)

        ctk.CTkButton(p, text="Run Selected Actions",
                      font=ctk.CTkFont(size=14, weight="bold"),
                      fg_color=C["accent"], hover_color=C["accent_h"],
                      height=50, corner_radius=10,
                      command=self._do_clean).pack(fill="x", pady=(20, 4))
        self._pages["clean"] = p

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

        self._ps = ctk.CTkScrollableFrame(p, fg_color="transparent",
                                          scrollbar_button_color=C["border"])
        self._ps.grid(row=3, column=0, sticky="nsew")
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
        card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
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
            r1 = subprocess.run(["brew","list","--formula"], capture_output=True, text=True, timeout=12, env=_BREW_ENV)
            r2 = subprocess.run(["brew","outdated","--quiet"], capture_output=True, text=True, timeout=15, env=_BREW_ENV)
            r3 = subprocess.run(["brew","list","--cask"], capture_output=True, text=True, timeout=12, env=_BREW_ENV)
            r4 = subprocess.run(["brew","outdated","--cask","--quiet"], capture_output=True, text=True, timeout=15, env=_BREW_ENV)
            self._installed_set  = set(r1.stdout.strip().split())
            self._outdated_set   = set(r2.stdout.strip().split())
            self._cask_installed = set(r3.stdout.strip().split())
            self._cask_outdated  = set(r4.stdout.strip().split())
            n_out = len(self._outdated_set) + len(self._cask_outdated)
            self.after(0, lambda: (
                self._s_out.configure(text=str(n_out),
                                     text_color=C["warn"] if n_out else C["ok"]),
                self._refresh_grid()))
        except Exception:
            pass


    # ══════════════════════════════════════════════════════════
    #  PAGE — UPGRADES
    # ══════════════════════════════════════════════════════════

    def _pg_upgrades(self):
        p = ctk.CTkFrame(self._cf, fg_color="transparent")
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(2, weight=1)

        hdr = ctk.CTkFrame(p, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(hdr, text="Upgrades",
                     font=ctk.CTkFont(family=_SF, size=26, weight="bold"),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(hdr, text="Upgrade individual packages and pin versions to prevent accidental upgrades.",
                     font=ctk.CTkFont(size=12), text_color=C["text2"]).pack(anchor="w", pady=(2, 0))

        toolbar = ctk.CTkFrame(p, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkButton(toolbar, text="↻  Refresh",
                      fg_color=C["panel"], text_color=C["text2"],
                      hover_color=C["accent_bg"], border_width=1, border_color=C["border"],
                      height=36, width=100, corner_radius=8,
                      command=self._refresh_upgrades).pack(side="left", padx=(0, 8))
        self._upgrade_sel_btn = ctk.CTkButton(
            toolbar, text="⬆  Upgrade Selected  (0)",
            fg_color=C["accent"], hover_color=C["accent_h"],
            height=36, width=210, corner_radius=8,
            command=self._do_upgrade_selected)
        self._upgrade_sel_btn.pack(side="left", padx=(0, 6))
        ctk.CTkButton(toolbar, text="⬆⬆  Upgrade All",
                      fg_color=C["panel"], text_color=C["warn"],
                      hover_color=C["accent_bg"], border_width=1, border_color=C["warn"],
                      height=36, width=150, corner_radius=8,
                      command=self._do_upgrade_all).pack(side="left")

        self._upgrades_list = ctk.CTkScrollableFrame(
            p, fg_color="transparent", scrollbar_button_color=C["border"])
        self._upgrades_list.grid(row=2, column=0, sticky="nsew")
        self._upgrades_list.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self._upgrades_list, text="Loading…",
                     font=ctk.CTkFont(size=12), text_color=C["text3"]
                     ).grid(row=0, column=0, pady=24)
        self._pages["upgrades"] = p

    def _refresh_upgrades(self):
        self._outdated_loaded = False
        for w in self._upgrades_list.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._upgrades_list, text="Refreshing…",
                     font=ctk.CTkFont(size=12), text_color=C["text3"]
                     ).grid(row=0, column=0, pady=24)
        self._outdated_loaded = True
        threading.Thread(target=self._load_outdated_data, daemon=True).start()

    def _load_outdated_data(self):
        try:
            r1 = subprocess.run(["brew","outdated","--json=v2"],
                                capture_output=True, text=True, timeout=25, env=_BREW_ENV)
            r2 = subprocess.run(["brew","list","--pinned"],
                                capture_output=True, text=True, timeout=10, env=_BREW_ENV)
            data = json.loads(r1.stdout) if r1.stdout.strip() else {}
            formulae = data.get("formulae", [])
            casks    = [dict(c, _is_cask=True) for c in data.get("casks", [])]
            self._outdated_data = formulae + casks
            self._pinned_set    = set(r2.stdout.strip().split())
            self.after(0, self._render_upgrades)
        except Exception as exc:
            self.after(0, lambda e=exc: self._render_upgrades_error(str(e)))

    def _render_upgrades(self):
        for w in self._upgrades_list.winfo_children():
            w.destroy()
        self._upgrade_vars = {}
        self._upgrade_sel  = set()
        self._upgrade_sel_btn.configure(text="⬆  Upgrade Selected  (0)")

        if not self._outdated_data:
            ctk.CTkLabel(self._upgrades_list,
                         text="✓  All packages are up to date",
                         font=ctk.CTkFont(size=13), text_color=C["ok"]
                         ).grid(row=0, column=0, pady=32)
            return

        ctk.CTkLabel(self._upgrades_list,
                     text=f"{len(self._outdated_data)} update(s) available",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C["text"]).grid(row=0, column=0, sticky="w", padx=4, pady=(4, 8))

        for i, pkg in enumerate(self._outdated_data):
            name    = pkg.get("name", "?")
            curr    = ", ".join(pkg.get("installed_versions", ["?"])) or "?"
            new_v   = pkg.get("current_version", "?")
            is_cask = pkg.get("_is_cask", False)
            pinned  = name in self._pinned_set

            var = tk.BooleanVar(value=False)
            self._upgrade_vars[name] = var

            row = ctk.CTkFrame(self._upgrades_list, fg_color=C["panel"],
                               corner_radius=10, border_width=1, border_color=C["border"])
            row.grid(row=i+1, column=0, sticky="ew", pady=3)
            row.grid_columnconfigure(2, weight=1)

            ctk.CTkCheckBox(row, text="", variable=var, width=30,
                            fg_color=C["accent"], hover_color=C["accent_h"],
                            border_color=C["border"],
                            command=lambda n=name, v=var: self._toggle_upgrade(n, v)
                            ).grid(row=0, column=0, padx=(12, 4), pady=12)
            ctk.CTkLabel(row, text="📱" if is_cask else "📦",
                         font=ctk.CTkFont(size=16), fg_color="transparent"
                         ).grid(row=0, column=1, padx=(0, 10))
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.grid(row=0, column=2, sticky="ew", pady=10)
            name_txt = name + ("  📌 pinned" if pinned else "")
            ctk.CTkLabel(info, text=name_txt,
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=C["warn"] if pinned else C["text"],
                         anchor="w").pack(anchor="w")
            ctk.CTkLabel(info, text=f"{curr}  →  {new_v}",
                         font=ctk.CTkFont(size=11), text_color=C["warn"],
                         anchor="w").pack(anchor="w")

            bf = ctk.CTkFrame(row, fg_color="transparent")
            bf.grid(row=0, column=3, padx=12)
            if not is_cask:
                ctk.CTkButton(
                    bf,
                    text="Unpin" if pinned else "📌 Pin",
                    width=76, height=28, corner_radius=6,
                    fg_color=C["warn"] if pinned else C["panel"],
                    text_color=C["text"], border_width=1,
                    border_color=C["warn"] if pinned else C["border"],
                    hover_color=C["accent_bg"], font=ctk.CTkFont(size=11),
                    command=lambda n=name, pn=pinned: self._toggle_pin(n, pn)
                ).pack(side="left", padx=(0, 4))
            ctk.CTkButton(
                bf, text="⬆ Upgrade", width=90, height=28, corner_radius=6,
                fg_color=C["accent"] if not pinned else C["panel2"],
                hover_color=C["accent_h"],
                text_color="#FFFFFF" if not pinned else C["text3"],
                state="normal" if not pinned else "disabled",
                font=ctk.CTkFont(size=11),
                command=lambda n=name, cask=is_cask: self._do_upgrade_one(n, cask)
            ).pack(side="left")

    def _render_upgrades_error(self, msg: str = ""):
        for w in self._upgrades_list.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._upgrades_list, text=f"⚠️  {msg or 'Could not load upgrade data.'}",
                     font=ctk.CTkFont(size=12), text_color=C["err"]
                     ).grid(row=0, column=0, pady=24)

    def _toggle_upgrade(self, name: str, var: tk.BooleanVar):
        if var.get():
            self._upgrade_sel.add(name)
        else:
            self._upgrade_sel.discard(name)
        self._upgrade_sel_btn.configure(
            text=f"⬆  Upgrade Selected  ({len(self._upgrade_sel)})")

    def _toggle_pin(self, name: str, currently_pinned: bool):
        def run():
            cmd = f"brew {'unpin' if currently_pinned else 'pin'} {name}"
            subprocess.run(cmd, shell=True, capture_output=True, env=_BREW_ENV)
            self._outdated_loaded = False
            self.after(0, self._refresh_upgrades)
        threading.Thread(target=run, daemon=True).start()

    # ══════════════════════════════════════════════════════════
    #  PAGE — SERVICES
    # ══════════════════════════════════════════════════════════

    def _pg_services(self):
        p = ctk.CTkFrame(self._cf, fg_color="transparent")
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(2, weight=1)

        hdr = ctk.CTkFrame(p, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(hdr, text="Services",
                     font=ctk.CTkFont(family=_SF, size=26, weight="bold"),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(hdr, text="Manage Homebrew-installed daemons (postgresql, redis, nginx, etc.)",
                     font=ctk.CTkFont(size=12), text_color=C["text2"]).pack(anchor="w", pady=(2, 0))

        toolbar = ctk.CTkFrame(p, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkButton(toolbar, text="↻  Refresh",
                      fg_color=C["panel"], text_color=C["text2"],
                      hover_color=C["accent_bg"], border_width=1, border_color=C["border"],
                      height=36, width=100, corner_radius=8,
                      command=self._refresh_services).pack(side="left", padx=(0, 8))
        ctk.CTkButton(toolbar, text="▶  Start All",
                      fg_color=C["ok"], hover_color="#16A34A",
                      height=36, width=110, corner_radius=8,
                      command=lambda: self._svc_all("start")).pack(side="left", padx=(0, 4))
        ctk.CTkButton(toolbar, text="■  Stop All",
                      fg_color=C["err"], hover_color="#C62828",
                      height=36, width=110, corner_radius=8,
                      command=lambda: self._svc_all("stop")).pack(side="left")

        self._services_list = ctk.CTkScrollableFrame(
            p, fg_color="transparent", scrollbar_button_color=C["border"])
        self._services_list.grid(row=2, column=0, sticky="nsew")
        self._services_list.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self._services_list, text="Loading…",
                     font=ctk.CTkFont(size=12), text_color=C["text3"]
                     ).grid(row=0, column=0, pady=24)
        self._pages["services"] = p

    def _refresh_services(self):
        self._services_loaded = False
        for w in self._services_list.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._services_list, text="Refreshing…",
                     font=ctk.CTkFont(size=12), text_color=C["text3"]
                     ).grid(row=0, column=0, pady=24)
        self._services_loaded = True
        threading.Thread(target=self._load_services_data, daemon=True).start()

    def _load_services_data(self):
        try:
            r = subprocess.run(["brew", "services", "list"],
                               capture_output=True, text=True, timeout=15, env=_BREW_ENV)
            services = []
            for line in r.stdout.strip().splitlines()[1:]:
                parts = line.split()
                if not parts:
                    continue
                services.append({
                    "name":   parts[0],
                    "status": parts[1] if len(parts) > 1 else "none",
                    "user":   parts[2] if len(parts) > 2 else "",
                })
            self._services_data = services
            self.after(0, self._render_services)
        except Exception as exc:
            self.after(0, lambda e=exc: self._render_svc_error(str(e)))

    def _render_services(self):
        for w in self._services_list.winfo_children():
            w.destroy()
        if not self._services_data:
            ctk.CTkLabel(self._services_list,
                         text="No Homebrew services found.\n"
                              "Install a service like postgresql, redis, or nginx first.",
                         font=ctk.CTkFont(size=12), text_color=C["text3"]
                         ).grid(row=0, column=0, pady=32)
            return
        SC = {"started": C["ok"], "stopped": C["err"], "none": C["text3"]}
        for i, svc in enumerate(self._services_data):
            sc  = SC.get(svc["status"], C["text3"])
            row = ctk.CTkFrame(self._services_list, fg_color=C["panel"],
                               corner_radius=10, border_width=1, border_color=C["border"])
            row.grid(row=i, column=0, sticky="ew", pady=3)
            row.grid_columnconfigure(2, weight=1)
            ctk.CTkLabel(row, text="●", font=ctk.CTkFont(size=11),
                         text_color=sc, fg_color="transparent", width=22
                         ).grid(row=0, column=0, padx=(14, 4), pady=14)
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.grid(row=0, column=2, sticky="ew", pady=10)
            ctk.CTkLabel(info, text=svc["name"],
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=C["text"], anchor="w").pack(anchor="w")
            sub = svc["status"].capitalize()
            if svc["user"]:
                sub += f"  •  {svc['user']}"
            ctk.CTkLabel(info, text=sub, font=ctk.CTkFont(size=10),
                         text_color=sc, anchor="w").pack(anchor="w")
            bf = ctk.CTkFrame(row, fg_color="transparent")
            bf.grid(row=0, column=3, padx=12)
            name = svc["name"]
            if svc["status"] == "started":
                ctk.CTkButton(bf, text="■ Stop", width=72, height=28, corner_radius=6,
                              fg_color=C["err"], hover_color="#C62828",
                              font=ctk.CTkFont(size=11),
                              command=lambda n=name: self._svc_run("stop", n)
                              ).pack(side="left", padx=(0, 4))
            else:
                ctk.CTkButton(bf, text="▶ Start", width=72, height=28, corner_radius=6,
                              fg_color=C["ok"], hover_color="#16A34A",
                              font=ctk.CTkFont(size=11),
                              command=lambda n=name: self._svc_run("start", n)
                              ).pack(side="left", padx=(0, 4))
            ctk.CTkButton(bf, text="↺ Restart", width=84, height=28, corner_radius=6,
                          fg_color=C["panel2"], text_color=C["accent"],
                          hover_color=C["accent_bg"], border_width=1,
                          border_color=C["accent"], font=ctk.CTkFont(size=11),
                          command=lambda n=name: self._svc_run("restart", n)
                          ).pack(side="left")

    def _render_svc_error(self, msg: str):
        for w in self._services_list.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._services_list, text=f"⚠️  {msg}",
                     font=ctk.CTkFont(size=12), text_color=C["err"]
                     ).grid(row=0, column=0, pady=24)

    def _svc_run(self, action: str, name: str):
        def run():
            subprocess.run(["brew", "services", action, name],
                           capture_output=True, env=_BREW_ENV)
            time.sleep(0.8)
            self.after(0, self._refresh_services)
        threading.Thread(target=run, daemon=True).start()

    def _svc_all(self, action: str):
        def run():
            subprocess.run(["brew", "services", action, "--all"],
                           capture_output=True, env=_BREW_ENV)
            time.sleep(1.0)
            self.after(0, self._refresh_services)
        threading.Thread(target=run, daemon=True).start()

    # ══════════════════════════════════════════════════════════
    #  PAGE — TAPS
    # ══════════════════════════════════════════════════════════

    def _pg_taps(self):
        p = ctk.CTkFrame(self._cf, fg_color="transparent")
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(2, weight=1)

        hdr = ctk.CTkFrame(p, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(hdr, text="Tap Manager",
                     font=ctk.CTkFont(family=_SF, size=26, weight="bold"),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(hdr, text="Add or remove third-party Homebrew formula repositories.",
                     font=ctk.CTkFont(size=12), text_color=C["text2"]).pack(anchor="w", pady=(2, 0))

        toolbar = ctk.CTkFrame(p, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkButton(toolbar, text="↻  Refresh",
                      fg_color=C["panel"], text_color=C["text2"],
                      hover_color=C["accent_bg"], border_width=1, border_color=C["border"],
                      height=36, width=100, corner_radius=8,
                      command=self._refresh_taps).pack(side="left", padx=(0, 8))
        add_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        add_frame.pack(side="right")
        self._tap_entry = ctk.CTkEntry(
            add_frame,
            placeholder_text="user/repo  (e.g. homebrew/cask-fonts)",
            font=ctk.CTkFont(size=12), height=36, width=280, corner_radius=8,
            fg_color=C["panel"], border_color=C["border"], text_color=C["text"])
        self._tap_entry.pack(side="left", padx=(0, 6))
        ctk.CTkButton(add_frame, text="+ Add Tap",
                      fg_color=C["accent"], hover_color=C["accent_h"],
                      height=36, width=100, corner_radius=8,
                      command=self._do_add_tap).pack(side="left")

        self._taps_list = ctk.CTkScrollableFrame(
            p, fg_color="transparent", scrollbar_button_color=C["border"])
        self._taps_list.grid(row=2, column=0, sticky="nsew")
        self._taps_list.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self._taps_list, text="Loading…",
                     font=ctk.CTkFont(size=12), text_color=C["text3"]
                     ).grid(row=0, column=0, pady=24)
        self._pages["taps"] = p

    def _refresh_taps(self):
        self._taps_loaded = False
        for w in self._taps_list.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._taps_list, text="Refreshing…",
                     font=ctk.CTkFont(size=12), text_color=C["text3"]
                     ).grid(row=0, column=0, pady=24)
        self._taps_loaded = True
        threading.Thread(target=self._load_taps_data, daemon=True).start()

    def _load_taps_data(self):
        try:
            r = subprocess.run(["brew", "tap-info", "--json", "--installed"],
                               capture_output=True, text=True, timeout=20, env=_BREW_ENV)
            taps_json = json.loads(r.stdout) if r.stdout.strip() else []
            self._taps_data = [
                {"name":     t.get("name","?"),
                 "count":    len(t.get("formula_names",[])) + len(t.get("cask_tokens",[])),
                 "remote":   t.get("remote",""),
                 "official": t.get("name","").startswith("homebrew/")}
                for t in taps_json
            ]
            self.after(0, self._render_taps)
        except Exception as exc:
            self.after(0, lambda e=exc: self._render_taps_error(str(e)))

    def _render_taps(self):
        for w in self._taps_list.winfo_children():
            w.destroy()
        if not self._taps_data:
            ctk.CTkLabel(self._taps_list, text="No taps found.",
                         font=ctk.CTkFont(size=12), text_color=C["text3"]
                         ).grid(row=0, column=0, pady=24)
            return
        ctk.CTkLabel(self._taps_list, text=f"{len(self._taps_data)} tap(s) installed",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C["text"]).grid(row=0, column=0, sticky="w", padx=4, pady=(4, 8))
        for i, tap in enumerate(self._taps_data):
            row = ctk.CTkFrame(self._taps_list, fg_color=C["panel"],
                               corner_radius=10, border_width=1, border_color=C["border"])
            row.grid(row=i+1, column=0, sticky="ew", pady=3)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text="🍺" if tap["official"] else "🧪",
                         font=ctk.CTkFont(size=18), fg_color="transparent"
                         ).grid(row=0, column=0, padx=(14, 10), pady=12)
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.grid(row=0, column=1, sticky="ew", pady=10)
            ctk.CTkLabel(info, text=tap["name"],
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=C["text"], anchor="w").pack(anchor="w")
            n   = tap["count"]
            rem = tap["remote"]
            sub = f"{n} formula{'e' if n != 1 else ''}"
            if rem:
                sub += f"  •  {rem[:55]}{'…' if len(rem) > 55 else ''}"
            ctk.CTkLabel(info, text=sub, font=ctk.CTkFont(size=10),
                         text_color=C["text2"], anchor="w").pack(anchor="w")
            if not tap["official"]:
                ctk.CTkButton(row, text="Untap", width=78, height=28, corner_radius=6,
                              fg_color=C["err"], hover_color="#C62828",
                              font=ctk.CTkFont(size=11),
                              command=lambda n=tap["name"]: self._do_untap(n)
                              ).grid(row=0, column=2, padx=12)

    def _render_taps_error(self, msg: str):
        for w in self._taps_list.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._taps_list, text=f"⚠️  {msg}",
                     font=ctk.CTkFont(size=12), text_color=C["err"]
                     ).grid(row=0, column=0, pady=24)

    def _do_add_tap(self):
        name = self._tap_entry.get().strip()
        if not name:
            messagebox.showinfo("Add Tap", "Enter a tap name, e.g.  homebrew/cask-fonts")
            return
        self._tap_entry.delete(0, "end")
        self._run_steps("Adding Tap", f"brew tap {name}", [
            ("Add tap",      lambda: self._sh(f"brew tap {name}")),
            ("Refresh list", self._refresh_taps)])

    def _do_untap(self, name: str):
        if not messagebox.askyesno(
                "Untap", f"Remove tap  {name}?\n\n"
                "All formulae from this tap will become unavailable."):
            return
        self._run_steps("Removing Tap", f"brew untap {name}", [
            ("Untap",        lambda: self._sh(f"brew untap {name}")),
            ("Refresh list", self._refresh_taps)])

    # ══════════════════════════════════════════════════════════
    #  PAGE — SNAPSHOTS
    # ══════════════════════════════════════════════════════════

    def _pg_snapshots(self):
        p = ctk.CTkFrame(self._cf, fg_color="transparent")
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(2, weight=1)

        hdr = ctk.CTkFrame(p, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(hdr, text="Snapshots",
                     font=ctk.CTkFont(family=_SF, size=26, weight="bold"),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(hdr, text="Save & restore package state. Export/import Brewfiles for machine migrations.",
                     font=ctk.CTkFont(size=12), text_color=C["text2"]).pack(anchor="w", pady=(2, 0))

        toolbar = ctk.CTkFrame(p, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkButton(toolbar, text="📸  Take Snapshot",
                      fg_color=C["accent"], hover_color=C["accent_h"],
                      height=36, corner_radius=8,
                      command=self._do_take_snapshot).pack(side="left", padx=(0, 6))
        ctk.CTkButton(toolbar, text="⬆  Export Brewfile",
                      fg_color=C["panel"], text_color=C["text2"],
                      hover_color=C["accent_bg"], border_width=1, border_color=C["border"],
                      height=36, corner_radius=8,
                      command=self._do_export_brewfile).pack(side="left", padx=(0, 6))
        ctk.CTkButton(toolbar, text="⬇  Import Brewfile",
                      fg_color=C["panel"], text_color=C["text2"],
                      hover_color=C["accent_bg"], border_width=1, border_color=C["border"],
                      height=36, corner_radius=8,
                      command=self._do_import_brewfile).pack(side="left")

        self._snaps_list = ctk.CTkScrollableFrame(
            p, fg_color="transparent", scrollbar_button_color=C["border"])
        self._snaps_list.grid(row=2, column=0, sticky="nsew")
        self._snaps_list.grid_columnconfigure(0, weight=1)
        self._pages["snapshots"] = p

    def _refresh_snapshots(self):
        for w in self._snaps_list.winfo_children():
            w.destroy()
        snaps = self._list_snapshots()
        if not snaps:
            ctk.CTkLabel(self._snaps_list,
                         text="No snapshots yet.\nClick 📸 Take Snapshot to save your current package list.",
                         font=ctk.CTkFont(size=12), text_color=C["text3"],
                         wraplength=500).grid(row=0, column=0, pady=32)
            return
        ctk.CTkLabel(self._snaps_list,
                     text=f"{len(snaps)} snapshot(s)  —  ~/.config/brewcleaner/snapshots/",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C["text"]).grid(row=0, column=0, sticky="w", padx=4, pady=(4, 8))
        for i, snap in enumerate(snaps):
            row = ctk.CTkFrame(self._snaps_list, fg_color=C["panel"],
                               corner_radius=10, border_width=1, border_color=C["border"])
            row.grid(row=i+1, column=0, sticky="ew", pady=3)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text="📸", font=ctk.CTkFont(size=20),
                         fg_color="transparent").grid(row=0, column=0, padx=(14, 10), pady=12)
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.grid(row=0, column=1, sticky="ew", pady=10)
            ctk.CTkLabel(info, text=snap["name"],
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=C["text"], anchor="w").pack(anchor="w")
            ctk.CTkLabel(info, text=f"{snap['date']}  •  {snap['count']} packages",
                         font=ctk.CTkFont(size=10), text_color=C["text2"],
                         anchor="w").pack(anchor="w")
            bf = ctk.CTkFrame(row, fg_color="transparent")
            bf.grid(row=0, column=2, padx=12)
            ctk.CTkButton(bf, text="Restore", width=80, height=28, corner_radius=6,
                          fg_color=C["accent"], hover_color=C["accent_h"],
                          font=ctk.CTkFont(size=11),
                          command=lambda s=snap: self._do_restore_snapshot(s)
                          ).pack(side="left", padx=(0, 4))
            ctk.CTkButton(bf, text="Delete", width=68, height=28, corner_radius=6,
                          fg_color=C["panel2"], text_color=C["err"],
                          border_width=1, border_color=C["err"],
                          hover_color=C["panel2"], font=ctk.CTkFont(size=11),
                          command=lambda s=snap: self._do_delete_snapshot(s)
                          ).pack(side="left")

    def _list_snapshots(self) -> List[Dict]:
        _SNAPS_PATH.mkdir(parents=True, exist_ok=True)
        snaps = []
        for f in sorted(_SNAPS_PATH.glob("*.json"), reverse=True):
            try:
                meta = json.loads(f.read_text())
                snaps.append({"name":  meta.get("name","?"),
                              "date":  meta.get("date","?"),
                              "count": meta.get("count", 0),
                              "path":  f})
            except Exception:
                pass
        return snaps

    def _do_take_snapshot(self):
        dlg  = ctk.CTkInputDialog(text="Name this snapshot:", title="Take Snapshot")
        name = dlg.get_input()
        if not name:
            return
        def run():
            try:
                r1 = subprocess.run(["brew","list","--formula"], capture_output=True, text=True, env=_BREW_ENV)
                r2 = subprocess.run(["brew","list","--cask"],    capture_output=True, text=True, env=_BREW_ENV)
                formulae = [x for x in r1.stdout.strip().splitlines() if x]
                casks    = [x for x in r2.stdout.strip().splitlines() if x]
                _SNAPS_PATH.mkdir(parents=True, exist_ok=True)
                meta = {"name": name,
                        "date": time.strftime("%Y-%m-%d %H:%M"),
                        "count": len(formulae) + len(casks),
                        "formulae": formulae, "casks": casks}
                (_SNAPS_PATH / f"{int(time.time())}.json").write_text(json.dumps(meta, indent=2))
                self.after(0, lambda: (
                    messagebox.showinfo("Snapshot Saved",
                                       f"Saved {len(formulae)} formulae and {len(casks)} casks."),
                    self._refresh_snapshots()))
            except Exception as exc:
                self.after(0, lambda e=exc: messagebox.showerror("Error", str(e)))
        threading.Thread(target=run, daemon=True).start()

    def _do_restore_snapshot(self, snap: Dict):
        if not messagebox.askyesno(
                "Restore Snapshot",
                f"Restore \"{snap['name']}\"?\n\n"
                "Packages from the snapshot that aren't installed will be installed.\n"
                "Packages added since the snapshot will NOT be removed."):
            return
        def build_steps():
            try:
                meta     = json.loads(snap["path"].read_text())
                formulae = meta.get("formulae", [])
                casks    = meta.get("casks", [])
                r1 = subprocess.run(["brew","list","--formula"], capture_output=True, text=True, env=_BREW_ENV)
                r2 = subprocess.run(["brew","list","--cask"],    capture_output=True, text=True, env=_BREW_ENV)
                need_f   = [f for f in formulae if f not in set(r1.stdout.strip().split())]
                need_c   = [c for c in casks    if c not in set(r2.stdout.strip().split())]
                if not need_f and not need_c:
                    self.after(0, lambda: messagebox.showinfo(
                        "Nothing to do", "All packages from this snapshot are already installed."))
                    return
                steps: List[Tuple[str, Callable]] = [
                    ("Update Homebrew", self._op_update_if_stale)]
                if need_f:
                    steps.append((f"Install {len(need_f)} formula(e)",
                                  lambda f=need_f: self._op_batch_install(f)))
                if need_c:
                    steps.append((f"Install {len(need_c)} cask(s)",
                                  lambda c=need_c: self._sh("brew install --cask " + " ".join(c))))
                self.after(0, lambda: self._run_steps(
                    "Restoring Snapshot", snap["name"], steps))
            except Exception as exc:
                self.after(0, lambda e=exc: messagebox.showerror("Restore Error", str(e)))
        threading.Thread(target=build_steps, daemon=True).start()

    def _do_delete_snapshot(self, snap: Dict):
        if not messagebox.askyesno("Delete Snapshot",
                                   f"Permanently delete snapshot \"{snap['name']}\"?"):
            return
        try:
            snap["path"].unlink()
        except Exception:
            pass
        self._refresh_snapshots()

    def _do_export_brewfile(self):
        path = filedialog.asksaveasfilename(
            title="Export Brewfile",
            defaultextension="",
            initialfile="Brewfile",
            filetypes=[("Brewfile","Brewfile"), ("All","*.*")])
        if not path:
            return
        self._run_steps("Export Brewfile", path, [
            ("Run brew bundle dump", lambda: self._sh(f"brew bundle dump --file='{path}' --force"))])

    def _do_import_brewfile(self):
        path = filedialog.askopenfilename(
            title="Import Brewfile",
            filetypes=[("Brewfile","Brewfile"), ("All","*.*")])
        if not path:
            return
        if not messagebox.askyesno(
                "Import Brewfile",
                f"Install all packages listed in:\n{path}\n\nThis may take a while."):
            return
        self._run_steps("Import Brewfile", path, [
            ("Update Homebrew",     self._op_update_if_stale),
            ("Run brew bundle install", lambda: self._sh(f"brew bundle install --file='{path}'"))])


    # ══════════════════════════════════════════════════════════
    #  PAGE — BREW HEALTH
    # ══════════════════════════════════════════════════════════

    def _pg_health(self):
        p = ctk.CTkFrame(self._cf, fg_color="transparent")
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(2, weight=1)

        hdr = ctk.CTkFrame(p, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(hdr, text="Brew Health",
                     font=ctk.CTkFont(family=_SF, size=26, weight="bold"),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(hdr, text="Run brew doctor and brew missing to spot configuration problems.",
                     font=ctk.CTkFont(size=12), text_color=C["text2"]).pack(anchor="w", pady=(2, 0))

        toolbar = ctk.CTkFrame(p, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkButton(toolbar, text="🩺  Run brew doctor",
                      fg_color=C["accent"], hover_color=C["accent_h"],
                      height=36, corner_radius=8,
                      command=self._run_doctor).pack(side="left", padx=(0, 6))
        ctk.CTkButton(toolbar, text="🔍  Check Missing Deps",
                      fg_color=C["panel"], text_color=C["text2"],
                      hover_color=C["accent_bg"], border_width=1, border_color=C["border"],
                      height=36, corner_radius=8,
                      command=self._run_missing).pack(side="left", padx=(0, 6))
        ctk.CTkButton(toolbar, text="🔧  brew cleanup --prune=all",
                      fg_color=C["panel"], text_color=C["warn"],
                      hover_color=C["accent_bg"], border_width=1, border_color=C["warn"],
                      height=36, corner_radius=8,
                      command=lambda: self._run_steps(
                          "Clean All", "Pruning all old downloads",
                          [("brew cleanup --prune=all",
                            lambda: self._sh("brew cleanup --prune=all"))])
                      ).pack(side="left")

        self._health_out = self._mk_term(p, 300)
        self._health_out.grid(row=2, column=0, sticky="nsew")
        self._tw(self._health_out, "Click a button above to check your Homebrew installation.\n")
        self._pages["health"] = p

    def _run_doctor(self):
        self._health_out.configure(state="normal")
        self._health_out.delete("1.0", "end")
        self._health_out.configure(state="disabled")
        self._tw(self._health_out, "$ brew doctor\n\n")
        def run():
            r = subprocess.run(["brew", "doctor"],
                               capture_output=True, text=True, timeout=60, env=_BREW_ENV)
            output = r.stdout + r.stderr
            if not output.strip():
                output = "Your system is ready to brew! ✓"
            self.after(0, lambda: (
                self._tw(self._health_out, output + "\n"),
                self._tw(self._health_out,
                         "\n✅  All checks passed.\n" if r.returncode == 0
                         else "\n⚠️  Issues found. Review the warnings above.\n")))
        threading.Thread(target=run, daemon=True).start()

    def _run_missing(self):
        self._health_out.configure(state="normal")
        self._health_out.delete("1.0", "end")
        self._health_out.configure(state="disabled")
        self._tw(self._health_out, "$ brew missing\n\n")
        def run():
            r = subprocess.run(["brew", "missing"],
                               capture_output=True, text=True, timeout=30, env=_BREW_ENV)
            output = r.stdout + r.stderr
            if not output.strip():
                output = "No missing dependencies found. ✓"
            self.after(0, lambda: self._tw(self._health_out, output + "\n"))
        threading.Thread(target=run, daemon=True).start()

    # ══════════════════════════════════════════════════════════
    #  PAGE — DEPENDENCIES
    # ══════════════════════════════════════════════════════════

    def _pg_deps(self):
        p = ctk.CTkFrame(self._cf, fg_color="transparent")
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(3, weight=1)

        hdr = ctk.CTkFrame(p, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(hdr, text="Dependencies",
                     font=ctk.CTkFont(family=_SF, size=26, weight="bold"),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(hdr, text="View what a formula depends on, or what depends on it.",
                     font=ctk.CTkFont(size=12), text_color=C["text2"]).pack(anchor="w", pady=(2, 0))

        search_row = ctk.CTkFrame(p, fg_color="transparent")
        search_row.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        search_row.grid_columnconfigure(0, weight=1)
        self._dep_entry = ctk.CTkEntry(
            search_row,
            placeholder_text="Enter a formula name, e.g. ffmpeg or postgresql@16",
            font=ctk.CTkFont(size=13), height=40, corner_radius=10,
            fg_color=C["panel"], border_color=C["border"], text_color=C["text"])
        self._dep_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(search_row, text="🔽  Dependencies",
                      fg_color=C["accent"], hover_color=C["accent_h"],
                      height=40, width=148, corner_radius=10,
                      command=self._show_deps).grid(row=0, column=1, padx=(0, 6))
        ctk.CTkButton(search_row, text="🔼  Used By",
                      fg_color=C["panel"], text_color=C["accent"],
                      border_width=1, border_color=C["accent"],
                      hover_color=C["accent_bg"], height=40, width=110, corner_radius=10,
                      command=self._show_uses).grid(row=0, column=2)

        ctk.CTkButton(p, text="🌳  Show full installed tree",
                      fg_color="transparent", text_color=C["text3"],
                      hover_color=C["accent_bg"], height=30,
                      font=ctk.CTkFont(size=11),
                      command=self._show_full_tree).grid(row=2, column=0, sticky="w", pady=(0, 4))

        self._deps_out = self._mk_term(p, 250)
        self._deps_out.grid(row=3, column=0, sticky="nsew")
        self._tw(self._deps_out, "Enter a formula name above and click 'Dependencies' or 'Used By'.\n")
        self._pages["deps"] = p

    def _show_deps(self):
        name = self._dep_entry.get().strip()
        if not name:
            return
        self._deps_out.configure(state="normal")
        self._deps_out.delete("1.0", "end")
        self._deps_out.configure(state="disabled")
        self._tw(self._deps_out, f"$ brew deps --tree {name}\n\n")
        def run():
            r = subprocess.run(["brew", "deps", "--tree", name],
                               capture_output=True, text=True, timeout=20, env=_BREW_ENV)
            out = r.stdout or r.stderr or "(no output)"
            self.after(0, lambda: self._tw(self._deps_out, out + "\n"))
        threading.Thread(target=run, daemon=True).start()

    def _show_uses(self):
        name = self._dep_entry.get().strip()
        if not name:
            return
        self._deps_out.configure(state="normal")
        self._deps_out.delete("1.0", "end")
        self._deps_out.configure(state="disabled")
        self._tw(self._deps_out, f"$ brew uses --installed {name}\n\n")
        def run():
            r = subprocess.run(["brew", "uses", "--installed", name],
                               capture_output=True, text=True, timeout=20, env=_BREW_ENV)
            out = r.stdout.strip() or "(nothing installed depends on this package)"
            self.after(0, lambda: self._tw(self._deps_out, out + "\n"))
        threading.Thread(target=run, daemon=True).start()

    def _show_full_tree(self):
        self._deps_out.configure(state="normal")
        self._deps_out.delete("1.0", "end")
        self._deps_out.configure(state="disabled")
        self._tw(self._deps_out, "$ brew deps --tree --installed\n\n")
        def run():
            r = subprocess.run(["brew", "deps", "--tree", "--installed"],
                               capture_output=True, text=True, timeout=30, env=_BREW_ENV)
            out = r.stdout or r.stderr or "(no installed formulae with dependencies)"
            self.after(0, lambda: self._tw(self._deps_out, out + "\n"))
        threading.Thread(target=run, daemon=True).start()

    # ══════════════════════════════════════════════════════════
    #  PAGE — PROGRESS
    # ══════════════════════════════════════════════════════════

    def _pg_progress(self):
        p = ctk.CTkFrame(self._cf, fg_color="transparent")
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(4, weight=1)

        self._pr_title = ctk.CTkLabel(
            p, text="No Task Running",
            font=ctk.CTkFont(family=_SF, size=26, weight="bold"),
            text_color=C["text"])
        self._pr_title.grid(row=0, column=0, sticky="w")
        self._pr_sub = ctk.CTkLabel(
            p, text="Start a task from any page to see live progress here.",
            font=ctk.CTkFont(size=12), text_color=C["text2"])
        self._pr_sub.grid(row=1, column=0, sticky="w", pady=(2, 14))

        sp = ctk.CTkFrame(p, fg_color=C["panel"], corner_radius=12,
                          border_width=1, border_color=C["border"])
        sp.grid(row=2, column=0, sticky="ew")
        self._steps_f = ctk.CTkFrame(sp, fg_color="transparent")
        self._steps_f.pack(fill="x", padx=16, pady=12)
        self._steps_idle_lbl = ctk.CTkLabel(
            self._steps_f,
            text="Steps will appear here when a task is running.",
            font=ctk.CTkFont(size=12), text_color=C["text3"])
        self._steps_idle_lbl.pack(pady=8)

        self._pbar = ctk.CTkProgressBar(
            p, fg_color=C["border"], progress_color=C["accent"],
            height=7, corner_radius=4)
        self._pbar.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        self._pbar.set(0)

        self._pr_term = self._mk_term(p, 200)
        self._pr_term.grid(row=4, column=0, sticky="nsew", pady=(10, 0))

        self._done_btn = ctk.CTkButton(
            p, text="✓  Done — Return to Dashboard",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=C["ok"], hover_color="#16A34A",
            height=50, corner_radius=10,
            command=lambda: self._goto("home"))
        self._done_btn.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        self._done_btn.grid_remove()
        self._pages["progress"] = p

    # ══════════════════════════════════════════════════════════
    #  PAGE — SETTINGS
    # ══════════════════════════════════════════════════════════

    def _pg_settings(self):
        p = ctk.CTkScrollableFrame(self._cf, fg_color="transparent",
                                   scrollbar_button_color=C["border"])
        self._section_hdr(p, "Settings")

        # Appearance
        self._mini_hdr(p, "Appearance")
        theme_row = ctk.CTkFrame(p, fg_color=C["panel"], corner_radius=10,
                                 border_width=1, border_color=C["border"])
        theme_row.pack(fill="x", pady=4)
        lf = ctk.CTkFrame(theme_row, fg_color="transparent")
        lf.pack(side="left", fill="x", expand=True, padx=16, pady=14)
        ctk.CTkLabel(lf, text="🌙  Dark Mode",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=C["text"], anchor="w").pack(fill="x")
        ctk.CTkLabel(lf, text="Toggle between light and dark colour scheme",
                     font=ctk.CTkFont(size=11), text_color=C["text2"],
                     anchor="w").pack(fill="x")
        self._dark_sw = ctk.CTkSwitch(
            theme_row, text="",
            fg_color=C["border"], progress_color=C["accent"],
            command=self._toggle_theme)
        self._dark_sw.pack(side="right", padx=20)
        if self._prefs.get("theme") == "dark":
            self._dark_sw.select()

        # Behaviour
        self._mini_hdr(p, "Behaviour")
        for key, title, desc in [
            ("notifications", "🔔  Notifications",
             "Send a macOS notification when operations complete"),
            ("auto_refresh",  "↻  Auto-refresh on launch",
             "Re-check brew status every time BrewCleaner opens"),
        ]:
            var = tk.BooleanVar(value=self._prefs.get(key, True))
            r = ctk.CTkFrame(p, fg_color=C["panel"], corner_radius=10,
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
        self._mini_hdr(p, "About")
        ab = ctk.CTkFrame(p, fg_color=C["panel"], corner_radius=10,
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
                      fg_color="transparent", text_color=C["text3"],
                      hover_color=C["accent_bg"], height=36, corner_radius=8,
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

    def _toggle_theme(self):
        if self._task_running:
            messagebox.showwarning("Task in Progress",
                                   "Cannot switch themes while a task is running.")
            if self._prefs.get("theme") == "dark":
                self._dark_sw.select()
            else:
                self._dark_sw.deselect()
            return
        new_dark = bool(self._dark_sw.get())
        self._prefs["theme"] = "dark" if new_dark else "light"
        _save_prefs(self._prefs)
        C.update(_DARK if new_dark else _LIGHT)
        ctk.set_appearance_mode("Dark" if new_dark else "Light")
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

    # ══════════════════════════════════════════════════════════
    #  SHARED WIDGET HELPERS
    # ══════════════════════════════════════════════════════════

    def _section_hdr(self, parent, title: str, sub: str = ""):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", pady=(0, 20))
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


    # ══════════════════════════════════════════════════════════
    #  QUICK ACTIONS
    # ══════════════════════════════════════════════════════════

    def _quick(self, cmd: str):
        def run():
            self.after(0, lambda: self._tw(self._home_term, f"\n$ {cmd}\n"))
            buf: List[str] = []
            buf_lock = threading.Lock()

            def flush():
                with buf_lock:
                    if buf:
                        self._tw(self._home_term, "".join(buf))
                        buf.clear()

            def sched():
                flush()
                if not getattr(self, "_quick_running", False):
                    return
                self.after(50, sched)

            self._quick_running = True
            self.after(50, sched)
            try:
                proc = subprocess.Popen(
                    cmd, shell=True,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, env=_BREW_ENV, bufsize=1)
                for line in iter(proc.stdout.readline, ""):
                    with buf_lock:
                        buf.append(line)
                proc.wait()
                self._quick_running = False
                self.after(0, flush)
                self.after(0, lambda rc=proc.returncode: self._tw(
                    self._home_term,
                    f"\n{'✅' if rc == 0 else '⚠️'}  Done (exit {rc})\n"))
            except Exception as exc:
                self._quick_running = False
                self.after(0, lambda e=exc: self._tw(self._home_term, f"\n❌  {e}\n"))
            threading.Thread(target=self._probe, daemon=True).start()

        threading.Thread(target=run, daemon=True).start()

    # ══════════════════════════════════════════════════════════
    #  UPGRADE ACTIONS
    # ══════════════════════════════════════════════════════════

    def _do_upgrade_one(self, name: str, is_cask: bool):
        flag = "--cask" if is_cask else ""
        self._run_steps(f"Upgrading {name}", name, [
            ("Update Homebrew",   self._op_update_if_stale),
            (f"Upgrade {name}",   lambda n=name, f=flag:
             self._sh(f"brew upgrade {f} {n}".strip())),
            ("Refresh list",      self._refresh_upgrades)])

    def _do_upgrade_selected(self):
        if not self._upgrade_sel:
            messagebox.showinfo("Nothing Selected", "Tick at least one package to upgrade.")
            return
        pkgs = sorted(self._upgrade_sel)
        self._run_steps("Upgrading Selected", f"{len(pkgs)} package(s)", [
            ("Update Homebrew",            self._op_update_if_stale),
            (f"Upgrade {len(pkgs)} pkg(s)",lambda p=pkgs: self._sh("brew upgrade " + " ".join(p))),
            ("Refresh list",               self._refresh_upgrades)])

    def _do_upgrade_all(self):
        if not messagebox.askyesno("Upgrade All",
                                   "Upgrade all installed formulae and casks?\n"
                                   "This may take several minutes."):
            return
        self._run_steps("Upgrading All", "brew upgrade", [
            ("Update Homebrew",  self._op_update_if_stale),
            ("Upgrade formulae", lambda: self._sh("brew upgrade")),
            ("Upgrade casks",    lambda: self._sh("brew upgrade --cask")),
            ("Refresh list",     self._refresh_upgrades)])

    # ══════════════════════════════════════════════════════════
    #  CLEAN ACTION
    # ══════════════════════════════════════════════════════════

    def _do_clean(self):
        opts = {k: v.get() for k, v in self._clean_vars.items()}
        if opts["full"] and not messagebox.askyesno(
                "Confirm Full Reinstall",
                "This will UNINSTALL every package and REMOVE Homebrew entirely,\n"
                "then reinstall Homebrew fresh.\n\nThis cannot be undone. Proceed?",
                icon="warning"):
            return
        steps: List[Tuple[str, Callable]] = []
        if opts["locks"]:
            steps.append(("Remove Lock Files",    self._op_rm_locks))
        if opts["cache"]:
            steps.append(("Clear Cache",          lambda: self._sh("brew cleanup --prune=all")))
        if opts["old"]:
            steps.append(("Remove Old Versions",  lambda: self._sh("brew cleanup")))
        if opts["orphans"]:
            steps.append(("Remove Orphans",       lambda: self._sh("brew autoremove")))
        if opts["logs"]:
            steps.append(("Clear Logs",           self._op_rm_logs))
        if opts["full"]:
            steps += [
                ("Uninstall All Packages", self._op_uninstall_all),
                ("Remove Homebrew",        self._op_rm_brew),
                ("Install Homebrew",       self._op_install_brew),
                ("Update Homebrew",        lambda: self._sh("brew update")),
            ]
        if not steps:
            messagebox.showinfo("Nothing Selected", "Tick at least one option.")
            return
        needs_sudo = opts["locks"] or opts["full"]
        if needs_sudo and not self._acquire_sudo():
            return
        self._run_steps("Cleaning Brew", f"{len(steps)} operation(s) queued", steps)

    # ══════════════════════════════════════════════════════════
    #  INSTALL ACTION
    # ══════════════════════════════════════════════════════════

    def _do_install(self):
        total = len(self._selected) + len(self._cask_sel)
        if not total:
            messagebox.showinfo("No Selection", "Select at least one package.")
            return
        conflicts: Dict[str, List[str]] = {}
        for pid in self._selected:
            pkg = self._find_pkg(pid)
            if not pkg:
                continue
            found = [n for spec, n in pkg.get("conflicts", [])
                     if self._chk_conflict(spec)]
            if found:
                conflicts[pkg["label"]] = found
        if conflicts:
            self._conflict_dlg(conflicts, self._actually_install)
        else:
            self._actually_install()

    def _actually_install(self):
        formulae = sorted(self._selected)
        casks    = sorted(self._cask_sel)
        steps: List[Tuple[str, Callable]] = [
            ("Update Homebrew", self._op_update_if_stale),
        ]
        if formulae:
            steps.append((f"Pre-fetch bottles  ({len(formulae)} formula)",
                          lambda f=formulae: self._op_prefetch(f)))
            steps.append((f"Install {len(formulae)} formula(e)",
                          lambda f=formulae: self._op_batch_install(f)))
        if casks:
            steps.append((f"Install {len(casks)} cask(s)",
                          lambda c=casks: self._sh("brew install --cask " + " ".join(c))))
        self._run_steps("Installing Packages",
                        f"{len(formulae)+len(casks)} package(s) queued", steps)

    def _find_pkg(self, pid: str) -> Optional[Dict]:
        for pks in PKGS.values():
            for p in pks:
                if p["id"] == pid:
                    return p
        for p in self._custom_pkgs:
            if p["id"] == pid:
                return p
        return None

    def _chk_conflict(self, spec: str) -> bool:
        if spec.startswith("cmd:"):
            try:
                return subprocess.run(
                    ["which", spec[4:]], capture_output=True, timeout=3
                ).returncode == 0
            except Exception:
                return False
        return os.path.exists(os.path.expanduser(spec))

    def _conflict_dlg(self, conflicts: Dict[str, List[str]], on_proceed: Callable):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Conflicts Detected")
        dlg.geometry("500x400")
        dlg.configure(fg_color=C["bg"])
        dlg.grab_set()
        dlg.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()  - 500) // 2
        y = self.winfo_y() + (self.winfo_height() - 400) // 2
        dlg.geometry(f"+{x}+{y}")
        ctk.CTkLabel(dlg, text="⚠️  Conflicts Detected",
                     font=ctk.CTkFont(family=_SF, size=18, weight="bold"),
                     text_color=C["text"]).pack(pady=(22, 4))
        ctk.CTkLabel(dlg,
                     text="Other installations of these packages exist on this Mac:",
                     font=ctk.CTkFont(size=12), text_color=C["text2"]).pack()
        sc = ctk.CTkScrollableFrame(dlg, fg_color=C["panel"],
                                    corner_radius=10, height=180)
        sc.pack(fill="x", padx=20, pady=14)
        for lbl, items in conflicts.items():
            ctk.CTkLabel(sc, text=f"  {lbl}",
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=C["text"]).pack(anchor="w", padx=8, pady=(8, 2))
            for item in items:
                ctk.CTkLabel(sc, text=f"    • {item} found",
                             font=ctk.CTkFont(size=11),
                             text_color=C["warn"]).pack(anchor="w", padx=8)
        bf = ctk.CTkFrame(dlg, fg_color="transparent")
        bf.pack(fill="x", padx=20, pady=(0, 20))
        bf.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(bf, text="Install Anyway",
                      fg_color=C["accent"], hover_color=C["accent_h"],
                      command=lambda: [dlg.destroy(), on_proceed()]
                      ).grid(row=0, column=0, padx=(0, 5), sticky="ew")
        ctk.CTkButton(bf, text="Cancel",
                      fg_color="transparent", text_color=C["text2"],
                      hover_color=C["border"], border_width=1, border_color=C["border"],
                      command=dlg.destroy
                      ).grid(row=0, column=1, padx=(5, 0), sticky="ew")

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

    # ══════════════════════════════════════════════════════════
    #  STEP RUNNER
    # ══════════════════════════════════════════════════════════

    def _run_steps(self, title: str, sub: str, steps: List[Tuple[str, Callable]]):
        self._task_running   = True
        self._task_title_str = title
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
        # Reset caches so next page visit fetches fresh data
        self._pkg_state_loaded = False
        self._installed_set    = set()
        self._outdated_set     = set()
        self._outdated_loaded  = False
        self._services_loaded  = False
        self._taps_loaded      = False
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

    # ══════════════════════════════════════════════════════════
    #  SYSTEM PROBE
    # ══════════════════════════════════════════════════════════

    def _probe(self):
        try:
            r = subprocess.run(["brew", "--version"],
                               capture_output=True, text=True, timeout=8)
            if r.returncode == 0:
                ver = r.stdout.splitlines()[0].replace("Homebrew", "").strip()
                self._brew_ok = True
                self.after(0, lambda v=ver: self._on_brew_found(v))
            else:
                raise RuntimeError
        except Exception:
            self._brew_ok = False
            self.after(0, self._on_brew_missing)
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

    # ══════════════════════════════════════════════════════════
    #  BREW OPERATIONS  (all blocking — run inside _run_steps)
    # ══════════════════════════════════════════════════════════

    def _op_update_if_stale(self, max_age: int = 3600):
        stale = True
        for fh in [Path("/opt/homebrew/.git/FETCH_HEAD"),
                   Path("/usr/local/Homebrew/.git/FETCH_HEAD")]:
            if fh.exists():
                age = time.time() - fh.stat().st_mtime
                if age < max_age:
                    stale = False
                    self._log(f"  ↻  brew update skipped ({int(age)}s ago — still fresh)")
                break
        if stale:
            self._sh("brew update")

    def _op_prefetch(self, pkgs: List[str]):
        if not pkgs:
            return
        chunk_size = 6
        for chunk in [pkgs[i:i+chunk_size] for i in range(0, len(pkgs), chunk_size)]:
            self._log(f"  ⬇  Fetching: {' '.join(chunk)}")
            self._sh(f"brew fetch --force --retry {' '.join(chunk)}")

    def _op_batch_install(self, pkgs: List[str]):
        if not pkgs:
            return
        self._sh(f"brew install --force-bottle --no-quarantine {' '.join(pkgs)}")

    def _op_batch_uninstall(self, pkgs: List[str]):
        if not pkgs:
            return
        self._sh(f"brew uninstall --force --ignore-dependencies {' '.join(pkgs)}")

    def _op_rm_locks(self):
        self._log("$ Scanning for lock / in-progress files…")
        removed = 0
        for d in ["/usr/local/var/homebrew/locks", "/opt/homebrew/var/homebrew/locks"]:
            dp = Path(d)
            if not dp.exists():
                continue
            for f in dp.iterdir():
                try:
                    f.unlink()
                    removed += 1
                    self._log(f"  rm {f.name}")
                except PermissionError:
                    r = subprocess.run(["sudo", "-n", "rm", "-f", str(f)],
                                       capture_output=True, timeout=10)
                    if r.returncode == 0:
                        removed += 1
                        self._log(f"  sudo rm {f.name}")
        cache = Path.home() / "Library" / "Caches" / "Homebrew"
        for f in (list(cache.rglob("*.lock")) if cache.exists() else []):
            try:
                f.unlink()
                removed += 1
            except Exception:
                pass
        for f in Path("/tmp").glob("brew-*"):
            try:
                f.unlink()
                removed += 1
            except Exception:
                pass
        self._log(f"  → {removed} lock file(s) removed.")

    def _op_rm_logs(self):
        log_dir = Path.home() / "Library" / "Logs" / "Homebrew"
        if log_dir.exists():
            self._sh(f"rm -rf '{log_dir}/'*")

    def _op_uninstall_all(self):
        self._log("$ Listing installed formulae…")
        r = subprocess.run(["brew","list","--formula"],
                           capture_output=True, text=True, env=_BREW_ENV)
        pkgs = [x for x in r.stdout.strip().splitlines() if x]
        if pkgs:
            self._log(f"  Uninstalling {len(pkgs)} formulae…")
            self._sh("brew uninstall --force --ignore-dependencies " + " ".join(pkgs))
        else:
            self._log("  No formulae installed.")
        r2 = subprocess.run(["brew","list","--cask"],
                            capture_output=True, text=True, env=_BREW_ENV)
        casks = [x for x in r2.stdout.strip().splitlines() if x]
        if casks:
            self._log(f"  Uninstalling {len(casks)} casks…")
            self._sh("brew uninstall --cask --force " + " ".join(casks))
        self._log("  → All packages removed.")

    def _op_rm_brew(self):
        self._log("$ Running official Homebrew uninstall script…")
        env = {**_BREW_ENV, "NONINTERACTIVE": "1", "CI": "1"}
        dl = subprocess.run(
            ["curl","-fsSL",
             "https://raw.githubusercontent.com/Homebrew/install/HEAD/uninstall.sh"],
            capture_output=True, text=True, timeout=30)
        if dl.returncode != 0:
            self._log("  ⚠️  Download failed. Falling back to manual removal.")
            self._op_rm_brew_manual()
            return
        proc = subprocess.Popen(["/bin/bash"], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, env=env)
        threading.Thread(target=lambda: (proc.stdin.write(dl.stdout), proc.stdin.close()),
                         daemon=True).start()
        buf: List[str] = []
        for line in iter(proc.stdout.readline, ""):
            buf.append(line)
            if len(buf) >= 5:
                chunk = "".join(buf); buf.clear()
                self.after(0, lambda c=chunk: self._tw(self._pr_term, c))
        if buf:
            self.after(0, lambda c="".join(buf): self._tw(self._pr_term, c))
        proc.wait()
        if proc.returncode != 0:
            self._log("  ⚠️  Script exited non-zero. Running manual removal…")
            self._op_rm_brew_manual()
        else:
            self._log("  → Homebrew removed ✓")

    def _op_rm_brew_manual(self):
        self._log("$ Manual Homebrew removal…")
        for path in ["/opt/homebrew", "/usr/local/Homebrew",
                     "/usr/local/Cellar", "/usr/local/Caskroom",
                     "/usr/local/Frameworks", "/usr/local/var/homebrew",
                     "/usr/local/bin/brew"]:
            if os.path.exists(path):
                r = subprocess.run(["sudo","-n","rm","-rf", path],
                                   capture_output=True, timeout=60)
                self._log(f"  {'✓' if r.returncode == 0 else '⚠️'}  rm -rf {path}")

    def _op_install_brew(self):
        self._log("$ Downloading Homebrew install script…")
        dl = subprocess.run(
            ["curl","-fsSL",
             "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"],
            capture_output=True, text=True, timeout=30)
        if dl.returncode != 0:
            raise RuntimeError("Could not download Homebrew install script. Check your internet connection.")
        self._log("$ Running install script (NONINTERACTIVE)…")
        env = {**_BREW_ENV, "NONINTERACTIVE": "1", "CI": "1"}
        proc = subprocess.Popen(["/bin/bash"], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, env=env)
        threading.Thread(target=lambda: (proc.stdin.write(dl.stdout), proc.stdin.close()),
                         daemon=True).start()
        buf: List[str] = []
        for line in iter(proc.stdout.readline, ""):
            buf.append(line)
            if len(buf) >= 5:
                chunk = "".join(buf); buf.clear()
                self.after(0, lambda c=chunk: self._tw(self._pr_term, c))
        if buf:
            self.after(0, lambda c="".join(buf): self._tw(self._pr_term, c))
        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"Homebrew install script exited {proc.returncode}. See output above.")
        brew_bin = "/opt/homebrew/bin/brew"
        if os.path.exists(brew_bin):
            for prof in ("~/.zprofile", "~/.bash_profile", "~/.profile"):
                pf = Path(os.path.expanduser(prof))
                if pf.exists() and "homebrew" not in pf.read_text().lower():
                    pf.write_text(pf.read_text() + '\neval "$(/opt/homebrew/bin/brew shellenv)"\n')
                    self._log(f"  Added brew shellenv to {prof}")
        self._log("  → Homebrew installed ✓")


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = App()
    app.mainloop()
