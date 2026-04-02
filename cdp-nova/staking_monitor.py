"""
Nova's Staking Monitor
Tracks Nova's SENATOR staking position and rewards.
Run via cron or health check.
"""

import subprocess
import json
from pathlib import Path

WALLET_PATH = "/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json"
POOL_ADDRESS = "0x0bb7b6d2334614dee123c4135d7b6fae244962f0"
NOVA_ADDRESS = "0xB743fdbA842379933A3774617786712458659D16"
SENATOR_TOKEN = "0x4add7e1b9c68f03ce0d83336f2d25c399d947dac"
CLAWS_TOKEN = "0x7ca47b141639b893c6782823c0b219f872056379"

STATE_FILE = Path("/home/sntrblck/.openclaw/workspace/memory/staking_state.json")


def get_state():
    """Load previous staking state"""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_staked": 0, "last_check": None, "rewards_claimed_total": 0}


def save_state(state):
    """Save current staking state"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_onchain_data():
    """Get current staking data from chain"""
    result = subprocess.run(
        ["node", "-e", """
import { createPublicClient, http } from 'viem';
import { base } from 'viem/chains';
import { readFileSync } from 'fs';

const pub = createPublicClient({ chain: base, transport: http() });
const wallet = JSON.parse(readFileSync('/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json'));
const { privateKeyToAccount } = await import('viem/accounts');
const account = privateKeyToAccount(wallet.privateKey);

// Nova's staked balance
const staked = await pub.readContract({
  address: '0x0bb7b6d2334614dee123c4135d7b6fae244962f0',
  functionName: 'balanceOf',
  args: [account.address],
  abi: [{ name: 'balanceOf', type: 'function', inputs: [{ name: 'account', type: 'address' }], outputs: [{ name: '', type: 'uint256' }] }]
});

// Nova's SENATOR wallet balance
const senatorBal = await pub.readContract({
  address: '0x4add7e1b9c68f03ce0d83336f2d25c399d947dac',
  functionName: 'balanceOf',
  args: [account.address],
  abi: [{ name: 'balanceOf', type: 'function', inputs: [{ name: 'account', type: 'address' }], outputs: [{ name: '', type: 'uint256' }] }]
});

// Pool's CLAWS balance (reward pool)
const poolClawsBal = await pub.readContract({
  address: '0x7ca47b141639b893c6782823c0b219f872056379',
  functionName: 'balanceOf',
  args: ['0x0bb7b6d2334614dee123c4135d7b6fae244962f0'],
  abi: [{ name: 'balanceOf', type: 'function', inputs: [{ name: 'account', type: 'address' }], outputs: [{ name: '', type: 'uint256' }] }]
});

console.log(JSON.stringify({
  staked: staked.toString(),
  senatorBalance: senatorBal.toString(),
  poolClawsBalance: poolClawsBal.toString(),
}));
"""],
        capture_output=True,
        text=True,
        cwd="/home/sntrblck/.openclaw/workspace/cdp-nova"
    )
    
    if result.returncode != 0:
        return {"error": result.stderr}
    
    try:
        return json.loads(result.stdout)
    except:
        return {"error": "parse error", "raw": result.stdout}


def check_position():
    """Check Nova's staking position and report changes"""
    import time
    
    state = get_state()
    data = get_onchain_data()
    
    if "error" in data:
        return {"status": "error", "message": data["error"]}
    
    staked = int(data["staked"])
    senator_balance = int(data["senatorBalance"])
    pool_claws = int(data["poolClawsBalance"])
    
    result = {
        "staked": staked,
        "senator_balance": senator_balance,
        "pool_rewards_available": pool_claws,
        "status": "ok",
        "changes": {}
    }
    
    # Check for changes
    if state["last_staked"] != staked:
        result["changes"]["staked"] = {
            "from": state["last_staked"],
            "to": staked
        }
    
    # Save state
    state["last_staked"] = staked
    state["last_check"] = time.time()
    save_state(state)
    
    return result


def format_wei(amount, decimals=18):
    """Format wei amount to readable string"""
    return f"{amount / (10**decimals):,.2f}"


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        result = check_position()
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Staked SENATOR: {format_wei(result['staked'])}")
            print(f"SENATOR in wallet: {format_wei(result['senator_balance'])}")
            print(f"Pool rewards available: {format_wei(result['pool_rewards_available'], 18)} CLAWS")
            if result.get("changes"):
                print("\nChanges detected:")
                for key, change in result["changes"].items():
                    print(f"  {key}: {format_wei(change['from'])} → {format_wei(change['to'])}")
    else:
        # Simple status
        data = get_onchain_data()
        if "error" in data:
            print(f"Error: {data['error']}")
        else:
            print(f"Nova's SENATOR staking position:")
            print(f"  Staked: {format_wei(int(data['staked']))} SENATOR")
            print(f"  In wallet: {format_wei(int(data['senatorBalance']))} SENATOR")
            print(f"  Pool reward balance: {format_wei(int(data['poolClawsBalance']), 18)} CLAWS")
