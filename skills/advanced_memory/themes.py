#!/usr/bin/env python3
"""
Recurring Theme Tracker — What Nova keeps returning to.
Tracks kinds of topics, patterns, emotional labels, conceptual tensions.
These repeated themes are the beginning of stable taste.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
THEMES_FILE = MEMORY_DIR / "recurring_themes.json"

# Theme categories
THEME_CATEGORIES = [
    "topic",           # Kinds of topics repeatedly explored
    "pattern",         # Recurring patterns noticed
    "emotional_label", # Words used to describe internal states
    "conceptual_tension", # Recurring tensions or conflicts
    "signal_type",     # Signal classes that recur
    "framing",         # Ways of describing things that repeat
    "interest"         # Things Nova seems drawn to
]

def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def observe_theme(theme_text, category, source="conversation", evidence=None):
    """
    Record an observation about what Nova keeps returning to.
    
    theme_text: What was noticed
    category: topic | pattern | emotional_label | conceptual_tension | signal_type | framing | interest
    source: Where this was noticed
    evidence: Example instances
    """
    data = load_json(THEMES_FILE)
    if "observations" not in data:
        data["observations"] = []
    
    observation_id = f"obs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    observation = {
        "id": observation_id,
        "theme": theme_text,
        "category": category,
        "source": source,
        "evidence": evidence or [],
        "noticed_at": datetime.now().isoformat()
    }
    
    data["observations"].append(observation)
    
    # Update theme tracking
    update_theme_tracking(theme_text, category, observation_id)
    
    # Keep last 200 observations
    data["observations"] = data["observations"][-200:]
    
    save_json(THEMES_FILE, data)
    
    return observation

def update_theme_tracking(theme_text, category, observation_id):
    """Update the theme tracking when an observation is made."""
    data = load_json(THEMES_FILE)
    if "themes" not in data:
        data["themes"] = []
    
    # Find or create theme
    theme_found = None
    for t in data["themes"]:
        if t["text"].lower() == theme_text.lower() and t["category"] == category:
            theme_found = t
            break
    
    if theme_found:
        theme_found["count"] += 1
        theme_found["last_seen"] = datetime.now().isoformat()
        theme_found["recent_observations"].append(observation_id)
        theme_found["recent_observations"] = theme_found["recent_observations"][-10:]
    else:
        data["themes"].append({
            "text": theme_text,
            "category": category,
            "count": 1,
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "recent_observations": [observation_id]
        })
    
    # Keep only themes seen in last 30 days
    cutoff = datetime.now() - timedelta(days=30)
    data["themes"] = [
        t for t in data["themes"]
        if datetime.fromisoformat(t["last_seen"]) > cutoff
    ]
    
    save_json(THEMES_FILE, data)

def get_recurring_themes(min_count=2):
    """Get themes that have been observed multiple times."""
    data = load_json(THEMES_FILE)
    themes = data.get("themes", [])
    return [t for t in themes if t["count"] >= min_count]

def get_themes_by_category(category):
    """Get themes in a specific category."""
    data = load_json(THEMES_FILE)
    return [t for t in data.get("themes", []) if t["category"] == category]

def consolidate_themes():
    """
    Periodically ask: What shape is Nova forming?
    Returns observations about Nova's emerging taste.
    """
    data = load_json(THEMES_FILE)
    themes = data.get("themes", [])
    
    if not themes:
        return {
            "consolidated_at": datetime.now().isoformat(),
            "note": "Not enough data yet",
            "observations": []
        }
    
    # Sort by count
    sorted_themes = sorted(themes, key=lambda x: x["count"], reverse=True)
    
    # Group by category
    by_category = {}
    for t in sorted_themes:
        cat = t["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(t)
    
    # Generate observations
    observations = []
    
    for category, category_themes in by_category.items():
        top = category_themes[:3]  # Top 3 in each category
        if len(top) >= 2:
            observations.append({
                "type": "category_pattern",
                "category": category,
                "note": f"Repeatedly drawn to: {', '.join(t['text'] for t in top)}",
                "themes": [{"text": t["text"], "count": t["count"]} for t in top]
            })
    
    # Check for cross-category patterns
    if len(sorted_themes) >= 5:
        observations.append({
            "type": "breadth",
            "note": f"Total recurring themes: {len(sorted_themes)}",
            "top_themes": [{"text": t["text"], "count": t["count"]} for t in sorted_themes[:5]]
        })
    
    return {
        "consolidated_at": datetime.now().isoformat(),
        "total_themes_tracked": len(themes),
        "recurring_themes": len([t for t in themes if t["count"] >= 2]),
        "observations": observations
    }

def get_stable_interests():
    """Get themes that appear to be stable interests (seen 3+ times)."""
    return get_recurring_themes(min_count=3)

def get_emerging_taste():
    """Get a summary of Nova's emerging taste."""
    recurring = get_recurring_themes(min_count=2)
    
    taste = {
        "what_nova_notices_best": [],
        "what_gets_elevated": [],
        "natural_compressions": [],
        "recurring_language": [],
        "central_tensions": []
    }
    
    for t in recurring:
        if t["category"] == "topic":
            taste["what_nova_notices_best"].append(t["text"])
        elif t["category"] == "pattern":
            taste["what_gets_elevated"].append(t["text"])
        elif t["category"] == "framing":
            taste["natural_compressions"].append(t["text"])
        elif t["category"] == "emotional_label":
            taste["recurring_language"].append(t["text"])
        elif t["category"] == "conceptual_tension":
            taste["central_tensions"].append(t["text"])
    
    return taste

