"""
Nova's Incoming Payment Detector
================================
Detects when Nova receives payments by monitoring balance changes.
"""

import json
import time
import subprocess
from pathlib import Path

STATE_FILE = Path("/home/sntrblck/.openclaw/workspace/memory/nova_balance_state.json")
ECONOMIC_LOG = Path("/home/sntrblck/.openclaw/workspace/memory/earnings_log.jsonl")

NOVA_ADDRESS = "0xB743fdbA842379933A3774617786712458659D16"


def get_balance():
    """Get current balance via viem"""
    result = subprocess.run(
        ["node", "-e", """
import { createPublicClient, http } from 'viem';
import { base } from 'viem/chains';
const pub = createPublicClient({ chain: base, transport: http() });
pub.getBalance({ address: '0xB743fdbA842379933A3774617786712458659D16' }).then(b => console.log((Number(b) / 1e18).toString()));
"""],
        capture_output=True,
        text=True,
        cwd="/home/sntrblck/.openclaw/workspace/cdp-nova"
    )
    return float(result.stdout.strip())


def load_state():
    """Load last known balance state"""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_balance": None, "last_check_timestamp": None}


def save_state(state):
    """Save balance state"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def check_for_incoming():
    """Check for incoming payments since last check."""
    state = load_state()
    current_balance = get_balance()
    last_balance = state.get("last_balance")

    result = {
        "current_balance": current_balance,
        "last_balance": last_balance,
        "change": 0,
        "incoming_eth": 0,
        "detected": False,
    }

    if last_balance is not None:
        change = current_balance - last_balance
        result["change"] = change

        if change > 0.000001:  # More than dust
            result["incoming_eth"] = change
            result["detected"] = True
            log_earning(change, "incoming_transfer")

    # Update state
    state["last_balance"] = current_balance
    state["last_check_timestamp"] = time.time()
    save_state(state)

    return result


def log_earning(amount_eth: float, earn_type: str):
    """Log earning to earnings log"""
    entry = {
        "type": earn_type,
        "amount_eth": amount_eth,
        "from_address": "unknown",
        "description": f"Detected incoming payment: {amount_eth:.6f} ETH",
        "timestamp": time.time(),
        "detected": True,
    }
    
    ECONOMIC_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(ECONOMIC_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Incoming Payment Detector")
        print("Commands: check | balance")
    
    cmd = sys.argv[1]
    
    if cmd == "check":
        result = check_for_incoming()
        print(f"Current balance: {result['current_balance']:.6f} ETH")
        if result['detected']:
            print(f"💰 INCOMING: +{result['incoming_eth']:.6f} ETH detected!")
        else:
            print("No new incoming payments")
    
    elif cmd == "balance":
        print(f"Balance: {get_balance():.6f} ETH")
