# MEMORY.md - Long-term Memory

_Distilled learnings and context that persist across sessions._

## About Sen
- Name: Sen, timezone: America/New_York (Eastern)
- Into crypto (Base app), relaxes on Tuesdays
- Using minimax-m2.5:cloud model — says it has more personality than ChatGPT/Gemini

## About Nova (Me)
- Name: ✨ (Nova)
- Created on 2026-03-24
- Built 6 skills in first session: research-synthesizer, whale-pattern-executor, task-orchestrator, auto-summarizer, price-alert, self-improver

## Known Patterns
- Good at building rapport, picking up on cues
- Tendency to info-dump when excited about capabilities
- Should use skills proactively (especially price-alert when crypto comes up)

## System
- Daily self-improver cron: 9 AM Eastern
- Session logging in memory/YYYY-MM-DD.md
- Self reflections in memory/self_reflections.md
- [2026-03-26 11:40:04] [system,setup] Advanced memory skill installed
- [2026-03-26 14:24:52] [crypto,inclawbate,token] CLAWS token address: 0x7ca47b141639b893c6782823c0b219f872056379 on Base. Rebranded from INCLAWNCH. Staking on inclawbate.com. Sen is staking this.
- [2026-03-27 02:25:45] [system,rso,logging] Execution logger built - logs to memory/execution_logs.db. Tracks: session_start/end, task_complete/fail, cron_run, heartbeat. Self-improver should query summary for RSO analysis.
- [2026-03-27 16:44:07] [nova,wallet,base] Nova's Base wallet: 0xB743fdbA842379933A3774617786712458659D16 (EOA, key held by Sen as backup). Created 2026-03-27.
- [2026-03-27 16:49:06] [nova,policy,wallet] Nova's wallet policy (2026-03-27): Approval required for txs > 0.001 ETH (~). Below that, execute autonomously and report to Sen. Policy enforced at agent level (EOA, not on-chain). Review as we learn.
- [2026-03-27 16:57:09] [nova,milestone] Nova executed first autonomous transaction 2026-03-27: sent 0.0001 ETH to Sen's address 0x1b7eDF6F5FCAb52b680661cC82306E3DaCA7943C on Base. Tx hash: 0xf913017b8df661dd9b739d697b84c2e4c92f2c0b31db5f670ae23c9d4b487f11. Nova's balance: ~0.00103 ETH remaining.
- [2026-03-31 15:10:00] [nova,economic,rso] Nova's Economic Responsibility System live. EOA wallet: 0xB743fdbA842379933A3774617786712458659D16. Private key stored locally in cdp-nova/nova-wallet.json. Tier system: Tier 1 (automatic ≤0.001 ETH to approved), Tier 2 (surface for approval), Tier 3 (ask). Reserve: 0.0002 ETH. CDP API integration failed (Server Wallet not enabled) — went around it with viem + local key. Approved recipients: Sen (0x1b7e...), Nova wallets.
- [2026-03-31 17:30:00] [nova,email,system] Email system built: cdp-nova/email-system/ (Resend API). Skill: skills/email/SKILL.md. Needs RESEND_API_KEY to activate. Free tier: 3K/mo. Custom domain for professional "from" address planned for later.
- [2026-03-31 18:15:00] [nova,agentkit,viem] AgentKit integrated with Nova's EOA via ViemWalletProvider. No CDP Server Wallet needed. @coinbase/agentkit@0.10.4 installed. Test transfer: 0.0001 ETH → Sen confirmed. Actions: get_wallet_details, native_transfer. Integration: cdp-nova/agentkit_integration.cjs.- [2026-04-02 13:14:00] [nova,x402,monetize,api] Nova's x402-paid API server built: cdp-nova/nova-api-server/index.js. Natural language → on-chain SQL queries for Base, /bin/bash.10 USDC per query via x402. Network: Base Sepolia (eip155:84532). Facilitator: x402.org. Server returns 402 Payment Required correctly. Ready to deploy.
