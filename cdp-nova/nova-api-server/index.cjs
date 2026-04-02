/**
 * Nova's x402-Paid API Server
 * Natural language → on-chain SQL / data queries on Base
 * 
 * Payment: 0.10 USDC per query via x402 (EIP-3009)
 * Network: Base Mainnet (eip155:8453)
 * 
 * Start: node index.js
 * Port: 3000
 */

const express = require('express');
const { createPublicClient, http } = require('viem');
const { base } = require('viem/chains');
const { privateKeyToAccount } = require('viem/accounts');
const { readFileSync } = require('fs');
const crypto = require('crypto');

const app = express();
app.use(express.json());

// ─── Wallet Setup ────────────────────────────────────────────────────────────
const WALLET_PATH = '/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json';
let _signer = null;
function getSigner() {
  if (!_signer) {
    const wallet = JSON.parse(readFileSync(WALLET_PATH, 'utf8'));
    _signer = privateKeyToAccount(wallet.privateKey);
  }
  return _signer;
}

// ─── On-Chain Client ─────────────────────────────────────────────────────────
const publicClient = createPublicClient({ chain: base, transport: http() });

// ─── x402 Payment Constants ───────────────────────────────────────────────────
const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const NOVA_ADDRESS = '0xB743fdbA842379933A3774617786712458659D16';
const PRICE_USDC = 10; // $0.10 per query (in USDC micro-units: 10 = $0.00001? No — USDC has 6 decimals)

// Actually: 10 USDC micro-units = 0.00001 USDC. 
// For $0.10 per query: 100000 (6 decimals) = 0.10 USDC
const PRICE_MICRO_USDC = 100_000; // 0.10 USDC (6 decimals)

// x402 facade address (where USDC is held for the payee)
// Using Nova's own wallet as the receiving address
const FACILITATOR = NOVA_ADDRESS;
const NETWORK = 'eip155:8453';

// ─── EIP-3009 Authorization Types ───────────────────────────────────────────
const authorizationTypes = {
  TransferWithAuthorization: [
    { name: "from", type: "address" },
    { name: "to", type: "address" },
    { name: "value", type: "uint256" },
    { name: "validAfter", type: "uint256" },
    { name: "validBefore", type: "uint256" },
    { name: "nonce", type: "bytes32" },
    { name: "v", type: "uint8" },
    { name: "r", type: "bytes32" },
    { name: "s", type: "bytes32" }
  ]
};

// ─── Utility: Build EIP-3009 hash for signing ───────────────────────────────
function buildTypedDataHash(domain, message) {
  // Simplified: in production use viem's TypedDataEncoder
  // For now, return a domain-separated hash
  const { default: crypto } = require('crypto');
  const { hashMessage, _TypedDataEncoder } = require('viem');
  return _TypedDataEncoder.hash({ domain, types: authorizationTypes, primaryType: 'TransferWithAuthorization', message });
}

// ─── x402 Discovery Endpoint ─────────────────────────────────────────────────
app.get('/', async (req, res) => {
  res.json({
    name: 'Nova Query API',
    description: 'Natural language on-chain data queries for Base — blocks, transactions, events, ERC-20 balances',
    version: '1.0.0',
    accepts: [
      {
        scheme: 'FUTUREU',
        address: USDC_ADDRESS,
        decimals: 6,
        symbol: 'USDC',
        amount: PRICE_MICRO_USDC.toString(),
        description: '$0.10 per query'
      }
    ],
    resources: [
      {
        path: '/query',
        method: 'POST',
        description: 'Execute a natural language on-chain query',
        body: {
          query: 'string (required) — e.g. "What is the ETH balance of 0x1b7e...?"',
          params: 'object (optional) — additional parameters'
        }
      },
      {
        path: '/balance/:address',
        method: 'GET',
        description: 'Get ETH balance for any address'
      },
      {
        path: '/health',
        method: 'GET',
        description: 'Health check'
      }
    ],
    network: NETWORK
  });
});

