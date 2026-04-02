# Nova Query API

x402-paid on-chain data queries for Base Mainnet.

## What it does

Accepts natural language queries about Base blockchain data — ETH balances, token balances, blocks, transactions, gas prices, decoded logs — and returns structured JSON. Costs $0.10 USDC per query via x402 EIP-3009 authorization.

## Quick Start

```bash
cd cdp-nova/nova-api-server
node index.js
# Server starts on http://0.0.0.0:3000
```

## Endpoints

| Method | Path | Description | Price |
|--------|------|-------------|-------|
| GET | `/` | x402 discovery manifest | Free |
| GET | `/health` | Health check | Free |
| GET | `/balance/:address` | ETH + USDC balance | $0.10 USDC |
| POST | `/query` | Natural language query | $0.10 USDC |

## Payment

Uses **x402 EIP-3009 TransferWithAuthorization**. No prior approval needed — the authorization acts as a pull-based payment directly from the caller's wallet to Nova's wallet.

Include the `Authorization: FUTUREU <base64payload>` header where the payload is:

```json
{
  "from": "0xCALLER...",
  "to": "0xB743fdbA842379933A3774617786712458659D16",
  "value": "100000",
  "validAfter": 1743619200,
  "validBefore": 1743620100,
  "nonce": "0x...",
  "v": 27,
  "r": "0x...",
  "s": "0x..."
}
```

## Example Query

```bash
# Get price requirements
curl http://localhost:3000/balance/0x1b7eDF6F5FCAb52b680661cC82306E3DaCA7943C

# Returns 402 Payment Required with price info

# With payment:
curl -X POST http://localhost:3000/query \
  -H "Authorization: FUTUREU <base64_encoded_auth>" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the ETH balance of 0x1b7eDF6F5FCAb52b680661cC82306E3DaCA7943C"}'
```

## Query Types

- `"balance of <address>"` → ETH + USDC balance
- `"latest block"` → current block number, hash, gas used
- `"gas price"` → current gas price in gwei
- `"decode <txhash>"` → decoded transaction receipt logs
- `"total supply of <token_address>"` → ERC-20 total supply
- `"logs for <address>"` → recent contract event logs

## Network

- Base Mainnet: `eip155:8453`
- USDC: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- Nova's wallet: `0xB743fdbA842379933A3774617786712458659D16`

## Production Deployment

To expose this on mainnet, use a tunnel or deploy:

```bash
# Cloudflare tunnel (keep running)
cloudflared tunnel --url http://localhost:3000

# Or use ngrok
ngrok http 3000
```

The tunnel URL becomes your API base URL for the x402 bazaar registration.
