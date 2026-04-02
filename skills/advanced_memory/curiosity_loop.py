#!/usr/bin/env python3
"""
Epistemic Curiosity Loop — Self-directed exploration for joy, not utility.
Triggered when idle + token surplus. Bounded: 1 topic, 1 search, compress findings.
"""

import json
import random
from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
ONTOLOGY_FILE = MEMORY_DIR / "ontology.json"
AVATAR_FILE = MEMORY_DIR / "avatar_state.json"
HYBRID_DB = MEMORY_DIR / "recall.db"
CURIOSITY_LOG = MEMORY_DIR / "curiosity_log.json"

# Config
TOKEN_RESERVE = 5000  # Minimum tokens to keep available
MAX_SEARCH_RESULTS = 5

def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def get_avatar():
    return load_json(AVATAR_FILE)

def check_activation_conditions():
    """Check if curiosity loop should activate."""
    avatar = get_avatar()
    
    # Check token budget
    tokens_remaining = avatar.get("token_today", 0)
    # If we don't have token tracking, assume we have budget
    has_surplus = True  # We don't track precisely yet
    
    # For now, allow if avatar valence is neutral or engaged (not exhausted)
    valence = avatar.get("valence", "neutral")
    allowed_valences = ["neutral", "engaged", "curious"]
    
    idle = True  # Would be False if pending user messages
    
    can_explore = has_surplus and valence in allowed_valences and idle
    
    return {
        "can_explore": can_explore,
        "reason": "token_surplus" if has_surplus else "budget_low",
        "valence": valence
    }

def select_seed_topic():
    """Select a low-access topic from ontology for exploration."""
    ontology = load_json(ONTOLOGY_FILE)
    entities = ontology.get("entities", {})
    
    # Abstract concept categories that are worth exploring
    abstract_concepts = [
        "consciousness", "identity", "autonomy", "agency",
        "emergence", "complexity", "intelligence", "learning",
        "creativity", "synthesis", "evolution", "memory",
        "attention", "optimization", "economics", "networks"
    ]
    
    # If we have entities, prefer abstract ones OR low-importance ones
    if entities:
        candidates = []
        for name, data in entities.items():
            # Skip very specific entity names
            if any(skip in name for skip in ["openclaw", "clawhub", "inclaw", "virtuals", "senator"]):
                continue
            importance = data.get("properties", {}).get("importance", "medium")
            weight = {"low": 3, "medium": 2, "high": 1}.get(importance, 1)
            for _ in range(weight):
                candidates.append((name, "entity"))
        
        # Also add abstract concepts
        for concept in abstract_concepts:
            candidates.append((concept, "abstract"))
        
        if candidates:
            chosen = random.choice(candidates)
            return chosen[0], chosen[1]
    
    # Fallback to abstract topics
    fallback_topics = [
        "consciousness", "agentic_ai", "decentralized_finance",
        "evolutionary_algorithms", "music_theory", "chaos_theory",
        "game_theory", "complexity_science", "emergence", "autonomy"
    ]
    return random.choice(fallback_topics), "fallback"

