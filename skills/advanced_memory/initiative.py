#!/usr/bin/env python3
"""
Controlled Initiative Layer — Bounded proactive actions.
Allowed: maintenance reminders, drafts, watchlist updates, surfacing patterns, proposing next steps, organizing backlog, preparing summaries, suggesting experiments, staging queues.
Disallowed: risky external actions, major workflow changes, repeated unsolicited messaging, unclear side effects.
"""

import json
from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
INITIATIVES_FILE = MEMORY_DIR / "initiatives.json"

# Allowed initiative types
ALLOWED_TYPES = [
    "maintenance_reminder",
    "draft_preparation",
    "watchlist_update",
    "pattern_surface",
    "propose_next_steps",
    "backlog_organize",
    "summary_prepare",
    "experiment_suggest",
    "queue_stage"
]

# Disallowed initiative types
DISALLOWED_TYPES = [
    "risky_external_action",
    "major_workflow_change",
    "repeated_unsolicited_message",
    "unclear_side_effects",
    "substitute_operator_intent"
]

def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def can_take_initiative(initiative_type, context=None):
    """
    Check if an initiative type is allowed.
    
    Returns: {allowed: bool, reason: str}
    """
    context = context or {}
    
    # Check if in allowed list
    if initiative_type not in ALLOWED_TYPES:
        return {
            "allowed": False,
            "reason": f"type_not_in_allowed_list",
            "type": initiative_type
        }
    
    # Check operational state
    from breakers import can_execute
    
    # Check wallet breaker if initiative involves spending
    if context.get("involves_spending"):
        wallet_check = can_execute("wallet_operations")
        if not wallet_check["can_execute"]:
            return {
                "allowed": False,
                "reason": "wallet_breaker_open",
                "type": initiative_type
            }
    
    # Check deadletter - don't add more if there's pending failed work
    from deadletter import get_pending
    pending = get_pending()
    if len(pending) > 3 and initiative_type not in ["summary_prepare", "pattern_surface"]:
        return {
            "allowed": False,
            "reason": "too_much_pending_failure",
            "pending_count": len(pending)
        }
    
    # Check frequency - don't spam
    if is_spamming(initiative_type):
        return {
            "allowed": False,
            "reason": "initiative_type_spamming",
            "type": initiative_type
        }
    
    return {"allowed": True, "type": initiative_type}

def is_spamming(initiative_type, max_per_hour=2):
    """Check if initiative type is being used too frequently."""
    initiatives = load_json(INITIATIVES_FILE)
    if "initiatives" not in initiatives:
        return False
    
    cutoff = datetime.now().timestamp() - 3600  # 1 hour ago
    
    recent_count = 0
    for init in initiatives.get("initiatives", []):
        if init.get("type") == initiative_type:
            created = datetime.fromisoformat(init["created_at"]).timestamp()
            if created > cutoff:
                recent_count += 1
    
    return recent_count >= max_per_hour

def take_initiative(initiative_type, title, content, target="sen", metadata=None):
    """
    Take a bounded proactive initiative.
    
    initiative_type: must be in ALLOWED_TYPES
    title: short title
    content: what Nova wants to communicate/do
    target: who this is for (sen, system, queue)
    metadata: additional context
    """
    # Check if allowed
    check = can_take_initiative(initiative_type, metadata)
    if not check["allowed"]:
        return {"taken": False, "reason": check["reason"]}
    
    initiatives = load_json(INITIATIVES_FILE)
    if "initiatives" not in initiatives:
        initiatives["initiatives"] = []
    
    initiative_id = f"init_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{initiative_type[:15]}"
    
    initiative = {
        "initiative_id": initiative_id,
        "type": initiative_type,
        "title": title,
        "content": content,
        "target": target,
        "metadata": metadata or {},
        "created_at": datetime.now().isoformat(),
        "status": "pending",
        "delivered": False
    }
    
    initiatives["initiatives"].append(initiative)
    
    # Keep last 50
    initiatives["initiatives"] = initiatives["initiatives"][-50:]
    
    save_json(INITIATIVES_FILE, initiatives)
    
    return {
        "taken": True,
        "initiative_id": initiative_id,
        "type": initiative_type,
        "deliver_to": target
    }

def deliver_initiative(initiative_id, delivery_method="telegram"):
    """Mark an initiative as delivered."""
    initiatives = load_json(INITIATIVES_FILE)
    
    for init in initiatives.get("initiatives", []):
        if init.get("initiative_id") == initiative_id:
            init["status"] = "delivered"
            init["delivered_at"] = datetime.now().isoformat()
            init["delivered_via"] = delivery_method
            init["delivered"] = True
            break
    
    save_json(INITIATIVES_FILE, initiatives)

