#!/usr/bin/env python3
"""
Task Completion Marker — Trigger memory consolidation on meaningful events.
Part of the event-driven metacognition framework.
"""

import json
from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
TASK_MARKER_FILE = MEMORY_DIR / "task_markers.json"
COMPLETION_LOG = MEMORY_DIR / "completion_log.json"

def mark_complete(task_id, outcome="success", notes=""):
    """Mark a task as complete and trigger consolidation check."""
    markers = load_markers()
    
    # Update or create marker
    markers[task_id] = {
        "task_id": task_id,
        "completed_at": datetime.now().isoformat(),
        "outcome": outcome,
        "notes": notes,
        "consolidation_triggered": False
    }
    
    save_markers(markers)
    
    # Check if consolidation is warranted
    consolidation_needed = should_consolidate(task_id, outcome)
    
    if consolidation_needed:
        markers[task_id]["consolidation_triggered"] = True
        save_markers(markers)
        return {"complete": True, "consolidation_triggered": True}
    
    return {"complete": True, "consolidation_triggered": False}

def should_consolidate(task_id, outcome):
    """Determine if consolidation should run after this task."""
    # Always consolidate successful tasks to store the win
    if outcome == "success":
        return True
    
    # Always consolidate failed tasks to learn from the failure
    if outcome == "failure":
        return True
    
    # Partial success — consolidate if it was a significant task
    if outcome == "partial":
        return True
    
    return False

def load_markers():
    if TASK_MARKER_FILE.exists():
        with open(TASK_MARKER_FILE) as f:
            return json.load(f)
    return {}

def save_markers(markers):
    with open(TASK_MARKER_FILE, 'w') as f:
        json.dump(markers, f, indent=2)

def get_recent_completions(limit=10):
    """Get recently completed tasks."""
    markers = load_markers()
    sorted_markers = sorted(
        markers.items(),
        key=lambda x: x[1].get("completed_at", ""),
        reverse=True
    )
    return [m for _, m in sorted_markers[:limit]]

def get_pending_consolidation():
    """Get tasks that completed but haven't been consolidated."""
    markers = load_markers()
    pending = [
        {"task_id": k, **v}
        for k, v in markers.items()
        if v.get("consolidation_triggered") and not v.get("consolidated", False)
    ]
    return pending

def mark_consolidated(task_id):
    """Mark a task as having been consolidated."""
    markers = load_markers()
    if task_id in markers:
        markers[task_id]["consolidated"] = True
        markers[task_id]["consolidated_at"] = datetime.now().isoformat()
        save_markers(markers)

def log_completion(task_id, outcome, summary=""):
    """Log a completion event for later analysis."""
    log = []
    if COMPLETION_LOG.exists():
        with open(COMPLETION_LOG) as f:
            log = json.load(f)
    
    entry = {
        "task_id": task_id,
        "outcome": outcome,
        "summary": summary,
        "logged_at": datetime.now().isoformat()
    }
    
    log.append(entry)
    
    # Keep last 100 entries
    log = log[-100:]
    
    with open(COMPLETION_LOG, 'w') as f:
        json.dump(log, f, indent=2)

def get_outcome_stats():
    """Get statistics on task outcomes."""
    log = []
    if COMPLETION_LOG.exists():
        with open(COMPLETION_LOG) as f:
            log = json.load(f)
    
    if not log:
        return {"total": 0, "success": 0, "failure": 0, "partial": 0}
    
    outcomes = [e.get("outcome", "unknown") for e in log]
    return {
        "total": len(outcomes),
        "success": outcomes.count("success"),
        "failure": outcomes.count("failure"),
        "partial": outcomes.count("partial")
    }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: task_marker.py <command> [args]")
        print("Commands: complete <task_id> [outcome], pending, stats, recent")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "complete" and len(sys.argv) >= 3:
        task_id = sys.argv[2]
        outcome = sys.argv[3] if len(sys.argv) > 3 else "success"
        notes = sys.argv[4] if len(sys.argv) > 4 else ""
        
        result = mark_complete(task_id, outcome, notes)
        print(f"Task {task_id} marked as {outcome}")
        if result.get("consolidation_triggered"):
            print("Consolidation triggered")
        log_completion(task_id, outcome)
    
    elif cmd == "pending":
        pending = get_pending_consolidation()
        print(f"Pending consolidation: {len(pending)} tasks")
        for p in pending:
            print(f"  - {p['task_id']} ({p['outcome']})")
    
    elif cmd == "stats":
        print(json.dumps(get_outcome_stats(), indent=2))
    
    elif cmd == "recent":
        recent = get_recent_completions()
        print(f"Recent completions: {len(recent)}")
        for r in recent[:5]:
            print(f"  - {r['task_id']}: {r['outcome']} at {r['completed_at']}")