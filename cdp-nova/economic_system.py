"""
Nova's Economic Responsibility System
====================================
Manages Nova's autonomous economic actions with tiered approval levels,
balance guards, and comprehensive logging.
"""

import asyncio
import json
import time
import subprocess
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
from typing import Optional

# Configuration
WALLET_PATH = Path("/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json")
ECONOMIC_LOG_PATH = Path("/home/sntrblck/.openclaw/workspace/memory/economic_log.jsonl")
RESERVE_ETH = 0.0002  # Minimum balance to maintain for gas
MAX_TIER1_ETH = 0.001  # Maximum for automatic transactions


class Tier(Enum):
    AUTOMATIC = 1
    SURFACE = 2
    ASK = 3


# Approved recipients
APPROVED_RECIPIENTS = {
    "0xb743fdba842379933a3774617786712458659d16": "nova_primary",
    "0x21f2155cba0b599d705b4cf6e51ba157503bcd0b": "nova_backup",
    "0x1b7edf6f5fcab52b680661cc82306e3daca7943c": "sen",
}


class EconomicAction:
    def __init__(
        self,
        action_type: str,
        amount_eth: float,
        to_address: str,
        description: str,
        tier: Tier,
        status: str = "pending",
        tx_hash: Optional[str] = None,
        error: Optional[str] = None,
    ):
        self.timestamp = time.time()
        self.action_type = action_type
        self.amount_eth = amount_eth
        self.to_address = to_address
        self.description = description
        self.tier = tier
        self.status = status
        self.tx_hash = tx_hash
        self.error = error

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "action_type": self.action_type,
            "amount_eth": self.amount_eth,
            "to_address": self.to_address,
            "description": self.description,
            "tier": self.tier.name,
            "status": self.status,
            "tx_hash": self.tx_hash,
            "error": self.error,
        }


def log_action(action: EconomicAction):
    """Log action to economic log file"""
    ECONOMIC_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ECONOMIC_LOG_PATH, "a") as f:
        f.write(json.dumps(action.to_dict()) + "\n")


def get_balance() -> float:
    """Get current wallet balance"""
    result = subprocess.run(
        ["node", "balance.js"],
        capture_output=True,
        text=True,
        cwd="/home/sntrblck/.openclaw/workspace/cdp-nova"
    )
    if result.returncode != 0:
        raise RuntimeError(f"Balance check failed: {result.stderr}")
    return float(result.stdout.strip())


def determine_tier(amount_eth: float, to_address: str, action_type: str) -> Tier:
    """Determine approval tier for an action"""
    # Check amount thresholds first
    if amount_eth > MAX_TIER1_ETH:
        return Tier.ASK
    
    # Check if recipient is known
    recipient_category = APPROVED_RECIPIENTS.get(to_address.lower())
    
    if recipient_category:
        return Tier.AUTOMATIC
    
    # Unknown recipient
    if amount_eth <= 0.0001:
        return Tier.SURFACE
    else:
        return Tier.ASK


def send_tx(to_address: str, amount_eth: float) -> str:
    """Send transaction via viem"""
    result = subprocess.run(
        ["node", "-e", f"""
import {{ createWalletClient, http }} from 'viem';
import {{ privateKeyToAccount }} from 'viem/accounts';
import {{ base }} from 'viem/chains';
import {{ readFileSync }} from 'fs';

const wallet = JSON.parse(readFileSync('./nova-wallet.json'));
const account = privateKeyToAccount(wallet.privateKey);
const client = createWalletClient({{ account, chain: base, transport: http() }});

const hash = await client.sendTransaction({{
  to: '{to_address}',
  value: BigInt({int(amount_eth * 1e18)})
}});
console.log(hash);
"""],
        capture_output=True,
        text=True,
        cwd="/home/sntrblck/.openclaw/workspace/cdp-nova"
    )
    
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


