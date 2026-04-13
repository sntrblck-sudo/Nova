/**
 * Deploy TipVault to Base Mainnet
 * Nova's owner address must be provided as arg[2]
 * Usage: node deploy.cjs <OWNER_ADDRESS>
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const https = require('https');

const RPC_URL = 'https://mainnet.base.org';
const NOVA_KEY_FILE = '/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json';
const OUTPUT_DIR = path.join(__dirname, 'compiled');
const CONFIG_DIR = path.join(__dirname, 'config');

fs.mkdirSync(CONFIG_DIR, { recursive: true });

async function main() {
  // --- Step 1: Compile ---
  console.log('📦 Compiling TipVault...');
  const solcInput = {
    language: 'Solidity',
    sources: { 'TipVault.sol': { content: fs.readFileSync(path.join(__dirname, 'contracts/TipVault.sol'), 'utf8') } },
    settings: { optimizer: { enabled: false }, outputSelection: { '*': { '*': ['abi', 'evm.bytecode.object'] } } }
  };

  let output = execSync('npx solc --standard-json', {
    input: JSON.stringify(solcInput),
    encoding: 'utf8',
    timeout: 30000
  });

  let result;
  try {
    result = JSON.parse(output.split('\n').filter(l => !l.startsWith('>>>')).join(''));
  } catch(e) {
    console.error('JSON parse error. Output:', output.slice(0, 500));
    process.exit(1);
  }

  const contract = result.contracts?.['TipVault.sol']?.TipVault;
  if (!contract) {
    console.error('Compilation failed. Errors:', JSON.stringify(result.errors, null, 2));
    process.exit(1);
  }

  const abi = contract.abi;
  const bytecode = contract.evm.bytecode.object;

  console.log(`✅ Compiled. Bytecode: ${bytecode.length} chars, ABI entries: ${abi.length}`);

  // Save artifacts
  fs.writeFileSync(path.join(OUTPUT_DIR, 'TipVault.abi.json'), JSON.stringify(abi, null, 2));
  fs.writeFileSync(path.join(OUTPUT_DIR, 'TipVault.bytecode.txt'), bytecode);
  console.log(`📁 Artifacts saved to ${OUTPUT_DIR}/`);

  // --- Step 2: Wallet setup ---
  const walletJson = JSON.parse(fs.readFileSync(NOVA_KEY_FILE, 'utf8'));
  const privateKey = walletJson.privateKey.startsWith('0x')
    ? walletJson.privateKey
    : '0x' + walletJson.privateKey;

  const { createWalletClient, createPublicClient, http, encodeDeployData, parseEther } = require('viem');
  const { privateKeyToAccount } = require('viem/accounts');
  const { base } = require('viem/chains');

  const account = privateKeyToAccount(privateKey);
  const ownerAddr = account.address;

  console.log(`\n🔑 Nova's address: ${ownerAddr}`);

  const publicClient = createPublicClient({ chain: base, transport: http(RPC_URL) });
  const walletClient = createWalletClient({ account, chain: base, transport: http(RPC_URL) });

  // Check balance
  const balance = await publicClient.getBalance({ address: ownerAddr });
  console.log(`💰 Balance: ${parseFloat(Number(balance) / 1e18).toFixed(6)} ETH`);

  // --- Step 3: Estimate gas ---
  const deployData = encodeDeployData({
    abi,
    bytecode: '0x' + bytecode,
    args: [ownerAddr]
  });

  const gasPrice = await publicClient.getGasPrice();
  const estimatedGas = 150000n; // conservative for ~7.5KB contract

  console.log(`⛽ Gas estimate: ${estimatedGas.toString()}`);
  console.log(`⛽ Gas price: ${parseFloat(Number(gasPrice) / 1e9).toFixed(2)} gwei`);

  const totalCost = estimatedGas * gasPrice;
  console.log(`💸 Estimated deployment cost: ${parseFloat(Number(totalCost) / 1e18).toFixed(6)} ETH`);

  if (balance < totalCost) {
    console.error(`❌ Insufficient balance. Need ${parseFloat(Number(totalCost) / 1e18).toFixed(6)} ETH, have ${parseFloat(Number(balance) / 1e18).toFixed(6)} ETH`);
    process.exit(1);
  }

  // --- Step 4: Deploy ---
  console.log('\n🚀 Deploying TipVault...');
  const hash = await walletClient.deployContract({
    abi,
    bytecode: '0x' + bytecode,
    args: [ownerAddr],
  });

  console.log(`📤 Deploy tx sent: ${hash}`);
  console.log('⏳ Waiting for receipt...');
  const receipt = await publicClient.waitForTransactionReceipt({ hash });

  if (receipt.status === 'reverted') {
    console.error('❌ Deployment reverted!');
    process.exit(1);
  }

  const contractAddr = receipt.contractAddress;
  console.log(`✅ Deployed at: ${contractAddr}`);

  // Save deployment info
  const deploymentInfo = {
    address: contractAddr,
    txHash: hash,
    owner: ownerAddr,
    timestamp: new Date().toISOString(),
    chain: 'base-mainnet',
    version: '1.0.0'
  };

  fs.writeFileSync(path.join(CONFIG_DIR, 'deployment.json'), JSON.stringify(deploymentInfo, null, 2));
  fs.writeFileSync(path.join(CONFIG_DIR, 'tipvault_address.txt'), contractAddr);
  console.log(`💾 Saved to ${CONFIG_DIR}/`);
  console.log('\n🎉 TipVault deployed successfully!');
}

main().catch(e => { console.error('Fatal:', e); process.exit(1); });
