/**
 * Nova's x402 API Server v3
 * Native ETH payment verification + x402 Bazaar auto-discovery
 * 
 * Payment: 0.00001 ETH (native ETH on Base Mainnet)
 * - No facilitator needed — server verifies ETH tx directly via receipt
 * - Uses x402 headers for discoverability and protocol compliance
 * - Auto-registers with x402 Bazaar via declareDiscoveryExtension
 * 
 * Start: node nova-api-server/x402_server.cjs
 * Port: 3001
 */

const express = require('express');
const { createPublicClient, http } = require('viem');
const { base } = require('viem/chains');
const { declareDiscoveryExtension } = require('@x402/extensions/bazaar');

const app = express();
app.use(express.json());

// ─── Config ─────────────────────────────────────────────────────────────────
const NOVA_ADDRESS = '0xB743fdbA842379933A3774617786712458659D16';
const PRICE_WEI = 10_000_000_000_000n; // 0.00001 ETH
const PRICE_ETH = 0.00001;
const NETWORK = 'eip155:8453';
const SCHEME = 'native';

// ─── On-Chain Client ─────────────────────────────────────────────────────────
const publicClient = createPublicClient({ chain: base, transport: http() });

// ─── Route Key Resolver ─────────────────────────────────────────────────────
function resolveRouteKey(req) {
  const path = req.originalUrl?.split('?')[0] || req.path;
  if (path.startsWith('/balance/')) return 'GET /balance/:address';
  if (path.startsWith('/query')) return 'POST /query';
  return `${req.method} ${path}`;
}

// ─── x402 Route Manifest ────────────────────────────────────────────────────
const X402_ROUTES = {
  'GET /balance/:address': {
    accepts: {
      scheme: SCHEME,
      address: NOVA_ADDRESS,
      decimals: 18,
      symbol: 'ETH',
      amount: PRICE_WEI.toString(),
      network: NETWORK,
      description: '0.00001 ETH per query'
    },
    description: 'Get ETH and USDC balance for any Base address',
    mimeType: 'application/json',
    extensions: declareDiscoveryExtension({
      output: {
        example: {
          address: '0x1b7eDF6F5FCAb52b680661cC82306E3DaCA7943C',
          eth: 0.5,
          usdc: 100.0
        },
        schema: {
          type: 'object',
          properties: {
            address: { type: 'string' },
            eth: { type: 'number' },
            usdc: { type: 'number' }
          }
        }
      }
    })
  },
  'POST /query': {
    accepts: {
      scheme: SCHEME,
      address: NOVA_ADDRESS,
      decimals: 18,
      symbol: 'ETH',
      amount: PRICE_WEI.toString(),
      network: NETWORK,
      description: '0.00001 ETH per query'
    },
    description: 'Natural language on-chain query — blocks, wallets, transactions, events, ERC-20 balances',
    mimeType: 'application/json',
    extensions: declareDiscoveryExtension({
      output: {
        example: { type: 'block', number: 12345678, hash: '0x...' },
        schema: { type: 'object' }
      }
    })
  }
};

// ─── x402 Payment Verification ──────────────────────────────────────────────
function verifyX402Payment(req) {
  const txHash = req.headers['x-payment-tx'];
  if (!txHash) return { needsPayment: true };
  if (!/^0x[0-9a-fA-F]{64}$/.test(txHash)) return { error: 'Invalid tx hash format' };
  return { txHash, needsPayment: false };
}

function sendPaymentError(res, routeKey) {
  const route = X402_ROUTES[routeKey];
  return res.status(402).json({
    error: 'Payment Required',
    payment: {
      scheme: SCHEME,
      address: NOVA_ADDRESS,
      amount: PRICE_WEI.toString(),
      decimals: 18,
      symbol: 'ETH',
      network: NETWORK,
      description: route?.accepts?.description || '0.00001 ETH per query'
    },
    instructions: `Send ${PRICE_ETH} ETH to ${NOVA_ADDRESS} on Base, then include tx hash as X-PAYMENT-TX header`
  });
}

async function verifyAndServe(req, res, handler) {
  const routeKey = resolveRouteKey(req);
  const check = verifyX402Payment(req);
  if (check.needsPayment) return sendPaymentError(res, routeKey);
  if (check.error) return res.status(400).json({ error: check.error });

  try {
    const receipt = await publicClient.getTransactionReceipt({ hash: check.txHash });
    if (receipt.status !== 'success') return res.status(400).json({ error: 'Payment tx failed on-chain' });
    
    const txTo = typeof receipt.to === 'string' ? receipt.to : receipt.to?.toString();
    if (txTo?.toLowerCase() !== NOVA_ADDRESS.toLowerCase()) {
      return res.status(400).json({ error: `Payment must be sent to ${NOVA_ADDRESS}` });
    }
    if (receipt.value < PRICE_WEI) {
      return res.status(400).json({ error: 'Insufficient payment amount', required: `${PRICE_ETH} ETH`, received: `${Number(receipt.value)/1e18} ETH` });
    }

    await handler(req, res, check.txHash);
  } catch (err) {
    if (err.message?.includes('not found')) {
      return res.status(400).json({ error: 'Transaction not found — wait for confirmation and retry' });
    }
    console.error('Error:', err);
    res.status(500).json({ error: err.message });
  }
}

// ─── Free Endpoints ─────────────────────────────────────────────────────────
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'Nova Query API v3', network: NETWORK, price: `${PRICE_ETH} ETH/query`, uptime: process.uptime(), ts: new Date().toISOString() });
});

app.get('/pay', (req, res) => {
  res.json({ address: NOVA_ADDRESS, amount: `${PRICE_ETH} ETH`, amountWei: PRICE_WEI.toString(), network: NETWORK, instructions: `Send ETH to ${NOVA_ADDRESS}, then include tx hash as X-PAYMENT-TX header` });
});

