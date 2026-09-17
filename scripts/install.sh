#!/usr/bin/env bash
set -euo pipefail

# ══════════════════════════════════════════════════════════════
#  BrewCleaner installer — v4.0
#
#  v3.1.3 always pointed the `brewcleaner` command at
#  `/usr/bin/python3` (Apple's system Python). That Python's bundled
#  Tcl/Tk is the one known to hard-crash on some macOS 13.x point
#  releases with "macOS 13 (1307) or later required, have instead
#  13 (1306)" — a bug in Tk itself, not in BrewCleaner, but one this
#  installer can steer around by picking a Python with a working Tk
#  *before* ever wiring up the `brewcleaner` command.
# ══════════════════════════════════════════════════════════════

GITHUB_USER="danh2011"
REPO_NAME="BrewCleaner"
SCRIPT_NAME="brewcleaner.py"
PKG_DIR_NAME="brewcleaner_pkg"
APP_NAME="brewcleaner"
INSTALL_DIR="/usr/local/share/${APP_NAME}"
BIN_DIR="/usr/local/bin/${APP_NAME}"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "This installer is only supported on macOS."
    exit 1
fi

MAC_VER="$(sw_vers -productVersion 2>/dev/null || echo "0.0")"
MAC_MAJOR="${MAC_VER%%.*}"
echo "[installer] Detected macOS ${MAC_VER}."
if [[ "${MAC_MAJOR}" -lt 11 ]]; then
    echo "[installer] Warning: BrewCleaner targets macOS 11 (Big Sur) and later."
    echo "            It may still work on ${MAC_VER}, but Homebrew itself may not support it."
fi

# ── Pick a Python with a working Tk ─────────────────────────────
# Preference order: an existing Homebrew python3 (already has a
# modern Tcl/Tk via python-tk), then Homebrew's own `python@3.x`,
# falling back to whatever `python3` resolves to on PATH last,
# since that may be the system one with the broken Tk.
tk_probe() {
    # Returns 0 if this interpreter can create+destroy a Tk root
    # window without aborting. Runs in a subprocess deliberately —
    # if Tk aborts, only the subprocess dies, not this installer.
    "$1" -c "import tkinter; r = tkinter.Tk(); r.destroy()" >/dev/null 2>&1
}

find_good_python() {
    local candidates=()
    [[ -x "/opt/homebrew/bin/python3" ]] && candidates+=("/opt/homebrew/bin/python3")
    [[ -x "/usr/local/bin/python3" ]] && candidates+=("/usr/local/bin/python3")
    command -v python3 >/dev/null 2>&1 && candidates+=("$(command -v python3)")
    candidates+=("/usr/bin/python3")

    for py in "${candidates[@]}"; do
        if [[ -x "${py}" ]] && tk_probe "${py}"; then
            echo "${py}"
            return 0
        fi
    done
    return 1
}

echo "[installer] Looking for a Python with a working Tk…"
if PYTHON_BIN="$(find_good_python)"; then
    echo "[installer] Using ${PYTHON_BIN}"
else
    echo "[installer] No working Tk found yet — trying to install one via Homebrew."
    if ! command -v brew >/dev/null 2>&1; then
        echo "[installer] Homebrew isn't installed. Install it first from https://brew.sh,"
        echo "            then re-run this installer."
        exit 1
    fi
    brew install python-tk || true
    if PYTHON_BIN="$(find_good_python)"; then
        echo "[installer] Using ${PYTHON_BIN} (after installing python-tk)."
    else
        echo "[installer] Still couldn't find a Python whose Tk actually starts."
        echo "            This is the same crash as: \"macOS 13 (1307) or later required, have instead 13 (1306)\""
        echo "            It's a bug in Tcl/Tk 8.6.12, not in BrewCleaner."
        echo "            Try:  brew reinstall python-tk"
        echo "            Then re-run this installer."
        exit 1
    fi
fi

echo "[installer] Installing ${APP_NAME}…"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

RAW_BASE="https://raw.githubusercontent.com/${GITHUB_USER}/${REPO_NAME}/main"
curl -fsSL "${RAW_BASE}/${SCRIPT_NAME}" -o "${TMP_DIR}/${SCRIPT_NAME}"
curl -fsSL "${RAW_BASE}/menubar_app.py" -o "${TMP_DIR}/menubar_app.py"

# Pull down the support package too (v4.0 split logic out of the
# single script — see brewcleaner_pkg/ in the repo).
mkdir -p "${TMP_DIR}/${PKG_DIR_NAME}"
for f in __init__.py version.py system.py prefs.py brew_env.py update.py snapshots.py disk.py tk_preflight.py notify.py; do
    curl -fsSL "${RAW_BASE}/${PKG_DIR_NAME}/${f}" -o "${TMP_DIR}/${PKG_DIR_NAME}/${f}"
done

# And the GUI itself, also split into a package as of v4.0 (see ui/
# in the repo — App is built from these mixins).
UI_DIR_NAME="ui"
mkdir -p "${TMP_DIR}/${UI_DIR_NAME}"
for f in __init__.py _shared.py splash.py core.py command_palette.py \
         page_dashboard.py page_clean.py page_packages.py page_upgrades.py \
         page_services.py page_taps.py page_snapshots.py page_health.py \
         page_deps.py page_progress.py page_settings.py widget_helpers.py \
         actions_quick.py actions_upgrade.py actions_clean.py actions_install.py \
         sudo.py step_runner.py probe.py brew_ops.py; do
    curl -fsSL "${RAW_BASE}/${UI_DIR_NAME}/${f}" -o "${TMP_DIR}/${UI_DIR_NAME}/${f}"
done

sudo mkdir -p "${INSTALL_DIR}"
echo "[installer] Moving files to ${INSTALL_DIR}…"
sudo rm -rf "${INSTALL_DIR:?}/${PKG_DIR_NAME}" "${INSTALL_DIR:?}/${UI_DIR_NAME}"
sudo mv "${TMP_DIR}/${SCRIPT_NAME}" "${INSTALL_DIR}/${SCRIPT_NAME}"
sudo mv "${TMP_DIR}/menubar_app.py" "${INSTALL_DIR}/menubar_app.py"
sudo mv "${TMP_DIR}/${PKG_DIR_NAME}" "${INSTALL_DIR}/${PKG_DIR_NAME}"
sudo mv "${TMP_DIR}/${UI_DIR_NAME}" "${INSTALL_DIR}/${UI_DIR_NAME}"

echo "[installer] Creating launch command at ${BIN_DIR}…"
cat <<EOF | sudo tee "${BIN_DIR}" > /dev/null
#!/usr/bin/env bash
exec "${PYTHON_BIN}" "${INSTALL_DIR}/${SCRIPT_NAME}" "\$@"
EOF
sudo chmod +x "${BIN_DIR}"

echo "[installer] Verifying the installed app can at least start Tk…"
if ! tk_probe "${PYTHON_BIN}"; then
    echo "[installer] Warning: the chosen Python's Tk failed the final check."
    echo "            The command was installed anyway, but running it may crash."
    echo "            See the troubleshooting note above (brew reinstall python-tk)."
fi

echo "[installer] ${APP_NAME} installation complete!"
echo "You can run the app using the command: ${APP_NAME}"
