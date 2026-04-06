#!/usr/bin/env python3
"""
Nova's Session Context Reconstructor
At session startup, runs to rebuild what happened since last contact
Combines: session_logger events + execution_log events + continuity.log
"""

import sqlite3
import json
import os
from datetime import datetime, timezone, timedelta

WORKSPACE = os.path.expanduser("~/.openclaw/workspace")
EXEC_DB = os.path.join(WORKSPACE, "memory/execution_logs.db")
SESS_DB = os.path.join(WORKSPACE, "memory/session_events.jsonl")
CONT_LOG = os.path.join(WORKSPACE, "memory/continuity.log")
STATE_FILE = os.path.join(WORKSPACE, "memory/last_session_state.json")

def get_last_session_ts():
    """Get timestamp of last session from state file."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            s = json.load(f)
            return s.get("last_session_end")
    return None

def save_last_session_ts(ts):
    """Save current session start as last session end."""
    with open(STATE_FILE, "w") as f:
        json.dump({"last_session_end": ts, "last_check": datetime.now(timezone.utc).isoformat()}, f)

def get_recent_session_events(hours=48):
    """Get events from session_logger."""
    if not os.path.exists(SESS_DB):
        return []
    
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    events = []
    
    with open(SESS_DB) as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                ts = datetime.fromisoformat(entry["timestamp"].replace("+00:00", ""))
                if ts >= cutoff:
                    events.append(entry)
            except:
                continue
    return events

def get_recent_exec_events(hours=48):
    """Get events from execution_logs.db."""
    if not os.path.exists(EXEC_DB):
        return []
    
    events = []
    conn = sqlite3.connect(EXEC_DB)
    c = conn.cursor()
    
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute("""
        SELECT timestamp, event_type, task, outcome 
        FROM execution_logs 
        WHERE timestamp > ? 
        ORDER BY timestamp DESC
    """, (cutoff,))
    
    for row in c.fetchall():
        events.append({
            "timestamp": row[0],
            "event_type": row[1],
            "task": row[2],
            "outcome": row[3],
        })
    
    conn.close()
    return events

def get_last_logged_session():
    """Read the last session entry from continuity.log."""
    if not os.path.exists(CONT_LOG):
        return None
    
    with open(CONT_LOG) as f:
        lines = f.readlines()
    
    # Find last timestamp in continuity log
    for line in reversed(lines):
        if "## 2026" in line or "## 2025" in line:
            return line.strip()
    return lines[-1].strip() if lines else None

def summarize():
    now = datetime.now(timezone.utc)
    last_ts = get_last_session_ts()
    
    print(f"=== Nova Session Context ===")
    print(f"Current time (UTC): {now.isoformat()}")
    print(f"Last session ended: {last_ts or 'unknown (first run?)'}")
    print()
    
    # Session logger events
    sess_events = get_recent_session_events()
    exec_events = get_recent_exec_events()
    last_cont = get_last_logged_session()
    
    print(f"--- Session Logger ({len(sess_events)} events) ---")
    if sess_events:
        for e in sess_events[-10:]:
            print(f"  [{e['timestamp']}] {e.get('event_type','?')}: {e.get('description','')[:70]}")
    else:
        print("  (no events logged)")
    
    print(f"\n--- Execution Log (last 48h, {len(exec_events)} entries) ---")
    # Show only interesting events (not heartbeat/cron)
    interesting = [e for e in exec_events if e["event_type"] not in ("heartbeat", "cron_run_import")]
    if interesting:
        for e in interesting[:10]:
            print(f"  [{e['timestamp']}] {e['event_type']}: {e['task'][:60] if e['task'] else ''}")
    else:
        print("  (no significant execution events)")
    
    print(f"\n--- Continuity Log (last entry) ---")
    print(f"  {last_cont}")
    
    print(f"\n--- What Nova should know ---")
    if sess_events:
        latest = sess_events[-1]
        print(f"Last event logged: [{latest['timestamp']}] {latest.get('event_type')}: {latest.get('description','')}")
    if last_cont:
        print(f"Last continuity entry: {last_cont[:100]}")
    
    return {
        "session_events": sess_events,
        "exec_events": exec_events,
        "last_continuity": last_cont,
        "last_session_ts": last_ts,
    }

if __name__ == "__main__":
    summarize()
