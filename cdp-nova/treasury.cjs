/**
 * Nova's Treasury System
 * Bookkeeping + portfolio tracker with USD valuations
 * 
 * Prices pulled from CoinGecko API (free, no key)
 * 
 * Usage:
 *   node treasury.js status     — current portfolio summary
 *   node treasury.js report    — detailed P&L report
 *   node treasury.js history   — transaction history
 *   node treasury.js log      — manual entry
 */

const Database = require('better-sqlite3');
const { createPublicClient, http } = require('viem');
const { base } = require('viem/chains');
const { readFileSync } = require('fs');
const path = require('path');

const pub = createPublicClient({ chain: base, transport: http() });
const DB_PATH = path.join(__dirname, 'treasury.db');

// ─── Config ──────────────────────────────────────────────────────────────────
const WALLET_KEY = JSON.parse(readFileSync(path.join(__dirname, 'nova-wallet.json'), 'utf8'));
const NOVA = '0xB743fdbA842379933A3774617786712458659D16'.toLowerCase();
const ACP = '0x87FC016E31D767E02Df25b00B3934b0dEe3759E2'.toLowerCase();

const TOKENS = {
  ETH:  { addr: null,                decimals: 18,  coingecko: 'ethereum',     symbol: 'ETH' },
  USDC: { addr: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'.toLowerCase(), decimals: 6, coingecko: 'usd-coin', symbol: 'USDC' },
  SENATOR: { addr: '0x4add7e1b9c68f03ce0d83336f2d25c399d947dac'.toLowerCase(), decimals: 18, coingecko: null, symbol: 'SENATOR' },
  CLAWS: { addr: '0x7ca47b141639b893c6782823c0b219f872056379'.toLowerCase(), decimals: 18, coingecko: null, symbol: 'CLAWS' },
  WETH: { addr: '0x4200000000000000000000000000000000000006'.toLowerCase(), decimals: 18, coingecko: 'ethereum', symbol: 'WETH' }
};

const CATEGORIES = {
  INCOME: 'income',
  EXPENSE: 'expense',
  TRANSFER_IN: 'transfer_in',
  TRANSFER_OUT: 'transfer_out',
  GAS: 'gas',
  INVESTMENT: 'investment',
  REWARD: 'reward'
};

const SOURCES = {
  STAKING: 'staking',
  X402_API: 'x402_api',
  ACP: 'acp',
  COMPOUND: 'compound',
  OPERATIONAL: 'operational',
  UNKNOWN: 'unknown'
};

// ─── Database Setup ────────────────────────────────────────────────────────────
const db = new Database(DB_PATH);

db.exec(`
  CREATE TABLE IF NOT EXISTS wallets (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    type TEXT DEFAULT 'eoa',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS holdings (
    wallet_id TEXT NOT NULL,
    asset TEXT NOT NULL,
    balance_raw TEXT NOT NULL,
    balance_usd REAL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (wallet_id, asset),
    FOREIGN KEY (wallet_id) REFERENCES wallets(id)
  );

  CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_id TEXT NOT NULL,
    type TEXT NOT NULL,
    category TEXT NOT NULL,
    source TEXT NOT NULL,
    asset TEXT NOT NULL,
    amount_raw TEXT NOT NULL,
    amount_usd REAL,
    fee_raw TEXT,
    fee_usd REAL,
    tx_hash TEXT,
    counterparty TEXT,
    note TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (wallet_id) REFERENCES wallets(id)
  );

  CREATE TABLE IF NOT EXISTS prices (
    asset TEXT PRIMARY KEY,
    price_usd REAL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_type TEXT NOT NULL,
    synced_at TEXT DEFAULT CURRENT_TIMESTAMP,
    items_updated INTEGER
  );
`);

db.exec(`
  CREATE TRIGGER IF NOT EXISTS prevent_delete_transaction
  BEFORE DELETE ON transactions BEGIN SELECT RAISE(ABORT, 'Deletes disabled'); END;
`);

// ─── Price Fetching ────────────────────────────────────────────────────────────
let priceCache = {};

async function fetchPrices() {
  // Try CoinGecko first, then fallback
  let fetched = false;
  
  try {
    const res = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=ethereum,usd-coin&vs_currencies=usd&include_24hr_change=false', {
      signal: AbortSignal.timeout(5000)
    });
    if (res.ok) {
      const data = await res.json();
      priceCache = {
        ETH: data.ethereum?.usd || 2000,
        USDC: data['usd-coin']?.usd || 1.0,
        WETH: data.ethereum?.usd || 2000
      };
      fetched = true;
      
      const stmt = db.prepare('INSERT OR REPLACE INTO prices (asset, price_usd, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)');
      for (const [asset, price] of Object.entries(priceCache)) {
        stmt.run(asset, price);
      }
    }
  } catch (err) {
    // Fall through to DB prices
  }
  
  if (!fetched) {
    // Try DB prices as fallback
    const rows = db.prepare('SELECT asset, price_usd FROM prices').all();
    for (const r of rows) priceCache[r.asset] = r.price_usd;
  }
  
  // Hard fallback if everything failed
  if (Object.keys(priceCache).length === 0 || !priceCache.ETH) {
    priceCache = { ETH: 2000, USDC: 1.0, WETH: 2000 };
    console.warn('[treasury] CoinGecko unavailable — using fallback ETH=$2000');
  }
  
  return priceCache;
}

