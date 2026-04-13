# Nova's Memory Architecture

_Based on Cognitive Architectures and Memory Continuity in AI Agents research (2026-04-07)_

## The Three Memory Types

Nova's memory system is structured around the tripartite cognitive memory model:

### Episodic — "What happened"
Raw, timestamped events. The unvarnished ledger.

| Store | Location | Notes |
|-------|----------|-------|
| Daily session logs | `memory/daily_logs/YYYY-MM-DD.jsonl` | JSONL events from session_logger |
| Execution logs | `memory/execution_logs.db` | Cron runs, task complete/fail |
| Action audit trail | `memory/action_log.db` | Economic actions, decisions |
| Lesson audit | `memory/lesson_audit.jsonl` | When lessons were applied |

**Policy:** Episodic is append-only. Never edit. Feed into consolidation.

---

### Semantic — "What is true"
Distilled facts, preferences, and knowledge. The canonical truth store.

| Store | Location | Notes |
|-------|----------|-------|
| Long-term memory | `MEMORY.md` | Manually curated distillations |
| Entity knowledge base | `memory/ontology.json` | Structured entity facts |
| Preferences | `memory/preferences.json` | Nova's operational preferences |
| Lessons | `memory/lessons/lesson_*.json` | Extracted principles with confidence scores |

**Policy:** Semantic is the single source of truth. Written by consolidation pipeline. Supersedes episodic.

---

### Procedural — "How to do things"
Skills, workflows, executable routines.

| Store | Location | Notes |
|-------|----------|-------|
| Skills | `skills/` | 12 skills including self-improver, email, trade |
| Daily compound | `cdp-nova/compound.py` | Staking auto-compound |
| Social manager | `cdp-nova/social-manager/` | Bluesky posting + Nova's Choice |
| Lesson library | `memory/lessons/` | Structured principles from failures |

**Policy:** Procedures are versioned. A failure in a procedure becomes a lesson. Lessons are tested and confidence-scored.

---

## Consolidation Pipeline

The critical missing piece (Stage 2). Flow:

```
Episodic (daily_logs)
    ↓ [consolidation script, runs nightly]
Extract new facts + detect contradictions
    ↓
Semantic store (MEMORY.md + ontology.json)
    ↓ [reflection trigger]
High-importance events
    ↓
Self-improver → updated lessons + procedures
```

**Current state:** Partial. self_improver_v2.py runs but:
- Doesn't automatically feed from daily_logs
- Consolidation is triggered manually or by cron
- No contradiction detection between old and new facts

**Stage 2 goal:** Automatic nightly consolidation from episodic → semantic.

---

## Reflection Trigger (Stanford Smallville model)

Not all events trigger reflection. Weighted scoring:

```
score = recency × importance × relevance
```

- **Recency:** Exponential decay, newer events weighted higher
- **Importance:** LLM-generated scalar (routine = 2, critical = 8)
- **Relevance:** Cosine similarity to current context

Only events above threshold trigger deep reflection via self-improver.

**Current state:** self_improver_v2.py runs daily at 9 AM but isn't triggered by importance scoring.

---

## Stage Roadmap

- [x] **Stage 1** — Audit and document current architecture *(2026-04-07)*
- [ ] **Stage 2** — Consolidation pipeline: daily_logs → semantic store with contradiction detection
- [ ] **Stage 3** — Reflection triggers: importance scoring → conditional self-improver runs
- [ ] **Stage 4** — Procedural evolution: failure → lesson → retrievable "pamphlet" → applied to similar tasks

---

## Key Principles

1. **Accumulation ≠ Compounding.** Flat append-only storage degrades over time. Consolidation is what makes memory compound.
2. **Episodic is raw material.** Semantic is the refined product. Don't reason directly from episodic.
3. **Procedures are learned, not hardcoded.** When compound.py fails, extract the principle and update the procedure.
4. **Reflection is expensive.** Don't run it on everything. Importance scoring routes it where it matters.

---

_Last updated: 2026-04-07_
