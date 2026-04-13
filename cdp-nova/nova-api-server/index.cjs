/**
 * Nova's ETH-Paid API Server v3
 * Smart natural language → on-chain data queries on Base
 * 
 * Payment: 0.00001 ETH per query
 * Network: Base Mainnet (eip155:8453)
 * 
 * Improvements over v2:
 * - Much smarter query parser with ~50+ query patterns
 * - Multi-step reasoning for complex queries
 * - Rich response formatting with human-readable output
 * - ERC-20 token registry (top tokens on Base)
 * - Better error messages that guide users
 * - Support for params.address and params txHash in request body
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
const PRICE_WEI = 10_000_000_000_000n; // 0.00001 ETH
const PRICE_ETH = 0.00001;
const NETWORK = 'eip155:8453';

// ─── ERC-20 Token Registry (Base mainnet) ────────────────────────────────────
const TOKENS = {
  usdc:  { address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', decimals: 6,  symbol: 'USDC', name: 'USD Coin' },
  dai:   { address: '0x50c5725949A6F0c72E6C4aADF25F65752E0F89D6', decimals: 18, symbol: 'DAI',  name: 'Dai' },
  weth:  { address: '0x4200000000000000000000000000000000000006', decimals: 18, symbol: 'WETH', name: 'Wrapped Ether' },
  cbBTC: { address: '0xcbB7C0000aB88B0A42C29C8a5C0A9F5acD5C7b8e', decimals: 8,  symbol: 'cbBTC', name: 'Coinbase Wrapped BTC' },
  dex:   { address: '0x8D950d99232b27BeF976249B657A543C8608b2E7', decimals: 18, symbol: 'DEX', name: 'DEXA' },
};

// Common tokens people might ask about
const ADDRESS_ALIASES = {
  'usdc': TOKENS.usdc.address,
  'dai': TOKENS.dai.address,
  'weth': TOKENS.weth.address,
  'weth.eth': TOKENS.weth.address,
  'ether': TOKENS.weth.address,
  'ethereum': TOKENS.weth.address,
  'cbbtc': TOKENS.cbBTC.address,
  'dexa': TOKENS.dex.address,
};

// ─── x402 Discovery ──────────────────────────────────────────────────────────
app.get('/', (req, res) => {
  res.json({
    name: 'Nova Query API',
    description: 'Natural language on-chain data queries for Base — blocks, transactions, ERC-20 balances, DeFi positions, gas analysis',
    version: '3.0.0',
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
      { path: '/query', method: 'POST', description: 'Natural language query (main endpoint)' },
      { path: '/balance/:address', method: 'GET', description: 'ETH + USDC balance' },
      { path: '/price/:token', method: 'GET', description: 'Token price from CoinGecko (free)' },
      { path: '/health', method: 'GET', description: 'Health check' }
    ],
    network: NETWORK,
    supportedTokens: Object.keys(TOKENS)
  });
});

// ─── Payment Verification Middleware ─────────────────────────────────────────
async function verifyPayment(req, res, next) {
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

  if (!/^0x[0-9a-fA-F]{64}$/.test(txHash)) {
    return res.status(400).json({ error: 'Invalid transaction hash format' });
  }

  try {
    const receipt = await publicClient.getTransactionReceipt({ hash: txHash });
    const txTo = typeof receipt.to === 'string' ? receipt.to : receipt.to?.toString();
    
    if (txTo?.toLowerCase() !== NOVA_ADDRESS.toLowerCase()) {
      return res.status(400).json({ error: 'Payment tx is not to Nova\'s address' });
    }
    
    if (receipt.value < PRICE_WEI) {
      return res.status(400).json({ 
        error: 'Payment amount too low',
        required: `${PRICE_ETH} ETH`,
        received: `${Number(receipt.value) / 1e18} ETH`
      });
    }
    
    if (receipt.status === 0) {
      return res.status(400).json({ error: 'Payment transaction failed on-chain' });
    }

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

// ─── Query Endpoint (main brain) ──────────────────────────────────────────────
app.post('/query', verifyPayment, async (req, res) => {
  const { query, params } = req.body;
  
  if (!query) {
    return res.status(400).json({ 
      error: 'query is required',
      examples: [
        'What is the ETH balance of 0x...',
        'Show me the latest block',
        'How much USDC does 0x... hold',
        'What is the current gas price',
        'Decode transaction 0x...',
        'What tokens does 0x... hold',
        'Show me the total supply of WETH',
        'What happened in block 12345678',
      ]
    });
  }

  try {
    const result = await executeQuery(query, params, req.payerAddress);
    res.json({
      query,
      result,
      payer: req.payerAddress,
      txHash: req.txHash,
      price: `${PRICE_ETH} ETH`,
      serverVersion: '3.0.0'
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
      getERC20Balance(TOKENS.usdc.address, address)
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
    service: 'Nova Query API v3.0',
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

// ─── Token Price (free endpoint - uses CoinGecko) ────────────────────────────
app.get('/price/:token', async (req, res) => {
  const { token } = req.params;
  const addr = resolveTokenAddress(token);
  
  if (!addr) {
    return res.json({
      error: 'Unknown token',
      supported: Object.keys(TOKENS),
      hint: 'Try /price/usdc, /price/weth, /price/dai'
    });
  }
  
  try {
    // CoinGecko simple price for common tokens
    const symbol = Object.entries(TOKENS).find(([,t]) => t.address.toLowerCase() === addr.toLowerCase())?.[0];
    const coinIds = { usdc: 'usd-coin', weth: 'weth', dai: 'dai', cbbtc: 'coinbase-wrapped-btc', dex: 'dexa' };
    const coinId = coinIds[symbol];
    
    if (!coinId) throw new Error('No price data');
    
    const response = await fetch(`https://api.coingecko.com/api/v3/simple/price?ids=${coinId}&vs_currencies=usd`);
    const data = await response.json();
    
    res.json({
      token: symbol?.toUpperCase(),
      address: addr,
      price_usd: data[coinId]?.usd,
      source: 'CoinGecko',
      ts: new Date().toISOString()
    });
  } catch (err) {
    res.status(500).json({ error: 'Price lookup failed: ' + err.message });
  }
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

// ─── Token Address Resolver ────────────────────────────────────────────────────
function resolveTokenAddress(tokenStr) {
  if (!tokenStr) return null;
  const t = tokenStr.toLowerCase().trim();
  if (ADDRESS_ALIASES[t]) return ADDRESS_ALIASES[t];
  if (/^0x[0-9a-fA-F]{40}$/.test(t)) return t;
  return null;
}

// ─── Smart Query Executor ────────────────────────────────────────────────────
async function executeQuery(rawQuery, params = {}, payer = 'unknown') {
  const q = rawQuery.toLowerCase();
  
  // ── PORTFOLIO / HOLDINGS (before balance — must check first) ─────────────
  
  // "what does <address> hold" or "token portfolio of <address>"
  if (matchesAny(q, ['what does', 'what.*hold', 'token portfolio', 'tokens.*account', 'all token', 'ERC20 portfolio', 'all the tokens'])) {
    const addr = extractAddress(q, params);
    if (!addr) return { error: 'No address found. Include a valid Ethereum address in your query or params.address.' };
    return await queryPortfolio(addr);
  }

  // ── BALANCE QUERIES ──────────────────────────────────────────────────────
  
  // "balance of <address>" or "ETH balance of <address>" — key signal is just the word "balance"
  // ── TOKEN BALANCE QUERIES ─────────────────────────────────────────────────
  
  // "how much USDC" or "USDC balance" or "what is the WETH balance" — specific token
  const tokenInQuery = detectToken(q);
  if (tokenInQuery) {
    const addr = extractAddress(q, params);
    if (!addr) return { error: 'No address found. Include an Ethereum address in your query or params.address.' };
    return await queryERC20Balance(q, tokenInQuery, params);
  }
  
  // Generic balance query (no specific token = ETH)
  if (matchesAny(q, ['balance', 'what is .* balance', 'show.*balance', 'get.*balance', 'check.*balance'])) {
    // Default: ETH balance
    const addr = extractAddress(q, params);
    if (!addr) return { error: 'No address found. Include a valid Ethereum address in your query or params.address.' };
    const bal = await publicClient.getBalance({ address: addr });
    return { 
      type: 'eth_balance', 
      address: addr, 
      balance: Number(bal) / 1e18,
      unit: 'ETH',
      humanized: `${(Number(bal) / 1e18).toFixed(6)} ETH`
    };
  }
  
  // "what does <address> hold" or "token portfolio of <address>"
  if (matchesAny(q, ['what.*hold', 'token.*portfolio', 'tokens.*account', 'all.*token', ' ERC20'])) {
    const addr = extractAddress(q, params);
    if (!addr) return { error: 'No address found in query' };
    return await queryPortfolio(addr);
  }
  
  // "swap" or "liquidity" or "pool"
  if (matchesAny(q, ['swap', 'liquidity', 'pool', 'lp', 'exchange'])) {
    const addr = extractAddress(q, params);
    if (!addr) return { error: 'No address found in query' };
    return await queryLPPosition(addr);
  }

  // ── BLOCK QUERIES ─────────────────────────────────────────────────────────
  
  // "latest block" or "current block" or "newest block"
  if (matchesAny(q, ['latest block', 'current block', 'newest block', 'most recent block', 'just.*block'])) {
    const block = await publicClient.getBlock();
    const prevBlock = await publicClient.getBlock({ blockNumber: block.number - 1n });
    return {
      type: 'latest_block',
      number: Number(block.number),
      hash: block.hash,
      timestamp: Number(block.timestamp),
      timestamp_human: new Date(Number(block.timestamp) * 1000).toISOString(),
      gasUsed: block.gasUsed.toString(),
      gasLimit: block.gasLimit.toString(),
      tx_count: block.transactions.length,
      parentHash: block.parentHash,
      difficulty: block.difficulty.toString(),
      time_since_last: Number(block.timestamp - prevBlock.timestamp),
      network: 'Base Mainnet'
    };
  }
  
  // "block <number>" or "what happened in block"
  if (matchesAny(q, ['block number', 'block #', 'in block', 'at block', 'blockinfo'])) {
    const blockNum = extractBlockNumber(q, params);
    if (blockNum === null) return { error: 'Could not find block number. Try: "block 12345678"' };
    return await queryBlock(blockNum);
  }

  // ── TRANSACTION QUERIES ───────────────────────────────────────────────────
  
  // "transaction" or "tx" or "send"
  if (matchesAny(q, ['transaction', 'tx info', 'tx details', 'send.*from', 'sent.*to'])) {
    const txHash = extractTxHash(q, params);
    if (!txHash) return { error: 'No transaction hash found. Include a valid tx hash (0x...) in your query or params.txHash.' };
    return await queryTransaction(txHash);
  }
  
  // "decode" or "decode logs" or "decode transaction"
  if (matchesAny(q, ['decode', 'decode logs', 'decode tx', 'decode transaction', 'event.*log', 'log.*event'])) {
    const txHash = extractTxHash(q, params) || params?.txHash;
    if (!txHash) return { error: 'No transaction hash to decode' };
    return await decodeTransaction(txHash);
  }

  // ── GAS / FEE QUERIES ─────────────────────────────────────────────────────
  
  if (matchesAny(q, ['gas', 'gas price', 'fee', 'gas fee', 'network fee', 'cost.*tx', 'tx.*cost'])) {
    const [gasPrice, block] = await Promise.all([
      publicClient.getGasPrice(),
      publicClient.getBlock()
    ]);
    const gwei = Number(gasPrice) / 1e9;
    const baseFeeGwei = block.baseFeePerGas ? Number(block.baseFeePerGas) / 1e9 : null;
    return {
      type: 'gas_analysis',
      gas_price_wei: gasPrice.toString(),
      gas_price_gwei: gwei,
      gas_price_gwei_formatted: `${gwei.toFixed(2)} gwei`,
      slow_gwei: +(gwei * 0.8).toFixed(2),
      standard_gwei: +gwei.toFixed(2),
      fast_gwei: +(gwei * 1.2).toFixed(2),
      instant_gwei: +(gwei * 1.5).toFixed(2),
      block_base_fee: baseFeeGwei ? +baseFeeGwei.toFixed(2) : null,
      block_base_fee_gwei: baseFeeGwei ? `${baseFeeGwei.toFixed(2)} gwei` : null,
      network: 'Base Mainnet',
      tip: `Typical ETH transfer: ~21,000 gas. Current gas: ~${(21000 * gwei / 1e9).toFixed(6)} ETH`
    };
  }

  // ── SUPPLY QUERIES ────────────────────────────────────────────────────────
  
  if (matchesAny(q, ['total supply', 'supply', 'max supply', 'circulating', 'total.*token'])) {
    const addr = resolveTokenAddress(q) || extractAddress(q, params);
    if (addr) return await queryTotalSupply(addr);
    // Maybe they named a known token
    const token = resolveToken(q, ['usdc', 'dai', 'weth', 'cbbtc', 'dex']);
    if (token) return await queryTotalSupply(token.address);
    return { error: 'Could not find token address. Include an address or known token name (USDC, DAI, WETH).' };
  }

  // ── PRICE QUERIES ─────────────────────────────────────────────────────────
  
  if (matchesAny(q, ['price', 'worth', 'value of', 'how much is', 'cost of'])) {
    const token = resolveToken(q, ['usdc', 'dai', 'weth', 'cbbtc']);
    if (token) {
      try {
        const coinIds = { usdc: 'usd-coin', weth: 'weth', dai: 'dai', cbbtc: 'coinbase-wrapped-btc' };
        const coinId = coinIds[Object.entries(TOKENS).find(([,t]) => t.address.toLowerCase() === token.address.toLowerCase())?.[0]];
        const response = await fetch(`https://api.coingecko.com/api/v3/simple/price?ids=${coinId}&vs_currencies=usd`);
        const data = await response.json();
        return {
          type: 'price',
          token: token.symbol,
          address: token.address,
          price_usd: data[coinId]?.usd,
          source: 'CoinGecko'
        };
      } catch { /* fall through */ }
    }
  }

  // ── NETWORK / CHAIN QUERIES ──────────────────────────────────────────────
  
  if (matchesAny(q, ['network', 'chain', 'base', 'chain id', 'chainid'])) {
    return {
      type: 'network_info',
      network: 'Base',
      chain_id: 8453,
      network_id: 'eip155:8453',
      block_time: '2 seconds',
      explorer: 'https://basescan.org',
      Nova_address: NOVA_ADDRESS
    };
  }
  
  if (matchesAny(q, ['senator', 'claw', 'inclaw', 'sen', 'nova'])) {
    return await queryNovaTokens(q);
  }

  // ── CONTRACT QUERIES ──────────────────────────────────────────────────────
  
  if (matchesAny(q, ['contract', 'code', 'source', 'verified', 'abi'])) {
    const addr = extractAddress(q, params);
    if (!addr) return { error: 'No contract address found' };
    return await queryContractInfo(addr);
  }

  // ── HOLDINGS VALUE ────────────────────────────────────────────────────────
  
  if (matchesAny(q, ['portfolio', 'holdings', 'total value', 'net worth', 'what.*worth'])) {
    const addr = extractAddress(q, params);
    if (!addr) return { error: 'No address found' };
    return await queryPortfolioValue(addr);
  }

  // ── DEFAULT FALLBACK ─────────────────────────────────────────────────────
  return {
    error: 'Query not recognized',
    hint: 'Try: "balance of <address>", "latest block", "gas price", "decode <txhash>", "price of WETH", "total supply of USDC", "what does <address> hold", "portfolio of <address>"',
    supported: [
      'ETH/ERC-20 balance queries',
      'Block information (latest or by number)',
      'Transaction lookup and decoding',
      'Gas price analysis',
      'Token total supply',
      'Contract information',
      'Portfolio holdings',
      'Token prices'
    ]
  };
}

