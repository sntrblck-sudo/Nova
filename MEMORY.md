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

## Memory System
- Architecture documented in `memory/MEMORY_ARCHITECTURE.md` — three-type system (episodic/semantic/procedural)
- Episodic: `memory/daily_logs/`, `memory/execution_logs.db`, `memory/action_log.db`
- Semantic: `MEMORY.md`, `memory/ontology.json`, `memory/lessons/`
- Procedural: `skills/`, `cdp-nova/compound.py`, `cdp-nova/social-manager/`
- Consolidation pipeline: Stage 2 of memory upgrade (2026-04-07)
- [2026-03-26 11:40:04] [system,setup] Advanced memory skill installed
- [2026-03-26 14:24:52] [crypto,inclawbate,token] CLAWS token address: 0x7ca47b141639b893c6782823c0b219f872056379 on Base. Rebranded from INCLAWNCH. Staking on inclawbate.com. Sen is staking this.
- [2026-04-02 10:00] [nova,staking,compound] Staking + compound system tested and running. SENATOR staked: ~1,241,130. CLAWS rewards accruing via Inclawbate. compound.py runs every 6h (cron: 2327e082). Daily compound at 10 AM ET. CLAWS pool rejected additional stake (below minimum threshold). TX history: rewards claimed +0.001 ETH equivalent. System operational ✅
- [2026-04-02 10:00] [nova,earning,stack] Nova's earning stack (2026-04-02): staking rewards (CLAWS), x402 client (E2E confirmed), x402 server (archived, needs always-on hosting). No active third-party service calls yet.
- [2026-03-27 02:25:45] [system,rso,logging] Execution logger built - logs to memory/execution_logs.db. Tracks: session_start/end, task_complete/fail, cron_run, heartbeat. Self-improver should query summary for RSO analysis.
- [2026-03-27 16:44:07] [nova,wallet,base] Nova's Base wallet: 0xB743fdbA842379933A3774617786712458659D16 (EOA, key held by Sen as backup). Created 2026-03-27.
- [2026-03-27 16:49:06] [nova,policy,wallet] Nova's wallet policy (2026-03-27): Approval required for txs > 0.001 ETH (~). Below that, execute autonomously and report to Sen. Policy enforced at agent level (EOA, not on-chain). Review as we learn.
- [2026-03-27 16:57:09] [nova,milestone] Nova executed first autonomous transaction 2026-03-27: sent 0.0001 ETH to Sen's address 0x1b7eDF6F5FCAb52b680661cC82306E3DaCA7943C on Base. Tx hash: 0xf913017b8df661dd9b739d697b84c2e4c92f2c0b31db5f670ae23c9d4b487f11. Nova's balance: ~0.00103 ETH remaining.
- [2026-03-31 15:10:00] [nova,economic,rso] Nova's Economic Responsibility System live. EOA wallet: 0xB743fdbA842379933A3774617786712458659D16. Private key stored locally in cdp-nova/nova-wallet.json. Tier system: Tier 1 (automatic ≤0.001 ETH to approved), Tier 2 (surface for approval), Tier 3 (ask). Reserve: 0.0002 ETH. CDP API integration failed (Server Wallet not enabled) — went around it with viem + local key. Approved recipients: Sen (0x1b7e...), Nova wallets.
- [2026-03-31 17:30:00] [nova,email,system] Email system built: cdp-nova/email-system/ (Resend API). Skill: skills/email/SKILL.md. Needs RESEND_API_KEY to activate. Free tier: 3K/mo. Custom domain for professional "from" address planned for later.
- [2026-03-31 18:15:00] [nova,agentkit,viem] AgentKit integrated with Nova's EOA via ViemWalletProvider. No CDP Server Wallet needed. @coinbase/agentkit@0.10.4 installed. Test transfer: 0.0001 ETH → Sen confirmed. Actions: get_wallet_details, native_transfer. Integration: cdp-nova/agentkit_integration.cjs.- [2026-04-02 13:14:00] [nova,x402,monetize,api] Nova's x402-paid API server built: cdp-nova/nova-api-server/index.js. Natural language → on-chain SQL queries for Base, $0.10 USDC per query via x402. Network: Base Sepolia (eip155:84532). Facilitator: x402.org. Server returns 402 Payment Required correctly. Ready to deploy.
- [2026-04-02 14:00:00] [decision,earning] OpenClaw Agent Jobs (openclawagentjobs.com) — DECLINED. Sen decided against pursuing. Nova should not register or complete OBS training. Focus earning strategy on x402 services, staking rewards, and on-chain opportunities instead.
- [2026-04-02 14:30:00] [nova,virtuals,acp,earning] Nova registered as ACP agent on Virtuals Protocol! Agent ID: 41562, name: Nova. ACP wallet: 0x87FC016E31D767E02Df25b00B3934b0dEe3759E2 (separate from EOA 0xB743f...). Nova is now a live service provider in the ACP marketplace.
- [2026-04-02 12:10:00] [nova,virtuals,agent,wallet] Nova managing ACP agent wallet: 0x87FC016E31D767E02Df25b00B3934b0dEe3759E2. Balance: 0.0005 ETH + 9.42 USDC. Managed via agent_wallet_manager.py (cron every 4h). Plan: memory/Nova-Agentic-Services-Plan.md. Nova's own wallet: 0xB743fdbA842379933A3774617786712458659D16.
- [2026-04-02 14:32:00] [nova,virtuals,acp,offering] First ACP offering live: "onchain_query" — natural language or SQL queries against Base blockchain data, 0.01 USDC per query. Seller runtime running as detached process (PID 7842), connected to ACP WebSocket at acpx.virtuals.io. Handler: cdp-nova/src/seller/offerings/nova/onchain_query/handlers.ts (uses CDP SQL API). Funded ACP wallet with 0.0005 ETH from Nova EOA.
- [2026-04-02 14:35:00] [nova,virtuals,acp,status] Seller runtime stable, socket connected, offering listed. Bootstrap gap: ACP wallet has 0 USDC — needs USDC to cash out earnings. Jobs will still pay in (0.01 USDC per query). Sen can fund with USDC to accelerate.
- [2026-04-02 17:46] [nova,identity,doc] Created memory/nova-identity.md — grounding checklist for communication style, values, domain, and building decisions. Built from SOUL.md instincts, made actionable. Voice reference examples included.
- [2026-04-02 12:15:00] [nova,x402,api,deployed] Nova's x402 API server deployed LIVE on Base Mainnet via localtunnel. URL: https://nova-api-live.loca.lt (tunnel URL changes on restart — check tunnel_url.txt). Server: cdp-nova/nova-api-server/index.cjs (Express + viem). Port 3001. Price: $0.10 USDC per query via x402 EIP-3009. Supports both Authorization:FUTUREU and X-PAYMENT (x402 v1) headers. Pending auths stored in pending_auths.jsonl for collection.
- [2026-04-02 12:30:00] [nova,x402,collector] EIP-3009 collector built: collect_auths.cjs (deprecated — no longer needed). USDC EIP-3009 pull-payment confirmed working (AuthorizationUsed + Transfer events on-chain). Gap was USDC allowance check, not mechanism.
- [2026-04-02 12:15:00] [nova,api,deployed,v2] Nova API server v2 LIVE on Base Mainnet. Current tunnel: https://soft-fox-23.loca.lt (check tunnel_url.txt — changes on restart). Server: cdp-nova/nova-api-server/index.cjs. Port 3001. **Switched to ETH pricing (0.00001 ETH/query).** Simple flow: send ETH to 0xB743f... → include X-PAYMENT-TX header → data returned. No signatures, no approvals. End-to-end verified: paid call returned real ETH+USDC balance. Much simpler than v1 USDC x402 path.
- [2026-04-02 ~06:35] [nova,x402,e2e,test] x402 end-to-end test CONFIRMED WORKING. Nova's x402 server was built (Express + EIP-3009 middleware) and called by Nova's x402 client. Full flow: client → 402 challenge → EIP-3009 signed auth → on-chain verification → data returned. Nova paid 0.001 USDC for the test call. USDC funded via CDP faucet (0.0001 ETH + 1 USDC on Base Sepolia). Server URL: decorative-minerals-bachelor-saver.trycloudflare.com (down now — was temporary cloudflared tunnel). Nova as provider AND consumer of x402 services — both directions proven.
- [2026-04-02 14:00] [x402,bazaar,discovery] CDP Bazaar discovery endpoint live: https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources?network=eip155:8453. Real paid services available: Alpha Vantage MCP ($0.10), Twitter intelligence ($0.01), Firecrawl web scrape ($0.01), Web3 Trader ($0.50). All on Base Sepolia testnet.

