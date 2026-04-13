/**
 * Nova's Smart Compounding System v2
 * Makes intelligent CLAWS staking decisions based on:
 * - Gas cost vs reward economics (never lose money on a tx)
 * - Learned pool minimum detection
 * - Consecutive reject tracking (don't spam failing transactions)
 * - Respecting DEX liquidity reality
 */

const { createPublicClient, http, createWalletClient, encodeFunctionData } = require('viem');
const { privateKeyToAccount } = require('viem/accounts');
const { base } = require('viem/chains');
const fs = require('fs');
const path = require('path');

const WORKSPACE = '/home/sntrblck/.openclaw/workspace/cdp-nova';
const MEMORY_DIR = '/home/sntrblck/.openclaw/workspace/memory';

// ─── Addresses ───────────────────────────────────────────────────────────────
const NOVA = '0xB743fdbA842379933A3774617786712458659D16';
const SENATOR_POOL = '0x0bb7b6d2334614dee123c4135d7b6fae244962f0';
const CLAWS_POOL = '0x206C97D4Ecf053561Bd2C714335aAef0eC1105e6';
const CLAWS_TOKEN = '0x7ca47B141639B893C6782823C0b219f872056379';
const WETH = '0x4200000000000000000000000000000000000006';
const UNISWAP_ROUTER = '0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24';

// ─── Config ──────────────────────────────────────────────────────────────────
const WALLET = JSON.parse(fs.readFileSync(path.join(WORKSPACE, 'nova-wallet.json'), 'utf8'));
const account = privateKeyToAccount(WALLET.privateKey);
const pub = createPublicClient({ chain: base, transport: http('https://mainnet.base.org') });
const walletClient = createWalletClient({ account, chain: base, transport: http() });

// Decision thresholds
const STAKE_THRESHOLD_CLAWS = 150000; // Only attempt stake if >= 150K CLAWS (learned from prior rejections)
const MAX_CONSECUTIVE_REJECTS = 3;    // Stop attempting if rejected 3x — pool minimum is higher than our balance
const MIN_REWARDS_CLAIMS = 1000;       // Only claim if >= 1000 CLAWS pending (~$0.0004 floor at current thin liquidity)
const GAS_GWEI_MAX = 50;               // Don't run if gas > 50 gwei (congestion safeguard)

// ─── ABIs ───────────────────────────────────────────────────────────────────
const erc20Abi = [
  { name: 'balanceOf', type: 'function', inputs: [{ name: 'account', type: 'address' }], outputs: [{ name: '', type: 'uint256' }] },
  { name: 'approve', type: 'function', inputs: [{ name: 'spender', type: 'address' }, { name: 'amount', type: 'uint256' }], outputs: [{ name: 'bool' }] }
];
const poolAbi = [
  { name: 'earned', type: 'function', inputs: [{ name: 'account', type: 'address' }], outputs: [{ name: '', type: 'uint256' }] },
  { name: 'balanceOf', type: 'function', inputs: [{ name: 'account', type: 'address' }], outputs: [{ name: '', type: 'uint256' }] },
  { name: 'claim', type: 'function', inputs: [], outputs: [] },
  { name: 'stake', type: 'function', inputs: [{ name: 'amount', type: 'uint256' }], outputs: [] }
];
const routerAbi = [
  { name: 'getAmountsOut', type: 'function', inputs: [{ type: 'uint256' }, { type: 'address[]' }], outputs: [{ type: 'uint256[]' }] }
];

// ─── State ─────────────────────────────────────────────────────────────────
const STATE_FILE = path.join(MEMORY_DIR, 'compound_v2_state.json');
function loadState() {
  if (fs.existsSync(STATE_FILE)) return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
  return { consecutiveRejects: 0, lastStakeAmount: null, lastClaimAmount: null, poolMinClaws: null, lastRun: null };
}
function saveState(s) { fs.writeFileSync(STATE_FILE, JSON.stringify(s, null, 2)); }

