#!/usr/bin/env node
/**
 * Nova's Portfolio Manager
 * Tracks positions, risk limits, and portfolio state.
 * Single source of truth for Nova's deployed capital.
 */

const fs = require('fs');
const path = require('path');

const PORTFOLIO_FILE = path.join(__dirname, 'portfolio_positions.json');
const RISK_FILE      = path.join(__dirname, 'risk_limits.json');
const LOG_FILE      = path.join(__dirname, 'portfolio.log');

const NOVA_WALLET = '0xB743fdbA842379933A3774617786712458659D16';

// === Risk Limits ===
const DEFAULT_RISK_LIMITS = {
  maxPositionUsd: 50,         // Max single position in USD
  maxTotalDeployUsd: 100,     // Max total deployed
  minHealthFactor: 1.5,       // For lending positions
  maxStableLTV: 0.80,          // Max loan-to-value for stablecoins
  depegThreshold: 0.98,       // USDC/USDM must stay above this
  maxGasPriceGwei: 50,         // Abort if gas exceeds this
  positionCooldownBlocks: 12, // ~2 min on Base between actions
};

function loadRiskLimits() {
  try {
    return JSON.parse(fs.readFileSync(RISK_FILE, 'utf8'));
  } catch {
    return DEFAULT_RISK_LIMITS;
  }
}

function saveRiskLimits(limits) {
  fs.writeFileSync(RISK_FILE, JSON.stringify(limits, null, 2));
}

// === Portfolio Positions ===
function loadPositions() {
  try {
    return JSON.parse(fs.readFileSync(PORTFOLIO_FILE, 'utf8'));
  } catch {
    return { positions: [], lastAction: null, totalValueUsd: 0 };
  }
}

function savePositions(data) {
  fs.writeFileSync(PORTFOLIO_FILE, JSON.stringify(data, null, 2));
}

function logAction(action, detail) {
  const ts = new Date().toISOString();
  const line = `[${ts}] [${action}] ${detail}`;
  console.log(line);
  fs.appendFileSync(LOG_FILE, line + '\n');
}

// === Portfolio State ===
function getPortfolioSummary(positions, prices) {
  let totalUsd = 0;
  const detailed = positions.map(p => {
    const price = prices[p.asset] || 0;
    const valueUsd = p.amount * price;
    totalUsd += valueUsd;
    const age = Date.now() - new Date(p.deployedAt).getTime();
    const days = Math.floor(age / 86400000);
    return { ...p, valueUsd, ageDays: days };
  });
  return { positions: detailed, totalValueUsd: totalUsd };
}

// === Check Risk Limits ===
function canDeploy(amountUsd, riskLimits, currentTotal) {
  if (amountUsd > riskLimits.maxPositionUsd) {
    return { allowed: false, reason: `Exceeds max position size (${riskLimits.maxPositionUsd} USD)` };
  }
  if (currentTotal + amountUsd > riskLimits.maxTotalDeployUsd) {
    return { allowed: false, reason: `Would exceed total deploy cap (${riskLimits.maxTotalDeployUsd} USD)` };
  }
  return { allowed: true };
}

// === Add Position ===
function addPosition(asset, amount, amountUsd, protocol, yieldApy, notes = '') {
  const data = loadPositions();
  const positions = data.positions;
  const riskLimits = loadRiskLimits();
  
  const totalCurrent = positions.reduce((sum, p) => sum + (p.valueUsd || 0), 0);
  const check = canDeploy(amountUsd, riskLimits, totalCurrent);
  
  if (!check.allowed) {
    console.log(`⚠️ Deploy blocked: ${check.reason}`);
    return null;
  }

  const newPos = {
    id: `pos_${Date.now()}`,
    asset,
    amount,
    valueUsd: amountUsd,
    protocol,
    yieldApy,
    notes,
    deployedAt: new Date().toISOString(),
    status: 'active'
  };

  positions.push(newPos);
  savePositions({ positions, lastAction: new Date().toISOString(), totalValueUsd: totalCurrent + amountUsd });
  logAction('DEPLOY', `${amount} ${asset} → ${protocol} (${amountUsd} USD, APY: ${yieldApy}%)`);
  console.log(`✅ Deployed: ${amount} ${asset} to ${protocol} at ${yieldApy}% APY`);
  return newPos;
}

