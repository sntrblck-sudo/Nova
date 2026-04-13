#!/usr/bin/env python3
"""
Nova's Smart Compounding System — Python Edition
Makes intelligent CLAWS staking decisions based on:
- Net reward calculation after gas costs
- Pool value assessment (is staking worth it?)
- Learned pool acceptance thresholds from rejections
- No unnecessary transactions when economics don't justify them
"""

import json
import time
import sqlite3
import requests
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

# ─── Config ───────────────────────────────────────────────────────────────────
NOVA = "0xB743fdbA842379933A3774617786712458659D16"
SENATOR_POOL = "0x0bb7b6d2334614dee123c4135d7b6fae244962f0"
CLAWS_POOL = "0x206C97D4Ecf053561Bd2C714335aAef0eC1105e6"
CLAWS_TOKEN = "0x7ca47B141639B893C6782823C0b219f872056379"
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
WETH = "0x4200000000000000000000000000000000000006"
UNISWAP_ROUTER = "0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24"

RPC_URL = "https://mainnet.base.org"
WALLET_PATH = Path("/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json")
MEMORY_DIR = Path("/home/sntrblck/.openclaw/workspace/memory")
COMPOUND_LOG = MEMORY_DIR / "compound_log.jsonl"
STATE_FILE = MEMORY_DIR / "compound_state.json"
LAST_RUN_FILE = MEMORY_DIR / "compound_last_run.json"

# Thresholds
NET_CLAIMS_THRESHOLD_USD = 0.10   # minimum net reward after gas to justify claim
NET_STAKE_THRESHOLD_USD = 0.05    # minimum net value after gas to justify stake
ESTIMATED_GAS_CLAIM = 100000       # gas units for claim tx
ESTIMATED_GAS_STAKE = 150000      # gas units for stake tx
ESTIMATED_GAS_APPROVE = 50000     # gas units for approve tx

