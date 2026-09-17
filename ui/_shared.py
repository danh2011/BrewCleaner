"""
Shared state for the App class and its mixins (ui/*.py) — v4.0.

This is the single place that owns everything the old monolith kept
as bare module-level globals: the ctk/tk imports, the color theme
(including the live-mutable `C` dict that _Splash/App swap between
light and dark by calling `C.update(...)`), the package catalogue,
and thin re-exports of the brewcleaner_pkg functions the UI needs.

Every ui/*.py mixin does `from ui._shared import *` and gets all of
this. brewcleaner.py does the same, right after its phase-1 bootstrap
(_boot()) has confirmed customtkinter is installed — this module is
only ever imported after that point, so importing it is never what
triggers the customtkinter install.
"""

from __future__ import annotations

import sys
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from typing import Dict, List, Optional, Callable, Tuple

from brewcleaner_pkg.version import APP_VERSION, GITHUB_URL, TOS_LINES
from brewcleaner_pkg.prefs import (
    load_prefs as _load_prefs,
    save_prefs as _save_prefs,
    PREFS_PATH as _PREFS_PATH,
    SNAPS_PATH as _SNAPS_PATH,
)
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
from brewcleaner_pkg import notify as _notify_mod

_check_clt_installed = _clt_installed

# v4.0: shared with ui/command_palette.py so the command palette and
# the sidebar can never drift out of sync with each other.
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


# ══════════════════════════════════════════════════════════════
#  THEME
# ══════════════════════════════════════════════════════════════

_LIGHT: Dict[str, str] = dict(
    bg="#EEF2FF",        sidebar="#FFFFFF",     panel="#FFFFFF",
    panel2="#F8FAFF",    accent="#0078D4",      accent_h="#106EBE",
    accent_bg="#E3F0FF", border="#E2E8F0",      text="#1A1A2E",
    text2="#475569",     text3="#94A3B8",
    ok="#16A34A",        warn="#D97706",         err="#EF4444",
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

# v4.0: built by brewcleaner_pkg.brew_env so it's covered by tests and
# correctly prefers /opt/homebrew (Apple Silicon) with a fallback to
# /usr/local (Intel) — v3.1.3 only ever prepended both blindly, which
# happened to work but wasn't verified anywhere.
_BREW_ENV: Dict[str, str] = _build_brew_env()


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


__all__ = [
    "ctk", "tk", "messagebox", "filedialog",
    "Dict", "List", "Optional", "Callable", "Tuple",
    "APP_VERSION", "GITHUB_URL", "TOS_LINES",
    "_load_prefs", "_save_prefs", "_PREFS_PATH", "_SNAPS_PATH",
    "_sys_is_dark", "_get_macos_version", "_get_recommended_xcode",
    "_clt_installed", "_check_clt_installed", "_xcode_app_installed",
    "_xcode_install_guidance", "_build_brew_env",
    "_update_mod", "_snapshots_mod", "_disk_mod", "_notify_mod",
    "NAV_ITEMS",
    "_LIGHT", "_DARK", "C", "_MAC", "_SF", "_MNO", "_SPIN", "_BREW_ENV",
    "PKGS", "CASKS",
]
