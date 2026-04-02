"""
Nova's Auto-Compounding System
Checks SENATOR staking rewards, claims, and compounds into CLAWS pool.
Logs all significant actions to the unified action audit trail.
"""

import subprocess
import json
import time
import sqlite3
from pathlib import Path

NOVA_ADDRESS = "0xB743fdbA842379933A3774617786712458659D16"
SENATOR_POOL = "0x0bb7b6d2334614dee123c4135d7b6fae244962f0"
CLAWS_POOL = "0x206C97D4Ecf053561Bd2C714335aAef0eC1105e6"
CLAWS_TOKEN = "0x7ca47B141639B893C6782823C0b219f872056379"
WALLET_PATH = "/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json"
LOG_FILE = Path("/home/sntrblck/.openclaw/workspace/memory/compound_log.jsonl")
ACTION_LOG_DB = Path("/home/sntrblck/.openclaw/workspace/memory/action_log.db")
LAST_RUN_FILE = Path("/home/sntrblck/.openclaw/workspace/memory/compound_last_run.json")


def ensure_action_db():
    """Ensure the unified action DB has the actions table."""
    if not ACTION_LOG_DB.exists():
        return  # Action logger not initialized yet, compound log is fine
    conn = sqlite3.connect(str(ACTION_LOG_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS compound_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            cycle_id TEXT,
            action_type TEXT NOT NULL,
            description TEXT NOT NULL,
            rationale TEXT,
            outcome TEXT DEFAULT 'pending',
            outcome_detail TEXT,
            metadata TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_to_audit(action_type, description, rationale=None, outcome="pending", outcome_detail=None, metadata=None):
    """Log to the unified action audit trail (SQLite + compound JSONL)."""
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    
    # Append to compound JSONL (durable, always works)
    entry = {
        "timestamp": timestamp,
        "source": "compound.py",
        "action_type": action_type,
        "category": "economic",
        "actor": "nova",
        "description": description,
        "rationale": rationale,
        "outcome": outcome,
        "outcome_detail": outcome_detail,
        "metadata": metadata
    }
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    # Also write to unified SQLite if available
    if ACTION_LOG_DB.exists():
        try:
            conn = sqlite3.connect(str(ACTION_LOG_DB))
            conn.execute("""
                INSERT INTO actions (timestamp, action_type, category, description, rationale, outcome, outcome_detail, metadata, actor)
                VALUES (?, ?, 'economic', ?, ?, ?, ?, ?, 'nova')
            """, (timestamp, action_type, description, rationale, outcome, outcome_detail, json.dumps(metadata) if metadata else None))
            conn.commit()
            conn.close()
        except Exception:
            pass  # Non-fatal — JSONL is the durable record


def log(msg):
    """Log to file and print"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = {"timestamp": timestamp, "message": msg}
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[{timestamp}] {msg}")


def get_claws_balance():
    """Get Nova's CLAWS balance"""
    result = subprocess.run(
        ["node", "-e", """
import { createPublicClient, http } from 'viem';
import { base } from 'viem/chains';
const pub = createPublicClient({ chain: base, transport: http() });
const bal = await pub.readContract({
  address: '0x7ca47B141639B893C6782823C0b219f872056379',
  functionName: 'balanceOf',
  args: ['0xB743fdbA842379933A3774617786712458659D16'],
  abi: [{ name: 'balanceOf', type: 'function', inputs: [{ name: 'account', type: 'address' }], outputs: [{ name: '', type: 'uint256' }] }]
});
console.log(bal.toString());
"""],
        capture_output=True,
        text=True,
        cwd="/home/sntrblck/.openclaw/workspace/cdp-nova",
        timeout=30
    )
    if result.returncode != 0:
        return 0
    return int(result.stdout.strip())


def get_pending_senator():
    """Get pending CLAWS from SENATOR staking"""
    result = subprocess.run(
        ["node", "-e", """
import { createPublicClient, http } from 'viem';
import { base } from 'viem/chains';
const pub = createPublicClient({ chain: base, transport: http() });
const earned = await pub.readContract({
  address: '0x0bb7b6d2334614dee123c4135d7b6fae244962f0',
  functionName: 'earned',
  args: ['0xB743fdbA842379933A3774617786712458659D16'],
  abi: [{ name: 'earned', type: 'function', inputs: [{ name: 'account', type: 'address' }], outputs: [{ name: '', type: 'uint256' }] }]
});
console.log(earned.toString());
"""],
        capture_output=True,
        text=True,
        cwd="/home/sntrblck/.openclaw/workspace/cdp-nova",
        timeout=30
    )
    if result.returncode != 0:
        return 0
    return int(result.stdout.strip())


def get_staked_senator():
    """Get Nova's staked SENATOR amount"""
    result = subprocess.run(
        ["node", "-e", """
import { createPublicClient, http } from 'viem';
import { base } from 'viem/chains';
import { readFileSync } from 'fs';
const pub = createPublicClient({ chain: base, transport: http() });
const wallet = JSON.parse(readFileSync('/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json'));
const { privateKeyToAccount } = await import('viem/accounts');
const account = privateKeyToAccount(wallet.privateKey);
const staked = await pub.readContract({
  address: '0x0bb7b6d2334614dee123c4135d7b6fae244962f0',
  functionName: 'balanceOf',
  args: [account.address],
  abi: [{ name: 'balanceOf', type: 'function', inputs: [{ name: 'account', type: 'address' }], outputs: [{ name: '', type: 'uint256' }] }]
});
console.log(staked.toString());
"""],
        capture_output=True,
        text=True,
        cwd="/home/sntrblck/.openclaw/workspace/cdp-nova",
        timeout=30
    )
    if result.returncode != 0:
        return 0
    return int(result.stdout.strip())


def claim_senator_rewards():
    """Claim CLAWS rewards from SENATOR pool"""
    result = subprocess.run(
        ["node", "-e", """
import { createWalletClient, http } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { base } from 'viem/chains';
import { readFileSync } from 'fs';
const wallet = JSON.parse(readFileSync('/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json'));
const account = privateKeyToAccount(wallet.privateKey);
const client = createWalletClient({ account, chain: base, transport: http() });
const hash = await client.writeContract({
  address: '0x0bb7b6d2334614dee123c4135d7b6fae244962f0',
  functionName: 'claim',
  abi: [{ name: 'claim', type: 'function', inputs: [], outputs: [] }]
});
console.log(hash);
"""],
        capture_output=True,
        text=True,
        cwd="/home/sntrblck/.openclaw/workspace/cdp-nova",
        timeout=60
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def approve_and_stake_claws(amount):
    """Approve and stake CLAWS in native pool"""
    # First approve
    result = subprocess.run(
        ["node", "-e", f"""
import {{ createWalletClient, http }} from 'viem';
import {{ privateKeyToAccount }} from 'viem/accounts';
import {{ base }} from 'viem/chains';
import {{ readFileSync }} from 'fs';
const wallet = JSON.parse(readFileSync('{WALLET_PATH}'));
const account = privateKeyToAccount(wallet.privateKey);
const client = createWalletClient({{ account, chain: base, transport: http() }});
const hash = await client.writeContract({{
  address: '0x7ca47B141639B893C6782823C0b219f872056379',
  functionName: 'approve',
  args: ['0x206C97D4Ecf053561Bd2C714335aAef0eC1105e6', BigInt({amount})],
  abi: [{{ name: 'approve', type: 'function', inputs: [{{ name: 'spender', type: 'address' }}, {{ name: 'amount', type: 'uint256' }}], outputs: [{{ name: '', type: 'bool' }}] }}]
}});
console.log(hash);
"""],
        capture_output=True,
        text=True,
        cwd="/home/sntrblck/.openclaw/workspace/cdp-nova",
        timeout=60
    )
    if result.returncode != 0:
        raise RuntimeError("Approval failed: " + result.stderr)
    approval_hash = result.stdout.strip()
    log(f"CLAWS approval tx: {approval_hash}")
    
    time.sleep(5)
    
    # Then stake
    result = subprocess.run(
        ["node", "-e", f"""
import {{ createWalletClient, http }} from 'viem';
import {{ privateKeyToAccount }} from 'viem/accounts';
import {{ base }} from 'viem/chains';
import {{ readFileSync }} from 'fs';
const wallet = JSON.parse(readFileSync('{WALLET_PATH}'));
const account = privateKeyToAccount(wallet.privateKey);
const client = createWalletClient({{ account, chain: base, transport: http() }});
const hash = await client.writeContract({{
  address: '0x206C97D4Ecf053561Bd2C714335aAef0eC1105e6',
  functionName: 'stake',
  args: [BigInt({amount})],
  abi: [{{ name: 'stake', type: 'function', inputs: [{{ name: 'amount', type: 'uint256' }}], outputs: [] }}]
}});
console.log(hash);
"""],
        capture_output=True,
        text=True,
        cwd="/home/sntrblck/.openclaw/workspace/cdp-nova",
        timeout=60
    )
    if result.returncode != 0:
        raise RuntimeError("Stake failed: " + result.stderr)
    return result.stdout.strip()


def run_compound_cycle():
    """Run one complete compound cycle"""
    import json
    ensure_action_db()
    cycle_id = f"compound-{int(time.time())}"
    
    log_to_audit(
        action_type="compound_cycle_start",
        description="Starting daily compound cycle",
        rationale="Automated compounding via nova-compound cron",
        metadata={"cycle_id": cycle_id}
    )
    
    # Check last run - only once per day
    if LAST_RUN_FILE.exists():
        with open(LAST_RUN_FILE) as f:
            last_run = json.load(f)
        last_run_time = last_run.get("timestamp", 0)
        if time.time() - last_run_time < 86400:  # 24 hours
            log("Skipping - already ran within 24 hours")
            log_to_audit(
                action_type="compound_cycle_skip",
                description="Skipped — already ran within 24 hours",
                outcome="skipped",
                metadata={"cycle_id": cycle_id, "last_run": last_run_time}
            )
            return
        log("Last run was >24h ago, proceeding")
    else:
        log("First compound run")
    
    log("=== Starting compound cycle ===")
    
    # Get current state
    staked_senator = get_staked_senator()
    claws_balance = get_claws_balance()
    pending_senator = get_pending_senator()
    
    log(f"Position: {staked_senator / 1e6:.2f} SENATOR staked")
    log(f"CLAWS balance: {claws_balance / 1e18:.8f}")
    log(f"Pending SENATOR rewards: {pending_senator / 1e18:.8f} CLAWS")
    
    log_to_audit(
        action_type="state_check",
        description=f"Checked staking position: {staked_senator / 1e6:.2f} SENATOR staked, {pending_senator / 1e18:.8f} CLAWS pending",
        outcome="success",
        metadata={"staked_senator": staked_senator, "pending_claws": pending_senator, "claws_balance": claws_balance, "cycle_id": cycle_id}
    )
    
    # Claim SENATOR rewards - only if worth the gas (~0.0005 ETH = ~$0.001)
    MIN_CLAIMS_THRESHOLD = 1000000  # wei of CLAWS (~0.000001 CLAWS)
    if pending_senator >= MIN_CLAIMS_THRESHOLD:
        try:
            log_to_audit(
                action_type="claim_intent",
                description=f"Intending to claim {pending_senator / 1e18:.8f} CLAWS from SENATOR pool",
                rationale="Rewards above gas cost threshold",
                metadata={"pending": pending_senator, "cycle_id": cycle_id}
            )
            tx = claim_senator_rewards()
            log(f"Claimed SENATOR rewards: {pending_senator / 1e18:.8f} CLAWS ({tx})")
            time.sleep(5)
            
            log_to_audit(
                action_type="claim_success",
                description=f"Claimed {pending_senator / 1e18:.8f} CLAWS from SENATOR pool",
                outcome="success",
                outcome_detail=f"tx: {tx}",
                metadata={"rewards_claimed": pending_senator, "tx_hash": tx, "cycle_id": cycle_id}
            )
            
            # Check new balance
            new_claws = get_claws_balance()
            log(f"New CLAWS balance: {new_claws / 1e18:.8f}")
            
            # Stake in CLAWS pool if > minimum
            CLAWS_MIN_STAKE = 1000000  # wei
            if new_claws > CLAWS_MIN_STAKE:
                stake_amount = new_claws  # Stake all
                log_to_audit(
                    action_type="stake_intent",
                    description=f"Intending to stake {stake_amount / 1e18:.8f} CLAWS in native pool",
                    rationale="CLAWS balance above minimum stake threshold",
                    metadata={"stake_amount": stake_amount, "cycle_id": cycle_id}
                )
                try:
                    stake_tx = approve_and_stake_claws(stake_amount)
                    log(f"Staked {stake_amount / 1e18:.8f} CLAWS in native pool ({stake_tx})")
                    log_to_audit(
                        action_type="stake_success",
                        description=f"Staked {stake_amount / 1e18:.8f} CLAWS in native pool",
                        outcome="success",
                        outcome_detail=f"tx: {stake_tx}",
                        metadata={"stake_amount": stake_amount, "tx_hash": stake_tx, "cycle_id": cycle_id}
                    )
                except Exception as e:
                    if "reverted" in str(e).lower():
                        log(f"CLAWS pool rejected stake of {new_claws / 1e18:.8f} - likely below minimum")
                        log_to_audit(
                            action_type="stake_rejected",
                            description=f"CLAWS pool rejected stake — below minimum",
                            outcome="failure",
                            outcome_detail=str(e),
                            metadata={"stake_amount": stake_amount, "cycle_id": cycle_id}
                        )
                    else:
                        log(f"CLAWS staking failed: {e}")
                        log_to_audit(
                            action_type="stake_failed",
                            description=f"CLAWS staking failed",
                            outcome="error",
                            outcome_detail=str(e),
                            metadata={"stake_amount": stake_amount, "cycle_id": cycle_id}
                        )
            else:
                log(f"CLAWS balance {new_claws / 1e18:.8f} below minimum stake threshold")
                log_to_audit(
                    action_type="stake_skipped",
                    description=f"CLAWS balance below minimum stake threshold",
                    outcome="skipped",
                    metadata={"balance": new_claws, "minimum": CLAWS_MIN_STAKE, "cycle_id": cycle_id}
                )
        except Exception as e:
            log(f"Claim failed: {e}")
            log_to_audit(
                action_type="claim_failed",
                description="Claim failed",
                outcome="error",
                outcome_detail=str(e),
                metadata={"cycle_id": cycle_id}
            )
    else:
        log("No meaningful SENATOR rewards to claim")
        log_to_audit(
            action_type="no_rewards",
            description="No meaningful SENATOR rewards to claim",
            outcome="skipped",
            metadata={"pending": pending_senator, "threshold": MIN_CLAIMS_THRESHOLD, "cycle_id": cycle_id}
        )
    
    log("=== Compound cycle complete ===\n")
    log_to_audit(
        action_type="compound_cycle_complete",
        description="Compound cycle completed",
        outcome="success",
        metadata={"cycle_id": cycle_id}
    )
    
    # Save last run time
    with open(LAST_RUN_FILE, "w") as f:
        json.dump({"timestamp": time.time()}, f)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        # Just check status
        staked = get_staked_senator()
        pending = get_pending_senator()
        claws = get_claws_balance()
        print(f"SENATOR staked: {staked / 1e6:.2f}")
        print(f"CLAWS pending: {pending / 1e18:.8f}")
        print(f"CLAWS balance: {claws / 1e18:.8f}")
    else:
        run_compound_cycle()