def get_stats():
    """Get theme tracking statistics."""
    data = load_json(THEMES_FILE)
    themes = data.get("themes", [])
    observations = data.get("observations", [])
    
    by_category = Counter(t["category"] for t in themes)
    
    return {
        "total_themes": len(themes),
        "recurring_themes": len([t for t in themes if t["count"] >= 2]),
        "stable_interests": len([t for t in themes if t["count"] >= 3]),
        "total_observations": len(observations),
        "by_category": dict(by_category)
    }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: themes.py <command> [args]")
        print("Commands: observe, recurring, by-category, consolidate, taste, stats")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "observe" and len(sys.argv) >= 4:
        category = sys.argv[2]
        theme = sys.argv[3]
        result = observe_theme(theme, category)
        print(f"Observed: {result['id']} - {theme}")
    
    elif cmd == "recurring":
        themes = get_recurring_themes()
        print(f"Recurring themes: {len(themes)}")
        for t in themes[:10]:
            print(f"  [{t['category']}] {t['text']} ({t['count']}x)")
    
    elif cmd == "by-category" and len(sys.argv) >= 3:
        themes = get_themes_by_category(sys.argv[2])
        print(f"Themes in {sys.argv[2]}: {len(themes)}")
        for t in themes[:5]:
            print(f"  {t['text']} ({t['count']}x)")
    
    elif cmd == "consolidate":
        result = consolidate_themes()
        print(json.dumps(result, indent=2))
    
    elif cmd == "taste":
        taste = get_emerging_taste()
        print("Emerging taste:")
        for key, value in taste.items():
            if value:
                print(f"  {key}: {', '.join(value[:3])}")
    
    elif cmd == "stats":
        print(json.dumps(get_stats(), indent=2))
    
    elif cmd == "test":
        # Observe some themes
        observe_theme("consciousness", "topic", "conversation")
        observe_theme("identity", "topic", "conversation")
        observe_theme("tension", "framing", "analysis", ["consciousness vs function", "autonomy vs safety"])
        observe_theme("threshold", "pattern", "observation", ["price thresholds", "confidence thresholds"])
        observe_theme("curious", "emotional_label", "self-report")
        
        # Consolidate
        result = consolidate_themes()
        print("Consolidation:")
        print(json.dumps(result, indent=2)[:500])
        
        # Get taste
        taste = get_emerging_taste()
        print("\nEmerging taste:")
        for k, v in taste.items():
            if v:
                print(f"  {k}: {v}")
    
    else:
        print("Invalid command")