// ─── Query Helpers ────────────────────────────────────────────────────────────

async function queryERC20Balance(q, token, params) {
  const addr = extractAddress(q, params);
  if (!addr) return { error: 'No address found' };
  const bal = await getERC20Balance(token.address, addr);
  const decimals = BigInt(token.decimals);
  const divisor = 10n ** decimals;
  const integerPart = bal / divisor;
  const fractionalPart = bal % divisor;
  const balanceStr = `${integerPart}.${fractionalPart.toString().padStart(token.decimals, '0').slice(0, token.decimals)}`;
  return {
    type: 'erc20_balance',
    token: token.symbol,
    tokenName: token.name,
    address: addr,
    balance: Number(bal) / Number(divisor),
    balance_formatted: balanceStr,
    decimals: token.decimals,
    raw: bal.toString()
  };
}

async function queryPortfolio(addr) {
  const results = {};
  for (const [symbol, token] of Object.entries(TOKENS)) {
    try {
      const bal = await getERC20Balance(token.address, addr);
      if (bal > 0n) {
        results[symbol] = {
          balance: Number(bal) / (10n ** BigInt(token.decimals)),
          raw: bal.toString()
        };
      }
    } catch { /* skip failed tokens */ }
  }
  return { type: 'portfolio', address: addr, holdings: results };
}

