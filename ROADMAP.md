# BrewCleaner v4.0 — what changed, what didn't, and why

This was done in three passes: (1) core logic/safety fixes, (2) the
GUI mixin split, (3) new UI features. Each pass was verified before
moving to the next — see `tests/` for what "verified" means for a
Tk app with no display available during development (short version:
static analysis of every method body, plus actually building the
real merged `App` class from stubbed tkinter/customtkinter and
asserting it succeeds — see `tests/test_ui_wiring.py`).

## Pass 1 — core logic, safety, the crash you hit

**The crash** (`macOS 13 (1307) or later required, have instead 13
(1306)`) is a bug in Tcl/Tk 8.6.12, not a BrewCleaner bug — it
misreads certain macOS point releases and hard-aborts before Python's
own error handling runs. Fixed two ways:
- `scripts/install.sh` now probes several Pythons for a working Tk
  before wiring up the `brewcleaner` command, preferring Homebrew +
  `python-tk` over Apple's system Python.
- `brewcleaner_pkg/tk_preflight.py` probes Tk in a subprocess at
  startup, so a bad install fails with a clear message instead of
  `zsh: abort`.

**Architecture, part 1.** Non-GUI logic split out of the single
3,500-line script into `brewcleaner_pkg/`: `system.py` (macOS/Xcode
detection), `prefs.py` (versioned preferences), `brew_env.py`,
`update.py` (self-update), `snapshots.py` (restore diffing),
`disk.py` (disk usage reporting).

**Three real bugs fixed**, all the same shape — a function or method
accidentally defined twice in the same file, so the first copy
silently became dead code (Python doesn't warn about this):
`_xcode_install_guidance`, `App._show_xcode_banner`/`_hide_xcode_banner`,
and `App._show_full_tree` (where the copy that *won* was the worse
one — 30s timeout, no `TimeoutExpired` handling — vs. the shadowed
copy's 120s + proper handling).

**Self-update hardened.** The old code wrote the downloaded script
directly over the running file with no validation, and its exception
handler duplicated the download-and-write logic a second time in a
way that could throw `UnboundLocalError` on top of the original
failure. Now: download → validate (parses as Python, contains the
expected version, checksum-verified if published) → write to a temp
file → atomic `os.replace()`.

## Pass 2 — GUI mixin split

The ~2,600-line `App` class is now built from 22 mixins under `ui/`,
one per section of the original file (Dashboard, Clean, Packages,
Upgrades, Services, Taps, Snapshots, Health, Deps, Progress, Settings,
plus the cross-cutting action/helper sections):

```python
class App(CoreMixin, DashboardMixin, ..., CommandPaletteMixin, ctk.CTk):
    pass
```

Cross-cutting state (theme colors, the `PKGS`/`CASKS` catalogue,
ctk/tk imports, prefs/system/update helpers) lives in `ui/_shared.py`,
imported by every mixin via `from ui._shared import *` — this avoids
circular imports between `App`'s home script and its own mixins.

Two real off-by-one bugs were found and fixed *during* this split (an
orphaned bracket, a truncated method body) by actually verifying line
ranges rather than assuming a mechanical extraction was clean.
`tests/test_ui_wiring.py` now guards against this class of bug
permanently — it imports every mixin and builds the real merged
class on every CI run, including an explicit check that no method
name is defined in two mixins at once.

## Pass 3 — new features

- **Native notifications** (`brewcleaner_pkg/notify.py`) — wired into
  the step-runner's completion hook, so any finished task (install,
  upgrade, clean, restore) fires a native macOS notification whether
  or not the app is in focus. Respects the existing notifications
  preference.
- **Command palette** (`ui/command_palette.py`, ⌘K or Ctrl+K) —
  deliberately scoped to page navigation only, not arbitrary actions.
  A palette that can fuzzy-match into a destructive brew command is a
  much bigger, riskier feature than one that jumps to a page; this is
  the safe version of that idea. Extending it to safe actions (Take
  Snapshot, Check for Updates) is a natural, low-risk follow-up.
- **Keyboard shortcuts** — ⌘, for Settings (standard macOS
  convention), ⌘1–⌘9 to jump straight to a page.
- **Snapshot restore UI** — the "also remove packages not in the
  snapshot" option is wired into the Snapshots page with a dedicated
  confirm step before anything destructive runs.
- **Disk space report** on the Clean page, showing what cleanup would
  actually free instead of asking you to run it blind.
- **Accessibility, part 1: color contrast.** `brewcleaner_pkg/a11y.py`
  computes WCAG 2.1 contrast ratios and checks them against the app's
  actual theme colors in `tests/test_a11y.py`. This caught two real
  failures in the light theme (the "ok"/green and "warn"/amber
  indicator colors were both under the 3:1 minimum against a white
  panel) — both fixed to slightly darker shades that keep the same
  color identity while passing AA.
- **Menu bar mode** (`brewcleaner --menubar`) — runs as its own
  lightweight process via `rumps`, not alongside the main Tk app in
  the same process (Tk and rumps would fight over the event loop).
  Shows an outdated-package count, refreshes every 30 minutes, and
  has one-click "Open BrewCleaner" (spawns the full GUI as a normal
  subprocess), "Quick Clean" (`brew cleanup -s --prune=all`, nothing
  more destructive than that from the menu bar on purpose), and
  "Check Now". All the actual logic (`brewcleaner_pkg/menubar_core.py`)
  is unit tested without needing `rumps` installed; the thin
  `rumps.App` wrapper (`menubar_app.py`) is kept as small as possible
  since it can't be tested outside real macOS.

## What's still open

- **Menu bar mode doesn't start at login or run as a true background
  service** — it's a process you start with `--menubar` and it runs
  until you quit it. A LaunchAgent plist to auto-start it is a
  natural, self-contained follow-up.
- **Accessibility, part 2: VoiceOver / native screen-reader labels
  and focus order.** This is genuinely limited by what Tk exposes on
  macOS (it doesn't map cleanly onto NSAccessibility the way a native
  AppKit app does) — worth investigating further, but it's a research
  task more than a coding task, and shouldn't be promised as "done"
  without someone actually testing it with VoiceOver on a real Mac.
- **Command palette actions** beyond navigation (see above).
- **Packaging/distribution** (`.app` bundling, code signing, a
  self-hosted Cask) — explicitly out of scope per your request; still
  worth doing later as its own self-contained piece of work.
- **Checksum/signature infrastructure** for self-update — `update.py`
  checks for a `<file>.sha256` next to each release and verifies it
  if present, but nothing publishes that file yet. Closing the loop
  just needs `shasum -a 256 brewcleaner.py > brewcleaner.py.sha256`
  committed alongside each release.
