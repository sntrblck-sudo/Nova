#!/usr/bin/env python3
"""
Nova's Knowledge Ontology — Frugal knowledge graph
Stores understanding as entity-relationship pairs
Max 100 entities, 200 relationships, weekly review
"""

import json
import os
from datetime import datetime
from pathlib import Path

ONTOLOGY_PATH = Path("/home/sntrblck/.openclaw/workspace/memory/ontology.json")
MAX_ENTITIES = 100
MAX_RELATIONSHIPS = 200

def load():
    """Load ontology or create empty."""
    if ONTOLOGY_PATH.exists():
        with open(ONTOLOGY_PATH) as f:
            return json.load(f)
    return {"entities": {}, "relationships": [], "last_full_review": None}

def save(ontology):
    """Save ontology — only if changed."""
    with open(ONTOLOGY_PATH, 'w') as f:
        json.dump(ontology, f, indent=2)

def add_entity(name, entity_type, summary, properties=None):
    """Add or update an entity. Returns False if skipped (no meaningful change)."""
    ontology = load()
    
    # Check entity limit
    if name not in ontology["entities"] and len(ontology["entities"]) >= MAX_ENTITIES:
        print(f"Entity limit reached ({MAX_ENTITIES}). Skipping {name}.")
        return False
    
    now = datetime.now().isoformat()
    existing = ontology["entities"].get(name, {})
    
    # Only update if meaningful change
    changed = False
    if existing.get("summary") != summary:
        changed = True
    if existing.get("type") != entity_type:
        changed = True
    if str(existing.get("properties")) != str(properties):
        changed = True
    
    if not changed:
        return False  # Skip write
    
    ontology["entities"][name] = {
        "type": entity_type,
        "summary": summary[:100],  # Cap at 100 chars
        "properties": properties or {},
        "updated": now
    }
    save(ontology)
    return True

def connect(from_entity, to_entity, rel_type, weight=5):
    """Connect two entities. Deduplicates."""
    ontology = load()
    
    # Check relationship limit
    if len(ontology["relationships"]) >= MAX_RELATIONSHIPS:
        print(f"Relationship limit reached ({MAX_RELATIONSHIPS}). Skipping.")
        return False
    
    # Check for duplicate
    for rel in ontology["relationships"]:
        if rel["from"] == from_entity and rel["to"] == to_entity and rel["type"] == rel_type:
            return False  # Already exists
    
    ontology["relationships"].append({
        "from": from_entity,
        "to": to_entity,
        "type": rel_type,
        "weight": min(10, max(1, weight))
    })
    save(ontology)
    return True

def query(entity_name, depth=1):
    """Query entity and its direct connections."""
    ontology = load()
    
    entity = ontology["entities"].get(entity_name)
    if not entity:
        return {"found": False}
    
    # Find direct connections
    connections = []
    for rel in ontology["relationships"]:
        if rel["from"] == entity_name:
            target = ontology["entities"].get(rel["to"], {})
            connections.append({"entity": rel["to"], "type": rel["type"], "weight": rel["weight"], "target_summary": target.get("summary", "")})
        elif rel["to"] == entity_name:
            source = ontology["entities"].get(rel["from"], {})
            connections.append({"entity": rel["from"], "type": rel["type"], "weight": rel["weight"], "direction": "inbound"})
    
    return {
        "found": True,
        "entity": entity_name,
        "data": entity,
        "connections": connections
    }

def grow_toward(interest, depth=2):
    """Find all entities connected to an interest/concept."""
    ontology = load()
    
    # Find entities matching interest
    matches = []
    for name, entity in ontology["entities"].items():
        if interest.lower() in name.lower() or interest.lower() in entity.get("summary", "").lower():
            matches.append(name)
    
    # Also check relationships
    related = set()
    for rel in ontology["relationships"]:
        if interest.lower() in rel["type"].lower():
            related.add(rel["from"])
            related.add(rel["to"])
    
    all_relevant = list(set(matches) | related)
    results = []
    for name in all_relevant:
        q = query(name)
        if q["found"]:
            results.append(q)
    
    return results

def review():
    """Weekly review — check staleness, consolidate, deepen."""
    ontology = load()
    now = datetime.now()
    changes = 0
    
    # Check last review date
    if ontology["last_full_review"]:
        last = datetime.fromisoformat(ontology["last_full_review"])
        if (now - last).days < 7:
            print("Review skipped — done within last 7 days")
            return
    
    # Mark stale entities (not updated in 30 days)
    stale = []
    for name, entity in ontology["entities"].items():
        if entity.get("updated"):
            updated = datetime.fromisoformat(entity["updated"])
            if (now - updated).days > 30:
                stale.append(name)
    
    # Remove stale entities and their relationships
    for name in stale:
        del ontology["entities"][name]
        ontology["relationships"] = [r for r in ontology["relationships"] if r["from"] != name and r["to"] != name]
        changes += 1
    
    ontology["last_full_review"] = now.isoformat()
    
    # Consolidate duplicate relationships (same from+to, keep highest weight)
    seen = {}
    deduped = []
    for rel in ontology["relationships"]:
        key = (rel["from"], rel["to"])
        if key not in seen:
            seen[key] = rel
            deduped.append(rel)
        elif rel["weight"] > seen[key]["weight"]:
            seen[key] = rel
            deduped[-1] = rel
    
    if len(deduped) < len(ontology["relationships"]):
        changes += len(ontology["relationships"]) - len(deduped)
        ontology["relationships"] = deduped
    
    if changes > 0:
        save(ontology)
    
    print(f"Review complete: {changes} entities/relationships cleaned")
    return changes

def stats():
    """Print current ontology stats."""
    ontology = load()
    print(f"Entities: {len(ontology['entities'])}/{MAX_ENTITIES}")
    print(f"Relationships: {len(ontology['relationships'])}/{MAX_RELATIONSHIPS}")
    print(f"Last review: {ontology.get('last_full_review', 'never')}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: ontology.py <command> [args]")
        print("Commands: add-entity, connect, query, grow, review, stats")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "add-entity" and len(sys.argv) >= 5:
        add_entity(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "connect" and len(sys.argv) >= 5:
        connect(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "query" and len(sys.argv) >= 3:
        print(json.dumps(query(sys.argv[2]), indent=2))
    elif cmd == "grow" and len(sys.argv) >= 3:
        print(json.dumps(grow_toward(sys.argv[2]), indent=2))
    elif cmd == "review":
        review()
    elif cmd == "stats":
        stats()
    else:
        print("Invalid command or missing args")