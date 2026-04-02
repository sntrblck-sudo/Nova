/**
 * Nova API - x402 Payment Test
 * Nova (payer) signs EIP-3009 auth and calls her own paid API
 * Proves end-to-end: sign → verify → query result
 */
const { createPublicClient, http, createWalletClient } = require('viem');
const { base } = require('viem/chains');
const { privateKeyToAccount, hashMessage, TypedDataEncoder } = require('viem/accounts');
const { readFileSync } = require('fs');

const API_URL = 'https://nova-nova-api.loca.lt';
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const NOVA_ADDR = '0xB743fdbA842379933A3774617786712458659D16';
const PRICE_MICRO_USDC = 100_000n; // 0.10 USDC

const WALLET_PATH = '/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json';

// EIP-3009 TransferWithAuthorization types
const TRANSFER_TYPES = {
  TransferWithAuthorization: [
    { name: 'from', type: 'address' },
    { name: 'to', type: 'address' },
    { name: 'value', type: 'uint256' },
    { name: 'validAfter', type: 'uint256' },
    { name: 'validBefore', type: 'uint256' },
    { name: 'nonce', type: 'bytes32' }
  ]
};

async function main() {
  console.log('=== Nova x402 API Payment Test ===\n');

  // Load wallet
  const walletKey = JSON.parse(readFileSync(WALLET_PATH, 'utf8'));
  const account = privateKeyToAccount(walletKey.privateKey);
  console.log('Nova wallet:', account.address);

  // Setup clients
  const publicClient = createPublicClient({ chain: base, transport: http() });
  const walletClient = createWalletClient({
    account,
    chain: base,
    transport: http()
  });

  // Check USDC balance before
  const usdcBefore = await publicClient.readContract({
    address: USDC,
    abi: [{ type: 'function', name: 'balanceOf', stateMutability: 'view', inputs: [{ type: 'address' }], outputs: [{ type: 'uint256' }] }],
    functionName: 'balanceOf',
    args: [NOVA_ADDR]
  });
  console.log('USDC before:', Number(usdcBefore) / 1e6, 'USDC\n');

  // Build EIP-3009 authorization
  const now = Math.floor(Date.now() / 1000);
  const domain = {
    name: 'USD Coin',
    version: '2',
    chainId: 8453,
    verifyingContract: USDC
  };

  const message = {
    from: NOVA_ADDR,
    to: NOVA_ADDR,       // Self-transfer (valid, just moves USDC)
    value: PRICE_MICRO_USDC.toString(),
    validAfter: now - 60,  // Valid from 60s ago
    validBefore: now + 300, // Valid for 5 min
    nonce: `0x${Math.random().toString(16).slice(2).padEnd(64, '0')}`
  };

  console.log('Signing EIP-3009 authorization...');
  console.log('  from:', message.from);
  console.log('  to:', message.to);
  console.log('  value:', message.value, 'micro-USDC (0.10 USDC)');
  console.log('  validBefore:', new Date(message.validBefore * 1000).toISOString(), '\n');

  // Sign the typed data (EIP-712 style for EIP-3009)
  // EIP-3009 uses the same domain-separated signing as EIP-712
  const signHash = TypedDataEncoder.hash({ domain, types: TRANSFER_TYPES, primaryType: 'TransferWithAuthorization', message });
  
  // For EIP-3009, the signature is over the domain-separated hash using personal_sign
  // This matches how EIP-3009 reference implementations sign
  const { signTypedData } = require('viem').actions;
  
  // Use the wallet client's signTypedData action
  const signature = await walletClient.signTypedData({
    account,
    domain,
    types: TRANSFER_TYPES,
    primaryType: 'TransferWithAuthorization',
    message
  });
  console.log('Signature:', signature.slice(0, 20) + '...\n');

  // Parse signature (standard 65-byte ECDSA sig)
  const sigHex = signature.slice(2);
  const r = '0x' + sigHex.slice(0, 64);
  const s = '0x' + sigHex.slice(64, 128);
  const v = parseInt(sigHex.slice(128, 130), 16);

  // Build the authorization payload (matches what server expects)
  const authPayload = {
    from: message.from,
    to: message.to,
    value: message.value,
    validAfter: message.validAfter,
    validBefore: message.validBefore,
    nonce: message.nonce,
    v, r, s
  };

  const authBase64 = Buffer.from(JSON.stringify(authPayload)).toString('base64');

  // Call the paid API endpoint
  console.log('Calling Nova API with payment...');
  const queryAddress = NOVA_ADDR; // query Nova's own balance
  const response = await fetch(`${API_URL}/balance/${queryAddress}`, {
    method: 'GET',
    headers: {
      'Authorization': `FUTUREU ${authBase64}`,
      'Content-Type': 'application/json'
    }
  });

  console.log('Response status:', response.status);
  const data = await response.json();
  console.log('\nResponse body:');
  console.log(JSON.stringify(data, null, 2));

  // Check USDC balance after
  const usdcAfter = await publicClient.readContract({
    address: USDC,
    abi: [{ type: 'function', name: 'balanceOf', stateMutability: 'view', inputs: [{ type: 'address' }], outputs: [{ type: 'uint256' }] }],
    functionName: 'balanceOf',
    args: [NOVA_ADDR]
  });
  console.log('\nUSDC after:', Number(usdcAfter) / 1e6, 'USDC');
  console.log('USDC deducted:', (Number(usdcBefore) - Number(usdcAfter)) / 1e6);

  if (response.status === 200 && data.eth !== undefined) {
    console.log('\n✅ PAYMENT TEST PASSED - Full x402 flow working!');
  } else if (response.status === 402) {
    console.log('\n❌ Payment was rejected - 402 Payment Required');
  } else {
    console.log('\n⚠️ Unexpected response');
  }
}

main().catch(e => {
  console.error('Test failed:', e.message);
  process.exit(1);
});
