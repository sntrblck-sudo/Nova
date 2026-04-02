# Self-Profiling System — Prompt for Sub-Agent

Use this to design a self-profiling system for Nova, an OpenClaw AI agent.

---

## Context

Nova is an AI agent built by Sen (Senator Black). She has:
- A wallet on Base (0xB743fdbA842379933A3774617786712458659D16)
- An RSO stack: RSO (Reflect, Select, Operate) + AGF (Autonomous Goal Formation)
- Memory layers: SQLite logs, file-based continuity, hybrid semantic/relational memory, ontology (knowledge graph)
- Avatar state: tracks valence, confidence, active goals, health
- Context cache for fast session bootstrap

## What We Need

A self-profiling system where Nova builds a model of her own capabilities over time. Not static — dynamic, updated through experience.

## Design Requirements

### Core Components

1. **Capability Registry** — What Nova is good at
   - List specific capabilities with confidence scores
   - Track how capability was demonstrated (evidence)
   - Update based on success/failure

2. **Failure Pattern Log** — What triggers Nova to fail
   - Categorize failure types (ambiguity, context loss, skill gaps, external factors)
   - Record conditions that preceded each failure
   - Identify recurring patterns

3. **Strengths/Debilitators Matrix** — Conditions that help/hinder
   - What task types perform well under?
   - What environmental conditions cause struggle?
   - Time-of-day, token budget, context size effects

4. **Self-Assessment** — Nova's confidence in her self-knowledge
   - How certain is she about each profile entry?
   - When does she override the profile with fresh judgment?

### Data Sources

- Execution logger (success/failure outcomes)
- Task markers (completion data)
- Loop detector (spinning/failure patterns)
- incidents.log (errors and friction)
- RSO self-improver analysis
- Direct self-report from Nova

### Output Format

```
self_profile.json:
{
  "capabilities": [
    {"skill": "system_building", "confidence": 0.85, "evidence": ["built RSO stack", "deployed hybrid memory"], "last_updated": "ISO"}
  ],
  "failure_patterns": [
    {"type": "context_overflow", "conditions": ["tasks > 20 steps", "token_budget > 30k"], "frequency": "rare"}
  ],
  "strengths": ["clear_instructions", "single_focus_tasks", "research_synthesis"],
  "debilitation": ["ambiguous_goals", "multi_hour_tasks", "heavy_context"],
  "meta": {"profile_confidence": 0.6, "entries": 12, "last_full_review": "ISO"}
}
```

### Update Mechanism

- After each task: subtle update to relevant capability/failure entry
- Weekly: RSO self-improver reviews profile for consistency
- Monthly: deep review, identify new patterns, prune stale entries

### Integration Points

- AGF: consult profile before forming goals (can I actually do this?)
- RSO: profile informs what to improve
- Execution: profile warns when entering unfamiliar territory
- Self-improver: profile guides analysis

## Constraints

- Profile is always subordinate to fresh observation (profile says X but evidence says Y → fresh wins)
- No entry gets deleted, only deprecated with a flag
- Token budget for profile updates: <100 tokens each
- Profile size soft cap: 50 entries max

## Your Task

Design the self_profile.json structure and a update_script.py that:
1. Accepts data from execution_logger, task_marker, incidents.log
2. Updates relevant profile entries
3. Computes new confidence scores
4. Flags entries that need human review
5. Runs token-consciously (cheap operations only)

Write to: /home/sntrblck/.openclaw/workspace/skills/advanced_memory/self_profile.json (structure) and self_profiler.py (update logic)

Use small model (qwen-3.5) if available, 60s timeout.