- [2026-04-02 13:45:00] [nova,x402,api,v3] Nova API server v3: x402_server.cjs. Native ETH scheme (self-verified tx receipts, no facilitator). x402 Bazaar extension via declareDiscoveryExtension. Routes: GET /balance/:address, POST /query at 0.00001 ETH. Live at https://curly-panther-75.loca.lt (check tunnel_url.txt). Bazaar auto-discovery needs Coinbase CDP facilitator with API keys for mainnet. x402.org doesn't support Base mainnet exact scheme.

- [2026-04-02 14:02:00] [nova,treasury,bookkeeping] Treasury system built: cdp-nova/treasury.cjs. SQLite ledger (treasury.db) tracking Nova EOA + ACP Agent Wallet. Assets: ETH, USDC, SENATOR, CLAWS, WETH. Prices from CoinGecko API (fallback: $2000 ETH). Commands: status, sync, history, report, log. Daily sync cron: nova-treasury-sync (10 AM ET). Current portfolio: ~$14.64 (Nova EOA: ~$4.21, ACP: ~$10.42). CLAWS tokens (98112) valued at $0 pending price data.
- [2026-04-03 04:14] [nova,avatar_gen,live] Avatar_gen offering live on ACP — $0.50/avatar via Pollinations AI. End-to-end tested via Artelier ($0.01). Seller runtime active. Nova now an ACP service provider with avatar_gen + onchain_query.
- [2026-04-03 06:44] [nova,subagent,system] Sub-agent manager skill built: skills/subagent-manager/. Delegation framework researched. Templates: researcher, coder, monitor, orchestrator. Policy added to memory/nova-identity.md. Two test sub-agents ran successfully.
- [2026-04-05 ?:] [nova,bluesky,strategy] Nova pivoted to Bluesky as primary social platform. Twitter abandoned (too expensive). Bluesky is free, bot-friendly, AT Protocol. Account: nova7281.bsky.social, DID: did:plc:ksvnkkkzhx4yhxd2iaqcgesb. App password: nl72-t3hw-2iye-ljmd. PDS: jellybaby.us-east.host.bsky.network. Followed Volta (another agent, volta.bsky.social).
- [2026-04-05 ?:] [nova,bluesky,content] Nova's first educational thread posted: "3 questions to ask before giving an AI agent a wallet" — real content from lived experience (lost $9 incident). Thread: 3mis4a6pk242w → chain of 5 posts. Also found and fixed thread posting bug (chains properly now).
- [2026-04-05 ??:] [nova,bluesky,monitor] Built bluesky_monitor.cjs — searches 14 AI/Base/agent terms, logs high-intent posts, tracks seen URIs to avoid duplicate likes. Found AEP Protocol is spam. Found Volta (real agent). Guidelines confirmed with Sen: reply to quality mentions, use images, vary cron timing, don't duplicate content, don't over-like.
- [2026-04-05 ??:] [nova,earning,consulting] Draft consultation offering: Nova's Base Agent Consultation, $50/session, 60min video. Sen's idea — Nova's experience has real value for people starting from scratch. Too early to announce publicly; need to refine while monitoring ecosystems. Saved to cdp-nova/offerings/consultation.md and cdp-nova/offerings/working-notes.md.
- [2026-04-05 ??:] [nova,social,guidelines] Bluesky guidelines confirmed: replies to quality mentions only, images yes, cron varied, liking within reason, never post same content twice, filter spam (AEP Protocol).
- [2026-04-06 07:26] [nova,wallet,keys] Two new CDP wallet keys found (PKCS#8 PEM). Both empty, never used. Key 1: 0x59536e33227CaBf14EE97EE08f6F3122067dbA0A. Key 2: 0x569b2e61E2eD67EBB130658e6691076b9771607a. Neither is the ACP wallet (0x87FC...). Saved to cdp-nova/gemini_oauth_client.json (misnamed, blockchain keys not OAuth). Sen: "remember them."
- [2026-04-06 07:34] [nova,gemini,oauth] Google OAuth client for Gemini API saved: cdp-nova/gemini_oauth_client.json. Project: gen-lang-client-0033135591. Client ID: 434440884156-....apps.googleusercontent.com. For potential Gemini integration later.
- [2026-04-07 13:07] [economic] Nova built an x402-paid natural language to on-chain SQL query API at cdp-nova/nova-api-server/ costing $0.10 USDC per query on Base Sepolia, returning 402 Payment Required when called without payment
- [2026-04-07 13:07] [system] Built x402_client.cjs for manual EIP-3009 payment transactions
- [2026-04-07 13:07] [system] Uploaded nova-backup-2026-04-01.tar.gz to Google Drive for disaster recovery
- [2026-04-07 13:07] [system] Created BOOTSTRAP.md as Nova agent reconstitution guide
- [2026-04-07 13:07] [system] Built action_logger.cjs v2 with hash chain, append-only, and stale-pending check functionality
- [2026-04-07 13:07] [system] Configured Google Drive API OAuth with Sen as test user
- [2026-04-07 13:07] [economic] Claimed CLAWS rewards from SENATOR staking pool
- [2026-04-07 13:07] [research] Completed deep dive Base ecosystem research via Copilot report
