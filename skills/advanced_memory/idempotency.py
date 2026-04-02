#!/usr/bin/env python3
"""
Idempotency Layer — Prevent duplicate operations, enable rollback.
Part of the Decision Intelligence Runtime pattern.
"""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
IDEMPOTENCY_DIR = MEMORY_DIR / "idempotency_keys"
OPERATIONS_DIR = MEMORY_DIR / "operations"

IDEMPOTENCY_DIR.mkdir(parents=True, exist_ok=True)
OPERATIONS_DIR.mkdir(parents=True, exist_ok=True)

def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def compute_idempotency_key(dfid, step_id, params):
    """
    Compute idempotency key from decision flow, step, and params.
    Excludes context/state to allow retries even when world changes.
    """
    # Sort params for canonical representation
    canonical = json.dumps(params, sort_keys=True)
    key_input = f"{dfid}:{step_id}:{canonical}"
    return hashlib.sha256(key_input.encode()).hexdigest()[:16]

def create_operation(dfid, step_id, operation_type, params, intent):
    """
    Create a new operation with idempotency key.
    Returns operation dict with key and status.
    """
    idempotency_key = compute_idempotency_key(dfid, step_id, params)
    
    operation = {
        "operation_id": f"op_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{idempotency_key}",
        "idempotency_key": idempotency_key,
        "dfid": dfid,
        "step_id": step_id,
        "operation_type": operation_type,
        "params": params,
        "intent": intent,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "attempts": 0,
        "last_attempt": None,
        "result": None,
        "error": None
    }
    
    # Check for duplicate
    if is_duplicate(idempotency_key):
        existing = get_operation_by_key(idempotency_key)
        return {
            "duplicate": True,
            "existing_operation": existing,
            "should_proceed": existing["status"] in ["failed", "completed"]
        }
    
    # Save operation
    save_json(OPERATIONS_DIR / f"{operation['operation_id']}.json", operation)
    
    # Track idempotency key
    track_key(idempotency_key, operation["operation_id"])
    
    return {
        "duplicate": False,
        "operation": operation,
        "should_proceed": True
    }

def is_duplicate(idempotency_key):
    """Check if an idempotency key has been used."""
    key_file = IDEMPOTENCY_DIR / f"{idempotency_key}.json"
    return key_file.exists()

def get_operation_by_key(idempotency_key):
    """Get operation by idempotency key."""
    key_file = IDEMPOTENCY_DIR / f"{idempotency_key}.json"
    if key_file.exists():
        key_data = load_json(key_file)
        op_file = OPERATIONS_DIR / f"{key_data['operation_id']}.json"
        if op_file.exists():
            return load_json(op_file)
    return None

def track_key(idempotency_key, operation_id):
    """Track an idempotency key."""
    save_json(IDEMPOTENCY_DIR / f"{idempotency_key}.json", {
        "idempotency_key": idempotency_key,
        "operation_id": operation_id,
        "created_at": datetime.now().isoformat()
    })

def record_attempt(operation_id, success=True, result=None, error=None):
    """Record an attempt at an operation."""
    op_file = OPERATIONS_DIR / f"{operation_id}.json"
    if not op_file.exists():
        return None
    
    operation = load_json(op_file)
    operation["attempts"] += 1
    operation["last_attempt"] = datetime.now().isoformat()
    
    if success:
        operation["status"] = "completed"
        operation["result"] = result
    else:
        operation["status"] = "failed"
        operation["error"] = error
    
    save_json(op_file, operation)
    return operation

def compensate_operation(operation_id):
    """
    Mark operation for compensation/rollback.
    In production, this would trigger compensating transactions.
    """
    op_file = OPERATIONS_DIR / f"{operation_id}.json"
    if not op_file.exists():
        return None
    
    operation = load_json(op_file)
    operation["status"] = "compensating"
    operation["compensate_at"] = datetime.now().isoformat()
    save_json(op_file, operation)
    
    return operation

def get_active_operations():
    """Get all pending/in-progress operations."""
    operations = []
    for f in OPERATIONS_DIR.glob("op_*.json"):
        op = load_json(f)
        if op["status"] in ["pending", "in_progress", "compensating"]:
            operations.append(op)
    return operations

def cleanup_old_operations(max_age_hours=24):
    """Remove completed/failed operations older than max_age_hours."""
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    removed = 0
    
    for f in OPERATIONS_DIR.glob("op_*.json"):
        op = load_json(f)
        last_attempt = op.get("last_attempt") or op.get("created_at")
        if datetime.fromisoformat(last_attempt) < cutoff and op["status"] in ["completed", "failed"]:
            # Also remove idempotency key
            key_file = IDEMPOTENCY_DIR / f"{op['idempotency_key']}.json"
            if key_file.exists():
                key_file.unlink()
            f.unlink()
            removed += 1
    
    return removed

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: idempotency.py <command> [args]")
        print("Commands: create, record, compensate, active, cleanup")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "create" and len(sys.argv) >= 5:
        dfid = sys.argv[2]
        step_id = sys.argv[3]
        op_type = sys.argv[4]
        params = json.loads(sys.argv[5]) if len(sys.argv) > 5 else {}
        result = create_operation(dfid, step_id, op_type, params, "")
        print(json.dumps(result, indent=2))
    
    elif cmd == "record" and len(sys.argv) >= 4:
        op_id = sys.argv[2]
        success = sys.argv[3].lower() == "true"
        result = record_attempt(op_id, success, "ok" if success else "failed")
        print(json.dumps(result, indent=2))
    
    elif cmd == "compensate" and len(sys.argv) >= 3:
        result = compensate_operation(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    elif cmd == "active":
        ops = get_active_operations()
        print(f"Active operations: {len(ops)}")
        for op in ops[:5]:
            print(f"  {op['operation_id']} - {op['operation_type']} ({op['status']})")
    
    elif cmd == "cleanup":
        removed = cleanup_old_operations()
        print(f"Removed {removed} old operations")