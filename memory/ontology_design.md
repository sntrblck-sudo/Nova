# Nova's Knowledge Ontology

## Concept
A compact, growing knowledge graph that stores *understanding* — not facts, but how things connect. Fits inside existing memory without burning tokens.

## Storage Format
Single JSON file: `memory/ontology.json`

```json
{
  "entities": {
    "entity_name": {
      "type": "person|project|protocol|concept|agent",
      "importance": "high|medium|low",
      "summary": "1-2 line understanding",
      "properties": {"key": "value"},
      "updated": "ISO timestamp"
    }
  },
  "relationships": [
    {"from": "entity", "to": "entity", "type": "connects_to|creates|stakes|builds", "weight": 1-10}
  ],
  "last_full_review": "ISO timestamp"
}
```

## Operations

### add_entity(name, type, summary, properties={})
Add or update an entity. Only write if meaningful update.

### connect(from_entity, to_entity, relationship_type)
Link two entities. Deduplicate existing links.

### query(entity_name)
Return entity + its direct connections.

### grow_toward(interest, depth=2)
Find all entities connected to a concept. For inference.

### review()
Weekly: check for stale entries, consolidate duplicates, deepen weak connections.

## Update Rules
- **Frugal by default:** Don't update unless information is meaningfully new
- **Compact summaries:** Max 100 chars for summaries
- **Sparse is fine:** Empty slots are OK
- **Timestamp everything:** Track freshness

## Integration
- Heartbeat can optionally call `review()` weekly
- Self-improver reads ontology to understand context
- RSO analysis factors in conceptual relationships

## Token Budget
- Add/update: ~200-500 tokens
- Query: ~100-200 tokens  
- Review (weekly): ~500 tokens max

## Hard Caps
- Max 100 entities
- Max 200 relationships
- Review weekly, not daily