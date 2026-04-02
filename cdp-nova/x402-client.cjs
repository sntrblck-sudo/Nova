/**
 * Nova's x402 Client - native implementation using viem + Nova's EOA
 * Handles EIP-3009 TransferWithAuthorization for x402 exact scheme payments
 */

const { createPublicClient, http, encodeAbiParameters, parseUnits, keccak256, toBytes } = require('viem');
const { baseSepolia } = require('viem/chains');
const { privateKeyToAccount } = require('viem/accounts');
const fetch = require('node:http');
const https = require('node:https');

const NOVA_ADDRESS = '0xB743fdbA842379933A3774617786712458659D16';
// EIP-3009 constants - all lowercase to bypass viem 2.x checksum validation in signTypedData
const USDC_ADDRESS = '0x036cbd53842c5426634e7929541ec2318f3dcf7e';

const EIP3009_DOMAIN = {
  name: 'USD Coin (EIP 3009)',
  version: '2',
  chainId: 84532n,
  verifyingContract: USDC_ADDRESS,
};

const EIP3009_TYPES = {
  TransferWithAuthorization: [
    { name: 'from', type: 'address' },
    { name: 'to', type: 'address' },
    { name: 'value', type: 'uint256' },
    { name: 'validAfter', type: 'uint256' },
    { name: 'validBefore', type: 'uint256' },
    { name: 'nonce', type: 'bytes32' },
  ],
  EIP712Domain: [
    { name: 'name', type: 'string' },
    { name: 'version', type: 'string' },
    { name: 'chainId', type: 'uint256' },
    { name: 'verifyingContract', type: 'address' },
  ],
};

// Build the client
const pub = createPublicClient({ chain: baseSepolia, transport: http('https://sepolia.base.org') });
const walletKey = require('./nova-wallet.json').privateKey;
const account = privateKeyToAccount(walletKey.startsWith('0x') ? walletKey : '0x' + walletKey);

function httpRequest(url, options = {}) {
  return new Promise((resolve, reject) => {
    const lib = url.startsWith('https') ? https : http;
    const req = lib.request(url, options, res => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: data }));
    });
    req.on('error', reject);
    if (options.body) req.write(options.body);
    req.end();
  });
}

async function getPaymentRequirements(url) {
  const res = await httpRequest(url, { method: 'GET' });
  if (res.status !== 402) {
    return { requiresPayment: false, data: res.body };
  }
  
  const header = res.headers['payment-required'];
  if (!header) throw new Error('No payment-required header');
  
  const payload = JSON.parse(Buffer.from(header, 'base64').toString('utf8'));
  return { requiresPayment: true, payload };
}

async function buildEIP3009Auth(payTo, value, from, nonce = null) {
  const validAfter = 0;
  const validBefore = Math.floor(Date.now() / 1000) + 300; // 5 min
  
  if (!nonce) {
    // Generate random nonce
    const bytes = crypto.getRandomValues(new Uint8Array(32));
    nonce = '0x' + Buffer.from(bytes).toString('hex');
  }
  
  // Build the EIP-712 typed data - all lowercase to bypass viem checksum validation
  const domain = {
    name: EIP3009_DOMAIN.name,
    version: EIP3009_DOMAIN.version,
    chainId: EIP3009_DOMAIN.chainId,
    verifyingContract: EIP3009_DOMAIN.verifyingContract,
  };
  
  const message = {
    from: from.toLowerCase(),
    to: payTo.toLowerCase(),
    value: BigInt(value),
    validAfter: BigInt(validAfter),
    validBefore: BigInt(validBefore),
    nonce,
  };
  
  // Sign the typed data
  const signature = await account.signTypedData({
    domain,
    types: EIP3009_TYPES,
    primaryType: 'TransferWithAuthorization',
    message,
  });
  
  return {
    domain,
    types: EIP3009_TYPES,
    message,
    signature,
  };
}

async function payAndRequest(url, maxAmount = null) {
  // Step 1: Get payment requirements
  console.log('Getting payment requirements...');
  const req = await getPaymentRequirements(url);
  
  if (!req.requiresPayment) {
    console.log('No payment required, returning data...');
    return JSON.parse(req.data);
  }
  
  const { payload } = req;
  console.log('Payment required:', JSON.stringify(payload.accepts[0], null, 2));
  
  const accept = payload.accepts[0];
  const amount = accept.amount;
  const payTo = accept.payTo;
  const asset = accept.asset;
  
  // Step 2: Build EIP-3009 authorization
  console.log('Building EIP-3009 authorization...');
  const auth = await buildEIP3009Auth(payTo, amount, NOVA_ADDRESS);
  
  // Step 3: Create the payment payload
  const paymentPayload = {
    scheme: 'eip3009',
    authorization: {
      domain: {
        name: auth.domain.name,
        version: auth.domain.version,
        chainId: auth.domain.chainId.toString(),
        verifyingContract: auth.domain.verifyingContract,
      },
      types: {
        EIP712Domain: auth.types.EIP712Domain,
        TransferWithAuthorization: auth.types.TransferWithAuthorization,
      },
      message: {
        from: auth.message.from,
        to: auth.message.to,
        value: auth.message.value.toString(),
        validAfter: auth.message.validAfter.toString(),
        validBefore: auth.message.validBefore.toString(),
        nonce: auth.message.nonce,
      },
      signature: auth.signature,
    },
  };
  
  // Step 4: Retry the request with payment header
  console.log('Submitting payment...');
  const paymentJson = JSON.stringify(paymentPayload);
  const paymentHeader = Buffer.from(paymentJson).toString('base64');
  const res = await httpRequest(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'PAYMENT-SIGNATURE': paymentHeader,
    },
  });
  
  console.log('Response status:', res.status);
  console.log('Response body:', res.body.slice(0, 300));
  
  return JSON.parse(res.body);
}

// CLI
const url = process.argv[2] || 'https://decorative-minerals-bachelor-saver.trycloudflare.com/api/balance/eth/0xB743fdbA842379933A3774617786712458659D16';

payAndRequest(url).then(r => {
  console.log('\nResult:', JSON.stringify(r, null, 2));
  process.exit(0);
}).catch(e => {
  console.error('Error:', e.message);
  process.exit(1);
});
