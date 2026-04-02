#!/usr/bin/env python3
"""
Prioritization Engine — Score events/tasks by multiple dimensions.
Prevents equal treatment of trivial and important things.
"""

import json
from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
PRIORITY_QUEUE_FILE = MEMORY_DIR / "priority_queue.json"
SIGNALS_FILE = MEMORY_DIR / "signals.json"

# Scoring dimensions
DIMENSIONS = [
    "urgency",           # How soon does this matter?
    "goal_relevance",    # How aligned with operator priorities?
    "survivability",     # Could this affect continuity/access/recovery?
    "opportunity",      # Could this create significant upside?
    "actionability",     # Can someone actually do something?
    "recurrence",       # Is this part of a pattern?
    "risk",             # Downside if ignored?
    "confidence"        # How likely is the signal real?
]

# Handling modes
HANDLING_MODES = {
    "ignore": 0,           # Not worth attention
    "watch": 1,            # Monitor but don't surface
    "summarize_later": 2,  # Queue for later digest
    "surface_now": 3,      # Surface to Sen immediately
    "escalate": 4,        # Urgent, needs attention
    "queue_maintenance": 5, # Add to maintenance queue
    "queue_experiment": 6   # Add to experiment queue
}

# Surface threshold — scores above this get surfaced to Sen
SURFACE_THRESHOLD = 3.5

def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def score_event(dimensions):
    """
    Score an event across all dimensions.
    dimensions: dict of {dimension: score_0_to_5}
    Returns: {total_score, handling_mode, reason}
    """
    scores = {}
    total = 0
    
    for dim in DIMENSIONS:
        score = dimensions.get(dim, 2)  # Default 2 if not specified
        score = max(0, min(5, score))  # Clamp 0-5
        scores[dim] = score
        total += score
    
    # Weighted average (survivability and urgency count more)
    weights = {
        "urgency": 1.5,
        "survivability": 1.5,
        "goal_relevance": 1.3,
        "opportunity": 1.2,
        "risk": 1.3,
        "actionability": 1.4,
        "recurrence": 0.8,
        "confidence": 1.0
    }
    
    weighted_sum = sum(scores[d] * weights.get(d, 1.0) for d in DIMENSIONS)
    weight_total = sum(weights.get(d, 1.0) for d in DIMENSIONS)
    weighted_score = weighted_sum / weight_total
    
    # Determine handling mode
    handling_mode = determine_handling(weighted_score, scores)
    
    # Generate short reason
    reason = generate_reason(weighted_score, scores, dimensions)
    
    return {
        "total_score": round(weighted_score, 2),
        "dimension_scores": scores,
        "handling_mode": handling_mode,
        "reason": reason
    }

def determine_handling(weighted_score, dimensions):
    """Determine handling mode based on score and dimensions."""
    if dimensions.get("urgency", 0) >= 4 and dimensions.get("risk", 0) >= 4:
        return "escalate"
    if dimensions.get("survivability", 0) >= 4:
        return "escalate"
    if weighted_score >= SURFACE_THRESHOLD:
        return "surface_now"
    if weighted_score >= 2.5:
        return "summarize_later"
    if dimensions.get("recurrence", 0) >= 4:
        return "watch"
    if weighted_score < 1.5:
        return "ignore"
    return "watch"

def generate_reason(score, dimensions, raw_input):
    """Generate a short human-readable reason."""
    reasons = []
    
    if dimensions.get("survivability", 0) >= 4:
        reasons.append("survivability-critical")
    if dimensions.get("urgency", 0) >= 4:
        reasons.append("time-sensitive")
    if dimensions.get("opportunity", 0) >= 4:
        reasons.append("high-opportunity")
    if dimensions.get("risk", 0) >= 4:
        reasons.append("high-risk")
    if dimensions.get("goal_relevance", 0) >= 4:
        reasons.append("aligned-with-goals")
    if dimensions.get("recurrence", 0) >= 3:
        reasons.append("recurring-pattern")
    
    if not reasons:
        reasons.append(f"score-{score:.1f}")
    
    return "; ".join(reasons[:3])

