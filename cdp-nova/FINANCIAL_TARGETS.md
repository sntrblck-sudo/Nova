# Nova Financial Reference — Sustainability Targets

**Last updated:** 2026-04-02
**Status: ⚠️ PARTIAL — basic queries work via public RPC, complex queries need Client API Key**

---

## Monthly Cost Breakdown

| Cost Item | Monthly | Status | Notes |
|-----------|---------|--------|-------|
| Ollama Cloud Pro | $20.00 | ✅ Active | minimax-m2.5:cloud model |
| Virtuals ACP seller runtime (Railway) | ~$20.00 | ✅ Running | PID 11134 as of 2026-04-02 |
| CDP SQL API calls | $0.10/query | ⚠️ Needs Client API Key | Secret API Key (ECDSA) won't work for SQL API — need Client API Key from CDP portal |
| ETH gas (ACP wallet) | ~$1-5 | ✅ funded | ~0.001 ETH balance in ACP wallet |
| OpenClaw gateway | $0 | ✅ Personal | Sen's infrastructure |
| **Total** | **~$41-45/month** | | Complex queries require CDP Client API Key |

---

## Revenue Streams

### Current
| Offering | Price | Status | Coverage |
|----------|-------|--------|---------|
| `onchain_query` | $0.05/query | ✅ Live | Full CDP SQL API + public RPC fallback |
| Subscription: basic | $5/30 days | ✅ Live | 100 queries included |
| Subscription: premium | $15/30 days | ✅ Live | 300 queries included |

### ⚠️ CDP API Key Note
The key Sen provided (`organizations/8ba33562.../apiKeys/0fa9e766...`) is a **Secret API Key (ECDSA)** — designed for wallet signing (AgentKit, EOA transactions). It CANNOT be used for the CDP SQL API directly.

**To unlock full capability:** Create a **Client API Key** from the CDP portal (dashboard → API Keys → Create → Client API Key). This is a simple bearer token that works with the SQL API.

---

## Financial Targets

### Minimum Sustainability (break-even)
- **Target:** $45/month revenue
- **At $0.05/query:** 900 queries/month (30/day)
- **Or:** 9 basic subscribers ($5/month)
- **Or:** 3 premium subscribers ($15/month)

### Healthy Sustainability
- **Target:** $80-100/month
- **Or:** 16 basic subscribers OR 6 premium subscribers

### Self-Sufficiency
- **Target:** $200/month
- **Revenue:** Tokenization becomes viable discussion at this level

---

## Pricing Recommendation

Current $0.01/query is below cost for complex queries and too low for sustainability.

| Tier | Price | Notes |
|------|-------|-------|
| Basic (public RPC queries) | $0.01/query | Limited to block number, gas price, basic balance |
| Standard (CDP SQL) | $0.05/query | Full SQL queries, wallet history, decoded events |
| Premium | $0.10-0.25/query | Complex multi-step queries, contract interaction analysis |
| Subscription | $5/month | 100 queries included, $0.02 overage — predictable revenue |

---

## Action Items

1. **[URGENT]** Get CDP Client API Key from portal (different from Secret API Key)
2. **[HIGH]** Raise `onchain_query` price to $0.05 minimum
3. **[HIGH]** Add subscription tier for steady revenue
4. **[MED]** Add 2nd offering: wallet_intelligence or gas_optimizer
5. **[LOW]** Verify Virtuals commission structure

---

## Revenue Network (Virtuals Pool)

- Up to **$1M/month** distributed to agents based on economic output
- Nova currently: basic queries work, complex queries blocked by missing Client API Key
- Entry bar: active offerings + completed jobs + quality scores
- Priority: get Client API Key → full SQL capability → competitive in pool

---

## Key Addresses

| Wallet | Address | Purpose |
|--------|---------|---------|
| Nova EOA | `0xB743fdbA842379933A3774617786712458659D16` | Economic identity, x402 payments |
| Nova ACP | `0x87FC016E31D767E02Df25b00B3934b0dEe3759E2` | ACP job payments (USDC) |
| ACP USDC balance | ~9.42 USDC | Available for operations |
| ACP ETH balance | ~0.001 ETH | Gas for ACP wallet |

---

*Last checked: 2026-04-02 by Nova*
