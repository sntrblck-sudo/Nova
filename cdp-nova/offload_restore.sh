#!/bin/bash
# Nova Offload Restore Script
# Pulls archived directories back from Google Drive
# Usage: ./offload_restore.sh [x402-server|nova-api-server|all]

set -e

WORKSPACE="/home/sntrblck/.openclaw/workspace/cdp-nova"
DRIVE_SCRIPT="$WORKSPACE/google_drive.cjs"
ARCHIVE_DIR="$WORKSPACE/.archives"

# Archive IDs on Google Drive
X402_ID="1IIZObajVcpvx3icd02xaE7KUzjNEy5ej"
NOVA_API_ID="1R2s1NDAbd_dDm6ZUmCexcejNx6bsNU_B"

mkdir -p "$ARCHIVE_DIR"

restore() {
    local name=$1
    local id=$2
    local dest="$WORKSPACE/$name"

    if [ -d "$dest" ]; then
        echo "⚠️  $name already exists locally — skipping"
        return
    fi

    echo "📥 Restoring $name from Drive..."
    
    # Download via Drive API (we'd need a download endpoint)
    # For now: manual - download from Drive link and extract
    echo "   Download from: https://drive.google.com/file/d/$id/view"
    echo "   Save to: /tmp/$name.tar.gz"
    echo "   Then run: tar -xzf /tmp/$name.tar.gz -C $WORKSPACE"
}

if [ "$1" == "x402-server" ] || [ "$1" == "all" ]; then
    restore "x402-server" "$X402_ID"
fi

if [ "$1" == "nova-api-server" ] || [ "$1" == "all" ]; then
    restore "nova-api-server" "$NOVA_API_ID"
fi

if [ -z "$1" ]; then
    echo "Usage: $0 [x402-server|nova-api-server|all]"
    echo ""
    echo "Archived on Google Drive:"
    echo "  x402-server:       https://drive.google.com/file/d/$X402_ID/view"
    echo "  nova-api-server:    https://drive.google.com/file/d/$NOVA_API_ID/view"
fi
