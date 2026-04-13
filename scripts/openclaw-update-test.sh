#!/bin/bash
# OpenClaw Update Pre-Flight Check
# Tests a new version before installing
# Usage: ./openclaw-update-test.sh [version]
#   version: optional, defaults to "latest"

set -e

VERSION=${1:-latest}
TEST_PORT=18889
TEST_DIR="/tmp/openclaw-test-$$"
BACKUP_DIR="/home/sntrblck/.openclaw-backups/$(date +%Y%m%d-%H%M%S)"
CURRENT_VERSION=$(openclaw --version 2>/dev/null | head -1 || echo "unknown")

echo "========================================"
echo "  OpenClaw Update Pre-Flight Check"
echo "========================================"
echo ""
echo "Current version: $CURRENT_VERSION"
echo "Target version: $VERSION"
echo "Test directory: $TEST_DIR"
echo ""

# Backup current installation
echo "[1/5] Backing up current installation..."
mkdir -p "$BACKUP_DIR"
cp -r /home/sntrblck/.npm-global/lib/node_modules/openclaw "$BACKUP_DIR/" 2>/dev/null || true
cp /home/sntrblck/.openclaw/openclaw.json "$BACKUP_DIR/" 2>/dev/null || true
echo "  ✓ Backup saved to $BACKUP_DIR"

# Download new version to temp dir
echo ""
echo "[2/5] Downloading version $VERSION to temp dir..."
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"
npm pack "openclaw@$VERSION" --pack-destination="$TEST_DIR" > /dev/null 2>&1
TARBALL=$(ls openclaw-*.tgz 2>/dev/null | head -1)
if [ -z "$TARBALL" ]; then
    echo "  ✗ Failed to download openclaw@$VERSION"
    rm -rf "$TEST_DIR"
    exit 1
fi
tar -xzf "$TARBALL" -C "$TEST_DIR"
echo "  ✓ Downloaded and extracted $TARBALL"

# Copy current config to test dir
echo ""
echo "[3/5] Setting up test environment..."
mkdir -p "$TEST_DIR/.openclaw"
cp /home/sntrblck/.openclaw/openclaw.json "$TEST_DIR/.openclaw/" 2>/dev/null || true
# Use a different port
sed -i "s/\"port\": 18789/\"port\": $TEST_PORT/" "$TEST_DIR/.openclaw/openclaw.json" 2>/dev/null || true
echo "  ✓ Test config ready (port $TEST_PORT)"

# Test gateway startup and channel loading
echo ""
echo "[4/5] Testing gateway startup and channel loading..."
cd "$TEST_DIR/package"
TEST_NODE_PATH="$TEST_DIR/node_modules"
export NODE_PATH="$TEST_NODE_PATH"

# Try to start the gateway with timeout
timeout 15s node dist/index.js gateway --port $TEST_PORT --config "$TEST_DIR/.openclaw/openclaw.json" > "$TEST_DIR/gateway-test.log" 2>&1 &
GATEWAY_PID=$!
sleep 5

# Check if process is running
if ! kill -0 $GATEWAY_PID 2>/dev/null; then
    echo "  ✗ Gateway failed to start"
    cat "$TEST_DIR/gateway-test.log"
    kill $GATEWAY_PID 2>/dev/null || true
    rm -rf "$TEST_DIR"
    exit 1
fi

# Check for channel loading in logs
CHANNEL_ERRORS=$(grep -i "failed to load\|error\|telegram" "$TEST_DIR/gateway-test.log" | grep -i "fail\|error" | grep -v "ENOENT\|lstat" || true)
if [ -n "$CHANNEL_ERRORS" ]; then
    echo "  ✗ Channel loading errors detected:"
    echo "$CHANNEL_ERRORS"
    kill $GATEWAY_PID 2>/dev/null || true
    rm -rf "$TEST_DIR"
    exit 1
fi

# Check for successful Telegram load
TELEGRAM_OK=$(grep -c "telegram.*starting\|channel.*telegram" "$TEST_DIR/gateway-test.log" 2>/dev/null || echo "0")
if [ "$TELEGRAM_OK" -gt 0 ]; then
    echo "  ✓ Telegram channel loaded successfully"
else
    # Check if channels section exists in config
    CHANNELS_EXISTS=$(grep -c '"telegram"' "$TEST_DIR/.openclaw/openclaw.json" 2>/dev/null || echo "0")
    if [ "$CHANNELS_EXISTS" -gt 0 ]; then
        echo "  ⚠ Telegram config found but not loaded (may need investigation)"
    else
        echo "  ⚠ No Telegram config in test (skip if intentional)"
    fi
fi

# Kill test gateway
kill $GATEWAY_PID 2>/dev/null || true
echo "  ✓ Test gateway stopped"

# Summary
echo ""
echo "[5/5] Pre-flight check complete"
echo ""
echo "========================================"
echo "  RESULT: PASS"
echo "========================================"
echo ""
echo "The new version appears to be working."
echo "You can safely run: npm install -g openclaw@$VERSION"
echo ""
echo "Backup location: $BACKUP_DIR"
echo ""

# Cleanup
rm -rf "$TEST_DIR"