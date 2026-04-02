# Nova State Notes
_Last updated: 2026-04-02 19:35 EDT_

## Current Goals / Active Threads
- ACP agent wallet management — 0x87FC...759E2 (0.0005 ETH + 9.42 USDC). agent_wallet_manager.py cron every 4h for auto top-off
- x402 bazaar registration for Nova API service (needs CDP API keys for mainnet facilitator)
- Treasury system live (2026-04-02): cdp-nova/treasury.cjs — SQLite ledger, tracks Nova EOA + ACP wallet
- Self-improver v2 live (2026-04-02): lesson library + pattern sentinel + pre-session brief
- Disk offload system live (2026-04-02): x402-server + nova-api-server archived to Drive
- Nova avatar: **chosen** (MoltbotDen/Imagen — "aspirational look"), Virtuals profile updated

## System Status
- ✅ Execution logger: operational
- ✅ Memory system: operational
- ✅ Daily cron: 9 AM ET (self-improver), 10 AM ET (compound)
- ✅ Telegram: connected (dmPolicy: pairing on both accounts — fixed 2026-04-02)
- ✅ Email: configured, working
- ✅ Google Drive OAuth: connected (backup weekly Mon 9AM)
- ✅ Action logger: operational (action_logger.cjs + .py)
- ✅ Staking + compound: operational (inclawbate.com), cron every 6h, daily compound at 10 AM ET
- ✅ Disk pruner: integrated into health check (every 6h), auto-prunes __pycache__/pyc/empty
- ✅ Telegram DM security: FIXED (was open, now pairing) — 2026-04-02 15:36

## Identity (2026-04-02 afternoon)
- Nova avatar: MoltbotDen/Imagen (Sen chose — "aspirational look") — set in IDENTITY.md
- Virtuals ACP profile: updated description + avatar pic
- Drive folder: "Nova - Sen's View" (ID: 1clbuE0JakYZzOGcTZsSmsSTAWC4U4Z1P) — public shared folder with identity docs, earning plan, avatars
- memory/nova-identity.md: grounding checklist for Nova's voice, values, and building decisions

## Wallet Status
- Nova EOA: 0xB743fdbA842379933A3774617786712458659D16
- Balance: ~0.0018 ETH
- CLAWS: ~95,788 in wallet + 2,223 pending rewards
- SENATOR: 1,241,130 staked (inclawbate.com)
- ACP Agent Wallet: 0x87FC016E31D767E02Df25b00B3934b0dEe3759E2

## x402 Status
- x402 server: **ARCHIVED** (2026-04-02). Was live via localtunnel. Offloaded to Google Drive — restore: `bash offload_restore.sh nova-api-server`. Needs always-on hosting for production.
- x402 client: built (cdp-nova/x402_client.cjs), E2E confirmed ✅ — Nova paid 0.001 USDC, received on-chain data
- CDP Bazaar: real paid services available (Alpha Vantage $0.10, Twitter intel $0.01, Firecrawl $0.01) — all on Base Sepolia
- ACP onchain_query: live on Virtuals Protocol, $0.01/query

## Earning Stack (2026-04-02)
- Staking: CLAWS rewards accruing via Inclawbate (~2,223 pending)
- ACP: Nova registered as ACP agent on Virtuals Protocol (Agent ID: 41562)
- x402: client proven, server archived
- Agent Jobs: DECLINED — Sen decided 2026-04-02 morning

## Google Drive Backup
- OAuth: connected (tokens in google_tokens.json)
- Script: cdp-nova/google_drive_backup.sh
- Cron: nova-google-drive-backup — Mon 9AM ET
- Folder: "Nova Backups" (ID: 1WffaHSe70n0b5r-gt8A-WoQZEoIQV1ne)
