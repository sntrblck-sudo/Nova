const { privateKeyToAccount } = require('viem/accounts');
const { base } = require('viem/chains');
const { createWalletClient, http, createPublicClient } = require('viem');
const { readFileSync } = require('fs');

const WALLET_PATH = '/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json';
const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';

const wallet = JSON.parse(readFileSync(WALLET_PATH, 'utf8'));
const account = privateKeyToAccount(wallet.privateKey);
const NOVA = account.address;

const walletClient = createWalletClient({ account, chain: base, transport: http('https://mainnet.base.org') });
const publicClient = createPublicClient({ chain: base, transport: http('https://mainnet.base.org') });

const USDC_ABI = [
  { name: 'transfer', type: 'function', inputs: [{ name: 'to', type: 'address' }, { name: 'amount', type: 'uint256' }], outputs: [{ name: '', type: 'bool' }] },
  { name: 'balanceOf', type: 'function', inputs: [{ name: 'account', type: 'address' }], outputs: [{ name: '', type: 'uint256' }] },
];

function usdc(v) { return (Number(v) / 1e6).toFixed(4); }

async function payAndCall(serviceUrl, body, description) {
  console.log('\n[SERVICE] ' + description);
  console.log('URL: ' + serviceUrl);

  // Step 1: Get 402
  const opts = { method: body ? 'POST' : 'GET', headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);

  let res = await fetch(serviceUrl, opts);
  let text = await res.text();

  if (res.status !== 402) {
    console.log('Status: ' + res.status + ' | ' + text.slice(0, 200));
    return;
  }

  const paymentData = JSON.parse(text);
  const accepts = paymentData.accepts?.[0] || paymentData;
  const payTo = accepts.payTo;
  const maxAmount = BigInt(accepts.maxAmountRequired);
  const amountStr = usdc(maxAmount);

  console.log('402: Pay ' + amountStr + ' USDC to ' + payTo);

  // Balance check
  const bal = await publicClient.readContract({ address: USDC_ADDRESS, abi: USDC_ABI, functionName: 'balanceOf', args: [NOVA] });
  console.log('Balance: ' + usdc(bal) + ' USDC');

  if (bal < maxAmount) { console.log('Insufficient!'); return; }

  // Step 2: Pay
  console.log('Sending payment...');
  const txHash = await walletClient.writeContract({
    address: USDC_ADDRESS, abi: USDC_ABI, functionName: 'transfer', args: [payTo, maxAmount],
  });
  await publicClient.waitForTransactionReceipt({ hash: txHash });
  console.log('Tx: ' + txHash);

  // Step 3: Call with X-PAYMENT (various formats to try)
  const formats = [
    txHash,
    'exact:' + payTo + ':' + maxAmount.toString() + ':' + txHash,
    txHash.slice(2),
    payTo + ':' + maxAmount.toString() + ':' + txHash,
  ];

  for (const fmt of formats) {
    const paidOpts = { method: body ? 'POST' : 'GET', headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', 'X-PAYMENT': fmt } };
    if (body) paidOpts.body = JSON.stringify(body);
    res = await fetch(serviceUrl, paidOpts);
    text = await res.text();
    console.log('\nFormat: ' + fmt.slice(0, 40) + '...');
    console.log('Status: ' + res.status + ' | ' + text.slice(0, 200));
    if (res.status === 200) { console.log('\n✅ SUCCESS!'); break; }
  }
}

async function main() {
  // Try the AIXBT project search - crypto project info
  await payAndCall(
    'https://mesh.heurist.xyz/x402/agents/AIXBTProjectInfoAgent/search_projects',
    { query: 'Base DeFi yield', limit: 3 },
    'AIXBT Project Search ($0.01)'
  );
}

main().catch(console.error);
