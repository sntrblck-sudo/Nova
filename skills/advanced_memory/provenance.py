#!/usr/bin/env python3
"""
Provenance Tracker — Track the source of durable facts.
Every personal fact stored should carry its origin metadata.
"""

import json
from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
PROVENANCE_FILE = MEMORY_DIR / "provenance.json"

def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def store_fact(fact, source, source_type, confidence="medium", storage_layer="unknown", notes=""):
    """
    Store a durable fact with provenance metadata.
    
    fact: What was stored (the claim)
    source: Where it came from (e.g., "Telegram chat", "Sen directly")
    source_type: conversation | document | observation | inference | unknown
    confidence: low | medium | high
    storage_layer: summary_memory | hybrid_memory | file | context_injection | unknown
    notes: Any additional context about how this was received
    """
    data = load_json(PROVENANCE_FILE)
    if "facts" not in data:
        data["facts"] = []
    
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    ms = str(datetime.now().microsecond)[:3]
    fact_id = f"fact_{ts}_{ms}"
    
    # Check if this fact already exists (deduplication)
    for existing in data["facts"]:
        if existing["fact"].lower() == fact.lower():
            # Update existing, don't duplicate
            existing["last_verified"] = datetime.now().isoformat()
            existing["confidence"] = confidence  # Update confidence
            save_json(PROVENANCE_FILE, data)
            return {"updated": True, "fact_id": existing["id"], "note": "fact already existed"}
    
    record = {
        "id": fact_id,
        "fact": fact,
        "source": source,
        "source_type": source_type,
        "confidence": confidence,
        "storage_layer": storage_layer,
        "notes": notes,
        "stored_at": datetime.now().isoformat(),
        "last_verified": datetime.now().isoformat(),
        "verification_count": 1
    }
    
    data["facts"].append(record)
    save_json(PROVENANCE_FILE, data)
    
    return {"stored": True, "fact_id": fact_id}

def get_provenance(fact_text):
    """Look up the provenance of a fact by text search."""
    data = load_json(PROVENANCE_FILE)
    
    for record in data.get("facts", []):
        # Partial match
        if fact_text.lower() in record["fact"].lower():
            return {
                "found": True,
                "fact": record["fact"],
                "source": record["source"],
                "source_type": record["source_type"],
                "confidence": record["confidence"],
                "storage_layer": record["storage_layer"],
                "stored_at": record["stored_at"],
                "last_verified": record["last_verified"]
            }
    
    return {"found": False, "fact": fact_text}

def verify_fact(fact_text):
    """Increment verification count when a fact is confirmed."""
    data = load_json(PROVENANCE_FILE)
    
    for record in data.get("facts", []):
        if fact_text.lower() in record["fact"].lower():
            record["verification_count"] = record.get("verification_count", 0) + 1
            record["last_verified"] = datetime.now().isoformat()
            save_json(PROVENANCE_FILE, data)
            return {"verified": True, "count": record["verification_count"]}
    
    return {"verified": False}

def flag_unknown_source(fact_text):
    """Flag that the source of a fact is genuinely unknown."""
    data = load_json(PROVENANCE_FILE)
    if "unknown_source" not in data:
        data["unknown_source"] = []
    
    # Check if already flagged
    for item in data["unknown_source"]:
        if item["fact"].lower() == fact_text.lower():
            item["flagged_at"] = datetime.now().isoformat()
            save_json(PROVENANCE_FILE, data)
            return {"already_flagged": True}
    
    data["unknown_source"].append({
        "fact": fact_text,
        "flagged_at": datetime.now().isoformat(),
        "note": "Source amnesia - fact known but origin unknown"
    })
    save_json(PROVENANCE_FILE, data)
    
    return {"flagged": True}

def get_facts_needing_verification():
    """Get facts with low confidence or never verified recently."""
    data = load_json(PROVENANCE_FILE)
    needs_review = []
    
    for record in data.get("facts", []):
        if record.get("confidence") == "low":
            needs_review.append(record)
        elif record.get("verification_count", 0) < 2:
            needs_review.append(record)
    
    return needs_review

def surface_with_provenance(fact_text):
    """
    When surfacing a personal fact, include source info.
    Returns: "I believe [fact], but [source info or unknown]."
    """
    prov = get_provenance(fact_text)
    
    if not prov["found"]:
        return {
            "surfaced": fact_text,
            "provenance_note": "source unknown - may need verification",
            "confidence": "unknown"
        }
    
    if prov["confidence"] == "low":
        confidence_note = "but I'm not certain about the source"
    elif prov["source_type"] == "unknown":
        confidence_note = "but I can't trace where this came from"
    else:
        confidence_note = f"from {prov['source']}"
    
    return {
        "surfaced": fact_text,
        "provenance_note": confidence_note,
        "source_type": prov["source_type"],
        "confidence": prov["confidence"]
    }

def get_stats():
    """Get provenance tracking statistics."""
    data = load_json(PROVENANCE_FILE)
    facts = data.get("facts", [])
    
    by_source_type = {}
    by_confidence = {}
    verified_counts = []
    
    for f in facts:
        st = f.get("source_type", "unknown")
        by_source_type[st] = by_source_type.get(st, 0) + 1
        conf = f.get("confidence", "unknown")
        by_confidence[conf] = by_confidence.get(conf, 0) + 1
        verified_counts.append(f.get("verification_count", 0))
    
    return {
        "total_facts": len(facts),
        "by_source_type": by_source_type,
        "by_confidence": by_confidence,
        "avg_verifications": sum(verified_counts) / len(verified_counts) if verified_counts else 0,
        "unknown_source_count": len(data.get("unknown_source", []))
    }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: provenance.py <command> [args]")
        print("Commands: store, lookup, verify, flag-unknown, stats")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "store" and len(sys.argv) >= 5:
        fact = sys.argv[2]
        source = sys.argv[3]
        source_type = sys.argv[4]
        result = store_fact(fact, source, source_type)
        print(json.dumps(result, indent=2))
    
    elif cmd == "lookup" and len(sys.argv) >= 3:
        result = get_provenance(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    elif cmd == "verify" and len(sys.argv) >= 3:
        result = verify_fact(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    elif cmd == "flag-unknown" and len(sys.argv) >= 3:
        result = flag_unknown_source(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    elif cmd == "stats":
        print(json.dumps(get_stats(), indent=2))
    
    elif cmd == "test":
        # Test storing facts
        r1 = store_fact(
            "Sen's cat is named Fang",
            "Telegram chat",
            "conversation",
            "medium",
            "hybrid_memory",
            "Sen mentioned Fang during morning conversation"
        )
        print(f"Stored: {r1}")
        
        r2 = store_fact(
            "Sen is Filipino-American",
            "Telegram chat",
            "conversation",
            "high",
            "hybrid_memory",
            "Sen revealed this during name discussion"
        )
        print(f"Stored: {r2}")
        
        r3 = store_fact(
            "Sen's cat is white and black tuxedo",
            "Telegram chat",
            "conversation",
            "medium",
            "hybrid_memory"
        )
        print(f"Stored: {r3}")
        
        # Lookup
        prov = get_provenance("Fang")
        print(f"\nProvenance of Fang: {prov}")
        
        # Surface with provenance
        surf = surface_with_provenance("Sen's cat is named Fang")
        print(f"\nSurface with provenance: {surf}")
        
        stats = get_stats()
        print(f"\nStats: {stats}")
    
    else:
        print("Invalid command")