function toUSD(amount, asset, prices) {
  // amount should be in base units (not pre-divided)
  const token = TOKENS[asset];
  const price = prices[asset] || (asset !== 'ETH' && asset !== 'WETH' && asset !== 'USDC' ? 0 : (prices.ETH || 2000));
  return (Number(amount) / Math.pow(10, token?.decimals || 18)) * price;
}

// ─── On-Chain Reading ──────────────────────────────────────────────────────────
async function getOnChainBalance(wallet, asset) {
  if (!TOKENS[asset]) return 0n;
  const token = TOKENS[asset];
  
  if (!token.addr) {
    // ETH
    return pub.getBalance({ address: wallet });
  }
  
  return pub.readContract({
    address: token.addr,
    abi: [{ type: 'function', name: 'balanceOf', inputs: [{ type: 'address' }], outputs: [{ type: 'uint256' }] }],
    functionName: 'balanceOf',
    args: [wallet]
  });
}

// ─── Sync Wallet Holdings ──────────────────────────────────────────────────────
async function syncHoldings(walletId) {
  const prices = await fetchPrices();
  
  const stmt = db.prepare(`INSERT OR REPLACE INTO holdings (wallet_id, asset, balance_raw, balance_usd, updated_at)
    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)`);
  
  const assets = ['ETH', 'USDC', 'SENATOR', 'CLAWS', 'WETH'];
  let updated = 0;
  
  for (const asset of assets) {
    try {
      const bal = await getOnChainBalance(walletId, asset);
      const usd = toUSD(bal, asset, prices);
      stmt.run(walletId, asset, bal.toString(), usd);
      updated++;
    } catch (e) {
      // Asset might not exist or wallet doesn't hold it
    }
  }
  
  db.prepare('INSERT INTO sync_log (sync_type, items_updated) VALUES (?, ?)').run('holdings', updated);
  return updated;
}

// ─── Record Transaction ────────────────────────────────────────────────────────
function recordTransaction({ walletId, type, category, source, asset, amount, fee, txHash, counterparty, note }) {
  const prices = priceCache;
  const amountUSD = toUSD(amount, asset, prices);
  const feeUSD = fee ? toUSD(fee, asset, prices) : null;
  
  const stmt = db.prepare(`INSERT INTO transactions 
    (wallet_id, type, category, source, asset, amount_raw, amount_usd, fee_raw, fee_usd, tx_hash, counterparty, note)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`);
  
  const result = stmt.run(walletId, type, category, source, asset, amount.toString(), amountUSD, fee?.toString() || null, feeUSD, txHash || null, counterparty || null, note || null);
  return result.lastInsertRowid;
}

