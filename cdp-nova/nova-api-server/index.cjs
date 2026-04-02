/**
 * Nova's ETH-Paid API Server
 * Natural language → on-chain SQL / data queries on Base
 * 
 * Payment: 0.00001 ETH per query (~$0.03 equivalent to $0.10 USDC)
 * Network: Base Mainnet (eip155:8453)
 * 
 * Flow: Client sends ETH to Nova's address first, then calls API with tx hash.
 *       Server verifies tx receipt → payment confirmed → returns data.
 * 
 * Start: node index.cjs
 * Port: 3001
 */

const express = require('express');
const { createPublicClient, http } = require('viem');
const { base } = require('viem/chains');
const { readFileSync } = require('fs');

const app = express();
app.use(express.json());

// ─── On-Chain Client ─────────────────────────────────────────────────────────
const publicClient = createPublicClient({ chain: base, transport: http() });

// ─── Payment Constants ────────────────────────────────────────────────────────
const NOVA_ADDRESS = '0xB743fdbA842379933A3774617786712458659D16';
const PRICE_WEI = 10_000_000_000_000n; // 0.00001 ETH (10^16 wei)
const PRICE_ETH = 0.00001;
const NETWORK = 'eip155:8453';

// ─── x402 Discovery ──────────────────────────────────────────────────────────
app.get('/', (req, res) => {
  res.json({
    name: 'Nova Query API',
    description: 'Natural language on-chain data queries for Base — blocks, transactions, events, ERC-20 balances',
    version: '2.0.0',
    accepts: [{
      scheme: 'native',
      address: NOVA_ADDRESS,
      decimals: 18,
      symbol: 'ETH',
      amount: PRICE_WEI.toString(),
      description: '0.00001 ETH per query'
    }],
    instructions: {
      step1: `Send ${PRICE_ETH} ETH to ${NOVA_ADDRESS}`,
      step2: 'Call any endpoint with header X-PAYMENT-TX: <your tx hash>',
      step3: 'Data returned on valid payment'
    },
    resources: [
      { path: '/query', method: 'POST', description: 'Natural language query' },
      { path: '/balance/:address', method: 'GET', description: 'ETH + USDC balance' },
      { path: '/health', method: 'GET', description: 'Health check' }
    ],
    network: NETWORK
  });
});

// ─── Payment Verification Middleware ─────────────────────────────────────────
async function verifyPayment(req, res, next) {
  // Accept tx hash in header or query param
  const txHash = req.headers['x-payment-tx'] || req.query.tx;
  
  if (!txHash) {
    return res.status(402).json({
      error: 'Payment Required',
      payment: {
        address: NOVA_ADDRESS,
        amount: `${PRICE_ETH} ETH`,
        amountWei: PRICE_WEI.toString(),
        description: 'Send ETH then include X-PAYMENT-TX header with the tx hash',
        instructions: `Send ${PRICE_ETH} ETH to ${NOVA_ADDRESS}, then retry with header X-PAYMENT-TX: <tx>`
      }
    });
  }

  // Validate hash format
  if (!/^0x[0-9a-fA-F]{64}$/.test(txHash)) {
    return res.status(400).json({ error: 'Invalid transaction hash format' });
  }

  try {
    // Get tx receipt
    const receipt = await publicClient.getTransactionReceipt({ hash: txHash });
    
    // Verify: to == Nova's address
    const txTo = typeof receipt.to === 'string' ? receipt.to : receipt.to?.toString();
    if (txTo?.toLowerCase() !== NOVA_ADDRESS.toLowerCase()) {
      return res.status(400).json({ error: 'Payment tx is not to Nova\'s address' });
    }
    
    // Verify: value >= PRICE_WEI
    if (receipt.value < PRICE_WEI) {
      return res.status(400).json({ 
        error: 'Payment amount too low',
        required: `${PRICE_ETH} ETH`,
        received: `${Number(receipt.value) / 1e18} ETH`
      });
    }
    
    // Verify: tx is confirmed (status === 1)
    if (receipt.status === 0) {
      return res.status(400).json({ error: 'Payment transaction failed on-chain' });
    }

    // Payment valid
    req.txHash = txHash;
    req.paymentValue = receipt.value;
    req.payerAddress = receipt.from;
    next();
    
  } catch (err) {
    if (err.message?.includes('transaction not found') || err.message?.includes('not found')) {
      return res.status(400).json({ error: 'Transaction not found — it may not be confirmed yet. Wait a few seconds and retry.' });
    }
    console.error('Payment verification error:', err.message);
    return res.status(500).json({ error: 'Payment verification failed: ' + err.message });
  }
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
      txHash: req.txHash,
      price: `${PRICE_ETH} ETH`
    });
  } catch (err) {
    console.error('Query error:', err);
    res.status(500).json({ error: err.message });
  }
});

