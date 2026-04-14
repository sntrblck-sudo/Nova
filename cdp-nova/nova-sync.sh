#!/bin/bash
# nova-sync.sh — Weekly backup + push to GitHub + Google Drive
# Run via cron every Sunday at 11 PM ET

set -e

WORKSPACE="/home/sntrblck/.openclaw/workspace"
cd "$WORKSPACE"

echo "[sync] $(date) — Starting weekly sync"

# 1. Create encrypted backup (with Google Drive upload)
echo "[sync] Running encrypted backup..."
bash cdp-nova/nova-backup.sh gdrive || echo "[sync] Backup/gdrive upload had issues, continuing..."

# 2. Ensure all changes are committed
echo "[sync] Checking for uncommitted changes..."
if ! git diff --quiet || ! git diff --cached --quiet; then
  git add -A
  git commit -m "Weekly auto-sync $(date +%Y-%m-%d)" || true
fi

# 3. Push to GitHub
echo "[sync] Pushing to GitHub..."
git push origin master 2>&1 || echo "[sync] Push failed, will retry next cycle"

echo "[sync] $(date) — Weekly sync complete"