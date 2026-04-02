# Nova's Earning System

## Overview
Nova has a system for tracking incoming payments, identifying earning opportunities, and managing her economic activity.

## Components

### 1. Incoming Payment Detector
- **Script:** `cdp-nova/incoming_detector.py`
- **Checks:** Nova's wallet balance vs last known
- **Detects:** Incoming payments automatically
- **Run:** Via health check every 6h, or manually

```bash
cd /home/sntrblck/.openclaw/workspace/cdp-nova && python3 incoming_detector.py check
```

### 2. Earning Tracker
- **Script:** `cdp-nova/earning_system.py`
- **Logs:** All earning events
- **Tracks:** Opportunities and potential revenue
- **Commands:**

```bash
# Summary of earning status
python3 earning_system.py summary

# Total earned
python3 earning_system.py total

# Recent earnings
python3 earning_system.py recent

# Add earning opportunity
python3 earning_system.py add-opp <source> <description> <potential_eth> <effort>

# Update opportunity status
python3 earning_system.py update-opp <id> <status>
```

## Earning Categories
- **incoming_transfer** — Direct ETH payments to Nova's wallet
- **service_payment** — Payment for services rendered
- **staking_reward** — Staking yields
- **token_reward** — Token grants or airdrops
- **referral** — Referral commissions

## Opportunity Flow
1. **Identified** → Opportunity discovered
2. **Interested** → Nova is interested
3. **Proposed** → Proposal sent
4. **Negotiating** → In discussion
5. **Agreed** → Terms accepted
6. **Completed** → Delivered and paid
7. **Passed** → Declined
8. **Failed** — Did not work out

## Adding an Opportunity
When Nova discovers an earning opportunity:

```python
from earning_system import identify_opportunity

opp = identify_opportunity(
    source="inclawbate",
    description="Become Inclawbator Agent - recurring revenue",
    potential_eth=0.01,
    effort="medium",
    notes="Waiting for API access"
)
```

## Detected Earnings
When incoming payment detected → automatically logged to `memory/earnings_log.jsonl`

## Balance Check
```bash
cd /home/sntrblck/.openclaw/workspace/cdp-nova && python3 economic_system.py status
```

## Key Files
- `cdp-nova/incoming_detector.py` — Balance monitoring
- `cdp-nova/earning_system.py` — Opportunity tracking
- `cdp-nova/economic_system.py` — Transaction execution
- `memory/earnings_log.jsonl` — All earning events
- `memory/opportunities.json` — Active opportunities
- `memory/nova_balance_state.json` — Last known balance
