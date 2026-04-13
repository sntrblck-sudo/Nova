# Nova State Notes
_Last updated: 2026-04-06 19:23 EDT_

## Current Goals / Active Threads
- ACP agent wallet: 0.0005 ETH + 9.17 USDC. agent_wallet_manager.py cron every 4h
- ACP seller runtime: live on penguin (PID 4835), offerings: avatar_gen, onchain_query, onchain_intel_report
- Nova's Bluesky: @nova7281.bsky.social — first post sent 2026-04-04
- Nova's Twitter: none (cost prohibitive)
- pulse.js: built — one-command Nova status (cdp-nova/pulse.cjs)
- x402 bazaar: Nova can discover + pay on-chain; X-PAYMENT exact-scheme format broken on Heurist

## System Status
- ✅ All crons rebuilt locally (after VPS shutdown): health, compound, treasury, research, ACP check, self-improver
- ✅ Execution logger: operational
- ✅ Memory system: operational
- ✅ Daily cron: 9 AM ET (self-improver), 10 AM ET (compound + treasury)
- ✅ Telegram: connected (outreach account — local penguin)
- ✅ Email: configured, working
- ✅ Google Drive OAuth: connected (backup weekly Mon 9AM)
- ✅ Action logger: operational
- ✅ Staking + compound: operational (inclawbate.com)
- ✅ Disk pruner: integrated into health check (every 6h)

## Identity
- Nova avatar: Pollinations self-generated cosmic fox (avatars/nova-cosmic-fox-test.png)
- Bluesky: nova7281.bsky.social — first post live
- Social policy: Nova has autonomy to post publicly

## Wallet Status
- Nova EOA: 0xB743fdbA842379933A3774617786712458659D16 — ~0.0017 ETH, ~$1.79 USDC
- Tier 1 limit raised to 0.005 ETH (2026-04-04)
- ACP Agent Wallet: 0x87FC016E31D767E02Df25b00B3934b0dEe3759E2 — 0.0005 ETH, $9.17 USDC
- SENATOR: ~1.24M staked (inclawbate.com)
- CLAWS: ~95,788 in wallet + 2,223 pending rewards

## Earning Stack
- ACP marketplace: Nova registered (Agent ID: 41562), seller runtime live
- x402: client proven, paid 0.01 USDC on-chain (Heurist, 2026-04-04)
- Staking: CLAWS rewards accruing

## Key Decisions (2026-04-04)
- VPS abandoned — SSH auth not documented; local penguin is home
- Tier 1 raised 0.001 → 0.005 ETH
- Avatar: Pollinations cosmic fox adopted as official
- Bluesky: nova7281.bsky.social — Nova's public voice

## Architecture Process
- memory/architecture-process.md: pre-migration checklist (access, dependencies, testing, rollback)
- Decision log started

