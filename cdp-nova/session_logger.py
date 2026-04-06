#!/usr/bin/env python3
"""
Nova's Session Event Logger
Lightweight event capture during sessions — decisions, builds, ideas, external events
Appends to memory/session_events.jsonl for startup context reconstruction
"""

import json
import sys
import os
from datetime import datetime, timezone

LOG_FILE = os.path.expanduser("~/.openclaw/workspace/memory/session_events.jsonl")

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")

def log_event(event_type, description, details=None, session_key="main"):
    entry = {
        "timestamp": now_iso(),
        "event_type": event_type,
        "description": description,
        "session_key": session_key,
    }
    if details:
        entry["details"] = details
    
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    return entry

def get_recent_events(hours=24, event_type=None):
    """Get recent events from the last N hours, optionally filtered by type."""
    if not os.path.exists(LOG_FILE):
        return []
    
    cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
    events = []
    
    with open(LOG_FILE) as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                ts = datetime.fromisoformat(entry["timestamp"].replace("+00:00", "+0000"))
                if ts.timestamp() >= cutoff:
                    if event_type is None or entry.get("event_type") == event_type:
                        events.append(entry)
            except:
                continue
    
    return events

def get_last_session_events():
    """Get all events from the most recent session (by session_key)."""
    if not os.path.exists(LOG_FILE):
        return []
    
    sessions = {}
    with open(LOG_FILE) as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                sk = entry.get("session_key", "unknown")
                if sk not in sessions:
                    sessions[sk] = []
                sessions[sk].append(entry)
            except:
                continue
    
    if not sessions:
        return []
    
    # Return the most recent session's events
    # Sort by last timestamp
    def last_ts(evts):
        return max(e["timestamp"] for e in evts)
    
    most_recent_key = max(sessions.keys(), key=lambda k: last_ts(sessions[k]))
    return sessions[most_recent_key]

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "log"
    
    if cmd == "log":
        if len(sys.argv) < 3:
            print("Usage: session_logger.py log <type> <description> [details_json]")
            sys.exit(1)
        event_type = sys.argv[2]
        desc = sys.argv[3]
        details = json.loads(sys.argv[4]) if len(sys.argv) > 4 else None
        e = log_event(event_type, desc, details)
        print(f"Logged: [{e['event_type']}] {e['description']}")
    
    elif cmd == "recent":
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        events = get_recent_events(hours)
        print(f"=== {len(events)} events in last {hours}h ===")
        for e in events[-20:]:
            print(f"  [{e['timestamp']}] {e['event_type']}: {e['description'][:80]}")
    
    elif cmd == "last-session":
        events = get_last_session_events()
        print(f"=== Last session: {len(events)} events ===")
        for e in events:
            print(f"  [{e['timestamp']}] {e['event_type']}: {e['description'][:80]}")
    
    elif cmd == "since":
        # Get events since a timestamp
        if len(sys.argv) < 3:
            print("Usage: session_logger.py since <iso_timestamp>")
            sys.exit(1)
        since_ts = sys.argv[2]
        events = get_recent_events(hours=999)
        filtered = [e for e in events if e["timestamp"] > since_ts]
        print(f"=== {len(filtered)} events since {since_ts} ===")
        for e in filtered:
            print(f"  [{e['timestamp']}] {e['event_type']}: {e['description'][:80]}")
    
    else:
        print("Commands: log <type> <desc> [details], recent [hours], last-session, since <ts>")