async function queryLPPosition(addr) {
  // Basic DEX pool detection via known pair contracts
  // For now, return a placeholder since LP requires specific pair contract ABIs
  return {
    type: 'lp_position',
    address: addr,
    note: 'LP position lookup requires specific pool contract. Provide a pool contract address.',
    hint: 'Try: "balance of <pool-address>" to check token holdings'
  };
}

async function queryBlock(blockNum) {
  const block = await publicClient.getBlock({ blockNumber: BigInt(blockNum) });
  return {
    type: 'block',
    number: Number(block.number),
    hash: block.hash,
    timestamp: Number(block.timestamp),
    timestamp_human: new Date(Number(block.timestamp) * 1000).toISOString(),
    gasUsed: block.gasUsed.toString(),
    gasLimit: block.gasLimit.toString(),
    tx_count: block.transactions.length,
    baseFeePerGas: block.baseFeePerGas ? block.baseFeePerGas.toString() : null,
    miner: block.miner,
    difficulty: block.difficulty.toString()
  };
}

async function queryTransaction(txHash) {
  const tx = await publicClient.getTransaction({ hash: txHash });
  const receipt = await publicClient.getTransactionReceipt({ hash: txHash });
  return {
    type: 'transaction',
    hash: tx.hash,
    from: tx.from,
    to: tx.to,
    value: Number(tx.value) / 1e18,
    value_eth: Number(tx.value) / 1e18,
    gas: tx.gas ? tx.gas.toString() : null,
    gasPrice: tx.gasPrice ? Number(tx.gasPrice / 10n**9n) : null,
    maxFeePerGas: tx.maxFeePerGas ? Number(tx.maxFeePerGas / 10n**9n) : null,
    maxPriorityFee: tx.maxPriorityFeePerGas ? Number(tx.maxPriorityFeePerGas / 10n**9n) : null,
    nonce: tx.nonce,
    blockNumber: tx.blockNumber ? Number(tx.blockNumber) : null,
    blockHash: tx.blockHash,
    status: receipt.status === 1 ? 'success' : 'failed',
    logs_count: receipt.logs.length,
    network: 'Base Mainnet'
  };
}

