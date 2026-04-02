#!/bin/bash
# Nova's Google Drive Backup Script
# Creates versioned tar.gz backups and uploads to Google Drive
# Run manually: ./google_drive_backup.sh
# Or via cron: 0 9 * * 1 bash /home/sntrblck/.openclaw/workspace/cdp-nova/google_drive_backup.sh

set -e

WORKSPACE="/home/sntrblck/.openclaw/workspace"
BACKUP_DIR="$WORKSPACE/cdp-nova"
MEMORY_DIR="$WORKSPACE/memory"
BOOTSTRAP="$WORKSPACE/BOOTSTRAP.md"
DRIVE_SCRIPT="$BACKUP_DIR/google_drive.cjs"

# Backup filename with date
DATE=$(date +%Y-%m-%d)
BACKUP_NAME="nova-backup-$DATE.tar.gz"
BACKUP_PATH="/tmp/$BACKUP_NAME"

echo "=== Nova Google Drive Backup ==="
echo "Date: $DATE"

# Check if authenticated
if [ ! -f "$BACKUP_DIR/google_tokens.json" ]; then
    echo "ERROR: Not authenticated with Google Drive."
    echo "Run: node google_drive.cjs auth"
    exit 1
fi

# Create backup (exclude node_modules to keep it small)
echo "Creating backup archive..."
tar \
    --exclude='cdp-nova/node_modules' \
    --exclude='cdp-nova/email-system/node_modules' \
    -czf "$BACKUP_PATH" \
    "$BOOTSTRAP" \
    "$BACKUP_DIR" \
    "$MEMORY_DIR" \
    2>/dev/null

SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
echo "Backup size: $SIZE"

# Upload to Google Drive
echo "Uploading to Google Drive..."
RESULT=$(cd "$BACKUP_DIR" && node google_drive.cjs upload "$BACKUP_PATH" "Nova Backups" 2>&1)

if echo "$RESULT" | grep -q "Uploaded"; then
    FILE_ID=$(echo "$RESULT" | grep "ID:" | awk '{print $2}')
    LINK=$(echo "$RESULT" | grep "Link:" | awk '{print $2}')
    echo ""
    echo "✅ Backup complete!"
    echo "   File: $BACKUP_NAME"
    echo "   Link: $LINK"
    
    # Also update a "latest" backup for quick access
    cp "$BACKUP_PATH" "/tmp/nova-backup-latest.tar.gz"
    cd "$BACKUP_DIR" && node google_drive.cjs upload "/tmp/nova-backup-latest.tar.gz" "Nova Backups" 2>&1 | grep -v "Created folder"
    echo "   Latest: https://drive.google.com/file/d/1WffaHSe70n0b5r-gt8A-WoQZEoIQV1ne/view?usp=drivesdk"
else
    echo "ERROR: Upload failed"
    echo "$RESULT"
    exit 1
fi

# Cleanup
rm -f "$BACKUP_PATH" "/tmp/nova-backup-latest.tar.gz"

echo ""
echo "Done."
