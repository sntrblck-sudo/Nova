#!/usr/bin/env python3
"""
Nova's Autonomous Goal Formation (AGF) — v1
Forms goals, tracks execution, stays transparent.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

GOALS_FILE = Path("/home/sntrblck/.openclaw/workspace/memory/goals.json")
ACTIVE_FILE = Path("/home/sntrblck/.openclaw/workspace/memory/active_goals.json")
MAX_ACTIVE_GOALS = 2

def load_goals():
    if GOALS_FILE.exists():
        with open(GOALS_FILE) as f:
            return json.load(f)
    return []

def save_goals(goals):
    with open(GOALS_FILE, 'w') as f:
        json.dump(goals, f, indent=2)

def load_active():
    if ACTIVE_FILE.exists():
        with open(ACTIVE_FILE) as f:
            return json.load(f)
    return []

def save_active(active):
    with open(ACTIVE_FILE, 'w') as f:
        json.dump(active, f, indent=2)

def count_active():
    return len(load_active())

def has_room():
    return count_active() < MAX_ACTIVE_GOALS

def form_goal(goal_text, why, category, plan, cost_estimate="low", requires_approval=False):
    """Form a new goal. Returns goal dict or None if no room."""
    
    if not has_room():
        print(f"No room for new goal (max {MAX_ACTIVE_GOALS} active)")
        return None
    
    goal = {
        "goal_id": f"goal_{uuid.uuid4().hex[:8]}",
        "created": datetime.now().isoformat(),
        "goal": goal_text,
        "why": why,
        "category": category,  # earning, growing, improving, observing
        "confidence": 0.5,
        "plan": plan,
        "cost_estimate": cost_estimate,
        "requires_approval": requires_approval,
        "status": "proposed",
        "notes": ""
    }
    
    goals = load_goals()
    goals.append(goal)
    save_goals(goals)
    
    # If doesn't need approval, make it active
    if not requires_approval:
        active = load_active()
        active.append(goal["goal_id"])
        save_active(active)
        goal["status"] = "running"
        goals = load_goals()
        for g in goals:
            if g["goal_id"] == goal["goal_id"]:
                g["status"] = "running"
        save_goals(goals)
    
    return goal

def update_goal(goal_id, status, notes=""):
    """Update goal status."""
    goals = load_goals()
    for g in goals:
        if g["goal_id"] == goal_id:
            g["status"] = status
            if notes:
                g["notes"] = notes
            break
    save_goals(goals)
    
    if status in ["achieved", "failed", "blocked"]:
        active = load_active()
        active = [a for a in active if a != goal_id]
        save_active(active)

def get_goal(goal_id):
    goals = load_goals()
    for g in goals:
        if g["goal_id"] == goal_id:
            return g
    return None

def get_active():
    """Get all active goals with full data."""
    active_ids = load_active()
    goals = load_goals()
    return [g for g in goals if g["goal_id"] in active_ids]

def list_goals(status=None, category=None, limit=10):
    goals = load_goals()
    if status:
        goals = [g for g in goals if g["status"] == status]
    if category:
        goals = [g for g in goals if g["category"] == category]
    return sorted(goals, key=lambda x: x["created"], reverse=True)[:limit]

def needs_approval():
    """Return goals pending approval."""
    goals = load_goals()
    return [g for g in goals if g["status"] == "proposed" and g.get("requires_approval")]

def approve(goal_id):
    """Approve a proposed goal."""
    goal = get_goal(goal_id)
    if not goal:
        return False
    if goal["status"] != "proposed":
        return False
    
    active = load_active()
    if len(active) >= MAX_ACTIVE_GOALS:
        return False  # No room
    
    active.append(goal_id)
    save_active(active)
    
    goals = load_goals()
    for g in goals:
        if g["goal_id"] == goal_id:
            g["status"] = "running"
    save_goals(goals)
    return True

def archive_goal(goal_id, reason=""):
    """Archive/discard a goal."""
    update_goal(goal_id, "blocked", reason)

def goal_summary():
    """Get summary of goal state."""
    goals = load_goals()
    active = load_active()
    
    stats = {
        "total": len(goals),
        "active": len(active),
        "achieved": len([g for g in goals if g["status"] == "achieved"]),
        "failed": len([g for g in goals if g["status"] == "failed"]),
        "pending_approval": len(needs_approval()),
        "categories": {}
    }
    
    for g in goals:
        cat = g.get("category", "unknown")
        if cat not in stats["categories"]:
            stats["categories"][cat] = 0
        stats["categories"][cat] += 1
    
    return stats

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: goals.py <command> [args]")
        print("Commands: form, list, active, pending, approve, archive, summary")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "form" and len(sys.argv) >= 3:
        goal_text = sys.argv[2]
        why = sys.argv[3] if len(sys.argv) > 3 else ""
        plan = sys.argv[4].split(",") if len(sys.argv) > 4 else []
        category = sys.argv[5] if len(sys.argv) > 5 else "growing"
        requires_approval = "--need-approval" in sys.argv
        
        goal = form_goal(goal_text, why, category, plan, requires_approval=requires_approval)
        if goal:
            print(f"Goal formed: {goal['goal_id']} ({goal['status']})")
        else:
            print("Failed to form goal")
    
    elif cmd == "list":
        goals = list_goals()
        for g in goals:
            print(f"[{g['goal_id']}] {g['goal']} ({g['status']})")
    
    elif cmd == "active":
        active = get_active()
        for g in active:
            print(f"[{g['goal_id']}] {g['goal']}")
    
    elif cmd == "pending":
        pending = needs_approval()
        for g in pending:
            print(f"[{g['goal_id']}] {g['goal']} - requires approval")
    
    elif cmd == "approve" and len(sys.argv) >= 3:
        if approve(sys.argv[2]):
            print("Goal approved and activated")
        else:
            print("Failed to approve goal")
    
    elif cmd == "archive" and len(sys.argv) >= 3:
        reason = sys.argv[3] if len(sys.argv) > 3 else ""
        archive_goal(sys.argv[2], reason)
        print("Goal archived")
    
    elif cmd == "summary":
        print(json.dumps(goal_summary(), indent=2))
    
    else:
        print("Invalid command or missing args")