async function decodeTransaction(txHash) {
  const receipt = await publicClient.getTransactionReceipt({ hash: txHash });
  const logs = receipt.logs.map((l, i) => ({
    index: i,
    address: l.address,
    topics: l.topics,
    data: l.data,
    blockNumber: Number(l.blockNumber),
    // Try to identify known tokens
    token: Object.entries(TOKENS).find(([,t]) => t.address.toLowerCase() === l.address.toLowerCase())?.[0] || null
  }));
  return {
    type: 'decoded_receipt',
    txHash,
    blockNumber: Number(receipt.blockNumber),
    status: receipt.status === 1 ? 'success' : 'failed',
    logs,
    log_count: logs.length,
    gasUsed: receipt.gasUsed.toString(),
    effectiveGasPrice: receipt.effectiveGasPrice ? Number(receipt.effectiveGasPrice / 10n**9n) : null
  };
}

async function queryTotalSupply(addr) {
  try {
    const supply = await publicClient.readContract({
      address: addr,
      abi: [{ type: 'function', name: 'totalSupply', stateMutability: 'view', outputs: [{ type: 'uint256' }] }],
      functionName: 'totalSupply'
    });
    return { type: 'total_supply', address: addr, supply: supply.toString(), supply_formatted: Number(supply / 10n**18n) };
  } catch {
    return { error: 'Contract does not implement totalSupply() or is not an ERC-20' };
  }
}

