"""
Services page.

Part of the App class mixin split (v4.0) — see brewcleaner.py's App
class definition for how all these mixins are combined, and
ROADMAP.md for why this split was done as a second, isolated pass
after the v4.0 logic/bugfix pass rather than bundled with it.

This file only contains methods that were already in brewcleaner.py's
App class (v3.1.3/early v4.0) — moved here verbatim, unchanged, under
the "Services page." section. No behavior was changed by this move.
"""

import subprocess
import threading
import time
from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, PKGS, CASKS, etc.

class ServicesMixin:
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
            row.grid(row=i, column=0, sticky="ew", pady=4, padx=8)
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

