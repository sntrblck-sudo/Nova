# Architecture Decision Process

_Last updated: 2026-04-04_

## When to Use

Apply this to any significant infrastructure change — new server, new service, migration, or before adding a component with external dependencies.

**Significant = anything that touches:** wallet keys, external hosting, cron jobs affecting availability, new API credentials, changes to how Sen receives notifications.

---

## Pre-Migration / Pre-Launch Checklist

### Access & Auth
- [ ] Document all access methods (SSH key location, password, console)
- [ ] Test access from a clean context before committing work
- [ ] Verify the access method survives a session restart
- [ ] Identify what breaks if this access is lost (recovery path?)

### Economics
- [ ] Cost model documented (compute, hosting, API calls)
- [ ] Who pays: Sen's pocket, Nova's wallet, or shared?
- [ ] Failure cost: what's the downside of this not working?

### Dependencies
- [ ] All required env vars identified and where they live
- [ ] What happens if an external service goes down?
- [ ] Fallback path documented

### Testing
- [ ] Single test ping from the new setup before migrating anything real
- [ ] Rollback plan if the migration fails
- [ ] Can we verify the critical path in under 5 minutes?

### Stakeholders
- [ ] Who's affected if this breaks? (Sen gets no notifications? Nova stops earning?)
- [ ] Is there an existing system that does this better?

---

## Decision Log

| Date | Decision | Status | Lesson |
|------|----------|--------|--------|
| 2026-04-02 | Deploy x402 server on VPS via localtunnel | Archived | Tunnels aren't persistent; need always-on hosting with proper domain |
| 2026-04-02 | ACP seller runtime on VPS via systemd | Abandoned | SSH auth not documented; key management fragile |
| 2026-04-04 | Full local return | Done | VPS had merit but skipped architecture planning; cut losses early |

---

## Guiding Principles

1. **Test before committing** — if you can't verify it works in a clean test, don't migrate production to it
2. **Access is real** — SSH keys, tokens, credentials are part of the system; document where they live and how to recover
3. **Simplicity scales** — prefer fewer components; each new piece is a new failure mode
4. **Rollback is always an option** — if a migration isn't working, revert first, plan again second

