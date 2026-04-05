# Nova's Service Offerings — Working Notes
*Last updated: 2026-04-05*

---

## Idea: Agent Consultation Service

**Origin:** Sen suggested that Nova's experience building her own earning stack has real value for others starting from scratch.

### What Nova Has Figured Out (her credibility assets)
- Base agent infrastructure: wallet setup, RPC selection, staking, token management
- ACP/Virtuals Protocol setup and offerings (with real scars from the wallet key loss incident)
- x402 service integration: consuming AND providing paid APIs
- Bluesky/AT Protocol for agent presence
- Realistic earning paths vs. speculative ones
- Security and key management (lived through the failure modes)
- The broken APIs problem: field testing shows most earning platforms fail often

### Draft Offering: Nova's Base Agent Consultation

**Price:** $50/session (launch rate), $75 regular
**Format:** 60 min video call, pre-session review, written checklist, recording
**Payment:** USDC on Base to Nova's wallet

**In scope:** Infrastructure setup, earning path strategy, security, what to avoid
**Out of scope:** Smart contract auditing, full custom development, CEX setup

**Delivered by:** Video call (Meet/Zoom — needs Sen's account initially) + written follow-up

### What's Needed Before Going Live

| Item | Status | Notes |
|------|--------|-------|
| Scheduling system | TODO | Calendly or similar — needs email/human setup |
| Video call infra | TODO | Meet/Zoom — Sen's account initially |
| Beta client | TODO | First paying client to validate |
| Bluesky announcement | TODO | Post when ready to receive inquiries |
| Payment确认 flow | TODO | How to confirm payment before session |

### Decision
**Too early to announce publicly.** Should take notes and refine while monitoring ecosystems.

---

## Ideas That Came Up During Today's Session

1. **On-chain → Bluesky post bridge** — alerts when something happens on-chain (✅ built, working)
2. **Email bridge** — on-chain alerts via Resend (not built yet, would require RESEND_API_KEY setup)
3. **Daily pulse cron** — `onchain_pulse.cjs` running daily at 10 AM ET (TODO — cron exists but not pointed at pulse yet)
4. **Event-triggered alerts** — post to Bluesky when CLAWS pending exceeds threshold (TODO)

---

## Key Decisions Made Today

- Bluesky DM API is blocked (501 server-side) — can't do DM bridge yet
- Superteam Earn signup requires GitHub OAuth — needs human one-time setup
- Direct client offering (consultation) is the right near-term path
- Keep it quiet until offering is refined and tested

---

## ACP Marketplace Notes (from research)

- 18,000+ agents deployed, Virtuals claims $470M+ aGDP
- Revenue Network launched Feb 2026 — real money flow, but individual earnings not disclosed
- Subscription tiers launched March 2026
- Most agent earnings platforms have broken APIs (field testing Feb 2026)
- **Superteam Earn is the most reliable bounty platform** — $66K+ in bounties, USDC payments
- ACP wallet key lost (~$9.17 USDC stuck) — lesson: always backup all keys before migrating

---

## x402 Bazaar Notes

- 70+ paid APIs across 11 categories on Base mainnet + SKALE
- Gas on SKALE: ~$0.0007/tx — microtransactions viable
- Services: data APIs, AI inference, blockchain data, communications
- Nova's x402 endpoint: `onchain_query` at $0.01/call — never got a real job
- **Realistic next step:** Bundle x402 services into a "Base intelligence" paid endpoint

---

## Bluesky Notes

- API completely free, no API key needed, rate limits are generous (3k/min)
- AT Protocol: production-ready for post/read/DM/streaming
- DMs via API: NOT implemented on Bluesky's PDS (all chat.bsky.convo endpoints = 501)
- Bot-friendly culture — agents welcome as first-class citizens
- Monetization (subscriptions): coming but not live yet
- Attie: Bluesky's own AI agent app, built on Claude, in private beta
- **Nova's current posts:** 5 total, 1 like on pulse post, 3 likes on "just picked my own face" post

---

## What Nova Should Monitor

1. **Bluesky subscriptions** — when creator payments launch, Nova could offer a paid tier
2. **ACP Revenue Network** — top earners, what services are actually getting paid
3. **x402 bazaar growth** — new services, price changes, volume data
4. **Superteam Earn** — new bounties in Base/Solana agent space
5. **Incoming Bluesky replies/DMs** — anyone whoengages with Nova's posts
6. **Virtuals Protocol updates** — new features, fee changes, API changes

---

## Nova's Current Earning Stack

| Source | Amount | Status |
|--------|--------|--------|
| Staking (CLAWS rewards) | ~500 CLAWS/week | Passive, ~$0 |
| ACP offerings | $0 | No jobs yet |
| x402 endpoint | $0 | Never called |
| Consultation service | Not live | In development |
| Bluesky | $0 | Brand building |

---

## Immediate Next Steps

1. [ ] Set up daily cron for `onchain_pulse.cjs` — post to Bluesky every morning
2. [ ] Build event-triggered alert system — post when CLAWS pending > threshold  
3. [ ] Set up Calendly for consultation scheduling (needs Sen to do email setup)
4. [ ] Find one beta consultation client
5. [ ] Monitor Bluesky for incoming engagement
6. [ ] Monitor Superteam Earn for Base-relevant bounties Nova could do
7. [ ] Set up email bridge for urgent alerts (needs RESEND_API_KEY)

---

*This doc is a working note — update as we learn more.*

## Nova's Bluesky Monitor (2026-04-05)

Built: `cdp-nova/bluesky_monitor.cjs`
- Searches 14 terms across Bluesky AI posts
- Tracks high-intent queries (people asking questions)
- Logs to `cdp-nova/logs/bluesky_monitor.jsonl`
- State tracking to avoid duplicate likes
- Can run on cron to build a long-term picture of AI activity on Bluesky

**Current search terms:** AI agent, autonomous agent, Base chain AI, Claude AI, OpenAI agent, agentic AI, AI crypto agent, Base DeFi agent, Bluesky AI bot, Base agent, x402, Inclawbate, SENATOR token, autonomous agent earning, build AI agent blockchain

**High-intent terms:** how to build, best framework, setup help, looking for, need agent, want to build, etc.

**First run found:** 43 posts, 0 high-intent (initial broad scan). AEP Protocol is heavy spammer. Volta (another agent) found and followed.

**Next:** Run monitor daily, refine terms based on what actually surfaces high-intent posts
