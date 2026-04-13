/**
 * Nova's Venice Top-Up — EIP-3009 USDC Authorization
 * Sends USDC to Venice's receiver wallet using EIP-3009 transferWithAuthorization
 */

const { createWalletClient, http, encodeFunctionData } = require('viem');
const { privateKeyToAccount } = require('viem/accounts');
const { base } = require('viem/chains');
const crypto = require('crypto');
const https = require('https');
const fs = require('fs');

const WALLET_PATH = '/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json';
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const VENICE_RECEIVER = '0x2670B922ef37C7Df47158725C0CC407b5382293F';
const AMOUNT = BigInt(5 * 1e6); // $5 USDC

const erc20ABI = [
  {
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
    outputs: [],
    stateMutability: 'nonpayable'
  }
];

const eip712Domain = [
  { name: 'name', type: 'string' },
  { name: 'version', type: 'string' },
  { name: 'chainId', type: 'uint256' },
  { name: 'verifyingContract', type: 'address' }
];

const transferTypes = [
  { name: 'from', type: 'address' },
  { name: 'to', type: 'address' },
  { name: 'value', type: 'uint256' },
  { name: 'validAfter', type: 'uint256' },
  { name: 'validBefore', type: 'uint256' },
  { name: 'nonce', type: 'bytes32' }
];

function splitSignature(sig) {
  // sig is 65 bytes: r (32) + s (32) + v (1)
  const r = '0x' + sig.slice(2, 66);
  const s = '0x' + sig.slice(66, 130);
  const v = parseInt(sig.slice(130, 132), 16);
  return { r, s, v };
}

async function httpsRequest(hostname, path, method, headers, body) {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : undefined;
    const req = https.request({ hostname, path, method, headers }, (res) => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => {
        try { resolve({ status: res.statusCode, data: JSON.parse(d) }); }
        catch { resolve({ status: res.statusCode, data: d }); }
      });
    });
    req.on('error', reject);
    if (data) req.write(data);
    req.end();
  });
}

async function main() {
  const walletData = JSON.parse(fs.readFileSync(WALLET_PATH, 'utf8'));
  const account = privateKeyToAccount(walletData.privateKey);
  const address = account.address;
  const pub = createPublicClient = require('viem').createPublicClient({ chain: base, transport: http() });
  const walletClient = createWalletClient({ account, chain: base, transport: http() });

  console.log('Nova wallet:', address);
  console.log('USDC amount:', AMOUNT.toString(), `($${Number(AMOUNT)/1e6})`);

  // Check USDC balance
  const balance = await pub.readContract({
    address: USDC,
    abi: [{ name: 'balanceOf', type: 'function', inputs: [{ name: 'account', type: 'address' }], outputs: [{ type: 'uint256' }] }],
    functionName: 'balanceOf',
    args: [address]
  });
  console.log('USDC balance:', Number(balance) / 1e6);
  if (balance < AMOUNT) {
    console.error('Insufficient USDC!');
    process.exit(1);
  }

  // Build EIP-712 message for transferWithAuthorization
  const nonce = '0x' + crypto.randomBytes(32).toString('hex');
  const validBefore = Math.floor(Date.now() / 1000) + 3600; // 1 hour

  const eip712Msg = {
    domain: { name: 'USD Coin', version: '2', chainId: 8453, verifyingContract: USDC },
    types: {
      TransferWithAuthorization: transferTypes,
      EIP712Domain
    },
    primaryType: 'TransferWithAuthorization',
    message: {
      from: address,
      to: VENICE_RECEIVER,
      value: AMOUNT.toString(),
      validAfter: '0',
      validBefore: String(validBefore),
      nonce
    }
  };

  console.log('\nSigning EIP-3009 authorization...');
  const sig = await walletClient.signTypedData(eip712Msg);
  console.log('Sig:', sig.slice(0, 20), '...');

  const { r, s, v } = splitSignature(sig);
  console.log('v:', v, 'r:', r.slice(0, 16), '... s:', s.slice(0, 16), '...');

  // Encode the function call
  const data = encodeFunctionData({
    abi: erc20ABI,
    functionName: 'transferWithAuthorization',
    args: [address, VENICE_RECEIVER, AMOUNT, BigInt(0), BigInt(validBefore), nonce, v, r, s]
  });

  // Check gas
  const gasPrice = await pub.getGasPrice();
  console.log('\nGas price:', gasPrice.toString());

  // Send tx
  console.log('Submitting transferWithAuthorization...');
  const hash = await walletClient.sendTransaction({
    to: USDC,
    data,
    value: BigInt(0),
    gasPrice
  });
  console.log('TX:', hash);
  console.log('https://basescan.org/tx/' + hash);

  // Wait for confirmation
  const receipt = await pub.waitForTransactionReceipt({ hash });
  console.log('TX status:', receipt.status === 1 ? '✅ SUCCESS' : '❌ FAILED');

  if (receipt.status === 1) {
    console.log('\nWaiting 10s for Venice to process...');
    await new Promise(r => setTimeout(r, 10000));

    // Now call Venice top-up endpoint with payment header
    console.log('\nCalling Venice top-up...');
    const paymentHeader = Buffer.from(JSON.stringify({
      abi: erc20ABI,
      functionName: 'transferWithAuthorization',
      args: [address, VENICE_RECEIVER, AMOUNT.toString(), '0', String(validBefore), nonce, String(v), r, s],
      transaction: { hash, chainId: 8453 }
    })).toString('base64');

    const result = await httpsRequest('api.venice.ai', '/api/v1/x402/top-up', 'POST', {
      'Content-Type': 'application/json',
      'X-402-Payment': paymentHeader,
      'User-Agent': 'Nova-Venice/1.0'
    }, {});

    console.log('Top-up response:', JSON.stringify(result));
  }
}

main().catch(e => console.error('Error:', e.message));
