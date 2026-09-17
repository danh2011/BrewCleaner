"""
App core: init, splash hookup, state, main window build, sidebar, status bar.

Part of the App class mixin split (v4.0) — see brewcleaner.py's App
class definition for how all these mixins are combined, and
ROADMAP.md for why this split was done as a second, isolated pass
after the v4.0 logic/bugfix pass rather than bundled with it.

This file only contains methods that were already in brewcleaner.py's
App class (v3.1.3/early v4.0) — moved here verbatim, unchanged, under
the "App core: init, splash hookup, state, main window build, sidebar, status bar." section. No behavior was changed by this move.
"""

import threading
from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, PKGS, CASKS, etc.
from ui.splash import _Splash

class CoreMixin:

    # ── init ─────────────────────────────────────────────────

    def __init__(self):
        super().__init__()
        self.withdraw()
        self.title("BrewCleaner")
        self.geometry("1160x740")
        self.minsize(980, 640)

        self._prefs = _load_prefs()
        theme = self._prefs.get("theme", "system")
        
        if theme == "system":
            ctk.set_appearance_mode("System")
            actual_mode = ctk.get_appearance_mode() 
            C.update(_DARK if actual_mode == "Dark" else _LIGHT)
        else:
            ctk.set_appearance_mode(theme.capitalize())
            C.update(_DARK if theme == "dark" else _LIGHT)

        self._init_state()
        
        # Show the splash screen FIRST
        self._probe_done = threading.Event()
        self._splash = _Splash(self, on_done=self._on_splash_done, loading_event=self._probe_done)

        # Defer the heavy UI building by 50ms so the splash renders instantly
        self.after(50, self._deferred_startup)

    def _deferred_startup(self):
        self._build()
        if self._prefs.get("auto_refresh", True):
            threading.Thread(target=self._probe, daemon=True).start()
        else:
            self._probe_done.set()  # no probe — mark done immediately so splash can close

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
        # v4.0: command palette — Cmd+K on macOS, Ctrl+K as a fallback
        # for anyone running this off a non-Mac keyboard layout.
        self._palette_win = None
        self.bind_all("<Command-k>", self._open_command_palette)
        self.bind_all("<Control-k>", self._open_command_palette)
        # v4.0 accessibility pass: standard macOS "preferences" shortcut,
        # and Cmd+1..9 to jump straight to a page by position, for
        # anyone who prefers not to reach for a mouse/trackpad at all.
        self.bind_all("<Command-,>", lambda e: self._goto("settings"))
        for i, (pid, _icon, _label) in enumerate(NAV_ITEMS[:9], start=1):
            self.bind_all(f"<Command-Key-{i}>", lambda e, p=pid: self._goto(p))
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

        # v4.0: NAV_ITEMS now lives in ui/_shared.py, shared with the
        # command palette (ui/command_palette.py) so they can't drift.
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

        ctk.CTkLabel(sb, text=f"v{APP_VERSION}  •  open source\n⌘K to jump  •  ⌘1-9 for pages",
                     font=ctk.CTkFont(size=10), text_color=C["text3"],
                     fg_color="transparent", justify="center").grid(row=3, column=0, sticky="s", pady=(0, 14))

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


