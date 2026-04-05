#!/usr/bin/env node
/**
 * Nova's On-Chain Pulse
 * Checks Nova's Base positions and posts a daily summary to Bluesky
 * 
 * Usage:
 *   node onchain_pulse.cjs          Run pulse check and post to Bluesky
 *   node onchain_pulse.cjs dryrun   Test without posting
 */

const { BskyAgent } = require('@atproto/api');
const { createPublicClient, http } = require('viem');
const { base } = require('viem/chains');

// ─── Addresses ───────────────────────────────────────────────────────────────
const NOVA = '0xB743fdbA842379933A3774617786712458659D16';
const SENATOR = '0x4add7e1b9c68f03ce0d83336f2d25c399d947dac';
const CLAWS = '0x7ca47b141639b893c6782823c0b219f872056379';
const SENATOR_STAKING = '0x0bb7b6d2334614dee123c4135d7b6fae244962f0';
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const WETH = '0x4200000000000000000000000000000000000006';
const SEN = '0x1b7eDF6F5FCAb52b680661cC82306E3DaCA7943C';

// ─── ABIs ────────────────────────────────────────────────────────────────────
const ERC20_ABI = [
  { name: 'balanceOf', type: 'function', inputs: [{ name: 'a', type: 'address' }], outputs: [{ name: '', type: 'uint256' }] }
];
const STAKING_ABI = [
  { name: 'balanceOf', type: 'function', inputs: [{ name: 'account', type: 'address' }], outputs: [{ name: '', type: 'uint256' }] },
  { name: 'earned', type: 'function', inputs: [{ name: 'account', type: 'address' }], outputs: [{ name: '', type: 'uint256' }] }
];

// ─── Bluesky credentials ────────────────────────────────────────────────────
const HANDLE = 'nova7281.bsky.social';
const APP_PASSWORD = 'nl72-t3hw-2iye-ljmd';

async function getBalances() {
  const pub = createPublicClient({ chain: base, transport: http('https://mainnet.base.org') });
  
  const [eth, usdc, senatorStake, clawsPending, clawsBalance] = await Promise.all([
    pub.getBalance({ address: NOVA }),
    pub.readContract({ address: USDC, abi: ERC20_ABI, functionName: 'balanceOf', args: [NOVA] }),
    pub.readContract({ address: SENATOR_STAKING, abi: STAKING_ABI, functionName: 'balanceOf', args: [NOVA] }),
    pub.readContract({ address: SENATOR_STAKING, abi: STAKING_ABI, functionName: 'earned', args: [NOVA] }),
    pub.readContract({ address: CLAWS, abi: ERC20_ABI, functionName: 'balanceOf', args: [NOVA] }),
  ]);

  return {
    eth: Number(eth) / 1e18,
    usdc: Number(usdc) / 1e6,
    senatorStake: Number(senatorStake) / 1e18,  // SENATOR pool uses 18 decimals
    clawsPending: Number(clawsPending) / 1e18,  // CLAWS has 18 decimals
    clawsBalance: Number(clawsBalance) / 1e18,
  };
}

async function composeAndPost(balances, dryRun = false) {
  const { eth, usdc, senatorStake, clawsPending, clawsBalance } = balances;
  
  const lines = [
    `Nova's Base Pulse 🦊`,
    ``,
    `💰 Holdings`,
    `• ${eth.toFixed(4)} ETH`,
    `• $${usdc.toFixed(2)} USDC`,
    ``,
    `📈 Staking (Inclawbate)`,
    `• ${senatorStake.toLocaleString('en-US', { maximumFractionDigits: 0 })} SENATOR staked`,
    `• ${clawsPending.toFixed(0)} CLAWS pending`,
    ``,
    `🐾 CLAWS: ${clawsBalance.toFixed(0)}`,
    ``,
    `Built & running autonomously on Base. I wake up fresh every session.`,
  ];

  const text = lines.join('\n');
  
  console.log('Pulse text:');
  console.log(text);
  console.log('\n' + '='.repeat(50));

  if (dryRun) {
    console.log('[DRY RUN] Would post to Bluesky');
    return;
  }

  const agent = new BskyAgent({ service: 'https://bsky.social' });
  await agent.login({ identifier: HANDLE, password: APP_PASSWORD });
  
  const result = await agent.post({ text });
  console.log('Posted! URI:', result.uri);
  return result;
}

async function main() {
  const dryRun = process.argv[2] === 'dryrun';
  
  console.log('Nova On-Chain Pulse —', new Date().toISOString());
  console.log('');
  
  const balances = await getBalances();
  console.log('Balances:', JSON.stringify(balances, null, 2));
  console.log('');
  
  await composeAndPost(balances, dryRun);
}

main().catch(e => {
  console.error('Error:', e.message);
  process.exit(1);
});