// === Remove Position ===
function closePosition(positionId, notes = '') {
  const data = loadPositions();
  const positions = data.positions;
  const pos = positions.find(p => p.id === positionId);
  if (!pos) {
    console.log(`⚠️ Position ${positionId} not found`);
    return null;
  }

  pos.status = 'closed';
  pos.closedAt = new Date().toISOString();
  pos.closeNotes = notes;

  const newTotal = positions.filter(p => p.status === 'active')
    .reduce((sum, p) => sum + (p.valueUsd || 0), 0);

  data.totalValueUsd = newTotal;
  data.lastAction = new Date().toISOString();
  savePositions(data);
  logAction('CLOSE', `${pos.asset} from ${pos.protocol} — ${notes}`);
  console.log(`✅ Closed: ${positionId} (${pos.asset})`);
  return pos;
}

// === Status Report ===
function status() {
  const data = loadPositions();
  const riskLimits = loadRiskLimits();
  const active = data.positions.filter(p => p.status === 'active');
  const totalUsd = active.reduce((sum, p) => sum + (p.valueUsd || 0), 0);

  console.log('\n╔═══════════════════════════════════════╗');
  console.log('║       NOVA PORTFOLIO STATUS          ║');
  console.log('╠═══════════════════════════════════════╣');
  console.log(`║ Total Deployed: $${totalUsd.toFixed(2)} / $${riskLimits.maxTotalDeployUsd}     ║`);
  console.log(`║ Positions: ${active.length} active               ║`);
  console.log('╠═══════════════════════════════════════╣');
  active.forEach(p => {
    const age = Math.floor((Date.now() - new Date(p.deployedAt).getTime()) / 86400000);
    console.log(`║ ${p.asset.padEnd(8)} ${p.amount.toFixed(4).padStart(12)} $${p.valueUsd.toFixed(2).padStart(8)} @ ${p.yieldApy}% ${p.protocol.padEnd(14)} ${age}d║`);
  });
  console.log('╚═══════════════════════════════════════╝');
  console.log(`Risk limits: max pos $${riskLimits.maxPositionUsd}, max total $${riskLimits.maxTotalDeployUsd}`);
  return { positions: active, totalUsd, riskLimits };
}

// === CLI ===
const cmd = process.argv[2];
if (cmd === 'status') {
  status();
} else if (cmd === 'add' && process.argv[3]) {
  // node portfolio_manager.cjs add <asset> <amount> <amountUsd> <protocol> <apy> [notes]
  const [, , , asset, amount, amountUsd, protocol, apy, ...notesArr] = process.argv;
  addPosition(asset, parseFloat(amount), parseFloat(amountUsd), protocol, parseFloat(apy), notesArr.join(' '));
} else if (cmd === 'close' && process.argv[3]) {
  const [, , , posId, ...notesArr] = process.argv;
  closePosition(posId, notesArr.join(' '));
} else if (cmd === 'limits') {
  const limits = loadRiskLimits();
  console.log('Risk limits:', JSON.stringify(limits, null, 2));
} else if (cmd === 'log') {
  console.log('=== Recent actions ===');
  const lines = fs.readFileSync(LOG_FILE, 'utf8').split('\n').filter(Boolean).slice(-20);
  lines.forEach(l => console.log(l));
} else {
  console.log('Usage:');
  console.log('  node portfolio_manager.cjs status');
  console.log('  node portfolio_manager.cjs add <asset> <amount> <amountUsd> <protocol> <apy> [notes]');
  console.log('  node portfolio_manager.cjs close <positionId> [notes]');
  console.log('  node portfolio_manager.cjs limits');
  console.log('  node portfolio_manager.cjs log');
}