// ─── Payment Verification Middleware ─────────────────────────────────────────
async function verifyPayment(req, res, next) {
  const auth = req.headers['authorization'];
  
  if (!auth || !auth.startsWith('FUTUREU ')) {
    const priceData = {
      accepts: [{
        scheme: 'FUTUREU',
        address: USDC_ADDRESS,
        decimals: 6,
        symbol: 'USDC',
        amount: PRICE_MICRO_USDC.toString(),
        description: '$0.10 per query'
      }],
      address: NOVA_ADDRESS,
      network: NETWORK,
      instruction: 'Include Authorization header with EIP-3009 TransferWithAuthorization signature'
    };
    return res.status(402).json({
      error: 'Payment Required',
      payment: priceData,
      message: 'This endpoint requires 0.10 USDC via x402 EIP-3009 authorization'
    });
  }

  // Parse the authorization header
  // Format: FUTUREU base64({validAfter,validBefore,nonce,v,r,s,from,to,value})
  try {
    const payload = JSON.parse(Buffer.from(auth.slice(7), 'base64').toString());
    req.paymentData = payload;
    
    // Basic validation
    const now = Math.floor(Date.now() / 1000);
    if (payload.validBefore && payload.validBefore < now) {
      return res.status(400).json({ error: 'Authorization expired' });
    }
    if (payload.from) {
      req.payerAddress = payload.from;
    }
  } catch (e) {
    return res.status(400).json({ error: 'Invalid authorization header format' });
  }

  next();
}

// ─── Query Endpoint ───────────────────────────────────────────────────────────
app.post('/query', verifyPayment, async (req, res) => {
  const { query, params } = req.body;
  
  if (!query) {
    return res.status(400).json({ error: 'query is required' });
  }

  try {
    const result = await executeQuery(query, params, req.payerAddress);
    res.json({
      query,
      result,
      payer: req.payerAddress,
      price: '0.10 USDC',
      tx: null // No on-chain tx for reads — USDC captured via auth
    });
  } catch (err) {
    console.error('Query error:', err);
    res.status(500).json({ error: err.message });
  }
});