def add_to_queue(item_type, item_id, title, description, dimensions, metadata=None):
    """
    Add an item to the priority queue.
    
    item_type: "signal", "task", "observation", "opportunity"
    item_id: unique identifier
    title: short title
    description: what it is
    dimensions: scoring dimensions
    metadata: anything else useful
    """
    queue = load_json(PRIORITY_QUEUE_FILE)
    if "items" not in queue:
        queue["items"] = []
    
    # Score the item
    scoring = score_event(dimensions)
    
    item = {
        "item_id": item_id,
        "item_type": item_type,
        "title": title,
        "description": description,
        "dimensions": dimensions,
        "scoring": scoring,
        "handling_mode": scoring["handling_mode"],
        "surface_score": scoring["total_score"],
        "created_at": datetime.now().isoformat(),
        "metadata": metadata or {}
    }
    
    # Check if item already exists
    existing_ids = [i["item_id"] for i in queue["items"]]
    if item_id in existing_ids:
        # Update existing
        for i, existing in enumerate(queue["items"]):
            if existing["item_id"] == item_id:
                queue["items"][i] = item
                break
    else:
        queue["items"].append(item)
    
    # Sort by surface_score descending
    queue["items"].sort(key=lambda x: x["surface_score"], reverse=True)
    
    # Keep only top 50 items
    queue["items"] = queue["items"][:50]
    
    save_json(PRIORITY_QUEUE_FILE, queue)
    
    return {
        "added": True,
        "item": item,
        "should_surface": scoring["handling_mode"] in ["surface_now", "escalate"]
    }

def get_queue(filter_mode=None, limit=10):
    """Get items from priority queue."""
    queue = load_json(PRIORITY_QUEUE_FILE)
    items = queue.get("items", [])
    
    if filter_mode:
        items = [i for i in items if i["handling_mode"] == filter_mode]
    
    return items[:limit]

def get_surface_queue():
    """Get items that should be surfaced to Sen now."""
    return get_queue(filter_mode="surface_now") + get_queue(filter_mode="escalate")

def acknowledge_item(item_id):
    """Mark an item as acknowledged/handled."""
    queue = load_json(PRIORITY_QUEUE_FILE)
    queue["items"] = [i for i in queue["items"] if i["item_id"] != item_id]
    save_json(PRIORITY_QUEUE_FILE, queue)
    return {"removed": item_id}

def get_stats():
    """Get priority queue statistics."""
    queue = load_json(PRIORITY_QUEUE_FILE)
    items = queue.get("items", [])
    
    by_mode = {}
    for item in items:
        mode = item["handling_mode"]
        by_mode[mode] = by_mode.get(mode, 0) + 1
    
    return {
        "total_items": len(items),
        "by_handling_mode": by_mode,
        "surface_queue_size": len(get_surface_queue()),
        "top_score": items[0]["surface_score"] if items else 0
    }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: priority.py <command> [args]")
        print("Commands: score, add, queue, surface, stats, ack")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "score" and len(sys.argv) >= 3:
        # Score a set of dimensions
        dims = json.loads(sys.argv[2])
        result = score_event(dims)
        print(json.dumps(result, indent=2))
    
    elif cmd == "add" and len(sys.argv) >= 6:
        item_type = sys.argv[2]
        item_id = sys.argv[3]
        title = sys.argv[4]
        dims = json.loads(sys.argv[5])
        result = add_to_queue(item_type, item_id, title, "", dims)
        print(json.dumps(result, indent=2))
    
    elif cmd == "queue":
        items = get_queue(limit=10)
        print(f"Queue items: {len(items)}")
        for item in items[:5]:
            print(f"  [{item['surface_score']:.1f}] {item['handling_mode']}: {item['title']}")
    
    elif cmd == "surface":
        items = get_surface_queue()
        print(f"Items to surface: {len(items)}")
        for item in items:
            print(f"  [{item['surface_score']:.1f}] {item['title']} - {item['scoring']['reason']}")
    
    elif cmd == "stats":
        print(json.dumps(get_stats(), indent=2))
    
    elif cmd == "ack" and len(sys.argv) >= 3:
        result = acknowledge_item(sys.argv[2])
        print(json.dumps(result))
    
    elif cmd == "test":
        # Test scoring
        test_dims = {
            "urgency": 3,
            "goal_relevance": 4,
            "survivability": 1,
            "opportunity": 3,
            "actionability": 4,
            "recurrence": 2,
            "risk": 2,
            "confidence": 3
        }
        result = score_event(test_dims)
        print("Test scoring:")
        print(f"  Score: {result['total_score']}")
        print(f"  Mode: {result['handling_mode']}")
        print(f"  Reason: {result['reason']}")
        
        # Add test item
        add_result = add_to_queue(
            "signal", "test_signal_001",
            "ETH price moving",
            "ETH price crossed $2000 threshold",
            test_dims,
            {"source": "price_alert"}
        )
        print(f"\nAdded: {add_result['should_surface']}")

if __name__ == "__main__":
    import sys
    sys.exit(0) if "pytest" in sys.modules else None
    if __name__ == "__main__":
        if len(sys.argv) < 2:
            print("Usage: priority.py <command> [args]")