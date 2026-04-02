#!/bin/bash
# Nova API Server Launcher
# Starts the x402-paid API server with tunnel

cd /home/sntrblck/.openclaw/workspace/cdp-nova

# Kill any existing instance on port 3001
fuser -k 3001/tcp 2>/dev/null

# Start the API server in background
node nova-api-server/index.cjs &
API_PID=$!
echo "API server PID: $API_PID"

# Wait for it to start
sleep 2

# Start localtunnel
npx --yes localtunnel --port 3001 --subdomain nova-nova-api &
LT_PID=$!
echo "Localtunnel PID: $LT_PID"

# Wait for tunnel
sleep 8

# Get the URL
URL=$(curl -s http://localhost:3001/health 2>/dev/null && echo "Server OK" || echo "Server failed")
echo "Server status: $URL"

# Save tunnel URL
echo "https://nova-nova-api.loca.lt" > nova-api-server/tunnel_url.txt
echo "Tunnel URL saved"
