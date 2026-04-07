#!/bin/bash

# Configuration
# Find the config file in a portable way
CONFIG_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/opencode/opencode.json"
[[ ! -f "$CONFIG_FILE" ]] && CONFIG_FILE="$HOME/.opencode.json"

MODELS_URL="http://localhost:8081/v1/models"
SLOTS_URL="http://localhost:8081/slots"

echo "Syncing OpenCode model with llm-server..."

# 1. Fetch the current model ID from the server
MODEL_ID=$(curl -s "$MODELS_URL" | jq -r '.data[0].id')

if [ -z "$MODEL_ID" ] || [ "$MODEL_ID" == "null" ]; then
    echo "Error: Could not fetch model ID from server. Is the server running?"
    exit 1
fi

echo "Detected model: $MODEL_ID"

# 2. Fetch the actual context size from the server slots
# We use the first slot's n_ctx as the baseline
SERVER_CTX=$(curl -s "$SLOTS_URL" | jq -r '.[0].n_ctx')

if [ -z "$SERVER_CTX" ] || [ "$SERVER_CTX" == "null" ]; then
    echo "Warning: Could not fetch context size from server. Defaulting to 65536."
    SERVER_CTX=65536
fi

# 3. Calculate the safe limit (10% less than server context)
SAFE_CTX=$(( SERVER_CTX * 90 / 100 ))

echo "Server context: $SERVER_CTX | OpenCode safe limit: $SAFE_CTX"

# 4. Update opencode.json using jq
TMP_FILE=$(mktemp)
jq --arg mid "$MODEL_ID" --argjson ctx "$SAFE_CTX" \
   '.provider["llama-cpp"].models = {($mid): {"name": $mid, "limit": {"context": $ctx, "output": 16384}}} | .model = "llama-cpp/" + $mid' \
   "$CONFIG_FILE" > "$TMP_FILE" && mv "$TMP_FILE" "$CONFIG_FILE"

if [ $? -eq 0 ]; then
    echo "Successfully updated $CONFIG_FILE"
    echo "  - Model: $MODEL_ID"
    echo "  - Context Limit: $SAFE_CTX"
else
    echo "Error: Failed to update configuration file."
    exit 1
fi
