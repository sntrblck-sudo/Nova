const { createPublicClient, http, createWalletClient } = require('viem');
const { base } = require('viem/chains');
const { privateKeyToAccount } = require('viem/accounts');
const { readFileSync } = require('fs');

const pub = createPublicClient({ chain: base, transport: http() });
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const walletKey = JSON.parse(readFileSync('nova-wallet.json','utf8'));
const account = privateKeyToAccount(walletKey.privateKey);
const walletClient = createWalletClient({ account, chain: base, transport: http() });

async function main() {
  // Get current nonce
  const nonce = await pub.readContract({
    address: USDC,
    abi: [{type:'function', name:'nonces', stateMutability:'view', inputs:[{type:'address'}], outputs:[{type:'uint256'}]}],
    functionName: 'nonces',
    args: [account.address]
  });
  console.log('Nova nonce:', nonce.toString());

  const authorizationTypes = {
    TransferWithAuthorization: [
      {name:'from',type:'address'},{name:'to',type:'address'},{name:'value',type:'uint256'},
      {name:'validAfter',type:'uint256'},{name:'validBefore',type:'uint256'},{name:'nonce',type:'bytes32'}
    ]
  };

  const now = Math.floor(Date.now()/1000);
  const DOMAIN = {
    name: 'USD Coin',
    version: '2',
    chainId: 8453n,
    verifyingContract: USDC
  };

  // Try nonce = current nonce (sequential)
  const nonceHex = '0x' + Number(nonce).toString(16).padStart(64, '0');
  const msg = {
    from: account.address,
    to: account.address,
    value: 100000n,
    validAfter: 0n,
    validBefore: BigInt(now + 300),
    nonce: nonceHex
  };

  console.log('Signing with nonce:', nonceHex.slice(0,20)+'...');
  const sig = await account.signTypedData({
    account,
    domain: DOMAIN,
    types: authorizationTypes,
    primaryType: 'TransferWithAuthorization',
    message: msg
  });

  const sigHex = sig.slice(2);
  const r = '0x' + sigHex.slice(0,64);
  const s = '0x' + sigHex.slice(64,128);
  const v = parseInt(sigHex.slice(128,130),16);
  console.log('sig v:', v);

  console.log('Submitting transferWithAuthorization...');
  const hash = await walletClient.writeContract({
    address: USDC,
    abi: [{type:'function',name:'transferWithAuthorization',inputs:[
      {name:'from',type:'address'},{name:'to',type:'address'},{name:'value',type:'uint256'},
      {name:'validAfter',type:'uint256'},{name:'validBefore',type:'uint256'},{name:'nonce',type:'bytes32'},
      {name:'v',type:'uint8'},{name:'r',type:'bytes32'},{name:'s',type:'bytes32'}
    ],outputs:[{type:'bool'}]}],
    functionName: 'transferWithAuthorization',
    args: [account.address, account.address, 100000n, 0n, BigInt(now+300), nonceHex, v, r, s]
  });

  console.log('TX hash:', hash);
  const receipt = await pub.waitForTransactionReceipt({ hash });
  console.log('TX status:', receipt.status === 1 ? '✅ SUCCESS' : '❌ FAILED');

  // Check new balance
  const newBal = await pub.readContract({
    address: USDC,
    abi: [{type:'function', name:'balanceOf', stateMutability:'view', inputs:[{type:'address'}], outputs:[{type:'uint256'}]}],
    functionName: 'balanceOf',
    args: [account.address]
  });
  console.log('New USDC balance:', Number(newBal)/1e6);
}

main().catch(e => console.error('Error:', e.message.includes('revert') ? 'REVERT: ' + e.message.slice(0,300) : e.message.slice(0,200)));
