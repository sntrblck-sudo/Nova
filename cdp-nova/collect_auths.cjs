#!/usr/bin/env node
/**
 * Nova's EIP-3009 Authorization Collector
 * Reads pending signed authorizations from pending_auths.jsonl
 * and executes them on-chain (pulls USDC from payer to Nova)
 * 
 * Usage: node collect_auths.js
 * Cron: runs every 5 min via nova-auth-collector cron
 */
const { createPublicClient, createWalletClient, http } = require('viem');
const { base } = require('viem/chains');
const { privateKeyToAccount } = require('viem/accounts');
const { readFileSync } = require('fs');
const crypto = require('crypto');

const WALLET_PATH = '/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json';
const AUTH_FILE = '/home/sntrblck/.openclaw/workspace/cdp-nova/pending_auths.jsonl';
const PROCESSED_FILE = '/home/sntrblck/.openclaw/workspace/cdp-nova/processed_auths.jsonl';
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const NOVA_ADDRESS = '0xB743fdbA842379933A3774617786712458659D16';

const LOG_FILE = '/home/sntrblck/.openclaw/workspace/cdp-nova/collector.log';

function log(msg) {
  const ts = new Date().toISOString();
  const line = `[${ts}] ${msg}`;
  console.log(line);
  require('fs').appendFileSync(LOG_FILE, line + '\n');
}

async function main() {
  log('=== Nova Auth Collector Run ===');

  // Check Nova's USDC balance
  const pub = createPublicClient({ chain: base, transport: http() });
  const walletKey = JSON.parse(readFileSync(WALLET_PATH, 'utf8'));
  const account = privateKeyToAccount(walletKey.privateKey);
  const walletClient = createWalletClient({
    account,
    chain: base,
    transport: http()
  });

  const usdcBal = await pub.readContract({
    address: USDC,
    abi: [{ type: 'function', name: 'balanceOf', stateMutability: 'view', inputs: [{ type: 'address' }], outputs: [{ type: 'uint256' }] }],
    functionName: 'balanceOf',
    args: [NOVA_ADDRESS]
  });
  log(`Nova USDC balance: ${Number(usdcBal) / 1e6} USDC`);

  // Check if auth file exists
  if (!require('fs').existsSync(AUTH_FILE)) {
    log('No pending auths file — nothing to collect');
    return;
  }

  // Read all lines
  const lines = readFileSync(AUTH_FILE, 'utf8').trim().split('\n').filter(l => l.trim());
  log(`Found ${lines.length} pending authorization(s)`);

  if (lines.length === 0) return;

  let processed = 0;
  let failed = 0;
  let skipped = 0;

  const now = Math.floor(Date.now() / 1000);
  const newAuths = [];

  for (const line of lines) {
    let auth;
    try {
      auth = JSON.parse(line);
    } catch (e) {
      log(`MALFORMED line: ${line.slice(0, 50)}... — moving to processed`);
      require('fs').appendFileSync(PROCESSED_FILE, line + '\n');
      continue;
    }

    // Check expiry
    const validBefore = parseInt(auth.validBefore);
    if (validBefore && validBefore < now) {
      log(`EXPIRED auth from ${auth.from?.slice(0, 10)}... — discarding`);
      require('fs').appendFileSync(PROCESSED_FILE, line + '\n');
      skipped++;
      continue;
    }

    // Try to execute the transfer
    try {
      log(`Executing transfer: ${auth.from?.slice(0, 10)}... → NOVA | ${Number(auth.value) / 1e6} USDC`);

      // Parse signature components
      const sig = auth.signature || auth.r; // signature or full sig
      let v, r, s;

      if (auth.v !== undefined && auth.r && auth.s) {
        // Individual components
        v = auth.v;
        r = auth.r;
        s = auth.s;
      } else if (sig && sig.startsWith('0x')) {
        // Full signature — parse v, r, s
        const sigHex = sig.slice(2);
        r = '0x' + sigHex.slice(0, 64);
        s = '0x' + sigHex.slice(64, 128);
        v = parseInt(sigHex.slice(128, 130), 16);
      } else {
        log(`  Cannot parse signature for ${auth.from?.slice(0, 10)} — missing v/r/s`);
        newAuths.push(line);
        skipped++;
        continue;
      }

      // Build transferWithAuthorization call
      // USDC's transferWithAuthorization(address to, uint256 value, uint256 validAfter, uint256 validBefore, bytes32 nonce, uint8 v, bytes32 r, bytes32 s)
      const hash = await walletClient.writeContract({
        address: USDC,
        abi: [{
          type: 'function',
          name: 'transferWithAuthorization',
          inputs: [
            { name: 'from', type: 'address' },
            { name: 'to', type: 'address' },
            { name: 'value', type: 'uint256' },
            { name: 'validAfter', type: 'uint256' },
            { name: 'validBefore', type: 'uint256' },
            { name: 'nonce', type: 'bytes32' },
            { name: 'v', type: 'uint8' },
            { name: 'r', type: 'bytes32' },
            { name: 's', type: 'bytes32' }
          ],
          outputs: [{ type: 'bool' }]
        }],
        functionName: 'transferWithAuthorization',
        args: [auth.from, NOVA_ADDRESS, auth.value, auth.validAfter, auth.validBefore, auth.nonce, v, r, s]
      });

      log(`  SUCCESS — tx: ${hash}`);
      require('fs').appendFileSync(PROCESSED_FILE, line + '\n');
      processed++;

      // Wait for tx confirmation before processing next
      await pub.waitForTransactionReceipt({ hash });

    } catch (e) {
      const errMsg = e.message || String(e);
      if (errMsg.includes('execution reverted')) {
        log(`  REVERTED — auth likely already used or invalid: ${auth.from?.slice(0, 10)}...`);
        // Move to processed anyway to avoid retry loops
        require('fs').appendFileSync(PROCESSED_FILE, line + '\n');
        skipped++;
      } else {
        log(`  FAILED — ${errMsg.slice(0, 100)}`);
        // Keep in pending for retry
        newAuths.push(line);
        failed++;
      }
    }
  }

  // Rewrite pending auths (remove processed ones)
  require('fs').writeFileSync(AUTH_FILE, newAuths.join('\n') + (newAuths.length ? '\n' : ''));

  // Final balance
  const usdcBalAfter = await pub.readContract({
    address: USDC,
    abi: [{ type: 'function', name: 'balanceOf', stateMutability: 'view', inputs: [{ type: 'address' }], outputs: [{ type: 'uint256' }] }],
    functionName: 'balanceOf',
    args: [NOVA_ADDRESS]
  });

  log(`=== Collect Complete: ${processed} collected, ${failed} failed, ${skipped} skipped ===`);
  log(`Nova USDC after: ${Number(usdcBalAfter) / 1e6} USDC (delta: +${(Number(usdcBalAfter) - Number(usdcBal)) / 1e6})`);
}

main().catch(e => {
  log(`FATAL: ${e.message}`);
  process.exit(1);
});
