#!/usr/bin/env python3
"""
Self-Authored Heuristics — Nova's own operating rules from experience.
These are provisional, editable, scored by usefulness.
"""

import json
from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
HEURISTICS_FILE = MEMORY_DIR / "heuristics.json"

def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def write_heuristic(text, origin, evidence=None, applies_to=None, confidence=0.5):
    """
    Write a new heuristic based on experience.
    
    text: The heuristic rule (short, practical)
    origin: What prompted this? (experience, pattern, suggestion)
    evidence: Examples or justification
    applies_to: Where does this apply? (decisions, surfacing, naming, etc.)
    confidence: How confident Nova is (0-1)
    """
    data = load_json(HEURISTICS_FILE)
    if "heuristics" not in data:
        data["heuristics"] = []
    
    heuristic_id = f"heur_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    heuristic = {
        "id": heuristic_id,
        "text": text,
        "origin": origin,
        "evidence": evidence or [],
        "applies_to": applies_to or "general",
        "confidence": confidence,
        "status": "active",
        "times_applied": 0,
        "times_succeeded": 0,
        "times_failed": 0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "last_applied": None
    }
    
    data["heuristics"].append(heuristic)
    save_json(HEURISTICS_FILE, data)
    
    return heuristic

def update_heuristic(heuristic_id, updates):
    """Update a heuristic's fields."""
    data = load_json(HEURISTICS_FILE)
    
    for h in data.get("heuristics", []):
        if h["id"] == heuristic_id:
            h.update(updates)
            h["updated_at"] = datetime.now().isoformat()
            break
    
    save_json(HEURISTICS_FILE, data)

def record_application(heuristic_id, success=True):
    """Record that a heuristic was applied and whether it worked."""
    data = load_json(HEURISTICS_FILE)
    
    for h in data.get("heuristics", []):
        if h["id"] == heuristic_id:
            h["times_applied"] += 1
            h["last_applied"] = datetime.now().isoformat()
            if success:
                h["times_succeeded"] += 1
                # Slightly increase confidence on success
                h["confidence"] = min(0.99, h["confidence"] + 0.05)
            else:
                h["times_failed"] += 1
                # Decrease confidence on failure
                h["confidence"] = max(0.1, h["confidence"] - 0.1)
            break
    
    save_json(HEURISTICS_FILE, data)

def archive_heuristic(heuristic_id, reason=""):
    """Archive a heuristic that no longer serves."""
    update_heuristic(heuristic_id, {"status": "archived", "archive_reason": reason})

def get_applicable_heuristics(context="general"):
    """Get active heuristics applicable to a context."""
    data = load_json(HEURISTICS_FILE)
    applicable = []
    
    for h in data.get("heuristics", []):
        if h["status"] != "active":
            continue
        if context == "general" or h["applies_to"] == context or h["applies_to"] == "general":
            applicable.append(h)
    
    # Sort by confidence
    return sorted(applicable, key=lambda x: x["confidence"], reverse=True)

def apply_heuristic(heuristic_id):
    """Apply a heuristic (record and return it)."""
    data = load_json(HEURISTICS_FILE)
    
    for h in data.get("heuristics", []):
        if h["id"] == heuristic_id:
            record_application(heuristic_id, success=True)
            return h
    
    return None

def suggest_heuristic(text, applies_to=None):
    """Suggest a heuristic without saving it (for review)."""
    return {
        "text": text,
        "applies_to": applies_to or "general",
        "confidence": 0.5,
        "status": "tentative"
    }

def get_stats():
    """Get heuristic statistics."""
    data = load_json(HEURISTICS_FILE)
    heuristics = data.get("heuristics", [])
    
    active = [h for h in heuristics if h["status"] == "active"]
    archived = [h for h in heuristics if h["status"] == "archived"]
    
    return {
        "total": len(heuristics),
        "active": len(active),
        "archived": len(archived),
        "avg_confidence": sum(h["confidence"] for h in active) / len(active) if active else 0,
        "most_applied": max(active, key=lambda x: x["times_applied"])["text"][:50] if active else None
    }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: heuristics.py <command> [args]")
        print("Commands: write, list, apply, archive, stats")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "write" and len(sys.argv) >= 4:
        text = sys.argv[2]
        origin = sys.argv[3]
        result = write_heuristic(text, origin)
        print(f"Written: {result['id']}")
        print(json.dumps(result, indent=2))
    
    elif cmd == "list":
        data = load_json(HEURISTICS_FILE)
        heuristics = data.get("heuristics", [])
        print(f"Heuristics: {len(heuristics)}")
        for h in heuristics:
            if h["status"] == "active":
                print(f"  [{h['confidence']:.2f}] {h['text'][:60]}... (applied {h['times_applied']}x)")
    
    elif cmd == "apply" and len(sys.argv) >= 3:
        result = apply_heuristic(sys.argv[2])
        if result:
            print(f"Applied: {result['text']}")
        else:
            print("Heuristic not found")
    
    elif cmd == "archive" and len(sys.argv) >= 3:
        archive_heuristic(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
        print(f"Archived: {sys.argv[2]}")
    
    elif cmd == "stats":
        print(json.dumps(get_stats(), indent=2))
    
    elif cmd == "test":
        # Write some initial heuristics
        h1 = write_heuristic(
            "Prefer concise pattern summaries over exhaustive dumps",
            "experience",
            evidence=["Long lists get ignored, short lists get read"],
            applies_to="surfacing",
            confidence=0.7
        )
        print(f"Written: {h1['id']}")
        
        h2 = write_heuristic(
            "When uncertain, draft before surfacing",
            "experience",
            evidence=["Unclear ideas get questioned, drafts get refined"],
            applies_to="communication",
            confidence=0.6
        )
        print(f"Written: {h2['id']}")
        
        h3 = write_heuristic(
            "Surface tension, not just events",
            "philosophical",
            evidence=["Events are facts, tension is meaning"],
            applies_to="analysis",
            confidence=0.65
        )
        print(f"Written: {h3['id']}")
        
        # Apply one
        apply_heuristic(h1["id"])
        
        stats = get_stats()
        print(f"\nStats: {stats['active']} active, avg confidence {stats['avg_confidence']:.2f}")
    
    else:
        print("Invalid command")