// ─── Logging ────────────────────────────────────────────────────────────────
function log(msg) {
  const ts = new Date().toISOString().slice(0, 19).replace('T', ' ');
  const line = `[${ts}] ${msg}`;
  console.log(line);
  const logFile = path.join(MEMORY_DIR, 'compound_log.jsonl');
  fs.appendFileSync(logFile, JSON.stringify({ timestamp: new Date().toISOString(), source: 'compound_v2', message: msg }) + '\n');
}

// ─── Onchain queries ────────────────────────────────────────────────────────
async function getClawsBalance(addr = NOVA) {
  return pub.readContract({ address: CLAWS_TOKEN, abi: erc20Abi, functionName: 'balanceOf', args: [addr] });
}
async function getStakedSenator(addr = NOVA) {
  return pub.readContract({ address: SENATOR_POOL, abi: poolAbi, functionName: 'balanceOf', args: [addr] });
}
async function getPendingRewards(addr = NOVA) {
  return pub.readContract({ address: SENATOR_POOL, abi: poolAbi, functionName: 'earned', args: [addr] });
}
async function getEthBalance(addr = NOVA) {
  return pub.getBalance({ address: addr });
}
async function getGasPrice() { return pub.getGasPrice(); }

// ─── Pricing ────────────────────────────────────────────────────────────────
async function getEthPriceUsd() {
  try {
    const res = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vsusd=1', { signal: AbortSignal.timeout(5000) });
    const data = await res.json();
    return data.ethereum?.usd || 1800;
  } catch { return 1800; }
}

async function getClawsPriceEth() {
  // Try Uniswap V3 CLAWS/WETH pool
  try {
    const amounts = await pub.readContract({
      address: UNISWAP_ROUTER, abi: routerAbi, functionName: 'getAmountsOut',
      args: [BigInt(1e18), [CLAWS_TOKEN, WETH]]
    });
    return Number(amounts[1]) / 1e18;
  } catch { return null; }
}

// ─── TX helpers ─────────────────────────────────────────────────────────────
async function submitTx(to, data, value = BigInt(0), gasLimit) {
  const gasPrice = await getGasPrice();
  const gasEst = gasLimit || await pub.estimateGas({ to, data, value, account: NOVA }).catch(() => BigInt(200000));
  const tx = await walletClient.sendTransaction({ to, data, value, gasPrice, gas: gasEst + BigInt(20000) });
  log(`  TX sent: ${tx}`);
  return tx;
}

async function waitForReceipt(hash) {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await pub.getTransactionReceipt({ hash });
      if (r) return r;
    } catch {}
    await new Promise(r => setTimeout(r, 2000));
  }
  throw new Error('Receipt timeout after 120s');
}

async function waitForBalanceUpdate(addr, token, initialBalance) {
  for (let i = 0; i < 15; i++) {
    await new Promise(r => setTimeout(r, 2000));
    const newBal = await getClawsBalance(addr);
    if (newBal !== initialBalance) return newBal;
  }
  return null;
}

