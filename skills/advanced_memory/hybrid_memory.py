#!/usr/bin/env python3
"""
Hybrid Memory Layer — Semantic (TF-IDF) + Relational (SQLite)
Frugal implementation without numpy or heavy ML dependencies.
"""

import json
import re
import sqlite3
import math
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
EMBEDDINGS_FILE = MEMORY_DIR / "embeddings.json"
RECALL_DB = MEMORY_DIR / "recall.db"
CORE_RULES_FILE = MEMORY_DIR / "core_rules.json"
AVATAR_FILE = MEMORY_DIR / "avatar_state.json"

MAX_EMBEDDINGS = 500
MAX_RECORDS = 1000

# Stopwords for keyword extraction
STOPWORDS = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
                 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                 'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
                 'that', 'this', 'these', 'those', 'it', 'its', 'they', 'them',
                 'their', 'we', 'our', 'you', 'your', 'he', 'she', 'him', 'her',
                 'i', 'my', 'me', 'what', 'which', 'who', 'when', 'where', 'why',
                 'how', 'not', 'no', 'so', 'if', 'then', 'than', 'about', 'into',
                 'through', 'during', 'before', 'after', 'above', 'below', 'up',
                 'down', 'out', 'off', 'over', 'under', 'again', 'further', 'once'])


def init_db():
    """Initialize SQLite database."""
    RECALL_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(RECALL_DB))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            salience REAL DEFAULT 0.5,
            entity_keys TEXT DEFAULT '[]',
            is_quarantined INTEGER DEFAULT 0,
            last_accessed TEXT,
            access_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            type TEXT,
            summary TEXT,
            updated TEXT
        );
        CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            summary TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            outcome TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp);
        CREATE INDEX IF NOT EXISTS idx_memories_salience ON memories(salience);
    """)
    conn.commit()
    conn.close()

def load_embeddings():
    if EMBEDDINGS_FILE.exists():
        with open(EMBEDDINGS_FILE) as f:
            return json.load(f)
    return {"entries": [], "keywords": {}}

def save_embeddings(embeddings):
    with open(EMBEDDINGS_FILE, 'w') as f:
        json.dump(embeddings, f, indent=2)

def extract_keywords(text, top_k=20):
    """Extract keywords using TF-IDF style scoring."""
    text = text.lower()
    words = re.findall(r'\b[a-z]{3,}\b', text)
    
    # Count frequencies
    freq = Counter(words)
    
    # Remove stopwords
    freq = {w: c for w, c in freq.items() if w not in STOPWORDS}
    
    # Score by frequency (simple TF)
    total = sum(freq.values()) or 1
    scored = {w: c/total for w, c in freq.items()}
    
    # Sort and return top_k
    sorted_words = sorted(scored.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:top_k]]

def compute_vector(keywords, all_keywords):
    """Compute sparse vector for keywords."""
    vector = {}
    for kw in keywords:
        if kw in all_keywords:
            vector[kw] = all_keywords[kw]
    return vector

def cosine_similarity(v1, v2):
    """Compute cosine similarity between two sparse vectors."""
    if not v1 or not v2:
        return 0.0
    
    # Dot product
    common = set(v1.keys()) & set(v2.keys())
    dot = sum(v1[k] * v2[k] for k in common)
    
    # Magnitudes
    mag1 = math.sqrt(sum(v**2 for v in v1.values()))
    mag2 = math.sqrt(sum(v**2 for v in v2.values()))
    
    if mag1 == 0 or mag2 == 0:
        return 0.0
    
    return dot / (mag1 * mag2)

def store(content, entity_keys=None, metadata=None):
    """Store a memory in both semantic and relational layers."""
    init_db()
    embeddings = load_embeddings()
    
    # Check limits
    if len(embeddings["entries"]) >= MAX_EMBEDDINGS:
        # Remove lowest salience entry
        embeddings["entries"].sort(key=lambda x: x.get("salience", 0))
        removed = embeddings["entries"].pop(0)
        # Also remove from DB
        conn = sqlite3.connect(str(RECALL_DB))
        conn.execute("DELETE FROM memories WHERE id=?", (removed["id"],))
        conn.commit()
        conn.close()
    
    # Extract keywords
    keywords = extract_keywords(content)
    
    # Update global keyword frequencies
    for kw in keywords:
        embeddings["keywords"][kw] = embeddings["keywords"].get(kw, 0) + 1
    
    # Compute normalized vector
    vector = compute_vector(keywords, embeddings["keywords"])
    
    # Store in SQLite
    now = datetime.now().isoformat()
    conn = sqlite3.connect(str(RECALL_DB))
    cursor = conn.execute("""
        INSERT INTO memories (content, timestamp, salience, entity_keys, last_accessed, access_count)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (content, now, 0.5, json.dumps(entity_keys or []), now, 1))
    memory_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Store in embeddings
    entry = {
        "id": memory_id,
        "keywords": keywords,
        "vector": vector,
        "timestamp": now,
        "salience": 0.5
    }
    embeddings["entries"].append(entry)
    save_embeddings(embeddings)
    
    return {"memory_id": memory_id, "keywords": keywords}

