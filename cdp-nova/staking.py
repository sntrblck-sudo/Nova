"""
Nova's Staking System
===================
Stake and claim SENATOR tokens in Inclawbate pools.
"""

import subprocess
import time
from pathlib import Path

# Nova's wallet
NOVA_ADDRESS = "0xB743fdbA842379933A3774617786712458659D16"
SENATOR_TOKEN = "0x4add7e1b9c68f03ce0d83336f2d25c399d947dac"
SENATOR_POOL = "0x0bb7b6d2334614dee123c4135d7b6fae244962f0"
CLAWS_TOKEN = "0x7ca47b141639b893c6782823c0b219f872056379"

WALLET_PATH = "/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json"


def get_balance():
    """Get Nova's SENATOR balance"""
    result = subprocess.run(
        ["node", "-e", """
import { createPublicClient, http } from 'viem';
import { base } from 'viem/chains';
import { readFileSync } from 'fs';

const pub = createPublicClient({ chain: base, transport: http() });
const wallet = JSON.parse(readFileSync('/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json'));
const { privateKeyToAccount } = await import('viem/accounts');
const account = privateKeyToAccount(wallet.privateKey);

const balance = await pub.readContract({
  address: '0x4add7e1b9c68f03ce0d83336f2d25c399d947dac',
  functionName: 'balanceOf',
  args: [account.address],
  abi: [{ name: 'balanceOf', type: 'function', inputs: [{ name: 'account', type: 'address' }], outputs: [{ name: '', type: 'uint256' }] }]
});

console.log(balance.toString());
"""],
        capture_output=True,
        text=True,
        cwd="/home/sntrblck/.openclaw/workspace/cdp-nova"
    )
    return int(result.stdout.strip())


def get_staked_balance():
    """Get Nova's staked balance"""
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
        cwd="/home/sntrblck/.openclaw/workspace/cdp-nova"
    )
    return int(result.stdout.strip())


def get_pending_rewards():
    """Get pending CLAWS rewards"""
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
console.log((Number(earned) / 1e18).toString());
"""],
        capture_output=True,
        text=True,
        cwd="/home/sntrblck/.openclaw/workspace/cdp-nova",
        timeout=30
    )
    if result.returncode != 0:
        return 0.0
    try:
        return float(result.stdout.strip())
    except:
        return 0.0


def get_claws_balance():
    """Get Nova's CLAWS balance"""
    result = subprocess.run(
        ["node", "-e", """
import { createPublicClient, http } from 'viem';
import { base } from 'viem/chains';
const pub = createPublicClient({ chain: base, transport: http() });
const bal = await pub.readContract({
  address: '0x7ca47b141639b893c6782823c0b219f872056379',
  functionName: 'balanceOf',
  args: ['0xB743fdbA842379933A3774617786712458659D16'],
  abi: [{ name: 'balanceOf', type: 'function', inputs: [{ name: 'account', type: 'address' }], outputs: [{ name: '', type: 'uint256' }] }]
});
console.log((Number(bal) / 1e18).toString());
"""],
        capture_output=True,
        text=True,
        cwd="/home/sntrblck/.openclaw/workspace/cdp-nova"
    )
    return float(result.stdout.strip())


def stake(amount: int) -> str:
    """Stake SENATOR tokens"""
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
  address: '{SENATOR_POOL}',
  functionName: 'stake',
  args: [BigInt({amount})],
  abi: [{{ name: 'stake', type: 'function', inputs: [{{ name: 'amount', type: 'uint256' }}], outputs: [] }}]
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


def approve(amount: int) -> str:
    """Approve the pool to spend SENATOR tokens"""
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
  address: '{SENATOR_TOKEN}',
  functionName: 'approve',
  args: ['{SENATOR_POOL}', BigInt({amount})],
  abi: [{{ name: 'approve', type: 'function', inputs: [{{ name: 'spender', type: 'address' }}, {{ name: 'amount', type: 'uint256' }}], outputs: [{{ name: '', type: 'bool' }}] }}]
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


def claim_rewards() -> str:
    """Claim staking rewards"""
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
  address: '{SENATOR_POOL}',
  functionName: 'claim',
  abi: [{{ name: 'claim', type: 'function', inputs: [], outputs: [] }}]
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


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Nova's Staking System")
        print("Commands: status | claim | pending")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "status":
        balance = get_balance()
        staked = get_staked_balance()
        pending = get_pending_rewards()
        claws = get_claws_balance()
        print(f"SENATOR in wallet: {balance / 1e18:.6f}")
        print(f"SENATOR staked: {staked / 1e18:.6f}")
        print(f"CLAWS pending: {pending:.8f}")
        print(f"CLAWS balance: {claws:.8f}")
    
    elif cmd == "pending":
        pending = get_pending_rewards()
        print(f"CLAWS pending: {pending:.8f}")
    
    elif cmd == "claim":
        pending = get_pending_rewards()
        if pending < 0.00000001:
            print("Rewards too small to claim")
        else:
            print(f"Claiming {pending:.8f} CLAWS...")
            tx_hash = claim_rewards()
            print(f"Claim tx: {tx_hash}")
            time.sleep(3)
            print(f"New CLAWS balance: {get_claws_balance():.8f}")
    
    elif cmd == "staked":
        staked = get_staked_balance()
        print(f"SENATOR staked: {staked / 1e18:.6f}")
    
    elif cmd == "balance":
        balance = get_balance()
        print(f"SENATOR balance: {balance / 1e18:.6f}")
    
    else:
        print("Unknown command")
        sys.exit(1)


if __name__ == "__main__":
    main()
