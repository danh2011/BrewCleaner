#!/usr/bin/env bash
set -euo pipefail

# Config
GITHUB_USER="danh2011"
REPO_NAME="BrewCleaner"
SCRIPT_NAME="brewcleaner.py"
APP_NAME="brewcleaner"
INSTALL_DIR="/usr/local/share/${APP_NAME}"
BIN_DIR="/usr/local/bin/${APP_NAME}"

# OS check

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "This installer is only supported on macOS."
    exit 1
fi

echo "[installer] Installing ${APP_NAME}..."

# Create installation directory
TMP_DIR="$(mktemp -d)"

INSTALL_URL="https://raw.githubusercontent.com/${GITHUB_USER}/${REPO_NAME}/main/${SCRIPT_NAME}"
curl -fsSL "${INSTALL_URL}" -o "${TMP_DIR}/${SCRIPT_NAME}"

if [[ ! -f "$INSTALL_DIR" ]]; then
    sudo mkdir -p "${INSTALL_DIR}"
fi

echo "[installer] Moving ${SCRIPT_NAME} to ${INSTALL_DIR}..."
sudo mv "${TMP_DIR}/${SCRIPT_NAME}" "${INSTALL_DIR}/${SCRIPT_NAME}"

# Create launch command
echo "[installer] Creating launch command at ${BIN_DIR}..."

cat <<EOF | sudo tee "${BIN_DIR}" > /dev/null
#!/usr/bin/env bash
exec /usr/bin/python3 "${INSTALL_DIR}/${SCRIPT_NAME}" "\$@"
EOF

sudo chmod +x "${BIN_DIR}"

# Cleanup
rm -rf "${TMP_DIR}"

echo "[installer] ${APP_NAME} installation complete!"
echo "You can run the app using the command: ${APP_NAME}"