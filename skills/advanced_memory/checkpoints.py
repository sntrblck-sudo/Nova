#!/usr/bin/env python3
"""
Checkpoint System — State snapshots at decision points for recovery.
Snapshots capture what you're about to do, allowing restore on failure.
"""

import json
from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
CHECKPOINTS_DIR = MEMORY_DIR / "checkpoints"
ACTIVE_DIR = CHECKPOINTS_DIR / "active"
ARCHIVED_DIR = CHECKPOINTS_DIR / "archived"

ACTIVE_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVED_DIR.mkdir(parents=True, exist_ok=True)

def create_checkpoint(operation_type, phase, next_step, context=None, metadata=None):
    """
    Create a checkpoint before a multi-step operation.
    
    operation_type: e.g., "send_tx", "skill_deployment", "research"
    phase: "starting", "in_progress", "paused", "checkpointing"
    next_step: what comes next
    context: current state snapshot (task params, relevant files, etc.)
    metadata: anything else worth preserving
    """
    checkpoint_id = f"cp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{operation_type}"
    
    checkpoint = {
        "checkpoint_id": checkpoint_id,
        "operation_type": operation_type,
        "phase": phase,
        "next_step": next_step,
        "context": context or {},
        "metadata": metadata or {},
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "status": "active",
        "retry_count": 0
    }
    
    # Archive any existing active checkpoint for this operation type
    archive_existing(operation_type)
    
    # Save new checkpoint
    save_checkpoint(checkpoint)
    
    return checkpoint

def save_checkpoint(checkpoint):
    """Save checkpoint to active directory."""
    with open(ACTIVE_DIR / f"{checkpoint['checkpoint_id']}.json", 'w') as f:
        json.dump(checkpoint, f, indent=2)

def load_checkpoint(checkpoint_id):
    """Load a checkpoint by ID."""
    # Check active first
    cp_file = ACTIVE_DIR / f"{checkpoint_id}.json"
    if cp_file.exists():
        with open(cp_file) as f:
            return json.load(f)
    
    # Check archived
    cp_file = ARCHIVED_DIR / f"{checkpoint_id}.json"
    if cp_file.exists():
        with open(cp_file) as f:
            return json.load(f)
    
    return None

def update_checkpoint(checkpoint_id, phase=None, next_step=None, context_update=None):
    """Update an active checkpoint."""
    checkpoint = load_checkpoint(checkpoint_id)
    if not checkpoint:
        return {"error": "checkpoint_not_found"}
    
    if checkpoint.get("status") != "active":
        return {"error": "checkpoint_not_active"}
    
    if phase:
        checkpoint["phase"] = phase
    if next_step:
        checkpoint["next_step"] = next_step
    if context_update:
        checkpoint["context"].update(context_update)
    
    checkpoint["updated_at"] = datetime.now().isoformat()
    save_checkpoint(checkpoint)
    
    return checkpoint

def archive_checkpoint(checkpoint_id, reason="completed"):
    """Archive a checkpoint (success or giving up)."""
    checkpoint = load_checkpoint(checkpoint_id)
    if not checkpoint:
        return {"error": "checkpoint_not_found"}
    
    checkpoint["status"] = "archived"
    checkpoint["archived_reason"] = reason
    checkpoint["archived_at"] = datetime.now().isoformat()
    
    # Move to archived
    active_file = ACTIVE_DIR / f"{checkpoint_id}.json"
    archived_file = ARCHIVED_DIR / f"{checkpoint_id}.json"
    
    if active_file.exists():
        with open(archived_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        active_file.unlink()
    
    return checkpoint

def archive_existing(operation_type):
    """Archive any existing active checkpoint for this operation type."""
    for f in ACTIVE_DIR.glob(f"*_{operation_type}.json"):
        checkpoint = json.load(open(f))
        archive_checkpoint(checkpoint["checkpoint_id"], "superseded")

def restore_checkpoint(checkpoint_id):
    """
    Restore a checkpoint for retry.
    Returns the checkpoint data so Nova can resume from where she left off.
    """
    checkpoint = load_checkpoint(checkpoint_id)
    if not checkpoint:
        return {"error": "checkpoint_not_found"}
    
    if checkpoint["status"] != "active":
        return {"error": "checkpoint_not_active"}
    
    checkpoint["retry_count"] += 1
    checkpoint["updated_at"] = datetime.now().isoformat()
    save_checkpoint(checkpoint)
    
    return {
        "restored": True,
        "checkpoint": checkpoint,
        "resume_from": checkpoint["next_step"],
        "context": checkpoint["context"]
    }

def get_active():
    """Get all active checkpoints."""
    checkpoints = []
    for f in ACTIVE_DIR.glob("*.json"):
        with open(f) as fp:
            checkpoints.append(json.load(fp))
    return checkpoints

def get_recent_archived(limit=10):
    """Get recently archived checkpoints."""
    checkpoints = []
    for f in sorted(ARCHIVED_DIR.glob("*.json"), reverse=True)[:limit]:
        with open(f) as fp:
            checkpoints.append(json.load(fp))
    return checkpoints

def cleanup_old_archived(max_age_days=7):
    """Remove archived checkpoints older than max_age_days."""
    import time
    cutoff = time.time() - (max_age_days * 86400)
    removed = 0
    
    for f in ARCHIVED_DIR.glob("*.json"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            removed += 1
    
    return removed

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: checkpoints.py <command> [args]")
        print("Commands: create, update, restore, archive, active, recent, cleanup")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "create" and len(sys.argv) >= 5:
        op_type = sys.argv[2]
        phase = sys.argv[3]
        next_step = sys.argv[4]
        cp = create_checkpoint(op_type, phase, next_step)
        print(f"Created: {cp['checkpoint_id']}")
        print(json.dumps(cp, indent=2))
    
    elif cmd == "update" and len(sys.argv) >= 3:
        cp_id = sys.argv[2]
        result = update_checkpoint(cp_id, phase=sys.argv[3] if len(sys.argv) > 3 else None, 
                                   next_step=sys.argv[4] if len(sys.argv) > 4 else None)
        print(json.dumps(result, indent=2))
    
    elif cmd == "restore" and len(sys.argv) >= 3:
        result = restore_checkpoint(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    elif cmd == "archive" and len(sys.argv) >= 3:
        result = archive_checkpoint(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "manual")
        print(f"Archived: {result.get('checkpoint_id', 'error')}")
    
    elif cmd == "active":
        checkpoints = get_active()
        print(f"Active checkpoints: {len(checkpoints)}")
        for cp in checkpoints:
            print(f"  [{cp['checkpoint_id']}] {cp['operation_type']} ({cp['phase']}) - next: {cp['next_step'][:50]}")
    
    elif cmd == "recent":
        checkpoints = get_recent_archived()
        print(f"Recent archived: {len(checkpoints)}")
        for cp in checkpoints[:5]:
            print(f"  [{cp['checkpoint_id']}] {cp['operation_type']} - {cp.get('archived_reason', 'unknown')}")
    
    elif cmd == "cleanup":
        removed = cleanup_old_archived()
        print(f"Removed {removed} old archived checkpoints")
    
    elif cmd == "test":
        # Test flow
        cp = create_checkpoint("send_tx", "starting", "validate contract", {"recipient": "0xABC", "value": 100})
        print(f"Created: {cp['checkpoint_id']}")
        
        result = restore_checkpoint(cp['checkpoint_id'])
        print(f"Restored: {result.get('resume_from')}")
        
        archive_checkpoint(cp['checkpoint_id'], "success")
        print("Archived")
    
    else:
        print("Invalid command")