"""
Reusable blocking brew operations run inside _run_steps.

Part of the App class mixin split (v4.0) — see brewcleaner.py's App
class definition for how all these mixins are combined, and
ROADMAP.md for why this split was done as a second, isolated pass
after the v4.0 logic/bugfix pass rather than bundled with it.

This file only contains methods that were already in brewcleaner.py's
App class (v3.1.3/early v4.0) — moved here verbatim, unchanged, under
the "Reusable blocking brew operations run inside _run_steps." section. No behavior was changed by this move.
"""

import os
import subprocess
import threading
import time
from pathlib import Path
from ui._shared import *  # noqa: F401,F403 — ctk, tk, C, PKGS, CASKS, etc.

class BrewOpsMixin:
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
