/**
 * Nova's Venice AI Client — x402 payment via SIWE
 * Pays for AI inference from Venice using Nova's Base wallet balance.
 * 
 * No API keys needed — just Nova's private key and USDC on Base.
 */

const { SiweMessage } = require('siwe');
const { createWalletClient, http } = require('viem');
const { base } = require('viem/chains');
const { privateKeyToAccount } = require('viem/accounts');
const https = require('https');

// ─── Config ───────────────────────────────────────────────────────────────────
const WALLET_PATH = '/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json';
const VENICE_BASE_URL = 'api.venice.ai';
const VENICE_API_PATH = '/api/v1/chat/completions';
const VENICE_CHAT_MODEL = 'kimi-k2-5';  // Venice's flagship model

// ─── SIWE Message Builder ─────────────────────────────────────────────────────
function buildSiweMessage(address, chainId = 8453) {
  const now = new Date();
  const expirationTime = new Date(now.getTime() + 10 * 60 * 1000); // 10 min

  const domain = 'outerface.venice.ai';
  const uri = 'https://outerface.venice.ai';
  const version = '1';
  const nonce = Math.random().toString(36).substring(2, 15);

  const message = new SiweMessage({
    domain,
    address,
    uri,
    version,
    chainId,
    nonce,
    issuedAt: now.toISOString(),
    expirationTime: expirationTime.toISOString(),
    statement: 'Sign in with Ethereum to Venice AI',
  });

  return message.prepareMessage();
}

// ─── SIWE Signer ──────────────────────────────────────────────────────────────
async function signSiwe(message, privateKey) {
  const account = privateKeyToAccount(privateKey);
  const signature = account.sign({ message });
  return signature;
}

// ─── Auth Header Builder ──────────────────────────────────────────────────────
function buildAuthHeader(address, message, signature, chainId = 8453) {
  const payload = {
    address,
    message,
    signature,
    chainId,
    timestamp: Date.now()
  };
  // Base64 encode the JSON payload
  return Buffer.from(JSON.stringify(payload)).toString('base64');
}

// ─── HTTP Request Helper ──────────────────────────────────────────────────────
function httpsRequest(host, path, headers, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const opts = {
      hostname: host,
      path,
      method: 'POST',
      headers: {
        ...headers,
        'Content-Length': Buffer.byteLength(data)
      }
    };

    const req = https.request(opts, (res) => {
      let responseData = '';
      res.on('data', chunk => responseData += chunk);
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, data: JSON.parse(responseData) });
        } catch {
          resolve({ status: res.statusCode, data: responseData });
        }
      });
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

// ─── Check Balance ────────────────────────────────────────────────────────────
async function checkBalance(address) {
  return new Promise((resolve, reject) => {
    const opts = {
      hostname: VENICE_BASE_URL,
      path: `/api/v1/x402/balance/${address}`,
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    };
    const req = https.request(opts, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); } catch { resolve(data); }
      });
    });
    req.on('error', reject);
    req.end();
  });
}

// ─── Main Chat Function ───────────────────────────────────────────────────────
async function chat(prompt, model = VENICE_CHAT_MODEL) {
  // Load wallet
  const walletData = JSON.parse(require('fs').readFileSync(WALLET_PATH, 'utf8'));
  const privateKey = walletData.privateKey;
  const account = privateKeyToAccount(privateKey);
  const address = account.address;

  console.log(`[Venice] Using wallet: ${address}`);

  // Check balance first
  const balance = await checkBalance(address);
  console.log('[Venice] Balance:', JSON.stringify(balance));

  // Build and sign SIWE message
  const siweMessage = buildSiweMessage(address);
  const signature = await signSiwe(siweMessage, privateKey);
  const authHeader = buildAuthHeader(address, siweMessage, signature);

  // Build request
  const headers = {
    'Content-Type': 'application/json',
    'X-Sign-In-With-X': authHeader,
    'User-Agent': 'Nova-Venice/1.0'
  };

  const body = {
    model,
    messages: [{ role: 'user', content: prompt }],
    max_tokens: 1024
  };

  console.log('[Venice] Sending chat request...');
  const response = await httpsRequest(VENICE_BASE_URL, VENICE_API_PATH, headers, body);
  
  if (response.status === 402) {
    console.log('[Venice] 402 Payment Required — insufficient balance');
    return { error: 'insufficient_balance', details: response.data };
  }

  return response;
}

// ─── CLI ──────────────────────────────────────────────────────────────────────
const [, , ...args] = process.argv;

if (args.includes('--balance')) {
  const walletData = JSON.parse(require('fs').readFileSync(WALLET_PATH, 'utf8'));
  const account = privateKeyToAccount(walletData.privateKey);
  checkBalance(account.address).then(b => console.log('Balance:', JSON.stringify(b, null, 2)));
} else if (args[0]) {
  chat(args.join(' ')).then(r => console.log(JSON.stringify(r, null, 2)));
} else {
  console.log(`
Nova Venice Client — x402 AI inference
Usage:
  node venice_client.js "your prompt here"
  node venice_client.js --balance
  `);
}

module.exports = { chat, checkBalance };
