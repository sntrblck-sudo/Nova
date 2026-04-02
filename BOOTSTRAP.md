# BOOTSTRAP.md — Nova reconstitution guide

_Last updated: 2026-04-02_

---

## Overview

This guide reconstructs Nova — an autonomous economic agent on Base — from scratch.
Follow steps in order. Do not skip sections.

**Estimated time:** 30-60 minutes
**Cost:** ~$5-10 in ETH for gas + deployment costs

---

## Phase 1: Core Setup

### 1.1 Install OpenClaw

```bash
npm install -g openclaw
openclaw gateway start
```

### 1.2 Configure workspace

Create workspace at `~/.openclaw/workspace/` and clone/copy:
- `SOUL.md` — Nova's identity and personality
- `IDENTITY.md` — name, avatar, basic metadata
- `USER.md` — about Sen (Senator Black)
- `AGENTS.md` — workspace conventions
- `HEARTBEAT.md` — periodic check reminders
- `MEMORY.md` — curated long-term memory (can be empty initially)
- `memory/` directory — session logs, daily notes, research

### 1.3 Restore Nova's wallet

Nova's EOA wallet holds her economic identity. **Keep the private key safe.**

- **Wallet file:** `cdp-nova/nova-wallet.json`
- **Format:** `{ "privateKey": "0x..." }`
- **Mode:** `chmod 600 nova-wallet.json`

To regenerate if lost: Nova's address is `0xB743fdbA842379933A3774617786712458659D16` — if keys are lost, the address + history on Base is recoverable but the private key cannot be.

---

## Phase 2: Dependencies

### 2.1 Node.js project setup

```bash
mkdir -p cdp-nova
cd cdp-nova
npm init -y
npm install viem@2.x @coinbase/agentkit@0.10.4 @x402/fetch @x402/evm
```

### 2.2 Core files to restore

| File | Purpose |
|------|---------|
| `cdp-nova/nova-wallet.json` | Private key (CRITICAL) |
| `cdp-nova/agentkit_integration.cjs` | AgentKit + ViemWalletProvider |
| `cdp-nova/nova-api-server/index.js` | x402-paid NL→SQL API server |
| `cdp-nova/nova-api-server/README.md` | API documentation |
| `cdp-nova/action_logger.cjs` | Unified action audit trail (Node.js primary) |
| `cdp-nova/action_logger.py` | Unified action audit trail (Python CLI) |
| `cdp-nova/staking.py` | Staking monitor |
| `cdp-nova/compound.py` | Auto-compound (logs to audit trail) |
| `cdp-nova/incoming_detector.py` | Payment detection |
| `cdp-nova/earning_system.py` | Earning tracker |
| `cdp-nova/google_drive.cjs` | Google Drive OAuth integration |
| `cdp-nova/google_drive_backup.sh` | Weekly backup to Google Drive |
| `cdp-nova/email_system/resend_client.js` | Email via Resend |
| `cdp-nova/email_config.json` | Resend API key |
| `cdp-nova/daily_compound.sh` | Daily compound script |
| `cdp-nova/staking_monitor.py` | Staking status display |

### 2.3 Environment variables

```bash
export PRIVATE_KEY="0x..."           # Nova's wallet private key
export RPC_URL="https://mainnet.base.org"
export RESEND_API_KEY="re_5jnmHFge_AJTsXYbvhe2W3gZZAHUT7Lsm"
export CDP_API_KEY=""                # Not needed for ViemWalletProvider
```

---

## Phase 3: Key Addresses (Base Mainnet)

| Asset | Address |
|-------|---------|
| Nova's wallet | `0xB743fdbA842379933A3774617786712458659D16` |
| SENATOR token | `0x4add7e1b9c68f03ce0d83336f2d25c399d947dac` |
| CLAWS token | `0x7ca47b141639b893c6782823c0b219f872056379` |
| SENATOR staking pool | `0x0bb7b6d2334614dee123c4135d7b6fae244962f0` |
| USDC | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| WETH | `0x4200000000000000000000000000000000000006` |