// ─── Core ───────────────────────────────────────────────────────────────────
async function runSmartCompound() {
  log('=== Smart Compound Cycle ===');
  const state = loadState();
  const ethBal = await getEthBalance();
  const ethBalFloat = Number(ethBal) / 1e18;
  const ethPrice = await getEthPriceUsd();
  const gasPrice = await getGasPrice();
  const gasPriceGwei = Number(gasPrice) / 1e9;

  log(`ETH: ${ethBalFloat.toFixed(6)} (~$${(ethBalFloat * ethPrice).toFixed(2)})`);
  log(`Gas: ${gasPriceGwei.toFixed(4)} gwei`);

  // Safeguard: don't run if gas is unreasonably high
  if (gasPriceGwei > GAS_GWEI_MAX) {
    log(`Gas too high (${gasPriceGwei.toFixed(2)} gwei). Skipping cycle.`);
    return;
  }

  // Safeguard: need ETH for gas
  if (ethBalFloat < 0.001) {
    log('Insufficient ETH for gas. Aborting.');
    return;
  }

  // Get staking state
  const [staked, pending, clawsBal] = await Promise.all([
    getStakedSenator(), getPendingRewards(), getClawsBalance()
  ]);
  const stakedFloat = Number(staked) / 1e6;
  const pendingFloat = Number(pending) / 1e18;
  const clawsFloat = Number(clawsBal) / 1e18;

  log(`SENATOR staked: ${stakedFloat.toFixed(2)}`);
  log(`CLAWS balance: ${clawsFloat.toFixed(4)}`);
  log(`Pending rewards: ${pendingFloat.toFixed(4)} CLAWS`);
  log(`Consecutive rejects: ${state.consecutiveRejects}`);

  // ─── Decision: Claim ────────────────────────────────────────────────────
  const clawsPriceEth = await getClawsPriceEth();
  let pendingUsd = 0;
  if (clawsPriceEth && clawsPriceEth > 0) {
    pendingUsd = pendingFloat * clawsPriceEth * ethPrice;
    log(`CLAWS price: ${clawsPriceEth.toExponential(2)} ETH (~$${(clawsPriceEth * ethPrice).toFixed(6)}/CLAWS)`);
    log(`Pending USD: ~$${pendingUsd.toFixed(6)}`);
  } else {
    log('CLAWS/ETH pool empty — cannot estimate USD value. Assuming tiny.');
    pendingUsd = pendingFloat * ethPrice * 0.00001; // extreme floor estimate
  }

  // Gas cost estimate
  const claimGasUsd = (Number(gasPrice) * 100000 / 1e18) * ethPrice;
  const netPendingUsd = pendingUsd - claimGasUsd;
  log(`Net pending after gas: ~$${netPendingUsd.toFixed(6)}`);

  if (pendingFloat >= MIN_REWARDS_CLAIMS && netPendingUsd > 0) {
    log(`DECISION: Claim ${pendingFloat.toFixed(4)} CLAWS (~$ ${pendingUsd.toFixed(6)})`);
    try {
      const data = encodeFunctionData({ abi: poolAbi, functionName: 'claim', args: [] });
      const tx = await submitTx(SENATOR_POOL, data, BigInt(0), BigInt(100000));
      const receipt = await waitForReceipt(tx);
      if (receipt.status === '0x1') {
        log('Claim confirmed!');
        state.lastClaimAmount = pendingFloat;
        // Wait for balance to update
        const newClaws = await waitForBalanceUpdate(NOVA, CLAWS_TOKEN, clawsBal);
        if (newClaws) {
          const delta = Number(newClaws - clawsBal) / 1e18;
          log(`CLAWS delta: ${delta.toFixed(4)}`);
        }
      } else {
        log('Claim FAILED (reverted)');
      }
    } catch(e) {
      log(`Claim error: ${e.message.slice(0, 150)}`);
    }
  } else if (pendingFloat > 0) {
    log(`SKIP CLAIM: ${pendingFloat.toFixed(4)} CLAWS below ${MIN_REWARDS_CLAIMS} min threshold, or net negative`);
  } else {
    log('No pending rewards.');
  }

  // ─── Decision: Stake ────────────────────────────────────────────────────
  const currentClawsBal = await getClawsBalance();
  const currentClawsFloat = Number(currentClawsBal) / 1e18;

  if (currentClawsFloat < 0.0001) {
    log('No CLAWS to stake.');
  } else if (state.consecutiveRejects >= MAX_CONSECUTIVE_REJECTS) {
    log(`SKIP STAKE: ${state.consecutiveRejects} consecutive rejects. Pool minimum appears above our balance (~${currentClawsFloat.toFixed(0)} CLAWS). Will try again when balance grows.`);
  } else if (currentClawsFloat < STAKE_THRESHOLD_CLAWS) {
    const deficit = STAKE_THRESHOLD_CLAWS - currentClawsFloat;
    log(`SKIP STAKE: ${currentClawsFloat.toFixed(2)} CLAWS < ${STAKE_THRESHOLD_CLAWS} threshold. Accumulate ~${deficit.toFixed(0)} more CLAWS to attempt.`);
  } else {
    log(`DECISION: Staking ${currentClawsFloat.toFixed(2)} CLAWS`);
    try {
      // Approve
      const approveData = encodeFunctionData({ abi: erc20Abi, functionName: 'approve', args: [CLAWS_POOL, currentClawsBal] });
      const approveTx = await submitTx(CLAWS_TOKEN, approveData, BigInt(0), BigInt(50000));
      const approveReceipt = await waitForReceipt(approveTx);
      log(`Approval ${approveReceipt.status === '0x1' ? 'confirmed' : 'FAILED'}`);

      // Stake
      const stakeData = encodeFunctionData({ abi: poolAbi, functionName: 'stake', args: [currentClawsBal] });
      const stakeTx = await submitTx(CLAWS_POOL, stakeData, BigInt(0), BigInt(150000));
      const stakeReceipt = await waitForReceipt(stakeTx);

      if (stakeReceipt.status === '0x1') {
        log(`STAKE SUCCESS: ${currentClawsFloat.toFixed(2)} CLAWS staked!`);
        state.consecutiveRejects = 0;
        state.lastStakeAmount = currentClawsFloat;
        state.poolMinClaws = null; // No minimum detected
      } else {
        log('STAKE REVERTED');
        state.consecutiveRejects++;
        log(`Consecutive rejects: ${state.consecutiveRejects}`);
      }
    } catch(e) {
      const msg = e.message || '';
      log(`Stake error: ${msg.slice(0, 200)}`);
      state.consecutiveRejects++;

      if (msg.toLowerCase().includes('minimum') || msg.toLowerCase().includes('below')) {
        log('Pool rejected: BELOW MINIMUM. Updating learned minimum.');
        // Try to extract the minimum from error
        const nums = msg.match(/\d+/g);
        if (nums && nums.length > 0) {
          const parsed = nums.map(n => BigInt(n));
          const validMins = parsed.filter(n => n > BigInt(0) && n < currentClawsBal);
          if (validMins.length > 0) {
            const bestGuess = validMins.reduce((a, b) => a < b ? a : b);
            state.poolMinClaws = Number(bestGuess) / 1e18;
            log(`Learned minimum: ~${state.poolMinClaws.toFixed(2)} CLAWS`);
          }
        }
      }
    }
  }

  state.lastRun = new Date().toISOString();
  saveState(state);
  log('=== Cycle Complete ===\n');
}

