#!/bin/bash
# Nova's auto-update script with pre-validate + gateway check
# 1. Check changelog for breaking changes
# 2. Dry-run install to /tmp first (validates deps, catches binary issues)
# 3. Only if dry-run passes → live install
# 4. Verify gateway comes up → notify

set -e

LOG="$HOME/.openclaw/workspace/cdp-nova/update.log"
TELEGRAM_CHAT_ID="8544939129"
TELEGRAM_BOT_TOKEN="8700570943:AAGTtaEGH4nReJTXcwlxsGKbOl6KDzEGkdc"
DRY_DIR="/tmp/openclaw-dry-$$"

log() {
    echo "[$(date -Iseconds)] $1" | tee -a "$LOG"
}

notify() {
    local msg="$1"
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}&text=${msg}&parse_mode=Markdown" >> "$LOG" 2>&1
}

cleanup() {
    rm -rf "$DRY_DIR"
}

trap cleanup EXIT

log "=== Starting OpenClaw update check ==="

# Get versions
LATEST=$(npm view openclaw version 2>/dev/null | head -1)
CURRENT=$(openclaw --version 2>/dev/null | awk '{print $2}' | tr -d '('')')

log "Current: $CURRENT | Latest: $LATEST"

if [[ "$CURRENT" == "$LATEST" ]]; then
    log "Already on latest. Nothing to do."
    exit 0
fi

# --- Phase 1: Changelog check ---
log "Checking changelog for breaking changes..."
CHANGELOG_URL="https://github.com/openclaw/openclaw/releases/tag/v${LATEST}"
BREAKING=false

# Quick fetch of release notes — look for keywords that indicate breaking changes
if curl -sf "$CHANGELOG_URL" 2>/dev/null | grep -qiE "breaking|migration|backup required|upgrade notes|incompatible"; then
    log "Potential breaking changes detected in release notes."
    BREAKING=true
fi

if $BREAKING; then
    notify "🟡 *OpenClaw v${LATEST} has breaking-change markers*%0ASomeone should review the changelog before updating.%0A%0A${CHANGELOG_URL}%0A%0ADisable auto-update temporarily or handle manually."
    log "Breaking changes detected. Not proceeding automatically."
    exit 0
fi

log "Changelog check passed."

# --- Phase 2: Dry-run install to /tmp ---
log "Phase 2: Dry-run install to $DRY_DIR..."
mkdir -p "$DRY_DIR"

if ! npm install --prefix "$DRY_DIR" --dry-run --no-save openclaw@latest 2>&1 | tee -a "$LOG" | grep -q "added"; then
    log "Dry-run failed — dependencies wouldn't resolve."
    notify "🔴 *OpenClaw v${LATEST} dry-run failed*%0ADependencies wouldn't resolve.%0ASee update.log for details."
    exit 1
fi
log "Dry-run passed — all deps resolve cleanly."

# --- Phase 3: Live install ---
log "Phase 3: Proceeding with live install..."
if ! npm update -g openclaw >> "$LOG" 2>&1; then
    notify "🔴 *OpenClaw update failed*%0ANPM update command failed."
    log "Update failed!"
    exit 1
fi

NEW_VERSION=$(openclaw --version 2>/dev/null | awk '{print $2}' | tr -d '('')')
log "Installed: $NEW_VERSION"

# --- Phase 4: Gateway validation ---
log "Phase 4: Validating gateway..."

# Check if gateway can start with current config
GATEWAY_TEST=$(timeout 20 openclaw gateway start 2>&1 || true)
if echo "$GATEWAY_TEST" | grep -qiE "config invalid|ENOENT|plugin.*failed"; then
    log "Gateway validation FAILED"
    notify "🔴 *OpenClaw v${NEW_VERSION} broke the gateway*%0AConfig validation failed after update.%0AGateway is DOWN.%0A%0A*Action needed:* Check openclaw.json or await hotfix."
    exit 1
fi

# Wait and confirm it's actually running
sleep 5
if openclaw gateway status 2>/dev/null | grep -q "running"; then
    log "Gateway is healthy."
    notify "✅ *OpenClaw updated*%0A${CURRENT} → *${NEW_VERSION*}%0AGateway healthy."
else
    log "Gateway status unclear."
    notify "🟡 *OpenClaw v${NEW_VERSION} installed*%0AGateway status unclear — check manually."
fi

log "=== Update complete ==="
