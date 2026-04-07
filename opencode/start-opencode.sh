#!/bin/bash

# 1. Sync the model from llm-server to opencode.json
"$(dirname "$(readlink -f "$0")")/sync-opencode-model.sh"

# 2. Start OpenCode
# Use the found opencode command, or check common local paths
OPENCODE_BIN=$(command -v opencode || echo "$HOME/.local/bin/opencode")

if [[ ! -x "$OPENCODE_BIN" ]]; then
    echo "Error: opencode not found. Please ensure it is in your PATH or at $HOME/.local/bin/opencode"
    exit 1
fi

"$OPENCODE_BIN" "$@"