// ─── Get Holdings ──────────────────────────────────────────────────────────────
function getHoldings(walletId) {
  const rows = db.prepare('SELECT asset, balance_raw, balance_usd, updated_at FROM holdings WHERE wallet_id = ? ORDER BY asset').all(walletId);
  return rows.map(r => ({
    asset: r.asset,
    balance: formatBalance(r.balance_raw, r.asset),
    balance_raw: r.balance_raw,
    balance_usd: r.balance_usd
  }));
}

function formatBalance(raw, asset) {
  if (!raw || raw === '0') return '0';
  const decimals = TOKENS[asset]?.decimals || 18;
  return (Number(raw) / Math.pow(10, decimals)).toFixed(decimals === 6 ? 2 : decimals === 18 ? 4 : 2);
}

// ─── Get Transaction History ──────────────────────────────────────────────────
function getHistory(walletId, { limit = 50, offset = 0, category, source } = {}) {
  let sql = 'SELECT * FROM transactions WHERE wallet_id = ?';
  const params = [walletId];
  if (category) { sql += ' AND category = ?'; params.push(category); }
  if (source) { sql += ' AND source = ?'; params.push(source); }
  sql += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?';
  params.push(limit, offset);
  return db.prepare(sql).all(...params);
}

// ─── Portfolio Summary ─────────────────────────────────────────────────────────
async function getPortfolioSummary() {
  const wallets = db.prepare('SELECT * FROM wallets').all();
  const prices = await fetchPrices();
  
  let totalUSD = 0;
  const summary = { wallets: {}, totalUSD: 0 };
  
  for (const w of wallets) {
    const holdings = getHoldings(w.id);
    let walletUSD = 0;
    for (const h of holdings) {
      if (h.balance_raw && h.balance_raw !== '0') {
        const usd = toUSD(h.balance_raw, h.asset, prices);
        walletUSD += usd;
      }
    }
    summary.wallets[w.id] = { label: w.label, holdings, totalUSD: walletUSD };
    totalUSD += walletUSD;
  }
  
  summary.totalUSD = totalUSD;
  summary.prices = prices;
  return summary;
}

// ─── Register Wallets (idempotent) ───────────────────────────────────────────
function registerWallet(id, label) {
  db.prepare('INSERT OR IGNORE INTO wallets (id, label) VALUES (?, ?)').run(id, label);
}

