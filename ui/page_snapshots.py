"""
Snapshots page (+ Brewfile import/export).

Part of the App class mixin split (v4.0) — see brewcleaner.py's App
class definition for how all these mixins are combined, and
ROADMAP.md for why this split was done as a second, isolated pass
after the v4.0 logic/bugfix pass rather than bundled with it.

This file only contains methods that were already in brewcleaner.py's
App class (v3.1.3/early v4.0) — moved here verbatim, unchanged, under
the "Snapshots page (+ Brewfile import/export)." section. No behavior was changed by this move.
"""

import subprocess
import threading
import time
import json
from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, PKGS, CASKS, etc.

class SnapshotsPageMixin:
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
                     text_color=C["text"]).grid(row=0, column=0, sticky="w", padx=12, pady=(4, 8))
        for i, snap in enumerate(snaps):
            row = ctk.CTkFrame(self._snaps_list, fg_color=C["panel"],
                               corner_radius=10, border_width=1, border_color=C["border"])
            row.grid(row=i+1, column=0, sticky="ew", pady=4, padx=8)
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
        # v4.0: restore can now optionally remove packages that aren't
        # in the snapshot too, not just add what's missing. Uses the
        # tested brewcleaner_pkg.snapshots.plan_restore() instead of
        # duplicating diff logic here.
        remove_extras = messagebox.askyesno(
            "Restore Snapshot",
            f"Restore \"{snap['name']}\"?\n\n"
            "Packages from the snapshot that aren't installed will be installed.\n\n"
            "Also REMOVE packages that aren't in the snapshot?\n"
            "(Choose No to only add what's missing, like previous versions did.)")
        # askyesno's return only tells us Yes/No for the *combined*
        # question above, which reads awkwardly for a "cancel" — give
        # a real cancel path by re-asking to confirm before doing
        # anything destructive when they chose to remove extras.
        if remove_extras and not messagebox.askyesno(
                "Confirm Removal",
                "This will UNINSTALL packages not in the snapshot. This cannot be undone.\n\n"
                "Continue?"):
            return

        def build_steps():
            try:
                meta = json.loads(snap["path"].read_text())
                r1 = subprocess.run(["brew", "list", "--formula"], capture_output=True, text=True, env=_BREW_ENV)
                r2 = subprocess.run(["brew", "list", "--cask"], capture_output=True, text=True, env=_BREW_ENV)
                installed_formulae = r1.stdout.strip().split()
                installed_casks = r2.stdout.strip().split()

                plan = _snapshots_mod.plan_restore(
                    meta, installed_formulae, installed_casks, remove_extras=remove_extras)

                if plan.is_noop:
                    self.after(0, lambda: messagebox.showinfo(
                        "Nothing to do", "Installed packages already match this snapshot."))
                    return

                steps: List[Tuple[str, Callable]] = [("Update Homebrew", self._op_update_if_stale)]
                if plan.install_formulae:
                    steps.append((f"Install {len(plan.install_formulae)} formula(e)",
                                  lambda f=plan.install_formulae: self._op_batch_install(f)))
                if plan.install_casks:
                    steps.append((f"Install {len(plan.install_casks)} cask(s)",
                                  lambda c=plan.install_casks: self._sh("brew install --cask " + " ".join(c))))
                if plan.remove_formulae:
                    steps.append((f"Remove {len(plan.remove_formulae)} formula(e)",
                                  lambda f=plan.remove_formulae: self._sh("brew uninstall " + " ".join(f))))
                if plan.remove_casks:
                    steps.append((f"Remove {len(plan.remove_casks)} cask(s)",
                                  lambda c=plan.remove_casks: self._sh("brew uninstall --cask " + " ".join(c))))

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


