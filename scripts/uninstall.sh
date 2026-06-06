#!/usr/bin/env bash
set -euo pipefail

# Config (keep synced with install.sh)
GITHUB_USER="danh2011"
REPO_NAME="BrewCleaner"
SCRIPT_NAME="brewcleaner.py"
APP_NAME="brewcleaner"
INSTALL_DIR="/usr/local/share/${APP_NAME}"
BIN_PATH="/usr/local/bin/${APP_NAME}"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "This uninstaller is only supported on macOS."
    exit 1
fi

echo "[uninstaller] Preparing to remove ${APP_NAME}..."

if [[ ! -e "${INSTALL_DIR}" && ! -e "${BIN_PATH}" ]]; then
    echo "[uninstaller] Nothing to uninstall: ${INSTALL_DIR} and ${BIN_PATH} not found."
    exit 0
fi

read -r -p "Are you sure you want to permanently remove ${APP_NAME} from this system? (y/N) " answer
case "${answer}" in
    [yY]|[yY][eE][sS]) ;;
    *)
        echo "Aborting.";
        exit 1 ;;
esac

# If the bin file exists, do a safety check to see if it references the installed script
if [[ -e "${BIN_PATH}" ]]; then
    # Try to read contents (works for wrapper script files)
    bin_contents="$(cat "${BIN_PATH}" 2>/dev/null || true)"
    if [[ -n "${bin_contents}" && "${bin_contents}" != *"${INSTALL_DIR}/${SCRIPT_NAME}"* ]]; then
        echo "[uninstaller] Warning: ${BIN_PATH} does not appear to point to ${INSTALL_DIR}/${SCRIPT_NAME}."
        read -r -p "Remove ${BIN_PATH} anyway? (y/N) " confirmbin
        case "${confirmbin}" in
            [yY]|[yY][eE][sS]) ;;
            *)
                echo "Skipping removal of ${BIN_PATH}."
                BIN_PATH="" ;;
        esac
    fi
fi

if [[ -n "${BIN_PATH}" && -e "${BIN_PATH}" ]]; then
    echo "[uninstaller] Removing ${BIN_PATH}..."
    sudo rm -f "${BIN_PATH}"
fi

if [[ -d "${INSTALL_DIR}" ]]; then
    echo "[uninstaller] Removing ${INSTALL_DIR}..."
    sudo rm -rf "${INSTALL_DIR}"
fi

echo "[uninstaller] ${APP_NAME} removal complete."

exit 0