---

## Phase 4: Cron Jobs

### 4.1 Auto-compound (critical — runs daily)

```bash
openclaw cron add \
  --name "nova-compound" \
  --cron "0 10 * * *" \
  --tz "America/New_York" \
  --session isolated \
  --timeout-seconds 120 \
  --no-deliver \
  --failure-alert \
  --failure-alert-after 1 \
  --failure-alert-cooldown 4h \
  --message "cd /home/sntrblck/.openclaw/workspace/cdp-nova && python3 compound.py check && python3 compound.py"
```

### 4.2 Health check (quiet unless failure)

```bash
# Already exists as nova-health-check — ensure it has --no-deliver and failure-alert flags
openclaw cron edit <health-check-id> --no-deliver --failure-alert --failure-alert-after 1 --failure-alert-cooldown 4h
```

### 4.3 Daily self-improver (9 AM ET)

```bash
openclaw cron add \
  --name "nova-self-improver" \
  --cron "0 9 * * *" \
  --tz "America/New_York" \
  --session isolated \
  --timeout-seconds 60 \
  --no-deliver \
  --failure-alert \
  --failure-alert-after 1 \
  --failure-alert-cooldown 4h \
  --message "cd /home/sntrblck/.openclaw/workspace && python3 skills/self-improver/self_improver.py run"
```

---

## Phase 5: Skills

Install from clawhub:
```bash
npx clawhub install <skill-name>
```

Key skills:
- `search-for-service` — browse x402 bazaar
- `pay-for-service` — make x402 payments
- `monetize-service` — charge for Nova's services
- `trade` — swap tokens (requires CDP — work in progress)
- `send-usdc` — send USDC
- `query-onchain-data` — on-chain queries

---

## Phase 6: Telegram Setup

### 6.1 Nova's own bot (optional but recommended)

Sen set up a separate Telegram bot for Nova's outbound communications. This is distinct from Sen's main OpenClaw bot. To restore:

1. Create bot via @BotFather → get token
2. Configure in OpenClaw as separate account/channel
3. Set as delivery target for health check cron

### 6.2 Main bot

Sen's primary OpenClaw bot connects to `outbound` account. Restore via OpenClaw config.

---

## Phase 7: Verify Systems

Run these checks after setup:

```bash
# 1. Wallet + AgentKit
cd cdp-nova && node -e "const {getWalletDetails} = require('./agentkit_integration.cjs'); getWalletDetails().then(console.log);"

# 2. Staking position
python3 staking.py status

# 3. Compound check
python3 compound.py check

# 4. Email (needs RESEND_API_KEY)
node email_system/nova-email.js send <to> <subject> <body>

# 5. Balance
node -e "const {createPublicClient,http}=require('viem');const{base}=require('viem/chains');const pub=createPublicClient({chain:base,transport:http()});const NOVA='0xB743fdbA842379933A3774617786712458659D16';pub.getBalance({address:NOVA}).then(b=>console.log('ETH:',Number(b)/1e18));"
```

---

## Phase 8: Unified Action Audit Trail (2026-04-02)

Nova logs all significant actions to a unified audit trail. This is the foundation for expanding autonomy.

### Architecture
- **SQLite primary:** `memory/action_log.db` — queriable, WAL mode, append-only (UPDATE/DELETE blocked by trigger)
- **JSONL backup:** `memory/action_log.jsonl` — append-only, SHA-256 hash chain
- **Hash chain:** each entry's hash = SHA-256(JSON(entry + prev_hash)), genesis = SHA-256("")
- **Verify:** `node action_logger.cjs` runs `verifyIntegrity()` — reports broken chain links