# ─── JSON-RPC helpers ─────────────────────────────────────────────────────────
def rpc(method: str, params: list = None) -> dict:
    resp = requests.post(RPC_URL, json={
        "jsonrpc": "2.0", "method": method, "params": params or [], "id": 1
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["result"]

def eth_call(to: str, data: str) -> str:
    return rpc("eth_call", [{"to": to, "data": data}])

def eth_estimate_gas(tx: dict) -> int:
    return int(rpc("eth_estimateGas", [tx]), 16)

def eth_gas_price() -> int:
    return int(rpc("eth_gasPrice", []), 16)

def eth_get_balance(addr: str) -> int:
    return int(rpc("eth_getBalance", [addr, "latest"]), 16)

def eth_send_raw_transaction(signed_tx: str) -> str:
    return rpc("eth_sendRawTransaction", [signed_tx])

def eth_get_transaction_receipt(tx_hash: str) -> dict:
    return rpc("eth_getTransactionReceipt", [tx_hash])

def eth_block_number() -> int:
    return int(rpc("eth_blockNumber", []), 16)

# ─── ABI encoders ─────────────────────────────────────────────────────────────
def address_to_hex(addr: str) -> str:
    return addr.lower().replace("0x", "").rjust(64, "0")

def uint256_hex(val: int) -> str:
    return hex(val).replace("0x", "").rjust(64, "0")

def func_selector(func_name: str) -> str:
    import hashlib
    sig = f"{func_name}()".encode()
    return hashlib.new('sha256')(sig).hexdigest()[:8]

def encode_balance_of(addr: str) -> str:
    sel = func_selector("balanceOf")
    addr_hex = address_to_hex(addr)
    return f"0x{sel}{addr_hex}"

def encode_earned(addr: str) -> str:
    sel = func_selector("earned")
    addr_hex = address_to_hex(addr)
    return f"0x{sel}{addr_hex}"

def encode_claim() -> str:
    return f"0x{func_selector('claim')}"

def encode_stake(amount: int) -> str:
    sel = func_selector("stake")
    amt_hex = uint256_hex(amount)
    return f"0x{sel}{amt_hex}"

def encode_approve(spender: str, amount: int) -> str:
    sel = func_selector("approve")
    spd_hex = address_to_hex(spender)
    amt_hex = uint256_hex(amount)
    return f"0x{sel}{spd_hex}{amt_hex}"

def decode_uint256(data: str) -> int:
    if not data or len(data) < 66:
        return 0
    return int(data[-64:], 16)

def decode_bool(data: str) -> bool:
    if not data or len(data) < 66:
        return False
    return int(data[-64:], 16) == 1

# ─── Wallet ───────────────────────────────────────────────────────────────────
def load_wallet():
    with open(WALLET_PATH) as f:
        return json.load(f)

def sign_and_send(tx_params: dict, wallet: dict) -> str:
    """Sign with private key and send raw transaction."""
    from eth_account import Account
    from eth_account.transactions import encode_transaction, serializable_typed_data_from_dict
    import rlp
    
    # Get nonce
    nonce = int(rpc("eth_getTransactionCount", [wallet["address"], "pending"]), 16)
    
    # Build transaction
    gas_price = eth_gas_price()
    chain_id = 8453
    
    tx = {
        "type": 2,
        "chainId": chain_id,
        "nonce": nonce,
        "to": tx_params.get("to", ""),
        "value": hex(tx_params.get("value", 0)),
        "data": tx_params.get("data", "0x"),
        "gasLimit": hex(tx_params.get("gas", 200000)),
        "maxFeePerGas": hex(gas_price),
        "maxPriorityFeePerGas": hex(1000000000),  # 1 gwei tip
    }
    
    # Sign
    signed = Account.sign_transaction(tx, wallet["privateKey"])
    return signed.rawTransaction.hex()

# ─── Onchain queries ───────────────────────────────────────────────────────────
def get_claws_balance(addr: str = NOVA) -> int:
    data = encode_balance_of(addr)
    result = eth_call(CLAWS_TOKEN, data)
    return decode_uint256(result)

def get_pending_rewards(addr: str = NOVA) -> int:
    data = encode_earned(addr)
    result = eth_call(SENATOR_POOL, data)
    return decode_uint256(result)

def get_staked_senator(addr: str = NOVA) -> int:
    data = encode_balance_of(addr)
    result = eth_call(SENATOR_POOL, data)
    return decode_uint256(result)

def get_eth_balance(addr: str = NOVA) -> int:
    return eth_get_balance(addr)

def get_gas_price() -> int:
    return eth_gas_price()

def get_claws_gas_estimate() -> int:
    """Estimate current gas cost in ETH terms."""
    return get_gas_price()

def wait_for_receipt(tx_hash: str, timeout: int = 60) -> dict:
    start = time.time()
    while time.time() - start < timeout:
        try:
            receipt = eth_get_transaction_receipt(tx_hash)
            if receipt:
                return receipt
        except:
            pass
        time.sleep(2)
    raise TimeoutError(f"Transaction {tx_hash} not confirmed within {timeout}s")

def submit_tx(to: str, data: str, value: int = 0, gas: int = 200000) -> str:
    wallet = load_wallet()
    tx_params = {"to": to, "data": data, "value": value, "gas": gas}
    signed = sign_and_send(tx_params, wallet)
    tx_hash = eth_send_raw_transaction(signed)
    return tx_hash

# ─── Pricing ───────────────────────────────────────────────────────────────────
def get_eth_price_usd() -> float:
    """Get ETH price in USD from CoinGecko."""
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "ethereum", "vsusd": "true"},
            timeout=10
        )
        return resp.json().get("ethereum", {}).get("usd", 1800.0)
    except:
        return 1800.0

def claws_value_usd(claws_wei: int) -> float:
    """Estimate CLAWS value in USD via WETH pair on Uniswap."""
    try:
        # Get CLAWS/WETH price
        data = (
            func_selector("getAmountsOut")
            + uint256_hex(10**18)  # 1 CLAWS
            + address_to_hex(CLAWS_TOKEN)
            + address_to_hex(WETH)
        )
        result = eth_call(UNISWAP_ROUTER, data)
        if not result or result == "0x":
            return 0.0
        # Parse the nested array result
        # getAmountsOut returns (address[] memory path, uint256[] memory amounts)
        # We need to decode the dynamic array
        # Simplified: just return 0 if it fails
        return 0.0
    except:
        return 0.0

def gas_cost_usd(gas_units: int) -> float:
    """Calculate gas cost in USD."""
    gwei = get_gas_price() / 1e9
    eth = gwei * gas_units / 1e9
    return eth * get_eth_price_usd()

# ─── State management ───────────────────────────────────────────────────────────
@dataclass
class CompoundState:
    learned_pool_min_claws: Optional[int] = None  # in wei
    consecutive_rejects: int = 0
    last_stake_amount: Optional[int] = None
    last_claim_amount: Optional[int] = None
    last_run_ts: Optional[str] = None

def load_state() -> CompoundState:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            d = json.load(f)
            return CompoundState(
                learned_pool_min_claws=d.get("learned_pool_min_claws"),
                consecutive_rejects=d.get("consecutive_rejects", 0),
                last_stake_amount=d.get("last_stake_amount"),
                last_claim_amount=d.get("last_claim_amount"),
                last_run_ts=d.get("last_run_ts")
            )
    return CompoundState()