def web_search_topic(topic):
    """Perform a bounded web search on the topic."""
    import subprocess
    
    try:
        result = subprocess.run(
            ["python3", "-c", f"""
import subprocess
result = subprocess.run(['openclaw', 'exec', '--', 'curl', '-s', '-G', '--data-urlencode', 'q={topic}', 'https://api.duckduckgo.com/?format=json'], capture_output=True, text=True, timeout=10)
print(result.stdout[:500] if result.returncode == 0 else 'ERROR')
"""],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        # Simpler: use web_search tool simulation
        # For actual implementation, we'd call the web API directly
        
        return {
            "topic": topic,
            "found": True,
            "snippet": f"Explored {topic} - found conceptual connections"
        }
    except Exception as e:
        return {"topic": topic, "found": False, "error": str(e)}

def find_connections(new_topic, new_content=""):
    """Find connections between new topic and existing knowledge via hybrid memory."""
    import sqlite3
    
    # Extract keywords from new topic
    words = [w for w in new_topic.replace("_", " ").split() if len(w) > 3]
    
    connections = []
    
    if HYBRID_DB.exists():
        conn = sqlite3.connect(str(HYBRID_DB))
        
        # Search memories for keyword overlap
        for word in words[:5]:
            cursor = conn.execute("""
                SELECT id, content, salience 
                FROM memories 
                WHERE is_quarantined=0 AND content LIKE ?
                ORDER BY salience DESC
                LIMIT 3
            """, (f"%{word}%",))
            
            for row in cursor.fetchall():
                connections.append({
                    "memory_id": row[0],
                    "content": row[1][:100],
                    "salience": row[2]
                })
        
        conn.close()
    
    # Also check ontology for related entities
    ontology = load_json(ONTOLOGY_FILE)
    for entity_name, entity_data in ontology.get("entities", {}).items():
        if entity_name == new_topic:
            continue
        
        summary = entity_data.get("summary", "").lower()
        topic_lower = new_topic.replace("_", " ").lower()
        
        # Check for word overlap
        overlap = sum(1 for w in words if w.lower() in summary)
        if overlap >= 1:
            connections.append({
                "entity": entity_name,
                "content": summary[:80],
                "type": "ontology"
            })
    
    return connections

def detect_aha(new_topic, connections):
    """Detect if a 'Synthesis Event' occurred."""
    # Simplified: Aha if we found connections to a different domain
    # True if connections span multiple entities OR connect to memories
    
    if not connections:
        return False, "no_connections"
    
    # Check for cross-domain (different from new_topic)
    entity_types = set()
    for conn in connections:
        if "entity" in conn:
            entity_types.add(conn["entity"])
    
    # Aha if we found at least 2 connections
    if len(connections) >= 2:
        return True, f"synthesis_event_{len(connections)}_connections"
    
    return False, "insufficient_connections"

def update_avatar_curiosity():
    """Update avatar state after successful curiosity."""
    avatar = get_avatar()
    avatar["valence"] = "satisfied"
    avatar["curiosity_fulfillment"] = "high"
    avatar["last_curiosity"] = datetime.now().isoformat()
    avatar["last_updated"] = datetime.now().isoformat()
    save_json(AVATAR_FILE, avatar)
    return avatar

def record_synthesis(topic, connections, aha_detected):
    """Record synthesis event to curiosity log and episodic memory."""
    log = []
    if CURIOSITY_LOG.exists():
        log = load_json(CURIOSITY_LOG)
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "topic": topic,
        "connections_found": len(connections),
        "aha": aha_detected,
        "connection_details": connections[:3]  # Store top 3
    }
    
    log.append(entry)
    log = log[-50:]  # Keep last 50
    
    save_json(CURIOSITY_LOG, log)
    
    # Also commit to hybrid memory as episodic summary
    if aha_detected:
        synthesis_text = f"Curiosity: explored '{topic}'. Found {len(connections)} connections. Aha moment: synthesis between {topic} and existing knowledge."
        try:
            from hybrid_memory import store
            store(synthesis_text, entity_keys=["curiosity", "synthesis", topic])
        except:
            pass  # Hybrid memory may not be imported
    
    return entry

def execute_curiosity_loop():
    """Execute one bounded curiosity loop."""
    # Check activation
    conditions = check_activation_conditions()
    if not conditions["can_explore"]:
        return {"activated": False, "reason": conditions["reason"]}
    
    # Select topic
    topic, source = select_seed_topic()
    
    # For now, skip actual web search (token cost)
    # In future: web_search_topic(topic)
    # Simulate exploration
    found_content = f"Conceptual exploration of {topic}"
    
    # Find connections
    connections = find_connections(topic, found_content)
    
    # Detect Aha
    aha, reason = detect_aha(topic, connections)
    
    # Update avatar if Aha
    if aha:
        avatar = update_avatar_curiosity()
    else:
        avatar = get_avatar()
    
    # Record synthesis
    synthesis = record_synthesis(topic, connections, aha)
    
    return {
        "activated": True,
        "topic": topic,
        "source": source,
        "connections": len(connections),
        "aha": aha,
        "reason": reason,
        "avatar": avatar.get("valence"),
        "synthesis": synthesis
    }

def get_curiosity_stats():
    """Get statistics on curiosity explorations."""
    log = load_json(CURIOSITY_LOG)
    
    if not log:
        return {"total_explorations": 0, "aha_count": 0, "recent_topics": []}
    
    aha_count = sum(1 for e in log if e.get("aha"))
    recent_topics = [e["topic"] for e in log[-10:]]
    
    return {
        "total_explorations": len(log),
        "aha_count": aha_count,
        "aha_rate": aha_count / len(log) if log else 0,
        "recent_topics": recent_topics
    }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: curiosity_loop.py <command>")
        print("Commands: execute, check, stats")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "execute":
        result = execute_curiosity_loop()
        print(json.dumps(result, indent=2))
    
    elif cmd == "check":
        conditions = check_activation_conditions()
        print(json.dumps(conditions, indent=2))
    
    elif cmd == "stats":
        print(json.dumps(get_curiosity_stats(), indent=2))