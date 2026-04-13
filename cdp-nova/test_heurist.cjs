const { privateKeyToAccount } = require('viem/accounts');
const { base } = require('viem/chains');
const { createWalletClient, http } = require('viem');
const { readFileSync } = require('fs');

const WALLET_PATH = '/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json';
const wallet = JSON.parse(readFileSync(WALLET_PATH, 'utf8'));
const account = privateKeyToAccount(wallet.privateKey);
const walletClient = createWalletClient({ account, chain: base, transport: http('https://mainnet.base.org') });

async function callX402Service(url, body) {
  const method = body ? 'POST' : 'GET';
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', 'User-Agent': 'Nova/1.0' },
  };
  if (body) opts.body = JSON.stringify(body);

  console.log(`\n📡 ${method} ${url}`);
  let res = await fetch(url, opts);
  let text = await res.text();
  
  if (res.status === 402) {
    console.log('💰 Got 402 — parsing payment instructions...');
    const data = JSON.parse(text);
    console.log(JSON.stringify(data, null, 2).slice(0, 1000));
    return data;
  } else {
    console.log(`Status: ${res.status} | ${text.slice(0, 300)}`);
    return null;
  }
}

async function main() {
  // Try Etherscan wallet analysis
  await callX402Service(
    'https://mesh.heurist.xyz/x402/agents/EtherscanAgent/get_address_history?address=0xB743fdbA842379933A3774617786712458659D16',
    null
  );
}

main().catch(console.error);