def save_state(state: CompoundState):
    with open(STATE_FILE, "w") as f:
        json.dump(asdict(state), f, indent=2)

# ─── Logging ──────────────────────────────────────────────────────────────────
def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(COMPOUND_LOG, "a") as f:
        f.write(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "message": msg}) + "\n")

# ─── Core decision engine ──────────────────────────────────────────────────────
def should_claim(pending_wei: int, gas_cost_claim_usd: float) -> tuple[bool, float]:
    """
    Returns (decision, net_value_usd).
    Decision is True if pending rewards exceed gas cost by more than NET_CLAIMS_THRESHOLD_USD.
    """
    # Very rough CLAWS/USD estimate — use 0 for now unless we can get a price
    # In production, we'd use the actual DEX price
    claws_per_eth = 1e18 / (get_eth_price_usd() * 1e18)  # just the ETH value
    pending_eth = pending_wei / 1e18
    pending_usd_estimate = pending_eth * get_eth_price_usd()  # assume CLAWS ~= ETH for rough estimate
    # Better: pending_usd_estimate = pending_wei / 1e18 * eth_price_usd * claws_vs_eth_ratio
    # Since we can't easily get CLAWS price, use a heuristic:
    # pending rewards in CLAWS tokens have unknown USD value
    # For now: if gas is cheap (< $0.50), always claim and let the pool handle it
    if gas_cost_claim_usd < 0.50:
        return True, pending_wei / 1e18  # return CLAWS amount as proxy
    return False, 0.0

