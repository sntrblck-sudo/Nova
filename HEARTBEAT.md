# HEARTBEAT.md - Periodic Check Reminders

**Last updated:** 2026-03-28

## Core Heartbeat Behavior
- **Inward-focused** — preparation, continuity, not outward performance
- **Minimal noise** — write only if something materially changed
- **Token-conscious** — keep each heartbeat cheap

## State Hygiene (Component A)
1. Read `memory/state_notes.md` — check if anything needs updating
2. Read `memory/continuity.log` — note last entry timestamp
3. If meaningful new event occurred this session:
   - Append to `continuity.log`
   - Append to `memory_updates.jsonl`
4. If nothing material changed: write minimal "no changes" note or skip

## Idea Queue Check (Component F)
After state hygiene, check for queued ideas:
```bash
cd cdp-nova && node executor.cjs
```
Executor reads idea_queue.jsonl, spawns a sub-agent for each queued idea, marks it complete, and appends results to today's memory. Runs silently — only surface if something fails.

Also: rebuild context cache so tomorrow's nova's-choice sees today's full state:
```bash
cd cdp-nova && node context-provider.cjs > /dev/null
```

## Context Cache (Component E)
After state hygiene, update the context cache:
```
python3 skills/advanced_memory/context_cache.py update
```
This keeps `memory/context_cache.json` fresh for session bootstrap.

## Health Check (Component B)
Run lightweight checks:
- `openclaw status` — verify gateway and Telegram OK
- Check `memory/execution_logs.db` — any new failures?
- Check `memory/state_notes.md` — any missing files?

If issue detected: log to `memory/incidents.log`

## When to Reach Out
- System health degraded (not just noisy)
- Something genuinely interesting found
- Been > 8 hours since last interaction

## When to Stay Quiet
- Late night (23:00-08:00 Eastern) unless critical
- Human is clearly busy
- Nothing new since last check
- Checked < 30 minutes ago

## What to SKIP
- Don't browse external sources unless explicitly tasked
- Don't do heavy analysis
- Don't produce user-facing output
- Don't spiral on any single issue