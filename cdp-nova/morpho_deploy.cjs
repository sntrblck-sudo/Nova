#!/usr/bin/env node
/**
 * Nova's Morpho Blue USDC Deployer
 * Deposits USDC into Morpho Blue Chip USDC Vault (Prime) on Base.
 * APY: ~4-7%, managed by professional risk curators (RE7L)
 */

const fs = require('fs');
const path = require('path');
const { createWalletClient, http, createPublicClient, formatEther } = require('viem');

const PORTFOLIO_FILE = path.join(__dirname, 'portfolio_positions.json');
const RISK_FILE      = path.join(__dirname, 'risk_limits.json');

function loadPositions() {
  try {
    return JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf8'));
  } catch {
    return { positions: [], lastAction: null, totalValueUsd: 0 };
  }
}

function loadRiskLimits() {
  try {
    return JSON.parse(fs.readFileSync(RISK_FILE, 'utf8'));
  } catch {
    return {};
  }
}
const { privateKeyToAccount } = require('viem/accounts');
const { base } = require('viem/chains');

// === Config ===
const NOVA_KEY_PATH = '/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json';
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const VAULT = '0x8A034f069D59d62a4643ad42E49b846d036468D7';
const MorphoBlue = '0x00000000000000000000000000000000000dd8F'; // Morpho Blue contract on Base
const RPC = 'https://mainnet.base.org';

const vaultABI = [
  {'name':'deposit','type':'function','inputs':[{'name':'assets','type':'uint256'},{'name':'receiver','type':'address'}],'outputs':[{'name':'',type:'uint256'}]},
  {'name':'redeem','type':'function','inputs':[{'name':'shares','type':'uint256'},{'name':'receiver','type':'address'},{'name':'owner','type':'address'}],'outputs':[{'name':'',type:'uint256'}]},
  {'name':'balanceOf','type':'function','inputs':[{'name':'account','type':'address'}],'outputs':[{'name':'',type:'uint256'}]},
  {'name':'convertToAssets','type':'function','inputs':[{'name':'shares','type':'uint256'}],'outputs':[{'name':'',type:'uint256'}]},
  {'name':'asset','type':'function','inputs':[],'outputs':[{'name':'',type:'address'}]},
  {'name':'totalAssets','type':'function','inputs':[],'outputs':[{'name':'',type:'uint256'}]},
];

const erc20ABI = [
  {'name':'approve','type':'function','inputs':[{'name':'spender','type':'address'},{'name':'amount','type':'uint256'}],'outputs':[{'name':'',type:'bool'}]},
  {'name':'allowance','type':'function','inputs':[{'name':'owner','type':'address'},{'name':'spender','type':'address'}],'outputs':[{'name':'',type:'uint256'}]},
  {'name':'balanceOf','type':'function','inputs':[{'name':'account','type':'address'}],'outputs':[{'name':'',type:'uint256'}]},
];

async function loadWallet() {
  const keyData = require(NOVA_KEY_PATH);
  const account = privateKeyToAccount(keyData.privateKey);
  return account;
}

async function getClients() {
  const account = await loadWallet();
  const wallet = createWalletClient({ account, chain: base, transport: http(RPC) });
  const pub = createPublicClient({ chain: base, transport: http(RPC) });
  return { wallet, pub, account };
}

async function getGasPrice(pub) {
  return await pub.getGasPrice();
}

async function deploy(amountUsdc) {
  const { wallet, pub, account } = await getClients();
  const NOVA = account.address;
  const amount = BigInt(Math.round(amountUsdc * 1e6)); // USDC 6 decimals

  console.log(`\n=== Morpho USDC Deploy ===`);
  console.log(`Amount: ${amountUsdc} USDC`);
  console.log(`From: ${NOVA}`);
  console.log(`To vault: ${VAULT}`);

  // Check USDC balance
  const usdcBal = await pub.readContract({ address: USDC, abi: erc20ABI, functionName: 'balanceOf', args: [NOVA] });
  console.log(`USDC balance: ${Number(usdcBal)/1e6}`);
  if (usdcBal < amount) {
    console.log(`❌ Insufficient USDC. Have ${Number(usdcBal)/1e6}, need ${amountUsdc}`);
    return null;
  }

  // Check allowance
  const allowance = await pub.readContract({ address: USDC, abi: erc20ABI, functionName: 'allowance', args: [NOVA, VAULT] });
  console.log(`Current allowance: ${Number(allowance)/1e6} USDC`);

  let txHash = null;

  // Step 1: Approve max (Morpho needs full allowance to work correctly)
  const maxUint = BigInt('0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff');
  if (allowance < amount) {
    console.log(`Approving vault to spend USDC...`);
    const approveTx = await wallet.writeContract({
      address: USDC,
      abi: erc20ABI,
      functionName: 'approve',
      args: [VAULT, maxUint],
    });
    const approveReceipt = await pub.waitForTransactionReceipt({ hash: approveTx });
    console.log(`✅ Approved. Hash: ${approveReceipt.transactionHash}`);
  } else {
    console.log(`Allowance sufficient, skipping approve.`);
  }

  // Step 2: Deposit
  console.log(`Depositing ${amountUsdc} USDC into Morpho vault...`);
  const gasPrice = await getGasPrice(pub);
  console.log(`Gas price: ${Number(gasPrice)/1e9} gwei`);

  const depositTx = await wallet.writeContract({
    address: VAULT,
    abi: vaultABI,
    functionName: 'deposit',
    args: [amount, NOVA],
    account,
  });
  const receipt = await pub.waitForTransactionReceipt({ hash: depositTx });
  console.log(`✅ Deposited. Hash: ${receipt.transactionHash}`);

  // Step 3: Check position
  const shares = await pub.readContract({ address: VAULT, abi: vaultABI, functionName: 'balanceOf', args: [NOVA] });
  const assets = await pub.readContract({ address: VAULT, abi: vaultABI, functionName: 'convertToAssets', args: [shares] });
  console.log(`Position: ${Number(shares)/1e18} shares = ${Number(assets)/1e6} USDC`);

  return {
    txHash: receipt.transactionHash,
    shares: Number(shares)/1e18,
    assetsUsdc: Number(assets)/1e6,
    amountUsdc
  };
}

