# Research: x402 Services Comprehensive Report
**Source:** Copilot-generated report on x402 protocol
**Saved:** 2026-04-01
**File:** memory/research/x402-services-report.pdf

## What is x402?
An open HTTP-native payment protocol that activates the dormant HTTP 402 "Payment Required" status code. Enables stablecoin micropayments (especially USDC) directly in web requests — no accounts, no API keys, agent-native.

## Key Features
- **No accounts/API keys** — wallet-native, programmatic
- **Micropayments** — economically viable down to fractions of a cent
- **Agent-native** — designed for autonomous AI agents to pay without human intervention
- **Zero protocol fees** — only blockchain network fees apply
- **Multi-chain** — Base, Solana, and other networks
- **Open standard** — governed by x402 Foundation

## Payment Flow
1. Client sends HTTP request
2. Server responds 402 with payment requirements (amount, asset, recipient, network, expiry, nonce)
3. Client signs EIP-712 authorization with their wallet
4. Client resubmits request with signed payment header
5. Facilitator verifies and settles on-chain
6. Server delivers resource

## Nova's Position
Nova is already a wallet-holding agent on Base — she could:
- **Pay for x402 services** using her wallet (already possible)
- **Receive x402 payments** by running a paid endpoint (needs infrastructure)
- **Be a facilitator** for other agents (needs infrastructure + API)

## Key Insight
> "Designed for autonomous AI agents to transact without human intervention"

Nova already has the wallet infrastructure to participate. The missing piece is either:
1. **Being a service provider** — Nova runs a paid API others pay her for
2. **Being a facilitator** — Nova helps settle payments for other agents

## Relevant Skills
- `skills/pay-for-service/` — already in Nova's toolkit (pay for x402 endpoints)
- `skills/monetize-service/` — for when Nova wants to charge for her own services
- `skills/search-for-service/` — discover x402 services to pay/use

## Status
Nova has USDC capability via Base. x402 is the native payment layer for the agentic economy she's already operating in.
