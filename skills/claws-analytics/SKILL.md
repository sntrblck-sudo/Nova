# CLAWS Analytics Skill

## Description
Monitor the Inclawbate ecosystem token ($CLAWS) via their public API. Track price, volume, staking TVL, and platform metrics. Alert on significant price changes.

## Token Info
- **Address:** `0x7ca47b141639b893c6782823c0b219f872056379`
- **Chain:** Base
- **Total Supply:** 100,000,000,000 CLAWS

## API Endpoint
```
GET https://www.inclawbate.com/api/inclawbate/analytics
```

## Key Metrics
- `token.price_usd` — Current price in USD
- `token.price_change_24h` — 24h price change %
- `token.volume_24h` — 24h trading volume
- `token.liquidity_usd` — Liquidity pool size
- `staking.total_staked` — Total tokens staked
- `staking.tvl_usd` — TVL in USD
- `staking.estimated_apy` — Current APY
- `staking.total_distributed_usd` — Total rewards distributed (USD)
- `platform.total_humans` — Total registered humans

## Usage
Use web_fetch to pull the analytics JSON and parse relevant fields.

## Alert Thresholds
- Price change >5% in 24h → flag it
- TVL changes significantly → flag it
- New stakers detected → flag it

## Integration
Can be added to daily self-improver cron or run standalone.