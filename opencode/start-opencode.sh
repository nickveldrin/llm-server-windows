#!/bin/bash

# 0. Check if OpenCode is already running (prevent duplicate instances)
existing_pid=$(pgrep -x opencode | head -1)
if [[ -n "$existing_pid" ]]; then
    echo "OpenCode is already running (PID $existing_pid)."
    echo "Kill it first: kill $existing_pid"
    exit 1
fi

# 1. Find and run the sync script
BASE_DIR="$(dirname "$(readlink -f "$0")")"
SYNC_SCRIPT=""
SEARCH_PATHS=(
    "$BASE_DIR/sync-opencode-model.sh"                     # Flat layout
    "$BASE_DIR/opencode/sync-opencode-model.sh"            # Sub-script mode
    "$HOME/llm-server/opencode/sync-opencode-model.sh"    # Git clone mode
)

for path in "${SEARCH_PATHS[@]}"; do
    if [[ -x "$path" ]]; then
        SYNC_SCRIPT="$path"
        break
    fi
done

if [[ -n "$SYNC_SCRIPT" ]]; then
    "$SYNC_SCRIPT"
else
    echo "Warning: sync-opencode-model.sh not found. Skipping config sync."
fi

# 2. Start OpenCode
# Use the found opencode command, or check common local paths
OPENCODE_BIN=$(command -v opencode || echo "$HOME/.local/bin/opencode")

if [[ ! -x "$OPENCODE_BIN" ]]; then
    echo "Error: opencode not found. Please ensure it is in your PATH or at $HOME/.local/bin/opencode"
    exit 1
fi

"$OPENCODE_BIN" "$@"