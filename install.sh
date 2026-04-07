#!/bin/bash
#
# install.sh — Robust installer for llm-server and downloader
# Installs to ~/.local/bin and ensures dependencies are met.
#

set -euo pipefail

INSTALL_DIR="${HOME}/.local/bin"
MODEL_DIR="${HOME}/ai_models"
mkdir -p "$INSTALL_DIR"
mkdir -p "$MODEL_DIR"

echo "═══ llm-server Installer ═══"
echo "Target directory: $INSTALL_DIR"
echo ""

# Detect platform and select appropriate files
OS="$(uname -s)"
case "$OS" in
    Darwin)
        FILES=("llm-server-mac" "llm-server-gui" "llm-opencode")
        # On macOS, also create a 'llm-server' symlink pointing to the mac version
        SYMLINK_MAC=1
        ;;
    *)
        FILES=("llm-server" "llm-server-gui" "llm-opencode")
        SYMLINK_MAC=0
        ;;
esac

for f in "${FILES[@]}"; do
    if [[ -f "$f" ]]; then
        cp "$f" "$INSTALL_DIR/$f"
        chmod +x "$INSTALL_DIR/$f"
        echo "  ✓ Installed $f"
    else
        echo "  ⚠ Warning: $f not found in current directory, skipping."
    fi
done

# On macOS, symlink llm-server → llm-server-mac so both names work
if (( SYMLINK_MAC )) && [[ -f "$INSTALL_DIR/llm-server-mac" ]]; then
    ln -sf "$INSTALL_DIR/llm-server-mac" "$INSTALL_DIR/llm-server"
    echo "  ✓ Symlinked llm-server → llm-server-mac"
fi

# Install the downloader to the model dir
if [[ -f "$MODEL_DIR/download_any_gguf.py" ]]; then
    echo "  ✓ Downloader already exists in $MODEL_DIR"
else
    if [[ -f "download_any_gguf.py" ]]; then
        cp "download_any_gguf.py" "$MODEL_DIR/download_any_gguf.py"
        echo "  ✓ Installed download_any_gguf.py to $MODEL_DIR"
    fi
fi

echo ""
echo "── Checking Dependencies ──"

# Check for python dependencies
if command -v python3 >/dev/null 2>&1; then
    echo "  ✓ python3 found"
    if python3 -c "import huggingface_hub, tqdm" >/dev/null 2>&1; then
        echo "  ✓ huggingface_hub and tqdm found"
    else
        echo "  ⚠ Installing Python dependencies..."
        if python3 -m pip install --user huggingface_hub tqdm >/dev/null 2>&1; then
            echo "  ✓ Installed huggingface_hub and tqdm"
        else
            echo "  ⚠ Warning: pip install failed. Run manually: pip install huggingface_hub tqdm"
        fi
    fi
else
    echo "  ✗ Error: python3 not found. Downloader will not work."
    echo "    Install: apt install python3 python3-pip  OR  brew install python3"
fi

# Check for GPU acceleration
if [[ "$OS" == "Darwin" ]]; then
    if system_profiler SPDisplaysDataType 2>/dev/null | grep -qi "Metal\|Apple"; then
        echo "  ✓ Apple Metal GPU detected"
    else
        echo "  ⚠ Warning: No Metal GPU detected. Will run CPU-only."
    fi
else
    if command -v nvidia-smi >/dev/null 2>&1; then
        echo "  ✓ nvidia-smi found (GPU acceleration enabled)"
    else
        echo "  ⚠ Warning: nvidia-smi not found. Script will fallback to CPU-only if no GPUs detected."
    fi
fi

# Check PATH
SHELL_RC="$HOME/.bashrc"
[[ "$OS" == "Darwin" ]] && SHELL_RC="$HOME/.zshrc"
if ! echo "$PATH" | tr ':' '\n' | grep -qx "$INSTALL_DIR"; then
    echo ""
    echo "  ⚠ WARNING: $INSTALL_DIR is not in your PATH."
    echo "    Add this to your $SHELL_RC:"
    echo "    export PATH=\"$INSTALL_DIR:\$PATH\""
fi

echo ""
echo "Done! You can now run:"
echo "  llm-server <model.gguf>      # Smart Launcher"
echo "  llm-server-gui               # Model Selector (TUI)"
echo "  llm-server <repo> --download # Smart Downloader"
echo "  llm-opencode                 # Sync config + launch OpenCode"
