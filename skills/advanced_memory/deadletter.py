#!/usr/bin/env python3
"""
Deadletter Queue — Failed work that exhausted retries goes here.
Keeps track of what failed, why, when, and how to potentially recover.
"""

import json
from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
QUEUES_DIR = MEMORY_DIR / "queues"
DEADLETTER_FILE = QUEUES_DIR / "deadletter.json"
INCIDENTS_DIR = MEMORY_DIR / "incidents"

QUEUES_DIR.mkdir(parents=True, exist_ok=True)
INCIDENTS_DIR.mkdir(parents=True, exist_ok=True)

def load_deadletter():
    if DEADLETTER_FILE.exists():
        with open(DEADLETTER_FILE) as f:
            return json.load(f)
    return []

def save_deadletter(items):
    with open(DEADLETTER_FILE, 'w') as f:
        json.dump(items, f, indent=2)

def add_item(task_type, task_data, failure_reason, retry_count=0, max_retries=3):
    """
    Add a failed item to the deadletter queue.
    
    task_type: what kind of task (e.g., "send_tx", "web_fetch", "skill_execution")
    task_data: the original task parameters
    failure_reason: why it failed
    retry_count: how many times we tried
    max_retries: how many attempts before giving up
    """
    items = load_deadletter()
    
    item = {
        "id": f"dl_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "task_type": task_type,
        "task_data": task_data,
        "failure_reason": failure_reason,
        "retry_count": retry_count,
        "max_retries": max_retries,
        "added_at": datetime.now().isoformat(),
        "status": "pending",
        "last_attempt": datetime.now().isoformat(),
        "resolution": None
    }
    
    items.append(item)
    save_deadletter(items)
    
    # Also write incident memo
    write_incident_memo(item)
    
    return item

def write_incident_memo(item):
    """Write an incident memo for a deadletter item."""
    incident = {
        "incident_id": item["id"],
        "task_type": item["task_type"],
        "failure_reason": item["failure_reason"],
        "occurred_at": item["added_at"],
        "task_data": item["task_data"]
    }
    
    incident_file = INCIDENTS_DIR / f"{item['id']}.json"
    with open(incident_file, 'w') as f:
        json.dump(incident, f, indent=2)

def get_pending():
    """Get all pending deadletter items."""
    items = load_deadletter()
    return [i for i in items if i["status"] == "pending"]

def resolve_item(item_id, resolution):
    """
    Mark a deadletter item as resolved.
    
    resolution: "replayed" (successfully retried), "abandoned" (giving up), "duplicate" (ignored)
    """
    items = load_deadletter()
    for item in items:
        if item["id"] == item_id:
            item["status"] = "resolved"
            item["resolution"] = resolution
            item["resolved_at"] = datetime.now().isoformat()
            break
    save_deadletter(items)

def retry_item(item_id):
    """Mark item for retry (decrement retry count, set status to pending_retry)."""
    items = load_deadletter()
    for item in items:
        if item["id"] == item_id:
            if item["retry_count"] >= item["max_retries"]:
                return {"error": "max_retries_exceeded", "item": item}
            item["retry_count"] += 1
            item["status"] = "pending_retry"
            item["last_attempt"] = datetime.now().isoformat()
            break
    save_deadletter(items)
    return {"item": item, "retry_count": item["retry_count"]}

def get_stats():
    """Get deadletter statistics."""
    items = load_deadletter()
    pending = len([i for i in items if i["status"] == "pending"])
    resolved = len([i for i in items if i["status"] == "resolved"])
    by_type = {}
    for item in items:
        t = item["task_type"]
        by_type[t] = by_type.get(t, 0) + 1
    
    return {
        "total": len(items),
        "pending": pending,
        "resolved": resolved,
        "by_type": by_type
    }

def has_deadletter():
    """Check if there are pending deadletter items."""
    return len(get_pending()) > 0

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: deadletter.py <command> [args]")
        print("Commands: add, pending, resolve, retry, stats")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "add" and len(sys.argv) >= 4:
        task_type = sys.argv[2]
        task_data = json.loads(sys.argv[3])
        reason = sys.argv[4] if len(sys.argv) > 4 else "unknown"
        item = add_item(task_type, task_data, reason)
        print(f"Added to deadletter: {item['id']}")
        print(json.dumps(item, indent=2))
    
    elif cmd == "pending":
        items = get_pending()
        print(f"Pending deadletter items: {len(items)}")
        for item in items:
            print(f"  [{item['id']}] {item['task_type']} - {item['failure_reason'][:50]}")
    
    elif cmd == "resolve" and len(sys.argv) >= 3:
        resolve_item(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "abandoned")
        print(f"Resolved: {sys.argv[2]}")
    
    elif cmd == "retry" and len(sys.argv) >= 3:
        result = retry_item(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    elif cmd == "stats":
        print(json.dumps(get_stats(), indent=2))
    
    elif cmd == "test":
        # Test adding an item
        item = add_item("send_tx", {"recipient": "0xABC", "value": 100}, "network_timeout", 3, 3)
        print(f"Test item: {item['id']}")
        print(f"Has deadletter: {has_deadletter()}")
    
    else:
        print("Invalid command")