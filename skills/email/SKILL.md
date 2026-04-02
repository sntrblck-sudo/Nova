# Email Skill — Nova's Email System

## Overview
Nova can send emails via Resend API. Currently uses free tier (`nova@resend.dev` sender), domain-based sending requires account setup.

## Setup
1. Get API key from https://resend.com/api-keys
2. Run: `node cdp-nova/email-system/nova-email.js setup <apiKey> [fromEmail] [domain]`
3. Test: `node cdp-nova/email-system/nova-email.js send test@example.com "Test" "Hello"`

## Components
- `resend_client.js` — Resend API wrapper class
- `nova-email.js` — CLI for sending/status/setup
- `package.json` — dependencies (resend npm package)

## Current Config
Config stored in `cdp-nova/email_config.json`

## Usage
```bash
# Send email
node cdp-nova/email-system/nova-email.js send \
  recipient@example.com \
  "Subject line" \
  "Email body text"

# Check config
node cdp-nova/email-system/nova-email.js status
```

## From Address
- **Default:** `nova@resend.dev` (free tier, works but looks informal)
- **Better:** Custom domain (e.g., `nova@yourdomain.com`) — requires domain verification in Resend

## Limits
- **Free tier:** 3,000 emails/month, 100/day
- **Transactional only** — no marketing features needed for agent comms

## To-Do
- [ ] Set up custom domain for professional "from" address
- [ ] Add inbound email handling (webhook or polling)
- [ ] Add email templates for common outreach scenarios