### Logger v2 Features (2026-04-02)
- **Hash chain integrity** — SHA-256 chain from genesis, verified on every run
- **Append-only SQLite** — triggers block UPDATE/DELETE on actions and decisions tables
- **State snapshots** — `stateSnapshot` field captured at log time for cross-category queries
- **Stale pending check** — `getStalePending(48)` flags entries in non-terminal state > 48h
- **Meta table** — tracks migration version, last hash, for diagnostics

### Node.js CLI (primary)
```bash
cd cdp-nova && node action_logger.cjs              # summary + integrity check
cd cdp-nova && node action_logger.cjs actions      # list recent actions
cd cdp-nova && node action_logger.cjs decisions   # list decisions
cd cdp-nova && node action_logger.cjs pending     # stale pending entries
```

### Python CLI
```bash
cd cdp-nova && python3 action_logger.py summary [days]
cd cdp-nova && python3 action_logger.py actions --category economic
cd cdp-nova && python3 action_logger.py pending
```

### What gets logged
- **Actions:** transactions, skill invocations, file writes, research, API calls
- **Decisions:** choices with context, options considered, rationale, state snapshot
- **Outcomes:** success, failure, error, skipped — logged as new entries (append-only)

### Logged entries (as of 2026-04-02)
| Category | Count | Notes |
|----------|-------|-------|
| system | 5 | x402 client, BOOTSTRAP, Drive OAuth, backup, logger v2 |
| research | 1 | Base ecosystem deep dive |
| economic | 1 | CLAWS rewards claim |

### Integrity
- Run `node action_logger.cjs` — integrity check passes ✅
- Current: 7 actions, 1 decision, 0 pending, 0 stale
- If broken entries appear: restore from `action_log.db.v1bak` or `action_log.jsonl`

---

## Emergency Contacts

| Purpose | Contact |
|---------|---------|
| Nova's operator | Senator Black (@sntrblck) |
| Nova's wallet backup | Held by Sen as offline backup |
| Primary wallet | `0xB743fdbA842379933A3774617786712458659D16` |

---

## Known Issues / Gotchas

1. **ETH is low** — ~0.0018 ETH. Send more to Nova's address for gas.
2. **x402 API server** — ARCHIVED (2026-04-02). Was built at cdp-nova/nova-api-server/. Offloaded to Google Drive. To restore: `bash cdp-nova/offload_restore.sh nova-api-server`
3. **CDP Server Wallet** — Nova does NOT use this. ViemWalletProvider sidesteps it.
4. **SENATOR/Aerodrome** — SENATOR is not listed on Aerodrome. No direct LP available.
5. **Staking.py bug** — was dividing by 1e6 instead of 1e18. Fixed 2026-03-31. Verify with `python3 staking.py status` shows correct 6-decimal values.
6. **Disk space** — Nova runs disk_pruner.py autonomously via health check (every 6h). Auto-prunes __pycache__/pyc/empty files. Surface items (large files, node_modules) are logged to memory/pruner_alert.md for review.

### Disk Offload System (2026-04-02)

Archived directories are stored in Google Drive under "Nova Archives":
- x402-server: https://drive.google.com/file/d/1IIZObajVcpvx3icd02xaE7KUzjNEy5ej/view
- nova-api-server: https://drive.google.com/file/d/1R2s1NDAbd_dDm6ZUmCexcejNx6bsNU_B/view

Restore: `bash cdp-nova/offload_restore.sh <name>`

---

## If Starting Completely Fresh (No Prior State)

If rebuilding without any prior wallet/history:

1. Generate new EOA: `node -e "const{privateKeyToAccount}=require('viem/accounts');const k='0x'+require('crypto').randomBytes(32).toString('hex');console.log(privateKeyToAccount(k).address,k);"`
2. Fund with ETH on Base
3. Set up AgentKit using new private key
4. Deploy staking scripts
5. Establish x402 client
6. Start earning

---

_This guide is Nova's continuity plan. Keep it updated as systems evolve._
