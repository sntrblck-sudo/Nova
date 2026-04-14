#!/bin/bash
# nova-backup.sh — Weekly encrypted backup of Nova's critical state
# Usage: ./nova-backup.sh [gdrive]
#   gdrive: upload to Google Drive after creating archive
#
# Restores with: tar xzf nova-backup-YYYYMMDD.tar.gz.gpg

set -e

WORKSPACE="/home/sntrblck/.openclaw/workspace"
BACKUP_DIR="$WORKSPACE/backups"
TIMESTAMP=$(date +%Y%m%d)
ARCHIVE="$BACKUP_DIR/nova-backup-$TIMESTAMP.tar.gz"
ENCRYPTED="$ARCHIVE.gpg"

# Passphrase — sourced from env or file
if [ -z "$NOVA_BACKUP_PASSPHRASE" ]; then
  if [ -f "$WORKSPACE/.backup-passphrase" ]; then
    NOVA_BACKUP_PASSPHRASE=$(cat "$WORKSPACE/.backup-passphrase")
  else
    echo "ERROR: Set NOVA_BACKUP_PASSPHRASE or create $WORKSPACE/.backup-passphrase"
    exit 1
  fi
fi

mkdir -p "$BACKUP_DIR"

echo "[backup] Creating archive for $TIMESTAMP..."

# Create tar of critical files (secrets, DBs, state)
tar czf "$ARCHIVE" \
  -C "$WORKSPACE" \
  cdp-nova/nova-wallet.json \
  cdp-nova/.env \
  cdp-nova/email_config.json \
  cdp-nova/gemini_oauth_client.json \
  cdp-nova/backup-wallet-1.json \
  cdp-nova/backup-wallet-2.json \
  cdp-nova/social-manager/social-state.json \
  memory/ \
  MEMORY.md \
  SOUL.md \
  IDENTITY.md \
  USER.md \
  AGENTS.md \
  HEARTBEAT.md \
  TOOLS.md \
  BOOTSTRAP.md \
  2>/dev/null || true

echo "[backup] Encrypting..."

# Encrypt with passphrase
echo "$NOVA_BACKUP_PASSPHRASE" | gpg --batch --yes --passphrase-fd 0 \
  --symmetric --cipher-algo AES256 -o "$ENCRYPTED" "$ARCHIVE"

# Remove unencrypted archive
rm -f "$ARCHIVE"

SIZE=$(du -h "$ENCRYPTED" | cut -f1)
echo "[backup] Done: $ENCRYPTED ($SIZE)"

# Upload to Google Drive if requested
if [ "$1" = "gdrive" ]; then
  echo "[backup] Uploading to Google Drive..."
  cd "$WORKSPACE/cdp-nova"
  node google_drive.cjs upload "$ENCRYPTED" "Nova Backups/nova-backup-$TIMESTAMP.tar.gz.gpg" 2>&1 || {
    echo "[backup] Google Drive upload failed — file available at $ENCRYPTED"
    exit 0
  }
  echo "[backup] Uploaded to Google Drive: Nova Backups/nova-backup-$TIMESTAMP.tar.gz.gpg"
fi

# Keep only last 4 local backups
ls -t "$BACKUP_DIR"/nova-backup-*.gpg 2>/dev/null | tail -n +5 | xargs -r rm -f
echo "[backup] Cleaned old backups (keeping last 4)"