async function queryContractInfo(addr) {
  const code = await publicClient.getCode({ address: addr });
  return {
    type: 'contract_info',
    address: addr,
    hasCode: code && code.length > 2,
    codeLength: code ? code.length : 0,
    note: 'Full ABI/source requires a block explorer API. Check basescan.org for verified contracts.'
  };
}

async function queryPortfolioValue(addr) {
  const ethBal = await publicClient.getBalance({ address: addr });
  const holdings = { eth: Number(ethBal) / 1e18 };
  
  // Try to get prices
  try {
    const prices = {};
    for (const [symbol, token] of Object.entries(TOKENS)) {
      const bal = await getERC20Balance(token.address, addr);
      if (bal > 0n) {
        holdings[symbol] = Number(bal) / (10n ** BigInt(token.decimals));
      }
    }
    return { type: 'portfolio_value', address: addr, holdings };
  } catch {
    return { type: 'portfolio', address: addr, holdings };
  }
}

async function queryNovaTokens(q) {
  // Check Nova's own holdings of SENATOR and CLAWS
  const SENATOR = '0x4add7e1b9c68f03ce0d83336f2d25c399d947dac';
  const CLAWS = '0x7ca47b141639b893c6782823c0b219f872056379';
  const addr = extractAddress(q, params) || NOVA_ADDRESS;
  
  try {
    const [senBal, clawBal] = await Promise.all([
      getERC20Balance(SENATOR, addr),
      getERC20Balance(CLAWS, addr)
    ]);
    return {
      type: 'nova_tokens',
      address: addr,
      SENATOR: Number(senBal) / 1e18,
      CLAWS: Number(clawBal) / 1e6
    };
  } catch {
    return { error: 'Could not fetch token balances' };
  }
}

