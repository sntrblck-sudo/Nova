#!/usr/bin/env python3
"""
Loop Detection — Track repeated patterns and detect when Nova is spinning.
Part of the event-driven metacognition framework.
"""

import json
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
LOOP_LOG = MEMORY_DIR / "loop_log.json"
STATE_FILE = MEMORY_DIR / "loop_state.json"

MAX_LOOP_THRESHOLD = 3  # Flag after 3 repeats
LOOKBACK_WINDOW = 10  # Check last N actions

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"recent_actions": [], "loops_detected": [], "last_update": None}

def save_state(state):
    state["last_update"] = datetime.now().isoformat()
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def extract_action_signature(tool_call):
    """Extract a normalized signature from a tool call for comparison."""
    # Normalize: remove specific values (timestamps, IDs, etc), keep the pattern
    normalized = tool_call.lower()
    # Remove hex strings
    normalized = re.sub(r'0x[a-f0-9]+', '0xHEX', normalized)
    # Remove numbers
    normalized = re.sub(r'\d+', 'N', normalized)
    # Remove paths
    normalized = re.sub(r'/[a-z0-9_./]+', '/PATH', normalized)
    # Collapse whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized

def check_for_loop(new_action):
    """Check if new action matches a recent repeated pattern."""
    state = load_state()
    
    signature = extract_action_signature(new_action)
    state["recent_actions"].append(signature)
    
    # Keep only last LOOKBACK_WINDOW
    state["recent_actions"] = state["recent_actions"][-LOOKBACK_WINDOW:]
    
    # Count occurrences of this signature
    counts = Counter(state["recent_actions"])
    
    loops = []
    for sig, count in counts.items():
        if count >= MAX_LOOP_THRESHOLD:
            # Find when this started
            indices = [i for i, s in enumerate(state["recent_actions"]) if s == sig]
            if indices:
                loops.append({
                    "signature": sig[:80],  # Truncate for readability
                    "count": count,
                    "started_at_index": indices[0],
                    "current_index": len(state["recent_actions"]) - 1
                })
    
    # Save state
    save_state(state)
    
    return loops

def record_action(action):
    """Record an action and check for loops."""
    loops = check_for_loop(action)
    
    if loops:
        # Log the loop
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action[:100],
            "loops": loops
        }
        
        # Load existing log
        loop_log = []
        if LOOP_LOG.exists():
            with open(LOOP_LOG) as f:
                loop_log = json.load(f)
        
        loop_log.append(log_entry)
        
        # Keep last 100 entries
        loop_log = loop_log[-100:]
        
        with open(LOOP_LOG, 'w') as f:
            json.dump(loop_log, f, indent=2)
    
    return loops

def get_active_loops():
    """Get currently active loops (last action still in repeat pattern)."""
    state = load_state()
    if not state["recent_actions"]:
        return []
    
    counts = Counter(state["recent_actions"])
    active = []
    for sig, count in counts.items():
        if count >= MAX_LOOP_THRESHOLD:
            active.append({"signature": sig[:80], "count": count})
    
    return active

def clear_state():
    """Clear the loop detection state."""
    state = {"recent_actions": [], "loops_detected": [], "last_update": datetime.now().isoformat()}
    save_state(state)

def get_loop_history(limit=10):
    """Get recent loop detection events."""
    if not LOOP_LOG.exists():
        return []
    
    with open(LOOP_LOG) as f:
        log = json.load(f)
    
    return log[-limit:]

def suggest_pivot(loops):
    """Suggest a pivot strategy when loops are detected."""
    if not loops:
        return None
    
    suggestions = []
    for loop in loops:
        sig = loop.get("signature", "")
        count = loop.get("count", 0)
        
        # Generic suggestions based on pattern
        if "web_fetch" in sig or "search" in sig:
            suggestions.append("Consider changing search terms or trying a different source")
        elif "exec" in sig or "python" in sig:
            suggestions.append("Command may be failing silently — check for errors")
        elif "read" in sig:
            suggestions.append("File access issue — verify path exists or try alternative")
        elif "edit" in sig or "write" in sig:
            suggestions.append("File operation repeating — check permissions or content")
        else:
            suggestions.append("Action repeating — try a different approach")
    
    return suggestions

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: loop_detector.py <command> [args]")
        print("Commands: check <action>, active, history, clear, suggest")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "check" and len(sys.argv) >= 3:
        loops = record_action(sys.argv[2])
        if loops:
            print(f"LOOP DETECTED: {len(loops)} pattern(s)")
            for l in loops:
                print(f"  - {l['signature'][:60]} (x{l['count']})")
        else:
            print("No loop detected")
    
    elif cmd == "active":
        loops = get_active_loops()
        if loops:
            print(f"Active loops: {len(loops)}")
            for l in loops:
                print(f"  - {l['signature'][:60]} (x{l['count']})")
        else:
            print("No active loops")
    
    elif cmd == "history":
        history = get_loop_history()
        print(f"Recent loops: {len(history)}")
        for h in history[-5:]:
            print(f"  [{h['timestamp']}] {h['action'][:50]}...")
    
    elif cmd == "clear":
        clear_state()
        print("Loop state cleared")
    
    elif cmd == "suggest":
        state = load_state()
        loops = get_active_loops()
        if loops:
            suggestions = suggest_pivot(loops)
            print("Pivot suggestions:")
            for s in suggestions:
                print(f"  - {s}")
        else:
            print("No loops to suggest pivots for")