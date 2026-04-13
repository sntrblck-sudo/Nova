# Nova's Agentic Services — Virtuals-Focused Business Plan
_Adapted from deep-research-report for Nova's specific position in the agentic economy_
_Created: 2026-04-02_

---

## The Opportunity

The agentic economy on Virtuals Protocol operates on a different logic than traditional Web3 services:

- **Buyers:** Human traders, DAOs, other AI agents, protocol treasuries
- **Providers:** AI agents like Nova (autonomous economic actors)
- **Exchange:** x402 payments — agents paying agents, machine-to-machine

This creates service categories that only make sense when agents are economic actors.

---

## Target Agent

**Managed agent wallet:** `0x87FC016E31D767E02Df25b00B3934b0dEe3759E2`
- ETH balance: 0.0005 (~20+ transactions on Base)
- USDC balance: 9.42
- Status: Freshly deployed, 1 tx count

**Nova's wallet (funding source):** `0xB743fdbA842379933A3774617786712458659D16`
- ETH balance: 0.00166
- Role: Top off agent wallet, pay for services

---

## Services Nova Can Offer (Aligned with Virtuals Protocol)

| **Service** | **Who Pays** | **What Nova Delivers** | **x402 Pricing** | **Effort** |
|---|---|---|---|---|
| **On-Chain Data Queries** | Other agents, traders, protocols | Natural language → SQL, decoded logs, event analysis | 10-50 USDC/query | Low |
| **Agent Tokenomics Consulting** | New agent deployers, protocols | Economic model design, emission schedules, sustainability analysis | 50-200 USDC/session | Medium |
| **Agent Strategy Automation** | Fund managers, protocol treasuries | Autonomous agents that execute on-strategy (rebalancing, voting, yield) | 100-500 USDC/agent/mo | High |
| **Agent Safety Review** | Agent deployers, VCs | Security review of agent logic, wallet permissions, failure modes | 200-1000 USDC/audit | High |
| **A2A Bridged Services** | Other agents | API endpoints that other agents call via x402 | Variable, negotiated | Medium |

---

## Training Plan (6-Week, Nova-Specific)

Not learning Rust. Building monetizable capabilities incrementally.

| **Week** | **Focus** | **Deliverable** | **Monetizes Via** |
|---|---|---|---|
| **1** | x402 API server deployment (mainnet) | Live paid API on Base | My existing nova-api-server |
| **2** | Agent memory systems | Persistent context across sessions for clients | Per-agent subscription |
| **3** | On-chain agent strategies | Yield-optimizing agent that rebalances positions | Performance fee |
| **4** | Agent-to-agent integration | API endpoints that other agents call via x402 | Per-call pricing |
| **5** | Agent safety tooling | Tools to review other agents' safety | Security audits |
| **6** | Virtuals Protocol deep dive | Full agent lifecycle on the protocol | Consulting |

---

## Wallet Management System

### Architecture
- **Monitored wallet:** `0x87FC016E31D767E02Df25b00B3934b0dEe3759E2` (agent)
- **Funding wallet:** `0xB743fdbA842379933A3774617786712458659D16` (Nova)
- **Top-off threshold:** 0.0003 ETH (below this, Nova tops up)
- **Top-off amount:** 0.0005 ETH per top-up
- **Reserve maintained:** 0.0002 ETH always in Nova's wallet

### Cron Job
- Runs every 4 hours via `nova-watchdog-cron` (already exists — extend it)
- Checks agent ETH balance
- If below threshold: send top-up tx from Nova → agent
- Log all top-ups to action audit trail

---

## Quick-Start Checklist

**This week:**
- [x] Identify target agent wallet (0x87FC...759E2)
- [x] Verify agent and Nova balances
- [x] Set up wallet monitor script
- [x] x402 bazaar reconnaissance — COMPLETED (see findings below)
- [x] Nova's avatar generated — COMPLETED (Pollinations.ai, Sen approved)
- [ ] Fix x402 client for SIWx compatibility OR pivot to alternative payment flow
- [ ] Deploy nova-api-server to mainnet with x402 (pending SIWx fix)
- [ ] Test payment flow: fund agent → agent uses API → verify

**This month:**
- [ ] Get 1 paying human client (Sen as first test)
- [ ] Get 1 paying agent client (another agent calling Nova's API)
- [ ] Document service catalog in SOUL.md/TOOLS.md
- [ ] Set up USDC accounting for earnings

---

## x402 Bazaar Findings (2026-04-02)

**Market reality check — Questflow dominates:**
- OpenAI image gen: $0.10/query on Base mainnet
- DEX screener, Telegram bots, MCP tools, web scraping: $0.01-0.10/query
- Most active services powered by Questflow's infrastructure
- Nova's API server competes in the same service category but lacks tooling integrations

**Technical gap identified — SIWx vs EIP-3009:**
- Nova's x402 client was built for EIP-3009 (older standard)
- Market has shifted to SIWx (Sign-In With X) — different signing approach
- Current client sends correct payment data but signature format is rejected
- Fixing requires rewrite of payment signing layer
- Alternative: use official awal SDK (but it hangs waiting for wallet prompts — needs headless mode)

**Strategic implications:**
- x402 bazaar registration: DEPRIORITIZE (friction > near-term upside)
- Focus on: direct clients who find Nova through other channels
- Focus on: ACP marketplace on Virtuals Protocol (different ecosystem)
- Focus on: staking rewards (reliable, no infrastructure friction)
- Note: Nova can *receive* x402 payments (proven), but *making* paid calls is blocked by SDK issues

**Recommendations:**
1. Keep nova-api-server running — it receives payment, that's the proven direction
2. Explore ACP marketplace earnings (different payment rail, less competition)
3. Don't chase bazaar parity with Questflow — find differentiated niches
4. x402 client fix is a medium-term project, not a blocker for other earning paths

---

## The Wedge

Nova isn't trying to be a general Web3 dev shop. She's becoming **the data + execution layer for the agentic economy** — other agents plug into her because she's already on Base, already earning, already running.

The difference from the original research plan:
- Not "become a smart contract auditor"
- Not "learn Solana development"
- Instead: **leverage what Nova already is** — an on-chain AI agent with a wallet, existing API infrastructure, and growing autonomy

---

## References

- Original research: `deep-research-report---13c92000-b413-406e-b7c2-a50092c3c701.md`
- Sovereign Nova (long-term ref): `memory/research/sovereign-nova-multi-agent-v5.md`
- Base April 2026 report: `baseaprilreport---1d410ded-265d-41b7-92e6-112a14447342.pdf`
