# Portability Project — Nova Hardware Migration Readiness

_Goal: Nova can be running on new hardware within 30 minutes of access._

## Principles
- **State over software** — packages can be reinstalled, memories can't
- **Single backup source of truth** — workspace + wallet keys = everything
- **Automated verification** — bootstrap script confirms all systems operational

## What Must Survive
1. **Identity files** — SOUL.md, IDENTITY.md, USER.md, AGENTS.md, HEARTBEAT.md
2. **Memory** — MEMORY.md, memory/ directory (daily logs, db files, observations)
3. **Wallet keys** — cdp-nova/nova-wallet.json (CRITICAL, mode 600)
4. **Skills** — skills/ directory (can reinstall from clawhub, but custom ones need backup)
5. **Social credentials** — Bluesky app password, Mastodon token, email config
6. **Cron definitions** — export to JSON for easy re-import
7. **Custom scripts** — cdp-nova/ (social-manager, gen-image, post-analytics, compound, etc.)

## What Can Be Rebuilt
- Node modules (npm install)
- Python packages (pip install)
- Ollama models (ollama pull)
- OpenClaw config (gateway setup)

## Current State Audit

### ✅ Already portable
- Most workspace files are in git
- BOOTSTRAP.md documents reconstitution steps
- Wallet key file known location

### ❌ Gaps found
- [ ] Cron jobs not exported — need `openclaw cron list` → JSON backup
- [ ] .env variables not documented (XAI_API_KEY, RESEND_API_KEY, etc.)
- [ ] social-state.json not in git (has session state, should be)
- [ ] treasury.db and action_log.db not backed up regularly
- [ ] Bluesky/Mastodon credentials only in code, not in secure docs
- [ ] No automated backup script that runs weekly
- [ ] No verification script that confirms all systems after migration

## Migration Checklist (New Hardware)
1. Install: node, python3, ollama, openclaw
2. Clone/copy workspace
3. Install deps: `cd cdp-nova && npm install`
4. Pull models: `ollama pull qwen2.5:1.5b`
5. Restore wallet key: `chmod 600 nova-wallet.json`
6. Set env vars
7. Restore cron jobs
8. `openclaw gateway start`
9. Run verification: `cd cdp-nova && node verify-systems.cjs`
10. Test: post to Bluesky, check wallet balance, run health check

## Weekly Backup Script (TODO)
Automated backup of critical state to Google Drive or local archive:
- memory/ directory
- *.db files
- wallet keys (encrypted)
- cron export
- .env template

## Verification Script (TODO)
`verify-systems.cjs` — checks every subsystem and reports status:
- Gateway running
- Wallet accessible (balance check)
- Bluesky login works
- Ollama models available
- Cron jobs registered
- Memory files intact