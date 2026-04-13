const { privateKeyToAccount } = require('viem/accounts');
const { base } = require('viem/chains');
const { createWalletClient, http, createPublicClient } = require('viem');
const { readFileSync } = require('fs');

const WALLET_PATH = '/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json';
const NOVA_ADDRESS = '0xB743fdbA842379933A3774617786712458659D16';
const RPC_URL = 'https://mainnet.base.org';

const wallet = JSON.parse(readFileSync(WALLET_PATH, 'utf8'));
const account = privateKeyToAccount(wallet.privateKey);

const walletClient = createWalletClient({ account, chain: base, transport: http(RPC_URL) });
const publicClient = createPublicClient({ chain: base, transport: http(RPC_URL) });

async function tryService(url, body) {
  const method = body ? 'POST' : 'GET';
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  
  console.log(`\n📡 ${method} ${url}`);
  const res = await fetch(url, opts);
  const text = await res.text();
  
  if (res.status === 402) {
    console.log(`💰 402 Payment Required`);
    try {
      const data = JSON.parse(text);
      console.log(JSON.stringify(data, null, 2).slice(0, 800));
    } catch { console.log(text.slice(0, 400)); }
  } else {
    console.log(`Status: ${res.status} | ${text.slice(0, 200)}`);
  }
}

async function main() {
  await tryService(
    'https://mesh.heurist.xyz/x402/agents/EtherscanAgent/get_addr?address=0xB743fdbA842379933A3774617786712458659D16',
    null
  );
  await tryService(
    'https://mesh.heurist.xyz/x402/agents/TrendingTokenAgent/get_trending',
    { limit: 3 }
  );
}

main().catch(console.error);