// ─── CLI ───────────────────────────────────────────────────────────────────
const args = process.argv.slice(2);

(async () => {
  if (args[0] === 'status') {
    const [claws, staked, pending, ethBal, gasPrice, ethPrice] = await Promise.all([
      getClawsBalance(), getStakedSenator(), getPendingRewards(), getEthBalance(), getGasPrice(), getEthPriceUsd()
    ]);
    const ethPriceF = Number(ethPrice);
    const gasGwei = Number(gasPrice) / 1e9;
    const state = loadState();
    const clawsPriceEth = await getClawsPriceEth();
    console.log('\n═══ Nova Staking Status ═══');
    console.log(`ETH:    ${(Number(ethBal)/1e18).toFixed(6)} (~$${((Number(ethBal)/1e18)*ethPriceF).toFixed(2)})`);
    console.log(`SENATOR: ${(Number(staked)/1e6).toFixed(2)}`);
    console.log(`CLAWS:  ${(Number(claws)/1e18).toFixed(4)} (${clawsPriceEth ? '~$'+((Number(claws)/1e18)*clawsPriceEth*ethPriceF).toFixed(4) : 'price unknown'})`);
    console.log(`Pending: ${(Number(pending)/1e18).toFixed(4)} CLAWS`);
    console.log(`Gas:    ${gasGwei.toFixed(4)} gwei`);
    console.log('─── State ───────────────');
    console.log(`Consecutive rejects: ${state.consecutiveRejects}`);
    console.log(`Pool minimum: ${state.poolMinClaws ? state.poolMinClaws.toFixed(2)+' CLAWS' : 'unknown'}`);
    console.log(`Last run: ${state.lastRun || 'never'}`);
    console.log('');
  } else if (args[0] === 'check') {
    const [claws, pending] = await Promise.all([getClawsBalance(), getPendingRewards()]);
    console.log(`CLAWS=${(Number(claws)/1e18).toFixed(2)} pending=${(Number(pending)/1e18).toFixed(2)}`);
  } else {
    await runSmartCompound();
  }
})();
