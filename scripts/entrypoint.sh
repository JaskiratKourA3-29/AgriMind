#!/usr/bin/env bash
set -euo pipefail

echo "================================================="
echo " AgriMind Production Container Entrypoint"
echo "================================================="

# 1. Resolve persistent paths with standard defaults
TARGET_MODEL="${AGRIMIND_MODEL_PATH:-/var/lib/agrimind/models/best_model.pth}"
UPLOADS_DIR="${AGRIMIND_UPLOADS_DIR:-/var/lib/agrimind/community_uploads}"
DB_PATH="${AGRIMIND_DB_PATH:-/var/lib/agrimind/cases.db}"
EXPECTED_SHA256="eb40b4d9ff9bc8278b63392809702fc17dbe701b05974c8a620588ab56c196d5"

# 2. Ensure persistent storage directories exist
echo "[AgriMind] Initializing persistent storage directories..."
mkdir -p "$(dirname "$TARGET_MODEL")"
mkdir -p "$UPLOADS_DIR"
mkdir -p "$(dirname "$DB_PATH")"

# 3. Model Checkpoint Verification & Download
if [ -f "$TARGET_MODEL" ]; then
    echo "[AgriMind] Found existing model checkpoint at: $TARGET_MODEL"
    echo "[AgriMind] Verifying SHA-256 integrity..."
    ACTUAL_SHA256=$(sha256sum "$TARGET_MODEL" | awk '{print $1}')
    if [ "$ACTUAL_SHA256" = "$EXPECTED_SHA256" ]; then
        echo "[AgriMind] Checkpoint integrity verified successfully ($ACTUAL_SHA256)."
    else
        echo "[AgriMind] WARNING: Checkpoint SHA-256 mismatch!"
        echo "  Expected: $EXPECTED_SHA256"
        echo "  Actual:   $ACTUAL_SHA256"
        echo "[AgriMind] Removing corrupted checkpoint and re-downloading..."
        rm -f "$TARGET_MODEL"
    fi
fi

if [ ! -f "$TARGET_MODEL" ]; then
    if [ -z "${MODEL_DOWNLOAD_URL:-}" ]; then
        echo "[AgriMind] ERROR: MODEL_DOWNLOAD_URL is not set and model checkpoint is missing at $TARGET_MODEL."
        echo "[AgriMind] Please set MODEL_DOWNLOAD_URL to the direct HTTPS release asset URL."
        exit 1
    else
        echo "[AgriMind] Downloading model from: $MODEL_DOWNLOAD_URL..."
        TEMP_MODEL="${TARGET_MODEL}.tmp.$$"
        curl -fSL --retry 3 --retry-delay 5 "$MODEL_DOWNLOAD_URL" -o "$TEMP_MODEL"
        
        echo "[AgriMind] Verifying downloaded model SHA-256..."
        DOWNLOAD_SHA256=$(sha256sum "$TEMP_MODEL" | awk '{print $1}')
        if [ "$DOWNLOAD_SHA256" = "$EXPECTED_SHA256" ]; then
            mv "$TEMP_MODEL" "$TARGET_MODEL"
            echo "[AgriMind] Model verified and installed successfully to $TARGET_MODEL."
        else
            echo "[AgriMind] ERROR: Downloaded model SHA-256 checksum mismatch!"
            echo "  Expected: $EXPECTED_SHA256"
            echo "  Actual:   $DOWNLOAD_SHA256"
            rm -f "$TEMP_MODEL"
            exit 1
        fi
    fi
fi

# 4. Hand off execution to Uvicorn using exec for clean signal handling
APP_PORT="${PORT:-8000}"
echo "[AgriMind] Starting Uvicorn on 0.0.0.0:$APP_PORT..."
exec uvicorn src.api.app:app --host 0.0.0.0 --port "$APP_PORT"

