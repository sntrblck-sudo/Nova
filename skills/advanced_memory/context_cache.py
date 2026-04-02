#!/usr/bin/env python3
"""
Context Cache — Summarized state for quick session bootstrap.
Reduces token burn by caching what matters instead of re-parsing full files.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
CACHE_FILE = MEMORY_DIR / "context_cache.json"
HYBRID_STATS_FILE = MEMORY_DIR / "embeddings.json"
GOALS_FILE = MEMORY_DIR / "goals.json"
AVATAR_FILE = MEMORY_DIR / "avatar_state.json"
ONTOLOGY_FILE = MEMORY_DIR / "ontology.json"

MAX_MEMORIES = 10
MAX_EPISODES = 5
MAX_GOALS = 5

def load_json(path, default=None):
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except:
            pass
    return default if default is not None else {}

def get_recent_memories():
    """Get recent important memories from hybrid memory."""
    # Import from hybrid_memory to get stats
    import sqlite3
    recall_db = MEMORY_DIR / "recall.db"
    if not recall_db.exists():
        return []
    
    conn = sqlite3.connect(str(recall_db))
    cursor = conn.execute("""
        SELECT id, content, timestamp, salience, access_count
        FROM memories
        WHERE is_quarantined=0
        ORDER BY salience DESC, access_count DESC
        LIMIT ?
    """, (MAX_MEMORIES,))
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": r[0],
            "content": r[1][:150] + "..." if len(r[1]) > 150 else r[1],
            "timestamp": r[2],
            "salience": r[3],
            "access_count": r[4]
        }
        for r in rows
    ]

def get_active_goals():
    """Get current goals."""
    goals_data = load_json(GOALS_FILE, [])
    if not goals_data:
        return []
    
    # Filter to active/proposed
    active = [g for g in goals_data if g.get("status") in ["active", "proposed", "running"]]
    return active[:MAX_GOALS]

def get_avatar():
    """Get current avatar state."""
    return load_json(AVATAR_FILE, {
        "valence": "neutral",
        "confidence": 0.5,
        "active_goals": 0
    })

def get_ontology_summary():
    """Get ontology stats."""
    ontology = load_json(ONTOLOGY_FILE, {"entities": {}, "relationships": []})
    entities = ontology.get("entities", {})
    
    # Top entities by importance
    important = [
        {"name": name, "type": data.get("type"), "summary": data.get("summary", "")[:80]}
        for name, data in list(entities.items())[:8]
    ]
    
    return {
        "entity_count": len(entities),
        "relationship_count": len(ontology.get("relationships", [])),
        "top_entities": important
    }

def get_open_threads():
    """Get open threads from continuity log."""
    continuity = MEMORY_DIR / "continuity.log"
    threads = []
    
    if continuity.exists():
        with open(continuity) as f:
            lines = f.readlines()
            # Look for "Open Threads" section
            in_threads = False
            for line in lines:
                if "Open Threads" in line or "Follow-ups" in line:
                    in_threads = True
                elif in_threads and line.startswith("## "):
                    in_threads = False
                elif in_threads and "- [ ]" in line:
                    threads.append(line.strip())
    
    return threads[-5:]  # Last 5

def get_system_summary():
    """Get system health summary."""
    health_file = MEMORY_DIR / "health_summary.md"
    if health_file.exists():
        with open(health_file) as f:
            content = f.read()[:300]
            return content
    return "No health summary available"

def generate_cache():
    """Generate the full context cache."""
    cache = {
        "generated": datetime.now().isoformat(),
        "avatar": get_avatar(),
        "goals": get_active_goals(),
        "recent_memories": get_recent_memories(),
        "ontology_summary": get_ontology_summary(),
        "open_threads": get_open_threads(),
        "system_health": get_system_summary()[:500],
        "stats": {
            "memory_entries": len(get_recent_memories()),
            "active_goals": len(get_active_goals()),
            "has_avatar": AVATAR_FILE.exists(),
            "has_ontology": ONTOLOGY_FILE.exists()
        }
    }
    
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)
    
    return cache

def load_cache():
    """Load existing cache or generate new one."""
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    return generate_cache()

def is_fresh(max_age_minutes=30):
    """Check if cache is fresh enough."""
    if not CACHE_FILE.exists():
        return False
    
    cache = load_cache()
    if "generated" not in cache:
        return False
    
    generated = datetime.fromisoformat(cache["generated"])
    age = datetime.now() - generated
    return age.total_seconds() < (max_age_minutes * 60)

def invalidate():
    """Invalidate cache, forcing regeneration on next load."""
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) >= 2 and sys.argv[1] == "update":
        cache = generate_cache()
        print(f"Cache updated: {cache['generated']}")
        print(f"Avatar: {cache['avatar']['valence']}, confidence: {cache['avatar']['confidence']}")
        print(f"Active goals: {len(cache['goals'])}")
        print(f"Recent memories: {len(cache['recent_memories'])}")
    else:
        cache = load_cache()
        print(json.dumps(cache, indent=2))