#!/bin/bash
#
# Install llm-server to ~/.local/bin (or /usr/local/bin with sudo)
#

set -euo pipefail

REPO="https://raw.githubusercontent.com/raketenkater/llm-server/main"
FILES=(llm-server llm-server-gui)

# Determine install directory
if [[ "${1:-}" == "--system" ]]; then
    INSTALL_DIR="/usr/local/bin"
    [[ $EUID -ne 0 ]] && { echo "Error: --system requires sudo"; exit 1; }
else
    INSTALL_DIR="${HOME}/.local/bin"
    mkdir -p "$INSTALL_DIR"
fi

echo "Installing to $INSTALL_DIR..."

for f in "${FILES[@]}"; do
    curl -sfL "$REPO/$f" -o "$INSTALL_DIR/$f"
    chmod +x "$INSTALL_DIR/$f"
    echo "  Installed $f"
done

# Check if install dir is in PATH
if ! echo "$PATH" | tr ':' '\n' | grep -qx "$INSTALL_DIR"; then
    echo ""
    echo "WARNING: $INSTALL_DIR is not in your PATH."
    echo "Add this to your ~/.bashrc or ~/.zshrc:"
    echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
fi

echo ""
echo "Done! Run: llm-server <model.gguf>"