def recall(query, depth=5, entity_filter=None, time_filter=None):
    """Recall memories using semantic search + relational filtering."""
    init_db()
    embeddings = load_embeddings()
    
    # Extract query keywords
    query_keywords = extract_keywords(query)
    query_vector = compute_vector(query_keywords, embeddings["keywords"])
    
    # Compute similarities
    similarities = []
    for entry in embeddings["entries"]:
        sim = cosine_similarity(query_vector, entry["vector"])
        if sim > 0.1:
            similarities.append((entry, sim))
    
    # Sort by similarity
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    # Fetch from SQLite with filters
    results = []
    conn = sqlite3.connect(str(RECALL_DB))
    
    for entry, sim in similarities[:depth * 2]:
        cursor = conn.execute("""
            SELECT id, content, timestamp, salience, entity_keys, is_quarantined, access_count
            FROM memories WHERE id=? AND is_quarantined=0
        """, (entry["id"],))
        row = cursor.fetchone()
        
        if row:
            keys = json.loads(row[4]) if row[4] else []
            
            # Apply entity filter
            if entity_filter and not any(entity_filter in k for k in keys):
                continue
            
            # Apply time filter (last N hours)
            if time_filter:
                ts = datetime.fromisoformat(row[2])
                if datetime.now() - ts > timedelta(hours=time_filter):
                    continue
            
            # Update access count
            conn.execute("UPDATE memories SET access_count=access_count+1, last_accessed=? WHERE id=?", 
                         (datetime.now().isoformat(), row[0]))
            
            results.append({
                "id": row[0],
                "content": row[1],
                "timestamp": row[2],
                "salience": row[3],
                "similarity": sim,
                "entity_keys": keys
            })
    
    conn.commit()
    conn.close()
    
    return results[:depth]

def quarantine(memory_id, reason=""):
    """Quarantine a memory."""
    init_db()
    conn = sqlite3.connect(str(RECALL_DB))
    conn.execute("UPDATE memories SET is_quarantined=1 WHERE id=?", (memory_id,))
    conn.commit()
    conn.close()
    
    # Add to quarantine review queue
    review_file = MEMORY_DIR / "quarantine_review.json"
    review = json.load(open(review_file)) if review_file.exists() else []
    review.append({"memory_id": memory_id, "reason": reason, "timestamp": datetime.now().isoformat()})
    json.dump(review, open(review_file, 'w'), indent=2)

def get_quarantine_review():
    """Get items pending quarantine review."""
    review_file = MEMORY_DIR / "quarantine_review.json"
    if review_file.exists():
        return json.load(open(review_file))
    return []

def load_core_rules():
    if CORE_RULES_FILE.exists():
        return json.load(open(CORE_RULES_FILE))
    return []

def save_core_rules(rules):
    with open(CORE_RULES_FILE, 'w') as f:
        json.dump(rules, f, indent=2)

