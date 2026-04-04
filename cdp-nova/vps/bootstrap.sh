#!/bin/bash
# Nova VPS Bootstrap — Run once on fresh VPS
set -e

echo "=== Nova VPS Bootstrap Starting ==="

# ─── 1. Security: Non-root user ───────────────────────────────────────────
echo "[1/8] Creating agent user..."
id agent &>/dev/null || useradd -m -s /bin/bash agent
usermod -aG sudo agent
mkdir -p /home/agent/.ssh
chmod 700 /home/agent/.ssh

# Copy authorized_keys from root
cp /root/.ssh/authorized_keys /home/agent/.ssh/ 2>/dev/null || true
chown -R agent:agent /home/agent/.ssh

# ─── 2. SSH hardening ───────────────────────────────────────────────────────
echo "[2/8] Hardening SSH..."
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
systemctl restart sshd

# ─── 3. UFW Firewall ────────────────────────────────────────────────────────
echo "[3/8] Configuring firewall (UFW)..."
ufw --force enable
ufw default deny incoming
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw reload
echo "UFW enabled: 22, 80, 443 allowed"

# ─── 4. Node.js 22.x via NodeSource ────────────────────────────────────────
echo "[4/8] Installing Node.js 22.x..."
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y nodejs
node --version
npm --version

# ─── 5. OpenClaw CLI ────────────────────────────────────────────────────────
echo "[5/8] Installing OpenClaw..."
npm install -g openclaw
openclaw --version

# ─── 6. Install hcloud CLI ─────────────────────────────────────────────────
echo "[6/8] Installing hcloud CLI..."
curl -fsSL https://github.com/hetznercloud/cli/releases/download/v2.3.0/hcloud-linux-amd64.tar.gz | tar -xz -C /usr/local/bin/
chmod +x /usr/local/bin/hcloud
hcloud server list 2>/dev/null | head -3

# ─── 7. OpenClaw workspace directory ───────────────────────────────────────
echo "[7/8] Setting up OpenClaw workspace..."
mkdir -p /opt/nova
chown -R agent:agent /opt/nova

# Copy workspace from git (or create fresh)
# We'll restore from the existing workspace git

# ─── 8. Log rotation ────────────────────────────────────────────────────────
echo "[8/8] Setting up logrotate..."
mkdir -p /var/log/nova
chown agent:agent /var/log/nova
cat > /etc/logrotate.d/nova << 'EOF'
/var/log/nova/*.log {
  daily
  rotate 7
  compress
  missingok
  notifempty
}
EOF

echo "=== Bootstrap Complete ==="
echo "Node: $(node --version)"
echo "NPM: $(npm --version)"
echo "OpenClaw: $(openclaw --version 2>/dev/null || echo 'installed')"
echo "Agent user: $(id agent)"
echo "Disk: $(df -h / | awk 'NR==2 {print $4}') free"
echo ""
echo "Next: Run 'openclaw onboard' as agent user to configure Nova"