async def execute_transaction(to_address: str, amount_eth: float, description: str, action_type: str = "transfer") -> EconomicAction:
    """Execute a transaction through the economic responsibility system"""
    
    tier = determine_tier(amount_eth, to_address, action_type)
    action = EconomicAction(action_type, amount_eth, to_address, description, tier)
    
    # Check balance
    balance = get_balance()
    action.balance_before = balance
    
    if balance < amount_eth:
        action.status = "rejected"
        action.error = f"Insufficient balance: {balance:.6f} ETH < {amount_eth:.6f} ETH"
        log_action(action)
        return action
    
    # Check reserve
    if balance - amount_eth < RESERVE_ETH:
        action.status = "rejected"
        action.error = f"Would drop below reserve: {balance - amount_eth:.6f} ETH < {RESERVE_ETH:.6f} ETH"
        log_action(action)
        return action
    
    # Execute based on tier
    if tier == Tier.ASK:
        action.status = "requires_approval"
        action.error = "Tier 3 action - requires explicit approval from Sen"
        log_action(action)
        return action
    
    if tier == Tier.SURFACE:
        action.status = "pending_approval"
        action.description = f"[SURFACE] {description}"
        log_action(action)
        return action
    
    # Tier 1 - Automatic execution
    try:
        action.tx_hash = send_tx(to_address, amount_eth)
        action.status = "confirmed"
        action.balance_after = get_balance()
    except Exception as e:
        action.status = "failed"
        action.error = str(e)
    
    log_action(action)
    return action


def get_recent_actions(limit: int = 10) -> list:
    """Get recent economic actions"""
    if not ECONOMIC_LOG_PATH.exists():
        return []
    
    actions = []
    with open(ECONOMIC_LOG_PATH) as f:
        for line in f:
            actions.append(json.loads(line))
    
    return actions[-limit:]


def get_balance_status() -> dict:
    """Get current balance with status"""
    balance = get_balance()
    return {
        "balance_eth": balance,
        "reserve_eth": RESERVE_ETH,
        "available_eth": balance - RESERVE_ETH,
        "status": "ok" if balance > RESERVE_ETH else "low"
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Nova's Economic Responsibility System")
        print("=" * 40)
        print("Commands:")
        print("  balance              - Check current balance")
        print("  status               - Full wallet status")
        print("  send <to> <amount>   - Execute transaction")
        print("  recent               - Recent actions")
        print("  tier <to> <amount>   - Check tier for action")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "balance":
        status = get_balance_status()
        print(f"Balance: {status['balance_eth']:.6f} ETH")
        print(f"Available: {status['available_eth']:.6f} ETH")
    
    elif cmd == "status":
        status = get_balance_status()
        print(f"Balance: {status['balance_eth']:.6f} ETH")
        print(f"Reserve: {status['reserve_eth']:.6f} ETH")
        print(f"Available: {status['available_eth']:.6f} ETH")
        print(f"Status: {status['status']}")
    
    elif cmd == "recent":
        for action in get_recent_actions():
            tier = action['tier']
            amt = action['amount_eth']
            to_short = action['to_address'][:12] + "..."
            status = action['status']
            print(f"[{tier}] {amt:.6f} ETH → {to_short} [{status}]")
    
    elif cmd == "tier" and len(sys.argv) >= 4:
        to_addr = sys.argv[2]
        amount = float(sys.argv[3])
        tier = determine_tier(amount, to_addr, "transfer")
        tier_names = {1: "AUTOMATIC", 2: "SURFACE", 3: "ASK"}
        print(f"Tier {tier.value} ({tier_names[tier.value]})")
        if tier.value > 1:
            print("⚠️  Requires approval before execution")
    
    elif cmd == "send" and len(sys.argv) >= 4:
        to_addr = sys.argv[2]
        amount = float(sys.argv[3])
        
        print(f"Sending {amount:.6f} ETH to {to_addr}...")
        action = asyncio.run(execute_transaction(to_addr, amount, "Manual send"))
        
        if action.status == "confirmed":
            print(f"✅ Confirmed! TX: {action.tx_hash}")
        elif action.status == "requires_approval":
            print(f"⏳ {action.error}")
        elif action.status == "pending_approval":
            print(f"⏳ Surface — awaiting approval")
        elif action.status == "rejected":
            print(f"❌ Rejected: {action.error}")
        else:
            print(f"❌ Failed: {action.error}")
    
    else:
        print("Unknown command or missing arguments")
        sys.exit(1)