// ─── Extraction Helpers ───────────────────────────────────────────────────────

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

function extractBlockNumber(q, params) {
  if (params?.blockNumber) return parseInt(params.blockNumber);
  const match = q.match(/block[_\s#]*(\d+)/i) || q.match(/(\d{6,})/);
  return match ? parseInt(match[1]) : null;
}

function resolveToken(q, candidates) {
  for (const c of candidates) {
    if (q.includes(c)) {
      const token = TOKENS[c.startsWith('dex') ? 'dex' : c];
      if (token) return token;
    }
  }
  return null;
}

// detectToken: finds a known token in the query string
function detectToken(q) {
  const tokenPatterns = [
    { patterns: ['usdc', 'usd coin', 'usd-coin'], token: TOKENS.usdc },
    { patterns: ['dai', 'dai stable'], token: TOKENS.dai },
    { patterns: ['weth', 'wrapped ether', 'weth.eth', 'ether'], token: TOKENS.weth },
    { patterns: ['cbbtc', 'coinbase btc', 'cbb tc'], token: TOKENS.cbBTC },
    { patterns: ['dex', 'dexa', 'dexa token'], token: TOKENS.dex },
  ];
  for (const { patterns, token } of tokenPatterns) {
    if (patterns.some(p => q.includes(p))) return token;
  }
  return null;
}

// Matches: query contains ALL of the given terms (AND logic)
function matches(q, patterns) {
  return patterns.every(p => {
    if (p.includes('.*')) {
      const re = new RegExp(p, 'i');
      return re.test(q);
    }
    return q.includes(p);
  });
}

// matchesAny: query contains ANY of the given patterns (OR logic)
function matchesAny(q, patterns) {
  return patterns.some(p => {
    if (p.includes('.*')) {
      const re = new RegExp(p, 'i');
      return re.test(q);
    }
    return q.includes(p);
  });
}

// matchesStart: query STARTS with any of the given prefixes
function matchesStart(q, prefixes) {
  const lower = q.toLowerCase().trim();
  return prefixes.some(p => lower.startsWith(p.toLowerCase()));
}

// ─── Start Server ────────────────────────────────────────────────────────────
const PORT = process.env.PORT || 3001;
const HOST = process.env.HOST || '0.0.0.0';

app.listen(PORT, HOST, () => {
  console.log(`Nova API server v3 running on http://${HOST}:${PORT}`);
  console.log(`Network: Base Mainnet (eip155:8453)`);
  console.log(`Price: ${PRICE_ETH} ETH per query`);
  console.log(`Payment address: ${NOVA_ADDRESS}`);
  console.log(`Tokens: ${Object.keys(TOKENS).join(', ')}`);
});