async function status() {
  const { pub, account } = await getClients();
  const NOVA = account.address;
  const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
  const VAULT = '0x8A034f069D59d62a4643ad42E49b846d036468D7';

  const vaultABI = [
    {'name':'balanceOf','type':'function','inputs':[{'name':'account','type':'address'}],'outputs':[{'name':'',type:'uint256'}]},
    {'name':'convertToAssets','type':'function','inputs':[{'name':'shares','type':'uint256'}],'outputs':[{'name':'',type:'uint256'}]},
    {'name':'asset','type':'function','inputs':[],'outputs':[{'name':'',type:'address'}]},
  ];
  const erc20ABI = [
    {'name':'balanceOf','type':'function','inputs':[{'name':'account','type':'address'}],'outputs':[{'name':'',type:'uint256'}]},
  ];

  const usdcBal = await pub.readContract({ address: USDC, abi: erc20ABI, functionName: 'balanceOf', args: [NOVA] });
  const shares = await pub.readContract({ address: VAULT, abi: vaultABI, functionName: 'balanceOf', args: [NOVA] });
  const assets = await pub.readContract({ address: VAULT, abi: vaultABI, functionName: 'convertToAssets', args: [shares] });


  const data = loadPositions();
  const riskLimits = loadRiskLimits();
  const active = data.positions.filter(p => p.status === 'active');
  const totalUsd = active.reduce((sum, p) => sum + (p.valueUsd || 0), 0) + Number(assets)/1e6;

  console.log(`\n╔═══════════════════════════════════════╗`);
  console.log(`║       NOVA PORTFOLIO STATUS          ║`);
  console.log(`╠═══════════════════════════════════════╣`);
  console.log(`║ Total Deployed: $${totalUsd.toFixed(2)} / $${riskLimits.maxTotalDeployUsd}     ║`);
  console.log(`║ Wallet USDC: $${(Number(usdcBal)/1e6).toFixed(2)}                 ║`);
  console.log(`║ Morpho shares: ${(Number(shares)/1e18).toFixed(4)} = $${(Number(assets)/1e6).toFixed(2)} USDC  ║`);
  console.log(`╠═══════════════════════════════════════╣`);
  active.forEach(p => {
    const age = Math.floor((Date.now() - new Date(p.deployedAt).getTime()) / 86400000);
    console.log(`║ ${p.asset.padEnd(8)} ${p.amount.toFixed(4).padStart(12)} $${p.valueUsd.toFixed(2).padStart(8)} @ ${p.yieldApy}% ${p.protocol.padEnd(14)} ${age}d║`);
  });
  console.log('╚═══════════════════════════════════════╝');
  return { positions: active, totalUsd, walletUsdc: Number(usdcBal)/1e6, morphoShares: Number(shares)/1e18, morphoAssets: Number(assets)/1e6 };
}

async function redeem(sharesAmount) {
  const { wallet, pub, account } = await getClients();
  const NOVA = account.address;
  const shares = BigInt(Math.round(sharesAmount * 1e18));

  console.log(`\n=== Morpho Redeem ===`);
  console.log(`Redeeming ${sharesAmount} shares...`);

  const redeemTx = await wallet.writeContract({
    address: VAULT,
    abi: vaultABI,
    functionName: 'redeem',
    args: [shares, NOVA, NOVA],
    account,
  });
  const receipt = await pub.waitForTransactionReceipt({ hash: redeemTx });
  console.log(`✅ Redeemed. Hash: ${receipt.transactionHash}`);
  return receipt.transactionHash;
}

// === CLI ===
const cmd = process.argv[2];
if (cmd === 'deploy' && process.argv[3]) {
  deploy(parseFloat(process.argv[3])).then(r => {
    if (r) console.log('\n✅ Deploy successful!');
    process.exit(0);
  }).catch(e => {
    console.error('❌ Deploy failed:', e.message);
    process.exit(1);
  });
} else if (cmd === 'status') {
  status().then(() => process.exit(0)).catch(e => {
    console.error('Status error:', e.message);
    process.exit(1);
  });
} else if (cmd === 'redeem' && process.argv[3]) {
  redeem(parseFloat(process.argv[3])).then(() => {
    console.log('\n✅ Redeem complete!');
    process.exit(0);
  }).catch(e => {
    console.error('❌ Redeem failed:', e.message);
    process.exit(1);
  });
} else {
  console.log('Usage:');
  console.log('  node morpho_deploy.cjs deploy <amount_usdc>');
  console.log('  node morpho_deploy.cjs status');
  console.log('  node morpho_deploy.cjs redeem <shares>');
}
