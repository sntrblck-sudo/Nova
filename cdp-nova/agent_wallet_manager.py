#!/usr/bin/env python3
"""
Nova's Agent Wallet Manager
Monitors and tops off the managed Virtuals agent wallet.

Target agent:  0x87FC016E31D767E02Df25b00B3934b0dEe3759E2
Funding wallet: Nova's EOA  0xB743fdbA842379933A3774617786712458659D16
"""
import os
import sys
import json
import time
import datetime
import subprocess
from pathlib import Path

# Paths
CDP_NOVA = Path("/home/sntrblck/.openclaw/workspace/cdp-nova")
AGENT_WALLET = "0x87FC016E31D767E02Df25b00B3934b0dEe3759E2"
NOVA_WALLET = "0xB743fdbA842379933A3774617786712458659D16"
WALLET_KEY_FILE = CDP_NOVA / "nova-wallet.json"
LOG_FILE = CDP_NOVA / "wallet_manager.log"

THRESHOLD_ETH = 0.0003      # below this → top up
TOPUP_ETH = 0.0005          # how much to send
RESERVE_ETH = 0.0002        # keep this much in Nova's wallet minimum

def log(msg):
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def get_balance(address):
    """Get ETH balance via viem Node.js script."""
    script = f"""
const {{ createPublicClient, http }} = require('viem');
const {{ base }} = require('viem/chains');
const pub = createPublicClient({{ chain: base, transport: http() }});
pub.getBalance({{ address: '{address}' }}).then(b => {{
  console.log(Number(b) / 1e18);
  process.exit(0);
}}).catch(e => {{ console.error(e.message); process.exit(1); }});
"""
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"Balance check failed: {result.stderr.strip()}")
    return float(result.stdout.strip())

def send_eth(to_address, amount_eth):
    """Send ETH from Nova's wallet to target via viem."""
    script = f"""
const {{ createWalletClient, custom, http }} = require('viem');
const {{ base }} = require('viem/chains');
const {{ privateKeyToAccount }} = require('viem/accounts');
const fs = require('fs');
const key = JSON.parse(fs.readFileSync('{WALLET_KEY_FILE}', 'utf8'));
const account = privateKeyToAccount(key.privateKey);
const wallet = createWalletClient({{
  account,
  chain: base,
  transport: http()
}});
wallet.sendTransaction({{
  to: '{to_address}',
  value: BigInt(Math.round({amount_eth} * 1e18))
}}).then(tx => {{
  console.log(tx);
  process.exit(0);
}}).catch(e => {{ console.error(e.message); process.exit(1); }});
"""
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"Send failed: {result.stderr.strip()}")
    return result.stdout.strip()

def get_nova_balance():
    return get_balance(NOVA_WALLET)

def get_agent_balance():
    return get_balance(AGENT_WALLET)

def main():
    log("=== Nova Agent Wallet Manager Run ===")
    
    try:
        agent_bal = get_agent_balance()
        nova_bal = get_nova_balance()
        log(f"Agent balance: {agent_bal:.6f} ETH")
        log(f"Nova balance:  {nova_bal:.6f} ETH")
        
        # Check reserve
        if nova_bal < RESERVE_ETH + TOPUP_ETH:
            log(f"NOVA_LOW_BALANCE: Nova has {nova_bal:.6f} ETH — below reserve + topup threshold. Skipping topup.")
            sys.exit(0)
        
        # Check if top-up needed
        if agent_bal < THRESHOLD_ETH:
            log(f"Top-up needed (agent {agent_bal:.6f} < {THRESHOLD_ETH})")
            tx_hash = send_eth(AGENT_WALLET, TOPUP_ETH)
            log(f"TOPUP_SUCCESS: sent {TOPUP_ETH} ETH → {AGENT_WALLET} | tx: {tx_hash}")
            
            # Log to action trail
            log_to_audit = f"""cd {CDP_NOVA} && node action_logger.cjs add-action --category economic --description "Top-up of {TOPUP_ETH} ETH to managed agent wallet {AGENT_WALLET[:8]}... | tx: {tx_hash}" --outcome success 2>/dev/null"""
            subprocess.run(log_to_audit, shell=True)
        else:
            log(f"No top-up needed (agent balance {agent_bal:.6f} ETH >= {THRESHOLD_ETH})")
        
        nova_bal_after = get_nova_balance()
        agent_bal_after = get_agent_balance()
        log(f"Post-topup — Agent: {agent_bal_after:.6f} ETH | Nova: {nova_bal_after:.6f} ETH")
        log("=== Run Complete ===")
        
    except Exception as e:
        log(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
