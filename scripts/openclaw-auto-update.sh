#!/bin/bash
# OpenClaw Auto-Update Checker
# Checks GitHub for new releases, tests them, installs if passing
# Run via cron weekly

set -e

REPO="openclaw/openclaw"
API_URL="https://api.github.com/repos/$REPO/releases/latest"
STATE_FILE="/home/sntrblck/.openclaw/workspace/scripts/.openclaw-last-version"
LOG_FILE="/home/sntrblck/.openclaw/workspace/scripts/openclaw-auto-update.log"
TEST_SCRIPT="/home/sntrblck/.openclaw/workspace/scripts/openclaw-update-test.sh"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Get current installed version
CURRENT_VERSION=$(openclaw --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1 || echo "unknown")
log "Current installed version: $CURRENT_VERSION"

# Get last checked version (if exists)
LAST_CHECKED=$(cat "$STATE_FILE" 2>/dev/null || echo "none")

# Fetch latest release from GitHub
log "Checking GitHub for latest release..."
LATEST=$(curl -s "$API_URL" | grep -oP '"tag_name":\s*"v\K[^"]+' | head -1)

if [ -z "$LATEST" ]; then
    log "ERROR: Failed to fetch latest version from GitHub"
    exit 1
fi

log "Latest GitHub release: $LATEST"

# Check if we've already processed this version
if [ "$LATEST" = "$LAST_CHECKED" ]; then
    log "Version $LATEST already checked. No action needed."
    exit 0
fi

# Check if this is newer than what we have
if [ "$LATEST" = "$CURRENT_VERSION" ]; then
    log "Already running version $LATEST. Updating state file."
    echo "$LATEST" > "$STATE_FILE"
    exit 0
fi

log "New version available: $LATEST (current: $CURRENT_VERSION)"

# Run the pre-flight test
log "Running pre-flight test for version $LATEST..."
if [ ! -x "$TEST_SCRIPT" ]; then
    log "ERROR: Test script not found or not executable: $TEST_SCRIPT"
    exit 1
fi

if "$TEST_SCRIPT" "$LATEST" >> "$LOG_FILE" 2>&1; then
    log "Pre-flight test PASSED for version $LATEST"
    
    # Install the new version
    log "Installing openclaw@$LATEST..."
    if npm install -g "openclaw@$LATEST" >> "$LOG_FILE" 2>&1; then
        log "SUCCESS: Installed openclaw@$LATEST"
        echo "$LATEST" > "$STATE_FILE"
        
        # Restart gateway
        log "Restarting gateway..."
        systemctl --user restart openclaw-gateway >> "$LOG_FILE" 2>&1 || true
        sleep 3
        
        # Verify
        NEW_VERSION=$(openclaw --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1 || echo "unknown")
        log "Verified installed version: $NEW_VERSION"
        
        # Notify on success
        if command -v send-notify &>/dev/null; then
            send-notify "OpenClaw Updated" "Successfully updated to $NEW_VERSION"
        fi
    else
        log "ERROR: Failed to install openclaw@$LATEST"
        exit 1
    fi
else
    log "Pre-flight test FAILED for version $LATEST - NOT INSTALLING"
    log "Check $LOG_FILE for details"
    echo "$LATEST" > "$STATE_FILE"  # Mark as checked so we don't retry immediately
    exit 1
fi

log "Auto-update check complete."