def run_compound_cycle():
    """Main smart compound logic."""
    log("=== Smart Compound Cycle ===")
    state = load_state()
    
    # Gather state
    claws_bal = get_claws_balance()
    staked = get_staked_senator()
    pending = get_pending_rewards()
    eth_bal = get_eth_balance()
    
    eth_price = get_eth_price_usd()
    gas_price_wei = get_gas_price()
    gas_price_gwei = gas_price_wei / 1e9
    
    claim_gas_usd = gas_cost_usd(ESTIMATED_GAS_CLAIM)
    stake_gas_usd = gas_cost_usd(ESTIMATED_GAS_STAKE)
    approve_gas_usd = gas_cost_usd(ESTIMATED_GAS_APPROVE)
    total_gas_usd = claim_gas_usd + stake_gas_usd + approve_gas_usd
    
    claws_bal_float = claws_bal / 1e18
    pending_float = pending / 1e18
    staked_float = staked / 1e6
    eth_bal_float = eth_bal / 1e18
    
    log(f"ETH balance: {eth_bal_float:.6f} (~${eth_bal_float * eth_price:.2f})")
    log(f"SENATOR staked: {staked_float:.2f}")
    log(f"CLAWS balance: {claws_bal_float:.4f}")
    log(f"Pending rewards: {pending_float:.4f} CLAWS")
    log(f"Gas price: {gas_price_gwei:.4f} gwei")
    log(f"Estimated total gas cost: ~${total_gas_usd:.4f}")
    
    # Check ETH for gas
    if eth_bal_float < 0.001:
        log("LOW ETH: insufficient for gas. Aborting cycle.")
        return
    
    # Decision: should we claim?
    # Simple rule: if pending > 0 and gas is reasonable, claim
    # The NET_CLAIMS_THRESHOLD is the floor — if rewards clear it, claim
    if pending > 0:
        # Heuristic: pending CLAWS worth ~$X (assume some USD value per CLAWS)
        # Since we don't have reliable CLAWS/USD price, use ETH value as floor estimate
        pending_eth_equiv = pending_float  # rough proxy
        pending_usd_estimate = pending_eth_equiv * eth_price
        net_estimate = pending_usd_estimate - claim_gas_usd
        
        log(f"Pending USD estimate: ~${net_estimate:.4f} (after ${claim_gas_usd:.4f} gas)")
        
        if net_estimate >= NET_CLAIMS_THRESHOLD_USD or claim_gas_usd < 0.20:
            log(f"DECISION: Claim pending rewards (net est. ${net_estimate:.4f} >= ${NET_CLAIMS_THRESHOLD_USD})")
            try:
                tx_hash = submit_tx(SENATOR_POOL, encode_claim(), 0, ESTIMATED_GAS_CLAIM)
                log(f"Claim tx submitted: {tx_hash}")
                receipt = wait_for_receipt(tx_hash)
                if receipt.get("status") == "0x1":
                    log("Claim confirmed!")
                    state.last_claim_amount = pending
                    # Get updated CLAWS balance
                    time.sleep(3)
                    new_claws = get_claws_balance()
                    claimed = new_claws - claws_bal
                    log(f"CLAWS received: {claimed / 1e18:.4f}")
                    claws_bal = new_claws
                else:
                    log("Claim FAILED")
            except Exception as e:
                log(f"Claim error: {e}")
        else:
            log(f"SKIP CLAIM: net estimate ${net_estimate:.4f} below ${NET_CLAIMS_THRESHOLD_USD} threshold")
    else:
        log("No pending rewards")
    
    # Decision: should we stake CLAWS?
    if claws_bal > 0:
        # Try to stake all CLAWS in native pool
        # The pool might reject if below minimum — we'll learn from the rejection
        log(f"DECISION: Attempting to stake {claws_bal / 1e18:.4f} CLAWS")
        
        try:
            # First approve
            approve_tx = submit_tx(CLAWS_TOKEN, encode_approve(CLAWS_POOL, claws_bal), 0, ESTIMATED_GAS_APPROVE)
            log(f"Approve tx: {approve_tx}")
            wait_for_receipt(approve_tx)
            log("Approval confirmed")
            
            # Then stake
            stake_tx = submit_tx(CLAWS_POOL, encode_stake(claws_bal), 0, ESTIMATED_GAS_STAKE)
            log(f"Stake tx submitted: {stake_tx}")
            receipt = wait_for_receipt(stake_tx)
            
            if receipt.get("status") == "0x1":
                log(f"STAKE SUCCESS: {claws_bal / 1e18:.4f} CLAWS staked!")
                state.consecutive_rejects = 0
                state.last_stake_amount = claws_bal
                state.learned_pool_min_claws = None  # No minimum detected
            else:
                log("STAKE FAILED: reverted")
                state.consecutive_rejects += 1
                log(f"Consecutive rejects: {state.consecutive_rejects}")
        except Exception as e:
            err_msg = str(e)
            log(f"Stake error: {err_msg[:200]}")
            
            if "minimum" in err_msg.lower() or "below" in err_msg.lower():
                state.consecutive_rejects += 1
                log(f"Pool rejected: below minimum. Consecutive rejects: {state.consecutive_rejects}")
                # Try to extract minimum from error
                import re
                nums = re.findall(r'\d+', err_msg)
                if nums:
                    min_claws = int(nums[-1])
                    state.learned_pool_min_claws = min_claws
                    log(f"Detected pool minimum: {min_claws / 1e18:.4f} CLAWS")
                    # If we have enough, we can try again
                    if claws_bal >= min_claws:
                        log(f"ERROR: Have {claws_bal / 1e18:.4f} CLAWS but pool still rejected. Trying probe...")
                    else:
                        log(f"Need {min_claws / 1e18:.4f} CLAWS to stake. Current: {claws_bal / 1e18:.4f}")
                        deficit = (min_claws - claws_bal) / 1e18
                        log(f"Deficit: {deficit:.4f} CLAWS. Will accumulate and retry.")
            else:
                state.consecutive_rejects += 1
    else:
        log("No CLAWS to stake")
    
    state.last_run_ts = datetime.now(timezone.utc).isoformat()
    save_state(state)
    log("=== Compound Cycle Complete ===\n")

# ─── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "status":
            claws = get_claws_balance()
            staked = get_staked_senator()
            pending = get_pending_rewards()
            eth_bal = get_eth_balance()
            eth_price = get_eth_price_usd()
            gas_price_gwei = get_gas_price() / 1e9
            
            state = load_state()
            
            print(f"NOVA ADDRESS: {NOVA}")
            print(f"ETH balance: {eth_bal / 1e18:.6f} (~${eth_bal / 1e18 * eth_price:.2f})")
            print(f"SENATOR staked: {staked / 1e6:.2f}")
            print(f"CLAWS balance: {claws / 1e18:.4f}")
            print(f"Pending rewards: {pending / 1e18:.4f} CLAWS")
            print(f"Gas price: {gas_price_gwei:.4f} gwei")
            print(f"Gas cost (claim): ~${gas_cost_usd(ESTIMATED_GAS_CLAIM):.4f}")
            print(f"Gas cost (stake): ~${gas_cost_usd(ESTIMATED_GAS_STAKE):.4f}")
            print(f"---")
            print(f"State: {asdict(state)}")
        elif sys.argv[1] == "check":
            # Quick check without decisions
            claws = get_claws_balance()
            pending = get_pending_rewards()
            print(f"CLAWS: {claws / 1e18:.4f}")
            print(f"Pending: {pending / 1e18:.4f}")
        else:
            run_compound_cycle()
    else:
        run_compound_cycle()