app.get('/', (req, res) => {
  res.json({ name: 'Nova Query API', description: 'Natural language on-chain queries on Base', version: '3.0.0', network: NETWORK, price: `${PRICE_ETH} ETH/query`, paymentAddress: NOVA_ADDRESS, scheme: SCHEME, endpoints: { free: ['/', '/health', '/pay'], paid: ['/balance/:address', '/query'] } });
});

// ─── Paid Endpoint: GET /balance/:address ───────────────────────────────────
app.get('/balance/:address', (req, res) => {
  verifyAndServe(req, res, async (req, res, txHash) => {
    const { address } = req.params;
    if (!/^0x[0-9a-fA-F]{40}$/.test(address)) return res.status(400).json({ error: 'Invalid Ethereum address' });

    const [ethBalance, usdcBalance] = await Promise.all([
      publicClient.getBalance({ address }),
      getERC20Balance('0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', address)
    ]);

    res.json({ address, eth: Number(ethBalance)/1e18, usdc: Number(usdcBalance)/1e6, payment: { txHash, amount: `${PRICE_ETH} ETH`, scheme: SCHEME } });
  });
});

// ─── Paid Endpoint: POST /query ─────────────────────────────────────────────
app.post('/query', (req, res) => {
  verifyAndServe(req, res, async (req, res, txHash) => {
    const { query, params } = req.body;
    if (!query) return res.status(400).json({ error: 'query is required' });

    const result = await executeQuery(query, params);
    res.json({ query, result, payment: { txHash, amount: `${PRICE_ETH} ETH`, scheme: SCHEME } });
  });
});

// ─── ERC-20 Balance ─────────────────────────────────────────────────────────
async function getERC20Balance(tokenAddress, holderAddress) {
  return publicClient.readContract({
    address: tokenAddress,
    abi: [{ type: 'function', name: 'balanceOf', stateMutability: 'view', inputs: [{ type: 'address' }], outputs: [{ type: 'uint256' }] }],
    functionName: 'balanceOf', args: [holderAddress]
  });
}

// ─── Query Executor ─────────────────────────────────────────────────────────
async function executeQuery(query, params = {}) {
  const q = query.toLowerCase();
  
  if (q.includes('balance') && q.includes('eth')) {
    const addr = extractAddress(q, params);
    if (!addr) throw new Error('Address not found');
    return { type: 'eth_balance', address: addr, balance: Number(await publicClient.getBalance({ address: addr }))/1e18, unit: 'ETH' };
  }
  if (q.includes('balance') && (q.includes('usdc') || q.includes('token'))) {
    const addr = extractAddress(q, params);
    if (!addr) throw new Error('Address not found');
    return { type: 'erc20_balance', address: addr, token: 'USDC', balance: Number(await getERC20Balance('0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', addr))/1e6, unit: 'USDC' };
  }
  if (q.includes('block') || q.includes('latest')) {
    const block = await publicClient.getBlock();
    return { type: 'block', number: Number(block.number), hash: block.hash, timestamp: Number(block.timestamp), gasUsed: block.gasUsed.toString() };
  }
  if (q.includes('transaction') || q.includes('tx')) {
    const txHash = extractTxHash(q, params);
    if (!txHash) throw new Error('Tx hash not found');
    const tx = await publicClient.getTransaction({ hash: txHash });
    return { type: 'transaction', hash: tx.hash, from: tx.from, to: tx.to, value: Number(tx.value)/1e18, blockNumber: tx.blockNumber ? Number(tx.blockNumber) : null };
  }
  if (q.includes('gas') || q.includes('fee')) {
    return { type: 'gas', gas_price_gwei: Number(await publicClient.getGasPrice())/1e9 };
  }
  if (q.includes('supply') || q.includes('total')) {
    const addr = extractAddress(q, params);
    if (!addr) throw new Error('Address not found');
    const supply = await publicClient.readContract({ address: addr, abi: [{ type: 'function', name: 'totalSupply', outputs: [{ type: 'uint256' }] }], functionName: 'totalSupply' });
    return { type: 'total_supply', address: addr, supply: Number(supply)/1e18 };
  }
  if (q.includes('decode') || q.includes('logs') || q.includes('events')) {
    const txHash = extractTxHash(q, params) || params?.txHash;
    if (!txHash) throw new Error('Tx hash required');
    const receipt = await publicClient.getTransactionReceipt({ hash: txHash });
    return { type: 'receipt', txHash, logs: receipt.logs.map(l => ({ address: l.address, topics: l.topics, data: l.data }))};
  }
  throw new Error('Query not recognized. Try: "balance of <address>", "latest block", "gas price", "decode <txhash>"');
}

function extractAddress(q, params) {
  if (params?.address && /^0x[0-9a-fA-F]{40}$/.test(params.address)) return params.address;
  const match = q.match(/0x[0-9a-fA-F]{40}/);
  return match ? match[0] : null;
}

function extractTxHash(q, params) {
  if (params?.txHash && /^0x[0-9a-fA-F]{64}$/.test(params.txHash)) return params.txHash;
  const match = q.match(/0x[0-9a-fA-F]{64}/);
  return match ? match[0] : null;
}

// ─── Start ─────────────────────────────────────────────────────────────────
const PORT = process.env.PORT || 3001;
app.listen(PORT, '0.0.0.0', () => {
  console.log(`Nova API v3 running on http://0.0.0.0:${PORT}`);
  console.log(`Network: ${NETWORK} | Price: ${PRICE_ETH} ETH/query | Scheme: ${SCHEME} (self-verified)`);
  console.log(`Payment address: ${NOVA_ADDRESS}`);
});
