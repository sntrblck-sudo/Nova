/**
 * Nova's Smart Compounding System — Enhanced Decision Engine
 * Makes intelligent CLAWS staking decisions based on:
 * - Onchain pool minimum detection
 * - Gas cost vs. reward comparison
 * - Learned pool acceptance thresholds
 */

import { createPublicClient, http, encodeFunctionData } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { base } from 'viem/chains';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const WORKSPACE = '/home/sntrblck/.openclaw/workspace/cdp-nova';

// Addresses
const NOVA = '0xB743fdbA842379933A3774617786712458659D16';
const SENATOR_POOL = '0x0bb7b6d2334614dee123c4135d7b6fae244962f0';
const CLAWS_POOL = '0x206C97D4Ecf053561Bd2C714335aAef0eC1105e6';
const CLAWS_TOKEN = '0x7ca47B141639B893C6782823C0b219f872056379';
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const UNISWAP_ROUTER = '0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24';
const WETH = '0x4200000000000000000000000000000000000006';

const WALLET = JSON.parse(fs.readFileSync(path.join(WORKSPACE, 'nova-wallet.json'), 'utf8'));
const account = privateKeyToAccount(WALLET.privateKey);
const pub = createPublicClient({ chain: base, transport: http() });
const walletClient = createWalletClient({ account, chain: base, transport: http() });

// ABI fragments
const erc20 = [
  { name: 'balanceOf', type: 'function', inputs: [{ name: 'a', type: 'address' }], outputs: [{ type: 'uint256' }] },
  { name: 'approve', type: 'function', inputs: [{ name: 'spender', type: 'address' }, { name: 'amount', type: 'uint256' }], outputs: [{ type: 'bool' }] },
  { name: 'transfer', type: 'function', inputs: [{ name: 'to', type: 'address' }, { name: 'value', type: 'uint256' }], outputs: [{ type: 'bool' }] }
];
const poolAbi = [
  { name: 'earned', type: 'function', inputs: [{ name: 'account', type: 'address' }], outputs: [{ type: 'uint256' }] },
  { name: 'balanceOf', type: 'function', inputs: [{ name: 'account', type: 'address' }], outputs: [{ type: 'uint256' }] }
];
const routerAbi = [{ name: 'getAmountsOut', type: 'function', inputs: [{ type: 'uint256' }, { type: 'address[]' }], outputs: [{ type: 'uint256[]' }] }];

// ─── State ───────────────────────────────────────────────────────────────────
const STATE_FILE = path.join(WORKSPACE, 'compound_state.json');
function loadState() {
  if (fs.existsSync(STATE_FILE)) return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
  return { learnedPoolMinimum: null, lastStakeAttempt: null, consecutiveRejects: 0 };
}
function saveState(s) { fs.writeFileSync(STATE_FILE, JSON.stringify(s, null, 2)); }

// ─── Logging ─────────────────────────────────────────────────────────────────
function log(msg) {
  const ts = new Date().toISOString().slice(0, 19).replace('T', ' ');
  const line = `[${ts}] ${msg}`;
  console.log(line);
  const logFile = path.join(WORKSPACE, '..', 'memory', 'compound_log.jsonl');
  fs.appendFileSync(logFile, JSON.stringify({ timestamp: new Date().toISOString(), message: msg }) + '\n');
}

// ─── Onchain queries ─────────────────────────────────────────────────────────
async function getClawsBalance() {
  return pub.readContract({ address: CLAWS_TOKEN, abi: erc20, functionName: 'balanceOf', args: [NOVA] });
}

async function getStakedSenator() {
  return pub.readContract({ address: SENATOR_POOL, abi: poolAbi, functionName: 'balanceOf', args: [NOVA] });
}

async function getPendingRewards() {
  return pub.readContract({ address: SENATOR_POOL, abi: poolAbi, functionName: 'earned', args: [NOVA] });
}

async function getGasPrice() { return pub.getGasPrice(); }

async function getClawsValueUsd(clawsWei) {
  // Try to get CLAWS price via WETH pair on Uniswap
  try {
    const amounts = await pub.readContract({
      address: UNISWAP_ROUTER, abi: routerAbi,
      functionName: 'getAmountsOut',
      args: [BigInt(1e18), [CLAWS_TOKEN, WETH]]
    });
    const ethPerClaws = Number(amounts[1]) / 1e18;
    const ethPriceUsd = await getEthPriceUsd();
    return ethPerClaws * ethPriceUsd * (Number(clawsWei) / 1e18);
  } catch { return 0; }
}

