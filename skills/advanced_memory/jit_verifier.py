#!/usr/bin/env python3
"""
JIT State Verifier — Snapshot state before decisions, verify before execution.
Part of the Decision Intelligence Runtime pattern.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
SNAPSHOTS_DIR = MEMORY_DIR / "state_snapshots"
CONTRACTS_DIR = MEMORY_DIR / "contracts"

# Ensure directories exist
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)

def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

# Default drift envelopes
DEFAULT_ENVELOPES = {
    "eth_price_pct": 5.0,      # Abort if ETH price moved > 5%
    "gas_price_pct": 20.0,     # Abort if gas price moved > 20%
    "balance_pct": 10.0,       # Abort if balance changed > 10%
    "max_context_age_sec": 60  # Abort if snapshot older than 60s
}

def get_current_state():
    """Get current relevant state for Nova's operations."""
    state = {
        "timestamp": datetime.now().isoformat(),
        "eth_balance": get_eth_balance(),
        "gas_price": get_gas_price(),
        "eth_price": get_eth_price_usd()
    }
    return state

def get_eth_balance():
    """Get Nova's ETH balance via RPC."""
    import subprocess
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", "https://mainnet.infura.io/v3/",
             "-H", "Content-Type: application/json",
             "-d", '{"jsonrpc":"eth_getBalance","params":["0xB743fdbA842379933A3774617786712458659D16","latest"],"id":1}'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            wei = int(data.get("result", "0x0"), 16)
            return wei / 1e18
    except:
        pass
    return None

def get_gas_price():
    """Get current gas price."""
    import subprocess
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", "https://mainnet.infura.io/v3/",
             "-H", "Content-Type: application/json",
             "-d", '{"jsonrpc":"eth_gasPrice","params":[],"id":1}'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            gwei = int(data.get("result", "0x0"), 16) / 1e9
            return gwei
    except:
        pass
    return None

def get_eth_price_usd():
    """Get ETH/USD price (simplified - would use an oracle in production)."""
    # In production: call a price oracle. For now, return None (skip price check)
    return None

def create_snapshot(operation_type, operation_params=None):
    """Create a state snapshot before an operation."""
    current = get_current_state()
    
    snapshot = {
        "snapshot_id": f"snap_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{operation_type}",
        "operation_type": operation_type,
        "operation_params": operation_params or {},
        "state": current,
        "envelopes": DEFAULT_ENVELOPES.copy(),
        "created_at": datetime.now().isoformat()
    }
    
    # Save snapshot
    save_json(SNAPSHOTS_DIR / f"{snapshot['snapshot_id']}.json", snapshot)
    
    return snapshot

def compute_drift(original_state, current_state, envelopes):
    """Compute drift between snapshot and current state."""
    drift_report = {}
    checks_passed = True
    
    # ETH balance drift
    if original_state.get("eth_balance") and current_state.get("eth_balance"):
        balance_drift = abs(current_state["eth_balance"] - original_state["eth_balance"]) / original_state["eth_balance"] * 100
        drift_report["balance_drift_pct"] = balance_drift
        if balance_drift > envelopes.get("balance_pct", 10):
            checks_passed = False
    
    # Gas price drift
    if original_state.get("gas_price") and current_state.get("gas_price"):
        gas_drift = abs(current_state["gas_price"] - original_state["gas_price"]) / original_state["gas_price"] * 100
        drift_report["gas_drift_pct"] = gas_drift
        if gas_drift > envelopes.get("gas_price_pct", 20):
            checks_passed = False
    
    # ETH price drift (if available)
    if original_state.get("eth_price") and current_state.get("eth_price"):
        price_drift = abs(current_state["eth_price"] - original_state["eth_price"]) / original_state["eth_price"] * 100
        drift_report["price_drift_pct"] = price_drift
        if price_drift > envelopes.get("eth_price_pct", 5):
            checks_passed = False
    
    # Context age check
    orig_time = datetime.fromisoformat(original_state["timestamp"])
    age_sec = (datetime.now() - orig_time).total_seconds()
    drift_report["context_age_sec"] = age_sec
    if age_sec > envelopes.get("max_context_age_sec", 60):
        checks_passed = False
    
    return drift_report, checks_passed

def verify_pre_execution(snapshot_id):
    """Verify state hasn't drifted beyond envelope before execution."""
    snapshot_file = SNAPSHOTS_DIR / f"{snapshot_id}.json"
    
    if not snapshot_file.exists():
        return {"valid": False, "reason": "snapshot_not_found"}
    
    snapshot = load_json(snapshot_file)
    original = snapshot["state"]
    envelopes = snapshot.get("envelopes", DEFAULT_ENVELOPES)
    
    current = get_current_state()
    drift_report, checks_passed = compute_drift(original, current, envelopes)
    
    result = {
        "snapshot_id": snapshot_id,
        "operation_type": snapshot["operation_type"],
        "passed": checks_passed,
        "drift_report": drift_report,
        "current_state": current,
        "verified_at": datetime.now().isoformat()
    }
    
    if not checks_passed:
        result["action"] = "ABORT"
        result["reason"] = "drift_exceeded_envelope"
    else:
        result["action"] = "PROCEED"
    
    return result

def create_and_verify(operation_type, operation_params=None):
    """Create snapshot and immediately verify (for testing)."""
    snapshot = create_snapshot(operation_type, operation_params)
    result = verify_pre_execution(snapshot["snapshot_id"])
    return {
        "snapshot": snapshot,
        "verification": result
    }

def get_snapshot_history(limit=10):
    """Get recent snapshots."""
    snapshots = []
    for f in sorted(SNAPSHOTS_DIR.glob("snap_*.json"), reverse=True)[:limit]:
        snapshots.append(load_json(f))
    return snapshots

def cleanup_old_snapshots(max_age_hours=24):
    """Remove snapshots older than max_age_hours."""
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    removed = 0
    
    for f in SNAPSHOTS_DIR.glob("snap_*.json"):
        snapshot = load_json(f)
        created = datetime.fromisoformat(snapshot["created_at"])
        if created < cutoff:
            f.unlink()
            removed += 1
    
    return removed

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: jit_verifier.py <command> [args]")
        print("Commands: snapshot <operation_type>, verify <snapshot_id>, test, history, cleanup")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "snapshot" and len(sys.argv) >= 3:
        op_type = sys.argv[2]
        params = sys.argv[3:] if len(sys.argv) > 3 else None
        snap = create_snapshot(op_type, params)
        print(f"Snapshot created: {snap['snapshot_id']}")
        print(json.dumps(snap["state"], indent=2))
    
    elif cmd == "verify" and len(sys.argv) >= 3:
        result = verify_pre_execution(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    elif cmd == "test":
        # Create and immediately verify
        result = create_and_verify("test_operation", {"test": True})
        print(json.dumps(result, indent=2))
    
    elif cmd == "history":
        history = get_snapshot_history()
        print(f"Recent snapshots: {len(history)}")
        for s in history[:5]:
            print(f"  {s['snapshot_id']} - {s['operation_type']} at {s['created_at']}")
    
    elif cmd == "cleanup":
        removed = cleanup_old_snapshots()
        print(f"Removed {removed} old snapshots")
    
    else:
        print("Invalid command")