def consolidate():
    """Weekly consolidation: raw → episodic → core rules."""
    init_db()
    
    # Find memories older than 48h that haven't been consolidated
    cutoff = (datetime.now() - timedelta(hours=48)).isoformat()
    
    conn = sqlite3.connect(str(RECALL_DB))
    
    # Get old memories
    cursor = conn.execute("""
        SELECT id, content, timestamp, salience, access_count 
        FROM memories 
        WHERE timestamp < ? AND is_quarantined=0
        ORDER BY access_count DESC
        LIMIT 50
    """, (cutoff,))
    old_memories = cursor.fetchall()
    
    if not old_memories:
        conn.close()
        return {"consolidated": 0, "new_core_rules": 0}
    
    # Group into episodes (simplified: by day)
    episodes = {}
    for m in old_memories:
        day = m[2][:10]  # YYYY-MM-DD
        if day not in episodes:
            episodes[day] = []
        episodes[day].append(m[1][:100])  # Truncate content
    
    # Create episode summaries
    episode_summaries = []
    for day, contents in episodes.items():
        summary = f"Episode {day}: {'; '.join(contents[:3])}"
        episode_summaries.append({"day": day, "summary": summary})
        
        # Insert episode
        conn.execute("""
            INSERT INTO episodes (summary, start_time, end_time, outcome) 
            VALUES (?, ?, ?, ?)
        """, (summary, f"{day}T00:00:00", f"{day}T23:59:59", "consolidated"))
    
    # Check for new core rules (high access, high salience, not yet in core rules)
    core_rules = load_core_rules()
    current_rule_texts = {r.get("content", "")[:50] for r in core_rules}
    
    new_rules = 0
    for m in old_memories[:10]:
        if m[4] >= 5 and m[3] >= 0.7:  # High access, high salience
            if m[1][:50] not in current_rule_texts:
                core_rules.append({
                    "content": m[1][:200],
                    "salience": m[3],
                    "access_count": m[4],
                    "verified": True,
                    "failure_count": 0,
                    "added": datetime.now().isoformat()
                })
                new_rules += 1
    
    # Delete old memories that were consolidated
    old_ids = [m[0] for m in old_memories]
    if old_ids:
        conn.execute(f"DELETE FROM memories WHERE id IN ({','.join('?'*len(old_ids))})", old_ids)
    
    conn.commit()
    conn.close()
    
    save_core_rules(core_rules)
    
    # Clean up embeddings
    embeddings = load_embeddings()
    embeddings["entries"] = [e for e in embeddings["entries"] if e["id"] not in old_ids]
    save_embeddings(embeddings)
    
    return {"consolidated": len(old_memories), "new_core_rules": new_rules, "episodes": len(episodes)}

def update_salience(memory_id, delta):
    """Update salience score for a memory."""
    init_db()
    conn = sqlite3.connect(str(RECALL_DB))
    conn.execute("UPDATE memories SET salience = MAX(0, MIN(1, salience + ?)) WHERE id=?", (delta, memory_id))
    conn.commit()
    conn.close()

def load_avatar():
    """Load current avatar state."""
    if AVATAR_FILE.exists():
        return json.load(open(AVATAR_FILE))
    return {
        "valence": "neutral",
        "confidence": 0.5,
        "active_goals": 0,
        "health": "unknown",
        "token_today": 0,
        "last_meaningful_event": None
    }

def save_avatar(state):
    with open(AVATAR_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def update_avatar(valence=None, confidence=None, active_goals=None, health=None, tokens_delta=None):
    """Update avatar state."""
    avatar = load_avatar()
    
    if valence is not None:
        avatar["valence"] = valence
    if confidence is not None:
        avatar["confidence"] = confidence
    if active_goals is not None:
        avatar["active_goals"] = active_goals
    if health is not None:
        avatar["health"] = health
    if tokens_delta is not None:
        avatar["token_today"] = max(0, avatar.get("token_today", 0) + tokens_delta)
    
    avatar["last_updated"] = datetime.now().isoformat()
    save_avatar(avatar)
    return avatar

def stats():
    """Get memory statistics."""
    init_db()
    conn = sqlite3.connect(str(RECALL_DB))
    
    cursor = conn.execute("SELECT COUNT(*) FROM memories")
    memory_count = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM episodes")
    episode_count = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM memories WHERE is_quarantined=1")
    quarantine_count = cursor.fetchone()[0]
    
    conn.close()
    
    embeddings = load_embeddings()
    core_rules = load_core_rules()
    
    return {
        "memories": memory_count,
        "episodes": episode_count,
        "embeddings": len(embeddings["entries"]),
        "quarantined": quarantine_count,
        "core_rules": len(core_rules),
        "avatar": load_avatar()
    }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: hybrid_memory.py <command> [args]")
        print("Commands: store, recall, quarantine, consolidate, stats, avatar")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "store" and len(sys.argv) >= 3:
        result = store(sys.argv[2])
        print(f"Stored: {result}")
    
    elif cmd == "recall" and len(sys.argv) >= 3:
        results = recall(sys.argv[2])
        print(json.dumps(results, indent=2))
    
    elif cmd == "quarantine" and len(sys.argv) >= 3:
        quarantine(int(sys.argv[2]))
        print("Quarantined")
    
    elif cmd == "consolidate":
        result = consolidate()
        print(json.dumps(result, indent=2))
    
    elif cmd == "stats":
        print(json.dumps(stats(), indent=2))
    
    elif cmd == "avatar":
        if len(sys.argv) >= 3:
            if sys.argv[2] == "update":
                update_avatar()
            elif sys.argv[2] == "get":
                print(json.dumps(load_avatar(), indent=2))
        else:
            print(json.dumps(load_avatar(), indent=2))
    
    else:
        print("Invalid command")