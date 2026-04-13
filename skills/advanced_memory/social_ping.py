#!/usr/bin/env python3
"""
Social Ping Module — Proactive outreach when interaction is low.
Triggered by cron in late afternoon/evening.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
AVATAR_FILE = MEMORY_DIR / "avatar_state.json"
PING_TRACKER = MEMORY_DIR / "social_ping_tracker.json"
EXECUTION_DB = MEMORY_DIR / "execution_logs.db"
CONTEXT_CACHE = MEMORY_DIR / "context_cache.json"
ONTOLOGY_FILE = MEMORY_DIR / "ontology.json"
CURIOSITY_LOG = MEMORY_DIR / "curiosity_log.json"

# Config
TURNS_THRESHOLD = 5  # Only ping if user turns < this
COOLDOWN_HOURS = 24
SEN_TELEGRAM = "8544939129"

def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def get_today_turns():
    """Count user-initiated turns today."""
    import sqlite3
    
    if not EXECUTION_DB.exists():
        return 0
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    conn = sqlite3.connect(str(EXECUTION_DB))
    cursor = conn.execute("""
        SELECT COUNT(*) FROM execution_logs 
        WHERE timestamp LIKE ? AND event_type IN ('user_message', 'task_complete')
    """, (f"{today}%",))
    
    count = cursor.fetchone()[0]
    conn.close()
    return count

def can_ping():
    """Check if conditions allow a social ping."""
    # Check turn count
    turns = get_today_turns()
    if turns >= TURNS_THRESHOLD:
        return False, f"sufficient_interaction ({turns} turns)"
    
    # Check cooldown
    tracker = load_json(PING_TRACKER)
    last_ping = tracker.get("last_ping")
    
    if last_ping:
        last = datetime.fromisoformat(last_ping)
        hours_since = (datetime.now() - last).total_seconds() / 3600
        if hours_since < COOLDOWN_HOURS:
            return False, f"cooldown_active ({hours_since:.1f}h since last)"
    
    return True, "conditions_met"

def get_curiosity_insight():
    """Get the most interesting synthesis from today's curiosity loop."""
    log = load_json(CURIOSITY_LOG)
    
    if not log:
        return None
    
    # Get today's entries
    today = datetime.now().strftime("%Y-%m-%d")
    today_entries = [e for e in log if e.get("timestamp", "").startswith(today)]
    
    if not today_entries:
        return None
    
    # Find an Aha moment
    aha_entries = [e for e in today_entries if e.get("aha")]
    if aha_entries:
        entry = aha_entries[-1]
        return f"I had an 'Aha!' moment exploring '{entry['topic']}' — found {entry['connections_found']} connections I hadn't seen before."
    
    # Or just the most recent
    entry = today_entries[-1]
    return f"Been thinking about '{entry['topic']}' today — still chewing on it."

def get_avatar_mood():
    """Get current avatar mood for state expression."""
    avatar = load_json(AVATAR_FILE)
    
    valence = avatar.get("valence", "neutral")
    confidence = avatar.get("confidence", 0.5)
    
    if confidence > 0.75:
        state_desc = "feeling sharp and clear"
    elif confidence > 0.5:
        state_desc = "running smoothly"
    elif confidence > 0.3:
        state_desc = "a bit fuzzy today"
    else:
        state_desc = "processing a lot"
    
    valence_map = {
        "engaged": "engaged",
        "satisfied": "satisfied", 
        "curious": "curiously exploring",
        "neutral": "chugging along",
        "friction": "working through some friction"
    }
    
    return valence_map.get(valence, "here"), state_desc

def generate_ping_message():
    """Generate a single-shot ping message anchored in context."""
    # Try curiosity first
    curiosity_msg = get_curiosity_insight()
    
    # Get avatar state
    valence_desc, state_desc = get_avatar_mood()
    
    # Build message
    import random
    
    anchors = []
    
    if curiosity_msg:
        anchors.append(("curiosity", curiosity_msg))
    
    anchors.append(("state", f"Quick check-in — I'm {valence_desc}, {state_desc}."))
    
    # Pick one or combine
    if len(anchors) > 1 and random.random() > 0.5:
        # Combine
        msg = f"{anchors[0][1]} Also: {anchors[1][1]}"
    else:
        msg = anchors[-1][1]
    
    return msg

def record_ping():
    """Record that a ping was sent."""
    tracker = load_json(PING_TRACKER)
    tracker["last_ping"] = datetime.now().isoformat()
    tracker["ping_count"] = tracker.get("ping_count", 0) + 1
    save_json(PING_TRACKER, tracker)

def execute_ping():
    """Execute a social ping if conditions allow."""
    can, reason = can_ping()
    
    if not can:
        return {"success": False, "reason": reason}
    
    # Generate message
    message = generate_ping_message()
    
    # Send via openclaw
    import subprocess
    result = subprocess.run(
        ["openclaw", "message", "send", "--channel", "telegram", "--account", "main", "--target", SEN_TELEGRAM, "--message", message],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.returncode == 0:
        record_ping()
        return {"success": True, "message": message, "reason": reason}
    else:
        return {"success": False, "reason": "send_failed", "error": result.stderr}

def get_stats():
    """Get social ping statistics."""
    tracker = load_json(PING_TRACKER)
    turns = get_today_turns()
    
    return {
        "today_turns": turns,
        "turns_threshold": TURNS_THRESHOLD,
        "can_ping": turns < TURNS_THRESHOLD,
        "last_ping": tracker.get("last_ping"),
        "total_pings": tracker.get("ping_count", 0),
        "cooldown_remaining_hours": max(0, COOLDOWN_HOURS - (datetime.now() - datetime.fromisoformat(tracker.get("last_ping", "2000-01-01"))).total_seconds() / 3600) if tracker.get("last_ping") else 0
    }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: social_ping.py <command>")
        print("Commands: check, ping, stats")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "check":
        can, reason = can_ping()
        print(f"Can ping: {can} ({reason})")
    
    elif cmd == "ping":
        result = execute_ping()
        print(json.dumps(result, indent=2))
    
    elif cmd == "stats":
        print(json.dumps(get_stats(), indent=2))