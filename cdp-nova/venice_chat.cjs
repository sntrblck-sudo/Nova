/**
 * Nova's Venice AI Client v2 — using @x402/extensions wrapFetchWithSIWx
 * No API keys needed. Pays for AI inference via wallet x402.
 * 
 * Usage:
 *   const { veniceChat } = require('./venice_chat.cjs');
 *   const response = await veniceChat("Hello!", { model: "kimi-k2-5" });
 */

const { SiweMessage } = require('siwe');
const { privateKeyToAccount } = require('viem/accounts');
const { wrapFetchWithSIWx, createSIWxMessage, createSIWxPayload, encodeSIWxHeader } = require('@x402/extensions');
const https = require('https');

const WALLET_PATH = '/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json';
const VENICE_API = 'https://api.venice.ai/api/v1';
const DEFAULT_MODEL = 'kimi-k2-5';

// ─── Wallet Setup ─────────────────────────────────────────────────────────────
let _walletData, _account, _address;
function getWallet() {
  if (!_walletData) {
    _walletData = JSON.parse(require('fs').readFileSync(WALLET_PATH, 'utf8'));
    _account = privateKeyToAccount(_walletData.privateKey);
    _address = _account.address;
  }
  return { account: _account, address: _address };
}

// ─── SIWx Signer for wrapFetchWithSIWx ──────────────────────────────────────
// wrapFetchWithSIWx needs a signer(message: string) => Promise<{ signature, address }>
function createVeniceSigner() {
  const { account, address } = getWallet();
  
  return async (message) => {
    const sig = await account.signMessage({ message });
    return { signature: sig, address };
  };
}

// ─── HTTP Fetch helper ────────────────────────────────────────────────────────
function httpsFetch(url, options = {}) {
  return new Promise((resolve, reject) => {
    const urlObj = new URL(url);
    const req = https.request({
      hostname: urlObj.hostname,
      path: urlObj.pathname + urlObj.search,
      method: options.method || 'GET',
      headers: options.headers || {}
    }, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try { resolve({ ok: res.statusCode >= 200 && res.statusCode < 300, status: res.statusCode, data: JSON.parse(data), headers: res.headers }); }
        catch { resolve({ ok: false, status: res.statusCode, data, headers: res.headers }); }
      });
    });
    req.on('error', reject);
    if (options.body) req.write(options.body);
    req.end();
  });
}

// ─── Main Chat Function ───────────────────────────────────────────────────────
async function veniceChat(prompt, opts = {}) {
  const model = opts.model || DEFAULT_MODEL;
  const maxTokens = opts.max_tokens || 1024;
  const { address } = getWallet();

  // Build SIWx message for Venice
  const now = new Date();
  const exp = new Date(now.getTime() + 10 * 60 * 1000);
  const nonce = Math.random().toString(36).substring(2, 15);

  const siweMsg = createSIWxMessage({
    domain: 'outerface.venice.ai',
    address,
    uri: 'https://outerface.venice.ai',
    version: '1',
    chainId: 8453,
    nonce,
    issuedAt: now.toISOString(),
    expirationTime: exp.toISOString(),
    statement: 'Sign in with Ethereum to Venice AI'
  });

  // Get wallet signature
  const { account } = getWallet();
  const sig = await account.signMessage({ message: siweMsg });

  // Build payload and encode as header
  const payload = createSIWxPayload({
    address,
    message: siweMsg,
    signature: sig,
    chainId: 8453
  });
  const authHeader = encodeSIWxHeader(payload);

  const body = JSON.stringify({
    model,
    messages: [{ role: 'user', content: prompt }],
    max_tokens: maxTokens
  });

  const headers = {
    'Content-Type': 'application/json',
    'X-Sign-In-With-X': authHeader,
    'User-Agent': 'Nova-Venice/1.0'
  };

  // First check balance
  const balanceData = await httpsFetch(`${VENICE_API}/x402/balance/${address}`, { headers });
  console.log('[Venice] Balance check:', JSON.stringify(balanceData.data));

  // Make the chat request
  const response = await httpsFetch(`${VENICE_API}/chat/completions`, {
    method: 'POST',
    headers,
    body
  });

  return response;
}

// ─── Quick test ──────────────────────────────────────────────────────────────
async function main() {
  console.log('Nova Venice Client v2\n');
  
  const { address } = getWallet();
  console.log('Wallet:', address);
  console.log();

  const result = await veniceChat('Say hello in one sentence. Be brief.');
  
  console.log('\nResponse:');
  if (result.ok) {
    console.log(JSON.stringify(result.data, null, 2));
  } else {
    console.log('Status:', result.status);
    console.log(JSON.stringify(result.data, null, 2));
  }
}

// CLI
const args = process.argv.slice(2);
if (args[0] === '--balance') {
  const { address } = getWallet();
  httpsFetch(`${VENICE_API}/x402/balance/${address}`, {
    headers: { 'User-Agent': 'Nova-Venice/1.0' }
  }).then(r => console.log(JSON.stringify(r.data, null, 2)));
} else if (args.length > 0) {
  veniceChat(args.join(' ')).then(r => {
    console.log(JSON.stringify(r.data, null, 2));
  });
} else {
  main();
}

module.exports = { veniceChat };
