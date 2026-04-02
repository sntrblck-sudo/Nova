#!/bin/bash
# Nova API Server Manager
# Checks if API server + tunnel are alive; restarts if not
# Runs every 30 min via cron

set -e

PORT=3001
API_DIR="/home/sntrblck/.openclaw/workspace/cdp-nova"
TUNNEL_URL_FILE="$API_DIR/nova-api-server/tunnel_url.txt"
LOG_FILE="$API_DIR/server_manager.log"

log() {
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $1" | tee -a "$LOG_FILE"
}

check_server() {
  curl -s -m 5 "http://localhost:$PORT/health" > /dev/null 2>&1
}

check_tunnel() {
  local url
  url=$(cat "$TUNNEL_URL_FILE" 2>/dev/null || echo "")
  if [ -z "$url" ]; then
    return 1
  fi
  curl -s -m 5 "$url/health" > /dev/null 2>&1
}

restart_server() {
  log "API server or tunnel down — restarting..."
  
  # Kill anything on port 3001
  fuser -k $PORT/tcp 2>/dev/null || true
  sleep 1
  
  # Start x402 server v3
  cd "$API_DIR"
  node nova-api-server/x402_server.cjs >> "$API_DIR/server.log" 2>&1 &
  sleep 2
  
  # Start localtunnel with fresh random subdomain
  npx --yes localtunnel --port $PORT > "$API_DIR/tunnel.log" 2>&1 &
  sleep 10
  
  # Extract new tunnel URL
  local new_url
  new_url=$(grep -o 'https://[^ ]*\.loca\.lt' "$API_DIR/tunnel.log" 2>/dev/null | head -1 || echo "")
  
  if [ -n "$new_url" ]; then
    echo "$new_url" > "$TUNNEL_URL_FILE"
    log "Server restarted. New tunnel: $new_url"
  else
    log "Tunnel URL not found in tunnel.log — check manually"
    cat "$API_DIR/tunnel.log" >> "$API_DIR/tunnel.log.bak" 2>/dev/null || true
  fi
}

# Main
if check_server && check_tunnel; then
  log "API server + tunnel OK"
else
  restart_server
fi