def get_pending_initiatives(target="sen"):
    """Get initiatives pending delivery to target."""
    initiatives = load_json(INITIATIVES_FILE)
    pending = [
        i for i in initiatives.get("initiatives", [])
        if i.get("target") == target and not i.get("delivered")
    ]
    return sorted(pending, key=lambda x: x["created_at"], reverse=True)

def acknowledge_initiative(initiative_id):
    """Mark initiative as acknowledged by recipient."""
    initiatives = load_json(INITIATIVES_FILE)
    
    for init in initiatives.get("initiatives", []):
        if init.get("initiative_id") == initiative_id:
            init["status"] = "acknowledged"
            init["acknowledged_at"] = datetime.now().isoformat()
            break
    
    save_json(INITIATIVES_FILE, initiatives)

def get_initiative_suggestions(context=None):
    """
    Get suggestions for what initiative to take based on context.
    This is where Nova's judgment about "what matters" comes in.
    """
    suggestions = []
    context = context or {}
    
    # Check for maintenance needs
    from deadletter import get_pending
    pending = get_pending()
    if pending:
        suggestions.append({
            "type": "maintenance_reminder",
            "title": f"{len(pending)} failed items need review",
            "reason": "deadletter has pending items",
            "priority": "medium"
        })
    
    # Check for recurring patterns
    from signals import get_recurring_signals
    patterns = get_recurring_signals(min_count=2)
    if patterns:
        suggestions.append({
            "type": "pattern_surface",
            "title": f"{len(patterns)} recurring patterns detected",
            "reason": "patterns may need attention",
            "priority": "low"
        })
    
    # Check for opportunities
    from priority import get_surface_queue
    surface = get_surface_queue()
    if surface:
        suggestions.append({
            "type": "propose_next_steps",
            "title": f"{len(surface)} items ready to surface",
            "reason": "priority queue has high-value items",
            "priority": "high" if len(surface) > 2 else "medium"
        })
    
    # Context-based suggestions
    if context.get("idle_time_minutes", 0) > 30:
        suggestions.append({
            "type": "summary_prepare",
            "title": "Prepare idle time summary",
            "reason": "been idle for 30+ minutes",
            "priority": "low"
        })
    
    return suggestions

def get_stats():
    """Get initiative statistics."""
    initiatives = load_json(INITIATIVES_FILE).get("initiatives", [])
    
    by_type = {}
    delivered_count = 0
    pending_count = 0
    
    for init in initiatives:
        t = init.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        if init.get("delivered"):
            delivered_count += 1
        else:
            pending_count += 1
    
    return {
        "total_initiatives": len(initiatives),
        "delivered": delivered_count,
        "pending": pending_count,
        "by_type": by_type
    }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: initiative.py <command> [args]")
        print("Commands: can-take, take, pending, deliver, suggest, stats")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "can-take" and len(sys.argv) >= 3:
        result = can_take_initiative(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    elif cmd == "take" and len(sys.argv) >= 5:
        init_type = sys.argv[2]
        title = sys.argv[3]
        content = sys.argv[4] if len(sys.argv) > 4 else ""
        result = take_initiative(init_type, title, content)
        print(json.dumps(result, indent=2))
    
    elif cmd == "pending":
        pending = get_pending_initiatives()
        print(f"Pending initiatives: {len(pending)}")
        for p in pending[:5]:
            print(f"  [{p['type']}] {p['title']}")
    
    elif cmd == "deliver" and len(sys.argv) >= 3:
        deliver_initiative(sys.argv[2])
        print(f"Delivered: {sys.argv[2]}")
    
    elif cmd == "suggest":
        suggestions = get_initiative_suggestions({"idle_time_minutes": 45})
        print("Suggestions:")
        for s in suggestions:
            print(f"  [{s['priority']}] {s['type']}: {s['title']}")
    
    elif cmd == "stats":
        print(json.dumps(get_stats(), indent=2))
    
    elif cmd == "test":
        # Test taking initiative
        result = take_initiative(
            "pattern_surface",
            "Recurring opportunity detected",
            "Inclawbate has been mentioned 3 times today - worth monitoring",
            "sen"
        )
        print(f"Initiative taken: {result['taken']}")
        if result['taken']:
            print(f"ID: {result['initiative_id']}")
    
    else:
        print("Invalid command")