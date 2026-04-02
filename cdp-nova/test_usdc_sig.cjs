const { createPublicClient, http, createWalletClient } = require('viem');
const { base } = require('viem/chains');
const { privateKeyToAccount } = require('viem/accounts');
const { readFileSync } = require('fs');

const pub = createPublicClient({ chain: base, transport: http() });
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const walletKey = JSON.parse(readFileSync('nova-wallet.json','utf8'));
const account = privateKeyToAccount(walletKey.privateKey);
const walletClient = createWalletClient({ account, chain: base, transport: http() });

const authorizationTypes = {
  TransferWithAuthorization: [
    { name: 'from', type: 'address' }, { name: 'to', type: 'address' },
    { name: 'value', type: 'uint256' }, { name: 'validAfter', type: 'uint256' },
    { name: 'validBefore', type: 'uint256' }, { name: 'nonce', type: 'bytes32' }
  ]
};
const domain = {
  name: 'USD Coin', version: '2', chainId: 8453n, verifyingContract: USDC
};
const now = Math.floor(Date.now()/1000);
const message = {
  from: account.address, to: account.address, value: 100000n,
  validAfter: 0n, validBefore: BigInt(now+300),
  nonce: '0x0000000000000000000000000000000000000000000000000000000000000001'
};

console.log('Signing message for USDC transfer...');
console.log('from:', account.address);
console.log('domain chainId:', domain.chainId);

account.signTypedData({ domain, types: authorizationTypes, primaryType: 'TransferWithAuthorization', message })
  .then(sig => {
    console.log('sig length:', sig.length, '(65 bytes = 64 hex + 0x)');
    const sigHex = sig.slice(2);
    const r = '0x' + sigHex.slice(0,64);
    const s = '0x' + sigHex.slice(64,128);
    const v = parseInt(sigHex.slice(128,130),16);
    console.log('v:', v, 'r:', r.slice(0,20)+'...', 's:', s.slice(0,20)+'...');
    
    return pub.simulateContract({
      address: USDC,
      abi: [{ type: 'function', name: 'transferWithAuthorization',
        inputs: [
          { name: 'from', type: 'address' }, { name: 'to', type: 'address' },
          { name: 'value', type: 'uint256' }, { name: 'validAfter', type: 'uint256' },
          { name: 'validBefore', type: 'uint256' }, { name: 'nonce', type: 'bytes32' },
          { name: 'v', type: 'uint8' }, { name: 'r', type: 'bytes32' }, { name: 's', type: 'bytes32' }
        ],
        outputs: [{ type: 'bool' }]
      }],
      functionName: 'transferWithAuthorization',
      args: [account.address, account.address, 100000n, 0n, BigInt(now+300), message.nonce, v, r, s]
    });
  })
  .then(r => console.log('✅ Simulate OK:', r))
  .catch(e => console.log('❌ FAIL:', e.message.includes('revert') ? e.message.slice(0,300) : e.message.slice(0,100)));
