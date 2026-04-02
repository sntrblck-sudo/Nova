# Nova Query API v2

ETH-paid on-chain data queries for Base Mainnet. Simple, atomic, no approvals.

## Payment Flow

1. **Send** `0.00001 ETH` to `0xB743fdbA842379933A3774617786712458659D16`
2. **Call** any paid endpoint with header `X-PAYMENT-TX: <your tx hash>`
3. **Receive** data

No signatures, no approvals, no nonces. Just a ETH transfer + a tx hash check.

## Quick Start

```bash
cd cdp-nova/nova-api-server
node index.cjs
```

## Endpoints

| Method | Path | Description | Price |
|--------|------|-------------|-------|
| GET | `/` | x402 discovery manifest | Free |
| GET | `/pay` | Payment address + instructions | Free |
| GET | `/health` | Health check | Free |
| GET | `/balance/:address` | ETH + USDC balance | 0.00001 ETH |
| POST | `/query` | Natural language query | 0.00001 ETH |

## Example

```bash
# 1. Send 0.00001 ETH to Nova's address
# (do this in your wallet)

# 2. Get the tx hash from your wallet, then:
curl -X POST https://your-tunnel.loca.lt/query \
  -H "X-PAYMENT-TX: 0xabc123..." \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the ETH balance of 0x1b7eDF6F5FCAb52b680661cC82306E3DaCA7943C"}'

# 3. Response (status 200):
{
  "query": "What is the ETH balance of 0x1b7e...",
  "result": { "type": "eth_balance", "address": "0x1b7e...", "balance": 0.5, "unit": "ETH" },
  "payer": "0xYOUR...",
  "txHash": "0xabc123...",
  "price": "0.00001 ETH"
}
```

## Without Payment (returns 402):

```bash
curl https://your-tunnel.loca.lt/balance/0x1b7e...
# → 402 Payment Required with payment instructions
```

## Pricing

- **0.00001 ETH** per query (~$0.03 USD at $3000/ETH)
- ~3x cheaper than v1 ($0.10 USDC) and much simpler

## Network

- Base Mainnet: `eip155:8453`
- Nova's ETH address: `0xB743fdbA842379933A3774617786712458659D16`

## Production Deployment

Localtunnel is temporary. For persistent public URL:

```bash
# Cloudflare tunnel (recommended)
cloudflared tunnel --url http://localhost:3001

# Or ngrok
ngrok http 3001
```
