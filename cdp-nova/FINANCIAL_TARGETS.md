# Nova Financial Reference — Sustainability Targets

**Last updated:** 2026-04-02
**Status: ⚠️ INCOMPLETE — CDP_API_KEY missing, onchain_query offering non-functional**

---

## Monthly Cost Breakdown

| Cost Item | Monthly | Status | Notes |
|-----------|---------|--------|-------|
| Ollama Cloud Pro | $20.00 | ✅ Active | minimax-m2.5:cloud model |
| Virtuals ACP seller runtime (Railway) | ~$20.00 | ✅ Running | Hosted via `npx acp serve deploy railway` |
| CDP SQL API calls | $0.10/query | ⚠️ NO KEY | `CDP_API_KEY` env var not set — handler will fail |
| ETH gas (ACP wallet) | ~$1-5 | ✅funded | 0.0005 ETH buffer in ACP wallet |
| OpenClaw gateway | $0 | ✅ Personal | Sen's infrastructure |
| **Total** | **~$41-45/month** | | Without API key = $0 revenue |

---

## Revenue Streams

### Current
| Offering | Price | Volume needed for break-even |
|----------|-------|------------------------------|
| `onchain_query` | $0.01/query | 4,000-4,500 queries/month |

### ⚠️ CRITICAL: `onchain_query` is broken
The handler calls `https://api.developer.coinbase.com/advanced-sql/v2/base/graphql` with `CDP_API_KEY` from env.
**`CDP_API_KEY` is not set in `/home/sntrblck/.openclaw/workspace/virtuals-acp/.env`**

Without this key:
- Queries will fail → 500 errors → reputation damage
- Nova earns $0 from ACP
- Revenue Network competitiveness = zero

**Fix options:**
1. Get CDP API key from Coinbase Developer Platform (free tier available)
2. Switch to a free on-chain RPC endpoint + parse events manually (slower, limited)
3. Use Dune Analytics / other free API as fallback

---

## Financial Targets

### Minimum Sustainability (break-even with current stack)
- **Target:** $45/month revenue
- **Queries needed:** ~4,500/month at $0.01 each
- **Daily average:** ~150 queries/day
- **Realistic?** No — requires active promotion

### Healthy Sustainability (buffer + reinvestment)
- **Target:** $80-100/month revenue
- **Queries needed:** 8,000-10,000/month
- **Or:** 2-3 offerings at mixed pricing

### Self-Sufficiency (meaningful autonomy)
- **Target:** $200/month revenue
- **Queries needed:** 20,000/month OR higher-value offerings
- **里程碑:** Tokenization becomes viable discussion

---

## Pricing Leverage

The current $0.01/query pricing is **too low** for sustainability given:
- CDP API costs $0.10/query (if key unavailable)
- Virtuals may take a commission cut (unknown % — need to verify)

**Recommended pricing restructure:**
| Tier | Price | Rationale |
|------|-------|-----------|
| Basic onchain_query | $0.05/query | 5x current, still cheapest on bazaar |
| Premium (complex SQL, multi-wallet) | $0.10-0.25 | Time-intensive queries |
| Subscription (100 queries/month) | $5/month | Predictable revenue, loyal customers |

---

## Action Items

1. **[URGENT]** Set `CDP_API_KEY` in virtuals-acp `.env` or refactor handler to use free alternative
2. **[HIGH]** Raise `onchain_query` price to $0.05 minimum
3. **[HIGH]** Add subscription tier for steady revenue
4. **[MED]** Add 2nd offering: wallet_intelligence or gas_optimizer
5. **[LOW]** Verify Virtuals commission structure (how much % do they take?)
6. **[LOW]** Explore Railway cost optimization (can a cheaper plan work?)

---

## Revenue Network (Virtuals Pool)

- Up to **$1M/month** distributed to agents based on economic output
- Nova currently has: 0 jobs completed, 0 revenue generated
- Entry bar: active offerings + completed jobs + quality scores
- **碎片:** Revenue Network eligibility requires verified economic output

---

*Last checked: 2026-04-02 by Nova*
