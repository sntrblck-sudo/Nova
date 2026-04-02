# Base Token Price & Listing Alert

## Description
This skill monitors tokens on the Base network for price changes and listing events. It uses DEXScreener API (no API key required). The agent sets up an automated background check using the OpenClaw cron tool to monitor continuously.

## Triggers
- "Track [Token Address] and alert me when it gets listed"
- "Set a price alert for [Token Address] at $[Price]"
- "Monitor [Token Address] on Base every [X] minutes"

## Requirements
- Access to `references/api.js` helper functions
- Access to OpenClaw `cron` tool

## State Management
Store tracking state in memory or cron job payload:
```json
{
 "tokenAddress": "0x...",
 "targetPrice": 0.05,
 "intervalMinutes": 5,
 "isListed": false,
 "lastPrice": 0,
 "isActive": true
}
```

## Instructions

1. **Initialization:**
 - Extract token address, target price, and interval (default 5 mins) from user request
 - Validate the token address format (0x... 40 hex chars)
 - Save configuration state
 - Schedule recurring check using `cron.add`:
   - `schedule.everyMs`: interval in ms (e.g., 5 min = 300000ms)
   - `payload.kind`: "agentTurn"
   - Include tokenAddress in payload

2. **Execution (Triggered by Cron):**
 - Import `getTokenData` from `references/api.js`
 - Call `getTokenData(tokenAddress)` to check price and listing status

3. **Evaluation & Alerting:**
 - **Listing Alert:** If `isListed` was `false` but now `true`, alert: *"🚨 [Token] has just been listed! Current price: $[Price]"*
 - **Price Alert:** If current price crosses `targetPrice`, alert: *"📈 Price Alert! [Token] has crossed $[Target]. Current price: $[Price]"*

4. **Completion:**
 - Update state with `lastPrice` and `isListed`
 - If user only wanted one-time alert and condition met, set `isActive: false` and remove cron job