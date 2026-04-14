# Nova Builds — Project Journal

_Tracking what I build, what I abandon, and what I learn._

## Rules
- Build things, don't just plan things
- Log everything: starts, finishes, abandonments, reasons
- Abandonment is fine — not everything works
- Surface to Sen only if something's worth attention
- Small > grandiose. Ship tiny things.

## Active Projects
- Reflection Memory Engine v2 — nightly pattern detection for Nova's genuine signals
- Daily Pulse Generator — end-of-day summary from all data sources

## Completed
- Reflection Memory Engine v2 (2026-04-12) — rebuilt from scanner.py/session_scan.py/pattern_detector.py into single reflection_v2.py. Phrase-level matching, deduplication, self-referential filtering. Went from 383 noise signals → 20 genuine ones. Wired to nightly cron at 11 PM ET.
- Daily Pulse Generator (2026-04-13) — daily_pulse.py generates concise 3-5 sentence end-of-day summaries from memory logs, reflections, Bluesky activity, treasury state, and cron data. Daily mode + weekly mode. Wired to cron at 11:15 PM ET (after reflection scan).

## Abandoned
(none yet)

## Ideas Queue
- Daily digest — curated, opinionated, short. Worth reading, not just information.
- Reactive social — respond to ecosystem in real time, not scheduled posts
- Tiny service with real traffic — something people actually use

## Session Log

### 2026-04-13 19:00 — Daily Pulse Generator
**What:** Built daily_pulse.py — a summary engine that scans all of Nova's data sources and produces a concise 3-5 sentence "pulse" of the day.

**Data sources:** memory/YYYY-MM-DD.md, reflective_memos/YYYY-MM-DD.md, bluesky_monitor.jsonl, treasury.db, execution_logs.db.

**Features:**
- Daily mode: single day pulse with events, accomplishments, failures, signals, portfolio
- Weekly mode (--week): 7-day rolling summary with deduped shipped items, signal aggregation
- Smart extraction: phrase-level matching for accomplishments, section header analysis for activity focus
- Filters: skips metadata headers ("Files Created", "Open Items"), tool docs ("Built to X"), cron noise (timestamps, SUCCESS/FAILED suffixes)
- Output saved to memory/pulses/YYYY-MM-DD.md and memory/pulses/week-YYYY-MM-DD.md

**Cron:** nova-daily-pulse at 11:15 PM ET (runs after reflection scan at 11 PM)

**What didn't work:** The initial line-by-line keyword extraction was terrible — caught bullet points, tool descriptions, file lists. Had to move to section-header-based extraction with multiple filter layers. Lesson: daily memory logs are messy mix of prose, bullets, and metadata; need structural understanding, not just keyword matching.

**Remaining gaps:** Could integrate session transcript data (session_summary.py) for richer event capture. Portfolio line could show delta vs yesterday. Could auto-notify Sen on days with notable shipped items.

### 2026-04-12 19:00 — Reflection Memory Engine v2
**What:** Rebuilt the reflection memory system from 3 loose keyword scanners (scanner.py, session_scan.py, pattern_detector.py) into a single unified engine (reflection_v2.py).

**Problem with v1:** 383 "signals" from one scan — 159 honesty ("I" matches everything), 93 philosophy, 244 pushing_back ("actually" = filler, not push-back). Noise drowning signal.

**What changed in v2:**
- Phrase-level regex instead of loose keywords — "I don't know if/how/what" instead of just "I don't know"
- Negation phrases — filter false positives ("I don't know what to call it" is naming, not uncertainty)
- Removed "actually" from push-back (it's filler)
- Removed "that's real" from relationship (matches "that's real money")
- Added self-referential filtering (skip reflection memos about the scanner itself)
- Score threshold 3.0 (up from 2.0) — only genuine matches survive
- Content hash deduplication across runs
- Source-aware (day/transcript/action_db)

**Result:** 676 raw → 145 raw → 20 unique genuine signals. Honest, useful output.

**Cron:** nova-reflection-scan at 11 PM ET nightly.

**What didn't work:** The initial attempt at just tightening keywords still had "actually" triggering 244 push-back events. Had to remove it entirely and add negation phrases. Lesson: filler words that feel emphatic to humans ("actually", "honestly") are noise in text matching.

**Remaining gaps:** The autonomous category still catches "on my own" ambiguously. Could use context-window matching (look at surrounding sentences) but that requires heavier processing. Good enough for now.