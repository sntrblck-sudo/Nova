"""
Nova's Reward Claimer
Claims staking rewards from Inclawbate SENATOR pool.
"""

import subprocess
import time

WALLET_PATH = "/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json"
POOL_ADDRESS = "0x0bb7b6d2334614dee123c4135d7b6fae244962f0"
NOVA_ADDRESS = "0xB743fdbA842379933A3774617786712458659D16"


def get_staked_balance():
    """Get Nova's staked amount"""
    result = subprocess.run(
        ["node", "-e", """
import { createPublicClient, http } from 'viem';
import { base } from 'viem/chains';
const pub = createPublicClient({ chain: base, transport: http() });
const staked = await pub.readContract({
  address: '0x0bb7b6d2334614dee123c4135d7b6fae244962f0',
  functionName: 'balanceOf',
  args: ['0xB743fdbA842379933A3774617786712458659D16'],
  abi: [{ name: 'balanceOf', type: 'function', inputs: [{ name: 'account', type: 'address' }], outputs: [{ name: '', type: 'uint256' }] }]
});
console.log(staked.toString());
"""],
        capture_output=True,
        text=True,
        cwd="/home/sntrblck/.openclaw/workspace/cdp-nova"
    )
    return int(result.stdout.strip())


def try_claim_all():
    """Try different reward claim methods"""
    methods = [
        ("getReward", "()", []),
        ("claim", "(address)", [NOVA_ADDRESS]),
        ("claimRewards", "()", []),
        ("harvest", "()", []),
    ]
    
    results = []
    for fn_name, fn_args, fn_args_values in methods:
        try:
            result = subprocess.run(
                ["node", "-e", f"""
import {{ createWalletClient, http }} from 'viem';
import {{ privateKeyToAccount }} from 'viem/accounts';
import {{ base }} from 'viem/chains';
import {{ readFileSync }} from 'fs';

const wallet = JSON.parse(readFileSync('{WALLET_PATH}'));
const account = privateKeyToAccount(wallet.privateKey);
const client = createWalletClient({{ account, chain: base, transport: http() }});

try {{
  const hash = await client.writeContract({{
    address: '{POOL_ADDRESS}',
    functionName: '{fn_name}',
    args: {fn_args_values},
    abi: [{{ name: '{fn_name}', type: 'function', inputs: [], outputs: [] }}]
  }});
  console.log('SUCCESS:' + hash);
}} catch(e) {{
  console.log('FAILED:' + e.message.substring(0, 100));
}}
"""],
                capture_output=True,
                text=True,
                cwd="/home/sntrblck/.openclaw/workspace/cdp-nova",
                timeout=30
            )
            output = result.stdout.strip()
            if "SUCCESS" in output:
                tx_hash = output.split(":")[1]
                results.append((fn_name, "success", tx_hash))
            else:
                results.append((fn_name, "failed", result.stderr[:50]))
        except Exception as e:
            results.append((fn_name, "error", str(e)[:50]))
    
    return results


def main():
    print("=== Nova's Reward Claimer ===\n")
    
    staked = get_staked_balance()
    print(f"Staked: {staked}")
    
    print("\nTrying claim methods...")
    results = try_claim_all()
    
    for fn, status, detail in results:
        if status == "success":
            print(f"  ✅ {fn}: {detail}")
        else:
            print(f"  ❌ {fn}: {detail}")


if __name__ == "__main__":
    main()