// ─── Balance Endpoint ─────────────────────────────────────────────────────────
app.get('/balance/:address', verifyPayment, async (req, res) => {
  const { address } = req.params;
  
  if (!/^0x[0-9a-fA-F]{40}$/.test(address)) {
    return res.status(400).json({ error: 'Invalid Ethereum address' });
  }

  try {
    const [ethBalance, usdcBalance] = await Promise.all([
      publicClient.getBalance({ address }),
      getERC20Balance('0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', address)
    ]);

    res.json({
      address,
      eth: Number(ethBalance) / 1e18,
      usdc: Number(usdcBalance) / 1e6,
      txHash: req.txHash,
      price: `${PRICE_ETH} ETH`
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─── Health Check ─────────────────────────────────────────────────────────────
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    service: 'Nova Query API v2.0',
    network: 'Base Mainnet',
    price: `${PRICE_ETH} ETH/query`,
    uptime: process.uptime(),
    ts: new Date().toISOString()
  });
});

// ─── ETH Payment Address (free info) ─────────────────────────────────────────
app.get('/pay', (req, res) => {
  res.json({
    address: NOVA_ADDRESS,
    amount: `${PRICE_ETH} ETH`,
    amountWei: PRICE_WEI.toString(),
    network: 'Base (eip155:8453)',
    instructions: 'Send ETH to the address above, then call any endpoint with X-PAYMENT-TX: <your tx hash>'
  });
});

// ─── ERC-20 Balance Reader ───────────────────────────────────────────────────
async function getERC20Balance(tokenAddress, holderAddress) {
  return publicClient.readContract({
    address: tokenAddress,
    abi: [{ type: 'function', name: 'balanceOf', stateMutability: 'view', inputs: [{ type: 'address' }], outputs: [{ type: 'uint256' }] }],
    functionName: 'balanceOf',
    args: [holderAddress]
  });
}

// ─── Query Executor ──────────────────────────────────────────────────────────
async function executeQuery(query, params = {}, payer = 'unknown') {
  const q = query.toLowerCase();
  
  if (q.includes('balance') && q.includes('eth')) {
    const addr = extractAddress(q, params);
    if (!addr) throw new Error('Could not find address in query');
    const bal = await publicClient.getBalance({ address: addr });
    return { type: 'eth_balance', address: addr, balance: Number(bal) / 1e18, unit: 'ETH' };
  }
  
  if (q.includes('balance') && (q.includes('usdc') || q.includes('token'))) {
    const addr = extractAddress(q, params);
    if (!addr) throw new Error('Could not find address in query');
    const bal = await getERC20Balance('0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', addr);
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
    if (!txHash) throw new Error('Could not find transaction hash');
    const tx = await publicClient.getTransaction({ hash: txHash });
    return { type: 'transaction', hash: tx.hash, from: tx.from, to: tx.to, value: Number(tx.value) / 1e18, blockNumber: tx.blockNumber ? Number(tx.blockNumber) : null };
  }
  
  if (q.includes('gas') || q.includes('fee')) {
    const gasPrice = await publicClient.getGasPrice();
    return { type: 'gas', gas_price_gwei: Number(gasPrice) / 1e9, gas_price_wei: gasPrice.toString() };
  }
  
  if (q.includes('supply') || q.includes('total')) {
    const addr = extractAddress(q, params);
    if (!addr) throw new Error('Could not find address');
    const supply = await publicClient.readContract({
      address: addr,
      abi: [{ type: 'function', name: 'totalSupply', stateMutability: 'view', outputs: [{ type: 'uint256' }] }],
      functionName: 'totalSupply'
    });
    return { type: 'total_supply', address: addr, supply: Number(supply) / 1e18 };
  }
  
  if (q.includes('decode') || q.includes('logs') || q.includes('events')) {
    const txHash = extractTxHash(q, params) || params?.txHash;
    if (txHash) {
      const receipt = await publicClient.getTransactionReceipt({ hash: txHash });
      return { type: 'receipt', txHash, logs: receipt.logs.map(l => ({ address: l.address, topics: l.topics, data: l.data, blockNumber: Number(l.blockNumber) }))};
    }
    throw new Error('Provide a transaction hash to decode');
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

// ─── Start Server ────────────────────────────────────────────────────────────
const PORT = process.env.PORT || 3001;
const HOST = process.env.HOST || '0.0.0.0';

app.listen(PORT, HOST, () => {
  console.log(`Nova API server running on http://${HOST}:${PORT}`);
  console.log(`Network: Base Mainnet (eip155:8453)`);
  console.log(`Price: ${PRICE_ETH} ETH per query`);
  console.log(`Payment address: ${NOVA_ADDRESS}`);
});
