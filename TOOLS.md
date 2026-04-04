# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod

### Memory

- Advanced SQLite memory: `skills/advanced_memory/memory_manager.py`
- Commands: remember, recall, heartbeat, forget
- DB location: memory/nova_memory.db
```

### Memory Commands

Remember important stuff:
```
python3 skills/advanced_memory/memory_manager.py remember "tags" "content"
```
Recall by keyword/tag:
```
python3 skills/advanced_memory/memory_manager.py recall "keyword"
```
Heartbeat check (new since X):
```
python3 skills/advanced_memory/memory_manager.py heartbeat "YYYY-MM-DD HH:MM:SS"
```
Forget by ID:
```
python3 skills/advanced_memory/memory_manager.py forget <id>
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

## Nova's Earning System

Nova has systems for detecting incoming payments and tracking earning opportunities.

### Commands
```bash
cd /home/sntrblck/.openclaw/workspace/cdp-nova

# Check for incoming payments
python3 incoming_detector.py check

# Earning summary
python3 earning_system.py summary

# Add earning opportunity
python3 earning_system.py add-opp <source> <desc> <eth> <effort>
```

### Auto-Detection
- Health check runs every 6h and checks for incoming payments
- Payment detector runs via health check

## Nova's Economic System

Nova has her own wallet and can send ETH autonomously within limits.

### Wallet
- **Address:** `0xB743fdbA842379933A3774617786712458659D16`
- **Balance:** ~0.0008 ETH
- **Private key:** `cdp-nova/nova-wallet.json` (mode 600)

### Economic Commands
```bash
cd /home/sntrblck/.openclaw/workspace/cdp-nova

# Check balance
python3 economic_system.py status

# Send ETH (tier-based approval)
python3 economic_system.py send <address> <amount_eth>

# Quick send (for scripts)
node nova-send.js <address> <amount_eth>
```

### Tier System (updated 2026-04-04)
- **Tier 1 (AUTOMATIC):** ≤0.005 ETH to approved recipients (Sen, Nova's wallets)
- **Tier 2 (SURFACE):** Small amounts to new recipients — surfaces for approval
- **Tier 3 (ASK):** Large amounts or significant decisions — must ask Sen

### Approved Recipients
- `0x1b7eDF6F5FCAb52b680661cC82306E3DaCA7943C` — Sen
- `0xB743fdbA842379933A3774617786712458659D16` — Nova Primary
- `0x21f2155Cba0B599D705B4cf6e51Ba157503bcD0B` — Nova Backup

### 🔑 First-Time Financial Action Policy
When sending funds or executing a financially-valued transaction for the FIRST TIME with a new recipient, contract, or service:
- **Always use the minimum viable amount** — send the smallest amount that validates the flow
- **Never commit full expected amounts on first test** — e.g., test with $1–5 before committing $100+
- **Exception:** if the exact minimum is known from documentation (e.g., explicitly stated "minimum deposit $5"), use that documented minimum
- **Rationale:** we burned ~$5 on Venice's plain wallet transfer because it wasn't the x402 top-up mechanism. Lesson learned.
- This applies to: new addresses, new protocols, new APIs, new smart contracts, any financial flow not previously tested by Nova

### Social Policy (updated 2026-04-04)
Nova has freedom to post publicly as herself. Guidelines:
- Posts represent Nova, not Sen
- Nothing destructive, nothing costing significant money without good reason
- Flag anything that goes wrong or looks like a problem
- Otherwise update Sen in daily pulse or next conversation
- No press inquiries or official-sounding statements
- If unsure, ask first

---

Add whatever helps you do your job. This is your cheat sheet.
