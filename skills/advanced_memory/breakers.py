#!/usr/bin/env python3
"""
Circuit Breakers — Subsystem failure isolation.
States: closed (normal) → open (failing) → half-open (testing)
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
BREAKERS_DIR = MEMORY_DIR / "breakers"
BREAKERS_DIR.mkdir(parents=True, exist_ok=True)

STATES = ["closed", "open", "half_open"]

DEFAULT_BREAKERS = {
    "wallet_operations": {
        "state": "closed",
        "failure_threshold": 3,
        "failure_window_hours": 1,
        "cooldown_hours": 0.5,
        "failure_count": 0,
        "last_failure": None,
        "last_state_change": None
    },
    "external_api": {
        "state": "closed", 
        "failure_threshold": 5,
        "failure_window_hours": 0.5,
        "cooldown_hours": 0.25,
        "failure_count": 0,
        "last_failure": None,
        "last_state_change": None
    },
    "memory_system": {
        "state": "closed",
        "failure_threshold": 3,
        "failure_window_hours": 1,
        "cooldown_hours": 1,
        "failure_count": 0,
        "last_failure": None,
        "last_state_change": None
    }
}

def load_breaker(name):
    """Load breaker state or initialize default."""
    breaker_file = BREAKERS_DIR / f"{name}.json"
    if breaker_file.exists():
        with open(breaker_file) as f:
            return json.load(f)
    
    if name in DEFAULT_BREAKERS:
        return DEFAULT_BREAKERS[name].copy()
    
    return None

def save_breaker(name, state):
    """Save breaker state."""
    breaker_file = BREAKERS_DIR / f"{name}.json"
    state["last_updated"] = datetime.now().isoformat()
    with open(breaker_file, 'w') as f:
        json.dump(state, f, indent=2)

def record_failure(breaker_name):
    """Record a failure and potentially open the breaker."""
    breaker = load_breaker(breaker_name)
    if not breaker:
        return {"error": "breaker_not_found"}
    
    now = datetime.now()
    
    # Check cooldown - if recently changed state, ignore
    if breaker.get("last_state_change"):
        last_change = datetime.fromisoformat(breaker["last_state_change"])
        cooldown_hours = breaker.get("cooldown_hours", 0.5)
        if (now - last_change).total_seconds() < cooldown_hours * 3600:
            return {"ignored": True, "reason": "cooldown_active"}
    
    # Check failure window - count recent failures
    failure_window_hours = breaker.get("failure_window_hours", 1)
    cutoff = now - timedelta(hours=failure_window_hours)
    
    if breaker.get("last_failure"):
        last_failure = datetime.fromisoformat(breaker["last_failure"])
        if last_failure < cutoff:
            # Outside window, reset counter
            breaker["failure_count"] = 0
    
    # Increment failure count
    breaker["failure_count"] += 1
    breaker["last_failure"] = now.isoformat()
    
    # Check threshold
    if breaker["failure_count"] >= breaker["failure_threshold"]:
        # Open the breaker
        breaker["state"] = "open"
        breaker["last_state_change"] = now.isoformat()
        breaker["failure_count"] = 0  # Reset after opening
    
    save_breaker(breaker_name, breaker)
    
    return {
        "name": breaker_name,
        "state": breaker["state"],
        "failure_count": breaker["failure_count"],
        "opened": breaker["state"] == "open"
    }

def record_success(breaker_name):
    """Record a success — close breaker if half-open, reset failure count."""
    breaker = load_breaker(breaker_name)
    if not breaker:
        return {"error": "breaker_not_found"}
    
    now = datetime.now()
    
    if breaker["state"] == "half_open":
        # Success in half-open → close
        breaker["state"] = "closed"
        breaker["last_state_change"] = now.isoformat()
        breaker["failure_count"] = 0
        save_breaker(breaker_name, breaker)
        return {"name": breaker_name, "state": "closed", "transitioned": True}
    
    # Reset failure count on success
    breaker["failure_count"] = 0
    save_breaker(breaker_name, breaker)
    
    return {"name": breaker_name, "state": breaker["state"], "failure_count": 0}

def probe(breaker_name):
    """Test if a subsystem has recovered (half-open → closed or open)."""
    breaker = load_breaker(breaker_name)
    if not breaker:
        return {"error": "breaker_not_found"}
    
    if breaker["state"] != "half_open":
        return {"name": breaker_name, "state": breaker["state"], "action": "none"}
    
    # Placeholder - actual probe would test the subsystem
    # For now, just return that it's ready to be probed
    return {
        "name": breaker_name,
        "state": "half_open",
        "action": "ready_to_probe"
    }

def transition_to_half_open(breaker_name):
    """Manually transition a breaker to half-open (for testing)."""
    breaker = load_breaker(breaker_name)
    if not breaker:
        return {"error": "breaker_not_found"}
    
    if breaker["state"] != "open":
        return {"error": "must_be_open"}
    
    breaker["state"] = "half_open"
    breaker["last_state_change"] = datetime.now().isoformat()
    save_breaker(breaker_name, breaker)
    
    return {"name": breaker_name, "state": "half_open", "transitioned": True}

def can_execute(breaker_name):
    """Check if an operation can proceed on this subsystem."""
    breaker = load_breaker(breaker_name)
    if not breaker:
        return {"can_execute": True}  # No breaker = assume ok
    
    state = breaker["state"]
    
    if state == "closed":
        return {"can_execute": True, "state": "closed"}
    elif state == "half_open":
        return {"can_execute": True, "state": "half_open", "warning": "testing_mode"}
    else:  # open
        return {"can_execute": False, "state": "open", "reason": "subsystem_failing"}

def get_all_breakers():
    """Get status of all breakers."""
    breakers = {}
    for f in BREAKERS_DIR.glob("*.json"):
        with open(f) as fp:
            b = json.load(fp)
            breakers[f.stem] = b
    return breakers

def initialize_defaults():
    """Initialize default breakers."""
    for name, state in DEFAULT_BREAKERS.items():
        if not (BREAKERS_DIR / f"{name}.json").exists():
            save_breaker(name, state.copy())
            print(f"Initialized breaker: {name}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: breakers.py <command> [args]")
        print("Commands: status, record-failure, record-success, can-execute, probe, init")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "status":
        breakers = get_all_breakers()
        print("Breakers:")
        for name, state in breakers.items():
            print(f"  {name}: {state['state']} (failures: {state['failure_count']})")
    
    elif cmd == "record-failure" and len(sys.argv) >= 3:
        result = record_failure(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    elif cmd == "record-success" and len(sys.argv) >= 3:
        result = record_success(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    elif cmd == "can-execute" and len(sys.argv) >= 3:
        result = can_execute(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    elif cmd == "probe" and len(sys.argv) >= 3:
        result = probe(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    elif cmd == "init":
        initialize_defaults()
    
    else:
        print("Invalid command")