// ─── CLI ──────────────────────────────────────────────────────────────────────
async function main() {
  const [,, cmd, ...args] = process.argv;
  
  // Register known wallets
  registerWallet(NOVA, 'Nova EOA');
  registerWallet(ACP, 'ACP Agent Wallet');
  
  switch (cmd) {
    case 'status': {
      await syncHoldings(NOVA);
      await syncHoldings(ACP);
      const summary = await getPortfolioSummary();
      console.log('\n╔══════════════════════════════════════════════════════════════╗');
      console.log('║              NOVA TREASURY — PORTFOLIO STATUS              ║');
      console.log('╠══════════════════════════════════════════════════════════════╣');
      for (const [id, w] of Object.entries(summary.wallets)) {
        console.log(`║ ${w.label.padEnd(56)} ║`);
        for (const h of w.holdings) {
          if (h.balance_raw && h.balance_raw !== '0') {
            const token = TOKENS[h.asset] || {};
            const usd = token.unpriced ? null : toUSD(h.balance_raw, h.asset, summary.prices);
            const usdStr = token.unpriced ? '(unpriced)' : usd > 0 ? `$${usd.toFixed(2)}` : '-';
            console.log(`║   ${h.asset.padEnd(8)} ${h.balance.padEnd(18)} ${usdStr.padEnd(20)} ║`);
          }
        }
        console.log(`║   ${'─'.repeat(54)} ║`);
        console.log(`║   Wallet Total: $${w.totalUSD.toFixed(2).padStart(8)}                                   ║`);
        console.log('╠══════════════════════════════════════════════════════════════╣');
      }
      console.log(`║ TOTAL PORTFOLIO: $${summary.totalUSD.toFixed(2).padStart(8)}                                              ║`);
      console.log('╠══════════════════════════════════════════════════════════════╣');
      console.log(`║ Prices: ETH $${summary.prices?.ETH?.toFixed(2).padEnd(8)} | USDC $${summary.prices?.USDC?.toFixed(4).padEnd(8)}                      ║`);
      console.log(`║ CLAWS: 98,112 tokens (staking on Inclawbate) — no DEX price   ║`);
      console.log(`╚══════════════════════════════════════════════════════════════╝`);
      break;
    }
    
    case 'sync': {
      console.log('Syncing holdings...');
      await syncHoldings(NOVA);
      await syncHoldings(ACP);
      console.log('Done.');
      break;
    }
    
    case 'history': {
      const wallet = args[0] === 'acp' ? ACP : NOVA;
      const txns = getHistory(wallet, { limit: 20 });
      console.log(`\nRecent transactions for ${wallet.slice(0,10)}...:`);
      console.log(`${'DATE'.padEnd(25)} ${'TYPE'.padEnd(12)} ${'ASSET'.padEnd(8)} ${'AMOUNT'.padEnd(15)} ${'USD'.padEnd(10)} NOTE`);
      console.log('─'.repeat(90));
      for (const t of txns) {
        const date = t.timestamp.split('.')[0];
        const amt = (Number(t.amount_raw) / 1e18).toFixed(4);
        console.log(`${date.padEnd(25)} ${t.type.padEnd(12)} ${t.asset.padEnd(8)} ${amt.padEnd(15)} $${(t.amount_usd||0).toFixed(2).padEnd(10)} ${t.note || ''}`);
      }
      break;
    }
    
    case 'report': {
      const period = args[0] || 'all';
      console.log(`\n=== NOVA TREASURY REPORT (${period}) ===`);
      const rows = db.prepare(`
        SELECT category, source, asset, SUM(CAST(amount_raw AS REAL)) as total_raw, SUM(amount_usd) as total_usd, COUNT(*) as count
        FROM transactions GROUP BY category, source, asset ORDER BY total_usd DESC
      `).all();
      console.log(`\n${'CATEGORY'.padEnd(15)} ${'SOURCE'.padEnd(15)} ${'ASSET'.padEnd(8)} ${'COUNT'.padEnd(8)} ${'TOTAL_USD'.padEnd(12)}`);
      console.log('─'.repeat(65));
      for (const r of rows) {
        console.log(`${r.category.padEnd(15)} ${r.source.padEnd(15)} ${r.asset.padEnd(8)} ${r.count.toString().padEnd(8)} $${(r.total_usd||0).toFixed(2).padEnd(12)}`);
      }
      break;
    }
    
    case 'log': {
      // node treasury.js log nova income x402_api ETH 10000000000000000 "API payment from client"
      const [wLabel, type, source, asset, amount, ...noteParts] = args;
      const walletId = wLabel === 'acp' ? ACP : NOVA;
      const txHash = noteParts.find(p => p.startsWith('0x')) || null;
      const note = noteParts.filter(p => !p.startsWith('0x')).join(' ');
      const amountRaw = BigInt(amount);
      recordTransaction({ walletId, type, category: type, source, asset, amount: amountRaw, txHash, note });
      console.log('Logged:', { walletId, type, source, asset, amount: amountRaw.toString(), note });
      break;
    }
    
    default:
      console.log('Commands: status | sync | history [acp] | report | log <wallet> <type> <source> <asset> <amount> [note]');
  }
  
  db.close();
}

main().catch(e => { console.error(e); process.exit(1); });