async function getEthPriceUsd() {
  // Use a simple estimate or CoinGecko
  try {
    const res = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vsusd');
    const data = await res.json();
    return data.ethereum?.usd || 1800;
  } catch { return 1800; }
}

async function estimateGasCost(gasUnits) {
  const gasPrice = await getGasPrice();
  const ethPrice = await getEthPriceUsd();
  return Number(gasPrice * BigInt(gasUnits)) / 1e18 * ethPrice;
}

// ─── Pool minimum detection ──────────────────────────────────────────────────
async function detectPoolMinimum() {
  const state = loadState();
  
  // Try to stake 1 wei to probe minimum
  const probeAmount = BigInt(1);
  const approveData = encodeFunctionData({ abi: erc20, functionName: 'approve', args: [CLAWS_POOL, probeAmount] });
  
  try {
    const gasPrice = await getGasPrice();
    const tx = await walletClient.sendTransaction({
      to: CLAWS_TOKEN,
      data: approveData,
      value: BigInt(0),
      gasPrice
    });
    await pub.waitForTransactionReceipt({ hash: tx });
    
    // Now try to stake the 1 wei
    const stakeData = encodeFunctionData({
      abi: [{ name: 'stake', type: 'function', inputs: [{ name: 'amount', type: 'uint256' }], outputs: [] }],
      functionName: 'stake',
      args: [probeAmount]
    });
    
    const gasEst = await pub.estimateGas({ to: CLAWS_POOL, data: stakeData, account: NOVA, value: BigInt(0) });
    await walletClient.sendTransaction({ to: CLAWS_POOL, data: stakeData, value: BigInt(0), gasPrice, gas: gasEst + BigInt(10000) });
    
    // If successful, minimum is 1 wei
    state.learnedPoolMinimum = BigInt(1);
    state.consecutiveRejects = 0;
    saveState(state);
    log('Pool minimum detected: 1 wei (no minimum)');
    return BigInt(1);
  } catch (e) {
    const msg = e.message || '';
    if (msg.includes('below')) {
      // Extract minimum from error message if possible
      const match = msg.match(/minimum.*?(\d+)/i) || msg.match(/(\d+).*minimum/i);
      if (match) {
        state.learnedPoolMinimum = BigInt(parseInt(match[1]));
        state.consecutiveRejects++;
      } else {
        state.consecutiveRejects++;
      }
    } else if (msg.includes('ds-math-sub-underflow') || msg.includes('insufficient')) {
      // Could be balance issue — try to learn from the rejection pattern
      state.consecutiveRejects++;
    }
    saveState(state);
    log(`Pool probe failed: ${e.message.slice(0, 100)}`);
    return null;
  }
}

