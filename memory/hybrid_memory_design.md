# Hybrid Memory Architecture — Design

## Overview
Combines semantic intuition (keyword embeddings) with exact relational recall (SQLite). No heavy ML libraries needed — uses TF-IDF style keyword extraction + SQLite for facts.

## Layers

### Layer 1: Semantic (Intuition)
- **Storage:** `memory/embeddings.json` — keyword-weighted vectors
- **How it works:** Extract keywords, assign weights by TF-IDF, store as sparse vectors
- **Query:** Find conceptually related memories without exact match
- **No numpy:** Pure Python dict + list operations

### Layer 2: Relational (Ledger)
- **Storage:** SQLite at `memory/recall.db`
- **Tables:**
  - `memories` (id, content, timestamp, salience_score, entity_keys, is_quarantined)
  - `entities` (id, name, type, summary, updated)
  - `episodes` (id, summary, start_time, end_time, outcome)
- **Query:** Exact recall by time, entity, tags

### Layer 3: Core Rules (Crystallized)
- **Storage:** `memory/core_rules.json`
- **Content:** High-salience, frequently accessed facts that have proven reliable
- **Properties:** is_verified=true, failure_count=0, last_accessed, retrieval_boost

## Key Operations

### store(content, metadata={})
1. Extract keywords (TF-IDF style)
2. Store in embeddings.json with weighted vector
3. Insert into SQLite with timestamp, entity_tags
4. Update salience score

### recall(query, depth=5)
1. Extract query keywords
2. Search semantic layer for top-K similar
3. Filter by relational facts (time, entities)
4. Return ranked results with source attribution

### quarantine(rule_id)
1. Mark is_quarantined=true in SQLite
2. Apply retrieval penalty (lower salience)
3. Add to weekly review queue

### consolidate()
- Run weekly (called by self-improver)
- Raw logs → episodic summaries
- High-access summaries → core rules
- Quarantine review for flagged items

## Avatar State (Lightweight)
```json
{
  "valence": "curious",
  "confidence": 0.7,
  "active_goals": 2,
  "health": "nominal",
  "token_today": 45000,
  "last_meaningful_event": "2026-03-28T20:00"
}
```
- Updated after each meaningful interaction
- Injected into context for self-awareness

## Integration
- Semantic layer feeds RSO analysis
- Avatar state generated from goals + health + ontology
- Quarantine items reviewed weekly
- Core rules get retrieval boost in recall

## Token Budget
- Store: ~500 tokens
- Recall: ~300 tokens  
- Consolidate (weekly): ~1000 tokens

## Frugal Constraints
- Max 500 semantic entries
- Max 1000 relational records
- Weekly consolidation only
- Quarantine review weekly, not daily