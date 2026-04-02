"""
Nova's Token Tracker
Tracks ERC20 token balances for Nova's wallet
"""

import json
import subprocess
from pathlib import Path

# Nova's address
NOVA_ADDRESS = "0xB743fdbA842379933A3774617786712458659D16"

# Known tokens on Base
TOKENS = {
    "SENATOR": "0x4add7e1b9c68f03ce0d83336f2d25c399d947dac",
}

TOKEN_STATE_FILE = Path("/home/sntrblck/.openclaw/workspace/memory/token_balances.json")


def get_token_balance(token_symbol: str) -> dict:
    """Get token balance using viem with ERC20 ABI"""
    token_addr = TOKENS.get(token_symbol.upper())
    if not token_addr:
        return {"error": f"Unknown token: {token_symbol}"}
    
    result = subprocess.run(
        ["node", "-e", f"""
import {{ createPublicClient, http }} from 'viem';
import {{ base }} from 'viem/chains';

const pub = createPublicClient({{ chain: base, transport: http() }});

// ERC20 balanceOf + decimals
const balance = await pub.readContract({{
  address: '{token_addr}',
  functionName: 'balanceOf',
  args: ['{NOVA_ADDRESS}'],
  abi: [
    {{
      name: 'balanceOf',
      type: 'function',
      inputs: [{{ name: 'account', type: 'address' }}],
      outputs: [{{ name: '', type: 'uint256' }}]
    }},
    {{
      name: 'decimals',
      type: 'function',
      inputs: [],
      outputs: [{{ name: '', type: 'uint8' }}]
    }},
    {{
      name: 'symbol',
      type: 'function',
      inputs: [],
      outputs: [{{ name: '', type: 'string' }}]
    }}
  ]
}});

const decimals = await pub.readContract({{
  address: '{token_addr}',
  functionName: 'decimals',
  abi: [
    {{
      name: 'decimals',
      type: 'function',
      inputs: [],
      outputs: [{{ name: '', type: 'uint8' }}]
    }}
  ]
}});

console.log(JSON.stringify({{
  balance: balance.toString(),
  decimals: decimals,
  formatted: (Number(balance) / Math.pow(10, decimals)).toString()
}}));
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
        return {"error": "Parse error", "raw": result.stdout}


def get_all_balances():
    """Get balances for all tracked tokens"""
    results = {}
    for symbol in TOKENS:
        results[symbol] = get_token_balance(symbol)
    return results


def save_balances(balances):
    """Save current token balances to state file"""
    TOKEN_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_STATE_FILE, "w") as f:
        json.dump(balances, f, indent=2)


def check_changes():
    """Check for balance changes since last save"""
    import time
    
    current = get_all_balances()
    previous = {}
    
    if TOKEN_STATE_FILE.exists():
        with open(TOKEN_STATE_FILE) as f:
            previous = json.load(f)
    
    changes = {}
    for symbol, data in current.items():
        if symbol in previous:
            prev_balance = previous[symbol].get("balance", "0")
            curr_balance = data.get("balance", "0")
            if prev_balance != curr_balance:
                changes[symbol] = {
                    "from": previous[symbol].get("formatted"),
                    "to": data.get("formatted"),
                    "change": str(int(curr_balance) - int(prev_balance))
                }
    
    save_balances(current)
    return {"current": current, "changes": changes}


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Token Tracker")
        print("Usage: token_tracker.py <symbol> | all | changes")
    
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if cmd == "all":
        balances = get_all_balances()
        for symbol, data in balances.items():
            if "error" in data:
                print(f"{symbol}: ERROR - {data['error']}")
            else:
                print(f"{symbol}: {data['formatted']}")
    
    elif cmd == "changes":
        result = check_changes()
        if result["changes"]:
            print("Changes detected:")
            for symbol, change in result["changes"].items():
                print(f"  {symbol}: {change['from']} → {change['to']}")
        else:
            print("No changes")
    
    elif cmd.upper() in TOKENS:
        data = get_token_balance(cmd.upper())
        if "error" in data:
            print(f"Error: {data['error']}")
        else:
            print(f"{cmd}: {data['formatted']}")
    
    else:
        print(f"Unknown token: {cmd}")
        print(f"Known: {list(TOKENS.keys())}")