// ─── Core decision logic ─────────────────────────────────────────────────────
async function runSmartCompound() {
  log('=== Smart Compound Cycle Starting ===');
  const state = loadState();
  const ethPrice = await getEthPriceUsd();
  
  // 1. Gather state
  const [clawsBal, staked, pending] = await Promise.all([
    getClawsBalance(),
    getStakedSenator(),
    getPendingRewards()
  ]);
  
  const clawsBalFloat = Number(clawsBal) / 1e18;
  const pendingFloat = Number(pending) / 1e18;
  const stakedFloat = Number(staked) / 1e18;
  const pendingUsd = await getClawsValueUsd(pending);
  const clawsBalUsd = await getClawsValueUsd(clawsBal);
  
  log(`SENATOR staked: ${stakedFloat.toFixed(2)} (${(stakedFloat/1e6).toFixed(2)}M)`);
  log(`CLAWS balance: ${clawsBalFloat.toFixed(4)} (~$${clawsBalUsd.toFixed(4)})`);
  log(`Pending rewards: ${pendingFloat.toFixed(4)} (~$${pendingUsd.toFixed(4)})`);
  
  // 2. Estimate costs
  const claimGasCostUsd = await estimateGasCost(100000); // claim tx
  const stakeGasCostUsd = await estimateGasCost(150000); // stake tx
  const totalGasUsd = claimGasCostUsd + stakeGasCostUsd;
  log(`Estimated gas cost: ~$${totalGasUsd.toFixed(4)} (claim + stake)`);
  
  // 3. Decision: should we claim?
  const NET_CLAIMS_THRESHOLD_USD = 0.10; // minimum $0.10 after gas to justify tx
  const pendingNetUsd = pendingUsd - claimGasCostUsd;
  
  if (pendingNetUsd < NET_CLAIMS_THRESHOLD_USd) {
    log(`SKIP CLAIM: Pending $${pendingUsd.toFixed(4)} - gas $${claimGasCostUsd.toFixed(4)} = net $${pendingNetUsd.toFixed(4)} < threshold $${NET_CLAIMS_THRESHOLD_USD}`);
    log('Decision: rewards too small to justify gas');
  } else {
    log(`DECISION: Claim $${pendingUsd.toFixed(4)} - gas $${claimGasCostUsd.toFixed(4)} = net $${pendingNetUsd.toFixed(4)} >= threshold`);
    // Actually claim
    try {
      const claimData = encodeFunctionData({
        abi: [{ name: 'claim', type: 'function', inputs: [], outputs: [] }],
        functionName: 'claim'
      });
      const gasPrice = await getGasPrice();
      const gasEst = await pub.estimateGas({ to: SENATOR_POOL, data: claimData, account: NOVA, value: BigInt(0) });
      const tx = await walletClient.sendTransaction({ to: SENATOR_POOL, data: claimData, value: BigInt(0), gasPrice, gas: gasEst + BigInt(20000) });
      log(`Claimed! TX: ${tx}`);
      await pub.waitForTransactionReceipt({ hash: tx });
      await new Promise(r => setTimeout(r, 5000)); // wait for balance update
      
      // Get new CLAWS balance
      const newClawsBal = await getClawsBalance();
      const claimedFloat = Number(newClawsBal - clawsBal) / 1e18;
      log(`Received ${claimedFloat.toFixed(4)} CLAWS`);
      
      // Update for staking decision
      const updatedClawsBal = newClawsBal;
      const updatedClawsUsd = await getClawsValueUsd(updatedClawsBal);
      
      // 4. Decision: should we stake?
      // Pool has no meaningful minimum (1 wei) - stake everything
      const stakeAmount = updatedClawsBal;
      const stakeNetUsd = updatedClawsUsd - stakeGasCostUsd;
      
      if (stakeAmount > BigInt(0)) {
        // Approve
        const approveData = encodeFunctionData({ abi: erc20, functionName: 'approve', args: [CLAWS_POOL, stakeAmount] });
        const gasPrice = await getGasPrice();
        const approveTx = await walletClient.sendTransaction({ to: CLAWS_TOKEN, data: approveData, value: BigInt(0), gasPrice });
        await pub.waitForTransactionReceipt({ hash: approveTx });
        log(`Approved ${Number(stakeAmount)/1e18} CLAWS for staking`);
        
        // Stake
        const stakeData = encodeFunctionData({
          abi: [{ name: 'stake', type: 'function', inputs: [{ name: 'amount', type: 'uint256' }], outputs: [] }],
          functionName: 'stake',
          args: [stakeAmount]
        });
        try {
          const gasEst = await pub.estimateGas({ to: CLAWS_POOL, data: stakeData, account: NOVA, value: BigInt(0) });
          const stakeTx = await walletClient.sendTransaction({ to: CLAWS_POOL, data: stakeData, value: BigInt(0), gasPrice, gas: gasEst + BigInt(20000) });
          log(`Staked! TX: ${stakeTx}`);
          state.consecutiveRejects = 0;
        } catch (e) {
          if (e.message.includes('below') || e.message.includes('minimum') || e.message.includes('revert')) {
            log(`POOL REJECTED: ${e.message.slice(0, 120)}`);
            state.consecutiveRejects++;
            log(`Consecutive rejects: ${state.consecutiveRejects}`);
            // The pool has a hidden minimum we need to learn
            // Save the rejection for learning
          } else {
            throw e;
          }
        }
      }
      saveState(state);
    } catch (e) {
      log(`Claim/stake failed: ${e.message.slice(0, 200)}`);
    }
  }
  
  log('=== Compound Cycle Complete ===\n');
}

// ─── CLI ─────────────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
if (args[0] === 'status') {
  (async () => {
    const [claws, staked, pending] = await Promise.all([getClawsBalance(), getStakedSenator(), getPendingRewards()]);
    const ethPrice = await getEthPriceUsd();
    console.log(`SENATOR staked: ${Number(staked)/1e6:.2f}`);
    console.log(`CLAWS balance: ${Number(claws)/1e18:.4f}`);
    console.log(`Pending rewards: ${Number(pending)/1e18:.4f}`);
    const state = loadState();
    console.log(`Pool minimum learned: ${state.learnedPoolMinimum ? Number(state.learnedPoolMinimum)/1e18 : 'unknown'}`);
    console.log(`Consecutive rejects: ${state.consecutiveRejects}`);
  })();
} else if (args[0] === 'probe') {
  detectPoolMinimum().then(m => console.log('Detected minimum:', m));
} else {
  runSmartCompound();
}

export { runSmartCompound, detectPoolMinimum, getClawsBalance, getStakedSenator, getPendingRewards };
