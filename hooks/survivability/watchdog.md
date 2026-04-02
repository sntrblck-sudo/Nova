---
name: nova-watchdog
description: "Tracks failures and updates circuit breakers"
metadata: { "openclaw": { "emoji": "👁️", "events": ["command:stop", "session:compact:after"] } }
---

# Nova Watchdog Hook

Monitors for repeated failures and updates circuit breakers. Triggered on session stop and after compaction.