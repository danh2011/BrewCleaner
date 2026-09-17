# BrewCleaner
![MacOS badge](https://img.shields.io/badge/mac%20os-000000?style=for-the-badge&logo=apple&logoColor=white) ![python language badge](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue)

BrewCleaner is open-source software for macOS which helps users find issues with Homebrew & fix them — clean up stale caches and old versions, manage packages and casks, check dependencies, run health checks, snapshot and restore your package list, and more.

## Requirements
BrewCleaner needs the following installed:
 - Python 3.9+
 - macOS 11 (Big Sur) or later

BrewCleaner will install the following Python requirements to run correctly:
 - tkinter (with a working Tcl/Tk — see [Troubleshooting](#troubleshooting) if this fails)
 - customtkinter

If you already have any of the Python packages, BrewCleaner will detect this.
If you need a newer version of Python, please install it via [this link](https://www.python.org/downloads/).

## Install & Running
In the Terminal, run the following command to download the app:

`/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/danh2011/BrewCleaner/main/scripts/install.sh)"`

Then run `brewcleaner` in the terminal.

This will cause Python Launcher to open and BrewCleaner will open onto the TOS page.
**You have now installed BrewCleaner!**

### Menu bar mode

As of v4.0, BrewCleaner can also run as a lightweight menu bar item instead of the full window — handy if you just want an outdated-package count at a glance and quick access to Clean/Update without keeping the main window open:

`brewcleaner --menubar`

It shows how many packages are outdated, refreshes periodically, and has one-click actions to open the full app, run a quick `brew cleanup`, or check for updates immediately. Menu bar mode requires `rumps`, which the installer sets up for you the first time you run `--menubar`; see [ROADMAP.md](ROADMAP.md) for exactly what this mode does and doesn't do yet (it's a separate lightweight process, not a background service that starts at login — that's still on the roadmap).

## Uninstall
If you decide you would no longer like to use BrewCleaner, uninstall is as easy as install. Just run the following command in the Terminal:

`/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/danh2011/BrewCleaner/main/scripts/uninstall.sh)"`

## Troubleshooting

**"macOS 13 (1307) or later required, have instead 13 (1306)" / the app aborts on launch.**
This is a bug in Tcl/Tk 8.6.12 (bundled with some Python installs), not a BrewCleaner bug — it misreads certain macOS point releases and crashes before BrewCleaner's own code even runs. Fix:
```
brew install python-tk
```
then re-run `scripts/install.sh` (or just re-run `brewcleaner` if you're on a build after v4.0, which checks for this automatically).

## Project layout (v4.0)

As of v4.0, BrewCleaner's code is split into three parts instead of one large script:
- `brewcleaner.py` — bootstraps the app (installs customtkinter if missing, checks for Xcode CLT, verifies Tk actually works) and assembles the main window
- `brewcleaner_pkg/` — the non-GUI logic (macOS/Xcode detection, preferences, the self-update mechanism, snapshot diffing, disk usage reporting, notifications). Covered by automated tests in `tests/`.
- `ui/` — the GUI itself, split into one file per page/feature area, all sharing state via `ui/_shared.py`. Also covered by `tests/test_ui_wiring.py`, which verifies the whole app actually assembles correctly without needing a display.

Run the tests with:
```
pip install pytest
pytest
```

See [ROADMAP.md](ROADMAP.md) for what's changed, what's new, and what's still planned.

## Contributing
We would love if you want to contribute. This began as a solo project when I kept breaking my Homebrew with a slow internet connection and being left with locked par-installed bottles & formulas. I want to make this the best it can be as I (and many others, I'm sure) will genuinely need this. Thank you.

### License
BrewCleaner is protected by the GNU General Public License v3. You can view it [here](https://github.com/danh2011/BrewCleaner/blob/main/LICENSE).
