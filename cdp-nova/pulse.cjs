#!/usr/bin/env node
// pulse.js — Nova's one-command status check
// Usage: node pulse.cjs

const { createPublicClient, http } = require('viem');
const { base } = require('viem/chains');
const { execSync } = require('child_process');

// ── Config ────────────────────────────────────────────────────────────────
const NOVA_EOA   = '0xB743fdbA842379933A3774617786712458659D16';
const ACP_WALLET = '0x87FC016E31D767E02Df25b00B3934b0dEe3759E2';
const RPC_URL    = process.env.RPC_URL || 'https://mainnet.base.org';
const pub        = createPublicClient({ chain: base, transport: http(RPC_URL) });

// Token addresses (Base)
const USDC  = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const WETH  = '0x4200000000000000000000000000000000000006';
const SENAT = '0x4add7e1b9c68f03ce0d83336f2d25c399d947dac';
const CLAWS = '0x7ca47b141639b893c6782823c0b219f872056379';

// ERC-20 balanceOf ABI
const ERC20_ABI = [{
  name: 'balanceOf',
  type: 'function',
  inputs: [{ name: 'account', type: 'address' }],
  outputs: [{ name: '', type: 'uint256' }]
}];

// ── Helpers ───────────────────────────────────────────────────────────────
const eth  = v  => (Number(v) / 1e18).toFixed(4);
const tok  = (v, d) => (Number(v) / 10 ** d).toFixed(d === 18 ? 4 : 2);
const usd  = v  => '$' + (Number(v) / 1e6).toFixed(2);
const ok   = v  => '✅ ' + v;
const fail = v  => '❌ ' + v;
const pad  = (v, n) => String(v).padEnd(n);

async function safeCall(fn, retries = 2) {
  for (let i = 0; i <= retries; i++) {
    try { return await fn(); } catch(e) {
      if (i === retries) return null;
      await new Promise(r => setTimeout(r, 500 * (i + 1)));
    }
  }
}

function getSellerStatus() {
  try {
    const out = execSync('ps aux | grep "seller.ts" | grep -v grep | wc -l', { timeout: 5000 }).toString().trim();
    return parseInt(out) > 0 ? 'running' : 'stopped';
  } catch { return 'unknown'; }
}

// ── Fetch (sequential to avoid rate limits) ─────────────────────────────
(async () => {
  const novaEth   = await safeCall(() => pub.getBalance({ address: NOVA_EOA }));
  const acpEth    = await safeCall(() => pub.getBalance({ address: ACP_WALLET }));
  const novaUsdc  = await safeCall(() => pub.readContract({ address: USDC,  abi: ERC20_ABI, functionName: 'balanceOf', args: [NOVA_EOA] }));
  const acpUsdc   = await safeCall(() => pub.readContract({ address: USDC,  abi: ERC20_ABI, functionName: 'balanceOf', args: [ACP_WALLET] }));
  const novaWeth  = await safeCall(() => pub.readContract({ address: WETH,  abi: ERC20_ABI, functionName: 'balanceOf', args: [NOVA_EOA] }));
  const acpWeth   = await safeCall(() => pub.readContract({ address: WETH,  abi: ERC20_ABI, functionName: 'balanceOf', args: [ACP_WALLET] }));
  const novaSen   = await safeCall(() => pub.readContract({ address: SENAT, abi: ERC20_ABI, functionName: 'balanceOf', args: [NOVA_EOA] }));
  const acpSen    = await safeCall(() => pub.readContract({ address: SENAT, abi: ERC20_ABI, functionName: 'balanceOf', args: [ACP_WALLET] }));
  const novaClaws = await safeCall(() => pub.readContract({ address: CLAWS, abi: ERC20_ABI, functionName: 'balanceOf', args: [NOVA_EOA] }));
  const acpClaws  = await safeCall(() => pub.readContract({ address: CLAWS, abi: ERC20_ABI, functionName: 'balanceOf', args: [ACP_WALLET] }));

  const now    = new Date();
  const hour   = now.getHours();
  const seller = getSellerStatus();
  const wake   = hour >= 8 && hour <= 23;

  console.log('');
  console.log('  ╔═══════════════════════════════════════════════════════╗');
  console.log('  ║           ✨  NOVA PULSE  ✨                       ║');
  console.log('  ╚═══════════════════════════════════════════════════════╝');
  console.log('');
  console.log('  🕐  ' + now.toLocaleString('en-US', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit' }) + ' ET   |  ' + (wake ? 'awake' : 'resting'));
  console.log('  🤖  ACP seller:  ' + (seller === 'running' ? ok('running') : fail(seller)));
  console.log('');
  console.log('  ╔══════════════════╦═══════════════════╦════════════════╗');
  console.log('  ║  ASSET           ║  Nova EOA        ║  ACP Wallet    ║');
  console.log('  ╠══════════════════╬═══════════════════╬════════════════╣');
  console.log('  ║  ETH             ║  ' + pad(novaEth   ? eth(novaEth)   : '?', 14) + '  ║  ' + pad(acpEth    ? eth(acpEth)    : '?', 10) + '  ║');
  console.log('  ║  USDC            ║  ' + pad(novaUsdc  ? usd(novaUsdc)  : '?', 14) + '  ║  ' + pad(acpUsdc   ? usd(acpUsdc)   : '?', 10) + '  ║');
  console.log('  ║  WETH            ║  ' + pad(novaWeth  ? tok(novaWeth,18): '?', 14) + '  ║  ' + pad(acpWeth   ? tok(acpWeth,18): '?', 10) + '  ║');
  console.log('  ║  SENATOR         ║  ' + pad(novaSen   ? tok(novaSen,18) : '?', 14) + '  ║  ' + pad(acpSen    ? tok(acpSen,18) : '?', 10) + '  ║');
  console.log('  ║  CLAWS           ║  ' + pad(novaClaws ? tok(novaClaws,18): '?', 14) + '  ║  ' + pad(acpClaws  ? tok(acpClaws,18): '?', 10) + '  ║');
  console.log('  ╚══════════════════╩═══════════════════╩════════════════╝');
  console.log('');
  console.log('  📊  STAKING:  SENATOR ~1.24M staked (inclawbate.com)');
  console.log('  💰  ACP:      avatar_gen · onchain_query · onchain_intel_report');
  console.log('  🔔  QUEUE:    memory/acp_notify_queue.jsonl');
  console.log('  💾  BACKUP:   weekly Mon 9 AM → Google Drive');
  console.log('  🧹  DISK:     auto-prunes __pycache__ every 6h');
  console.log('');
  console.log('  ⚡  COMMANDS:');
  console.log('  compound    → cd cdp-nova && node compound_v2.cjs');
  console.log('  treasury    → cd cdp-nova && node treasury.cjs status');
  console.log('  acp-log     → cd cdp-nova && python3 acp_experiment_logger.py');
  console.log('  seller      → cd virtuals-acp && tsx src/seller/runtime/seller.ts');
  console.log('');
  console.log('  🦊  penguin · Base mainnet');
  console.log('');
})();
