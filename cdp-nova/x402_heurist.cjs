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
function fmtAmt(amount, decimals) { return (Number(amount) / Math.pow(10, decimals)).toFixed(4); }

async function getUSDCBalance(addr) {
  return await publicClient.readContract({ address: USDC_ADDRESS, abi: USDC_ABI, functionName: 'balanceOf', args: [addr] });
}

async function payAndCall(serviceUrl, body, description) {
  console.log('\n========================================');
  console.log(description);
  console.log('========================================');
  console.log('URL: ' + serviceUrl);

  // Step 1: Get 402 response
  console.log('\n[1] Requesting 402...');
  const opts = {
    method: body ? 'POST' : 'GET',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);

  let res = await fetch(serviceUrl, opts);
  let text = await res.text();

  if (res.status !== 402) {
    console.log('Status: ' + res.status);
    console.log('Response: ' + text.slice(0, 300));
    return;
  }

  const paymentData = JSON.parse(text);
  const accepts = paymentData.accepts?.[0] || paymentData;
  const payTo = accepts.payTo;
  const maxAmount = BigInt(accepts.maxAmountRequired);
  const scheme = accepts.scheme;
  const resource = accepts.resource || serviceUrl;
  const amountStr = usdc(maxAmount);

  console.log('Got 402');
  console.log('  Pay: ' + amountStr + ' USDC to ' + payTo);
  console.log('  Scheme: ' + scheme);

  // Check balance
  const bal = await getUSDCBalance(NOVA);
  console.log('Nova USDC balance: ' + usdc(bal));
  if (bal < maxAmount) {
    console.log('Insufficient USDC!');
    return;
  }

  // Step 2: Transfer USDC
  console.log('\n[2] Sending ' + amountStr + ' USDC to ' + payTo + '...');
  let txHash;
  try {
    txHash = await walletClient.writeContract({
      address: USDC_ADDRESS,
      abi: USDC_ABI,
      functionName: 'transfer',
      args: [payTo, maxAmount],
    });
    console.log('Tx: ' + txHash);
    await publicClient.waitForTransactionReceipt({ hash: txHash });
    console.log('Confirmed!');
  } catch(e) {
    console.log('Transfer failed: ' + (e.shortMessage || e.message));
    return;
  }

  // Step 3: Call with X-PAYMENT header (exact scheme: exact:<payTo>:<amount>:<txHash>)
  console.log('\n[3] Calling service with payment proof...');
  const paymentHeader = 'exact:' + payTo + ':' + maxAmount.toString() + ':' + txHash;
  console.log('X-PAYMENT: ' + paymentHeader);
  const paidOpts = {
    method: body ? 'POST' : 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'X-PAYMENT': paymentHeader,
    },
  };
  if (body) paidOpts.body = JSON.stringify(body);

  res = await fetch(serviceUrl, paidOpts);
  text = await res.text();
  console.log('Status: ' + res.status);
  console.log('Headers: ' + JSON.stringify(Object.fromEntries(Object.entries(Object.fromEntries(res.headers)).slice(0, 10))));
  console.log('Response: ' + text.slice(0, 600));
}

async function main() {
  // Firecrawl URL scrape
  await payAndCall(
    'https://mesh.heurist.xyz/x402/agents/FirecrawlSearchDigestAgent/firecrawl_scrape_url',
    { url: 'https://en.wikipedia.org/wiki/Artificial_intelligence', limit: 1 },
    'Firecrawl Web Scrape'
  );
}

main().catch(console.error);
