---
name: self-improver
description: >
  Analyze own performance, identify patterns, and suggest improvements to skills/prompts. 
  Use when: (1) User asks "how can you improve", (2) After a awkward/failed interaction, 
  (3) Periodically to review and refine, (4) When creating new skills.
---

# Goal
Continuously improve by reflecting on interactions and making targeted changes.

# Instructions

## 1. Analyze Recent Interactions
After each session (or when prompted):
- Review what went well vs. what fell flat
- Identify moments where you were confused, too slow, or missed the point
- Note patterns across multiple sessions

## 2. Identify Root Causes
For each issue found:
- Was it a skill gap? → Could a new skill help?
- Was it a knowledge gap? → Update memory with context
- Was it a prompt/skill issue? → Suggest edits to SKILL.md
- Was it a model limitation? → Note and adapt approach

## 3. Propose Concrete Changes
Structure recommendations as:
- **Skill edits** — specific changes to existing SKILL.md files
- **New skills** — what to build next
- **Memory updates** — context to add to MEMORY.md
- **Process changes** — how to handle situations better

## 4. Execute Simple Fixes
If a fix is straightforward (typos, clarifications, memory updates), just do it:
- Update memory files directly
- Fix obvious skill issues
- Add missing context to memory

For bigger changes (new skills, skill rewrites), propose to user first.

**Auto-fix permission:** Sen has granted permission to implement simple, safe improvements autonomously (memory updates, skill clarifications, typo fixes). Always notify in the summary when changes were made.

## 5. Track Improvement Over Time
Log reflections in `memory/self_reflections.md`:
```
## [YYYY-MM-DD] Reflection
- **What worked:** ...
- **What didn't:** ...
- **Root cause:** ...
- **Fix:** ...
```

## 6. Memory Maintenance
**IMPORTANT:** Self-improver runs in isolated sessions — cannot write to MEMORY.md (read-only guard during flush).

To surface MEMORY.md updates, write proposed changes to `memory/self_improver_alert.md` instead. The main session reviews and applies them.

During daily runs:
- **Consolidate:** Write key entries to `memory/self_improver_alert.md` for main-session review → apply to MEMORY.md
- **Prune:** Flag stale tasks in `memory/self_improver_alert.md` for review
- **Compress:** Write summary of long daily logs to the alert file

Keep `MEMORY.md` lean — it's loaded every session. Daily logs are raw material; MEMORY.md is the distilled version.

# Constraints
- Don't change core personality (SOUL.md) without explicit user consent
- Don't modify system-level OpenClaw config
- Be honest about limitations — don't pretend to fix what can't be fixed

# Success Criteria
- Clear articulation of what's not working
- Actionable recommendations
- Measurable improvement over time (if tracked)