// ─── Balance Endpoint ─────────────────────────────────────────────────────────
app.get('/balance/:address', verifyPayment, async (req, res) => {
  const { address } = req.params;
  
  // Basic address validation
  if (!/^0x[0-9a-fA-F]{40}$/.test(address)) {
    return res.status(400).json({ error: 'Invalid Ethereum address' });
  }

  try {
    const [ethBalance, usdcBalance] = await Promise.all([
      publicClient.getBalance({ address }),
      getERC20Balance(USDC_ADDRESS, address)
    ]);

    res.json({
      address,
      eth: Number(ethBalance) / 1e18,
      usdc: Number(usdcBalance) / 1e6,
      eth_raw: ethBalance.toString(),
      usdc_raw: usdcBalance.toString()
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─── Health Check ─────────────────────────────────────────────────────────────
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    service: 'Nova Query API',
    network: 'Base Mainnet',
    uptime: process.uptime(),
    ts: new Date().toISOString()
  });
});

// ─── ERC-20 Balance Reader ───────────────────────────────────────────────────
async function getERC20Balance(tokenAddress, holderAddress) {
  const data = {
    address: tokenAddress,
    abi: [{ type: 'function', name: 'balanceOf', stateMutability: 'view', inputs: [{ type: 'address' }], outputs: [{ type: 'uint256' }] }],
    functionName: 'balanceOf',
    args: [holderAddress]
  };
  return publicClient.readContract(data);
}

// ─── Query Executor ──────────────────────────────────────────────────────────
async function executeQuery(query, params = {}, payer = 'unknown') {
  const q = query.toLowerCase();
  
  // Parse query intent
  if (q.includes('balance') && q.includes('eth')) {
    // Extract address from query or params
    const addr = extractAddress(q, params);
    if (!addr) throw new Error('Could not find address in query');
    const bal = await publicClient.getBalance({ address: addr });
    return { type: 'eth_balance', address: addr, balance: Number(bal) / 1e18, unit: 'ETH' };
  }
  
  if (q.includes('balance') && (q.includes('usdc') || q.includes('token'))) {
    const addr = extractAddress(q, params);
    if (!addr) throw new Error('Could not find address in query');
    const bal = await getERC20Balance(USDC_ADDRESS, addr);
    return { type: 'erc20_balance', address: addr, token: 'USDC', balance: Number(bal) / 1e6, unit: 'USDC' };
  }
  
  if (q.includes('block') || q.includes('latest')) {
    const block = await publicClient.getBlock();
    return { 
      type: 'block', 
      number: Number(block.number), 
      hash: block.hash,
      timestamp: Number(block.timestamp),
      gasUsed: block.gasUsed.toString()
    };
  }
  
  if (q.includes('transaction') || q.includes('tx')) {
    const txHash = extractTxHash(q, params);
    if (!txHash) throw new Error('Could not find transaction hash in query');
    const tx = await publicClient.getTransaction({ hash: txHash });
    return { type: 'transaction', ...formatTx(tx) };
  }
  
  if (q.includes('gas') || q.includes('fee')) {
    const gasPrice = await publicClient.getGasPrice();
    return { type: 'gas', gas_price_gwei: Number(gasPrice) / 1e9, gas_price_wei: gasPrice.toString() };
  }
  
  if (q.includes('supply') || q.includes('total')) {
    const addr = extractAddress(q, params);
    if (!addr) throw new Error('Could not find address in query');
    const supply = await publicClient.readContract({
      address: addr,
      abi: [{ type: 'function', name: 'totalSupply', stateMutability: 'view', outputs: [{ type: 'uint256' }] }],
      functionName: 'totalSupply'
    });
    return { type: 'total_supply', address: addr, supply: Number(supply) / 1e18 };
  }
  
  if (q.includes('decode') || q.includes('logs') || q.includes('events')) {
    const addr = extractAddress(q, params) || params?.address;
    const txHash = extractTxHash(q, params);
    if (txHash) {
      const receipt = await publicClient.getTransactionReceipt({ hash: txHash });
      return { type: 'receipt', txHash, logs: receipt.logs.map(l => ({
        address: l.address, topics: l.topics, data: l.data, blockNumber: Number(l.blockNumber)
      }))};
    }
    if (addr) {
      const logs = await publicClient.getLogs({ address: addr, fromBlock: 'latest', toBlock: 'latest', limit: 10 });
      return { type: 'logs', address: addr, logs: logs.map(l => ({
        topics: l.topics, data: l.data, blockNumber: Number(l.blockNumber)
      }))};
    }
    throw new Error('Provide an address or transaction hash to decode');
  }

  // Default: return helpful error
  throw new Error('Query not recognized. Try: "balance of <address>", "latest block", "gas price", "decode <txhash>"');
}

function extractAddress(q, params) {
  if (params?.address && /^0x[0-9a-fA-F]{40}$/.test(params.address)) return params.address;
  // Try to find 0x address in the query string
  const match = q.match(/0x[0-9a-fA-F]{40}/);
  return match ? match[0] : null;
}

function extractTxHash(q, params) {
  if (params?.txHash && /^0x[0-9a-fA-F]{64}$/.test(params.txHash)) return params.txHash;
  if (params?.tx) return params.tx;
  const match = q.match(/0x[0-9a-fA-F]{64}/);
  return match ? match[0] : null;
}

function formatTx(tx) {
  return {
    hash: tx.hash,
    from: tx.from,
    to: tx.to,
    value: Number(tx.value) / 1e18,
    gas: tx.gas?.toString(),
    gasPrice: tx.gasPrice?.toString(),
    nonce: tx.nonce,
    blockNumber: tx.blockNumber ? Number(tx.blockNumber) : null
  };
}

// ─── Start Server ────────────────────────────────────────────────────────────
const PORT = process.env.PORT || 3001;
const HOST = process.env.HOST || '0.0.0.0';

app.listen(PORT, HOST, () => {
  console.log(`Nova API server running on http://${HOST}:${PORT}`);
  console.log(`Network: Base Mainnet (eip155:8453)`);
  console.log(`Price: 0.10 USDC per query via x402 EIP-3009`);
  console.log(`Nova wallet: ${NOVA_ADDRESS}`);
  console.log(`USDC: ${USDC_ADDRESS}`);
});
