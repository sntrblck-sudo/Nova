/**
 * Nova's Unified Action Logger v2
 * Persistent audit trail with hash chain integrity
 * 
 * Integrity guarantees:
 * - Hash chain: each entry contains SHA-256 of previous entry
 * - SQLite append-only: UPDATE/DELETE blocked by trigger
 * - JSONL: append-only with hash chain
 * - Stale pending check: flags entries stuck in non-terminal state
 * 
 * Usage:
 *   const { logAction, logOutcome, logDecision, queryActions, getSummary, checkStalePending } = require('./action_logger.cjs');
 */

const Database = require('better-sqlite3');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const LOG_DIR = '/home/sntrblck/.openclaw/workspace/memory';
const LOG_DB = path.join(LOG_DIR, 'action_log.db');
const LOG_JSONL = path.join(LOG_DIR, 'action_log.jsonl');

if (!fs.existsSync(LOG_DIR)) {
  fs.mkdirSync(LOG_DIR, { recursive: true });
}

// Initialize SQLite with append-only integrity
const db = new Database(LOG_DB);

// Enable WAL mode for better concurrency
db.pragma('journal_mode = WAL');

// Create tables
db.exec(`
  CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    session_id TEXT,
    action_type TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    rationale TEXT,
    actor TEXT NOT NULL DEFAULT 'nova',
    outcome TEXT NOT NULL DEFAULT 'pending',
    outcome_detail TEXT,
    metadata TEXT,
    entry_hash TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    session_id TEXT,
    decision_type TEXT NOT NULL,
    context TEXT NOT NULL,
    options_considered TEXT,
    choice TEXT NOT NULL,
    rationale TEXT NOT NULL,
    confidence TEXT,
    metadata TEXT,
    entry_hash TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
  );
`);

// Append-only trigger: block updates and deletes
try {
  db.exec(`
    CREATE TRIGGER IF NOT EXISTS actions_no_update BEFORE UPDATE ON actions
    BEGIN SELECT RAISE(ABORT, 'Append-only: updates not allowed'); END;
    
    CREATE TRIGGER IF NOT EXISTS actions_no_delete BEFORE DELETE ON actions
    BEGIN SELECT RAISE(ABORT, 'Append-only: deletes not allowed'); END;
    
    CREATE TRIGGER IF NOT EXISTS decisions_no_update BEFORE UPDATE ON decisions
    BEGIN SELECT RAISE(ABORT, 'Append-only: updates not allowed'); END;
    
    CREATE TRIGGER IF NOT EXISTS decisions_no_delete BEFORE DELETE ON decisions
    BEGIN SELECT RAISE(ABORT, 'Append-only: deletes not allowed'); END;
  `);
} catch (e) {
  // Triggers may already exist
}

// Get the hash of the last entry
function getLastHash(table, hashColumn = 'entry_hash') {
  try {
    const row = db.prepare(`SELECT ${hashColumn} FROM ${table} ORDER BY id DESC LIMIT 1`).get();
    return row ? row[hashColumn] : genesisHash();
  } catch (e) {
    return genesisHash();
  }
}

function genesisHash() {
  return crypto.createHash('sha256').update('').digest('hex');
}

function hashEntry(entry, prevHash) {
  const content = JSON.stringify({ ...entry, prevHash });
  return crypto.createHash('sha256').update(content).digest('hex');
}

// JSONL helpers
function readLastJsonlEntry() {
  if (!fs.existsSync(LOG_JSONL)) return null;
  const lines = fs.readFileSync(LOG_JSONL, 'utf8').trim().split('\n').filter(l => l.length);
  if (lines.length === 0) return null;
  return JSON.parse(lines[lines.length - 1]);
}

function appendJsonl(entry, prevHash) {
  entry.prevHash = prevHash;
  entry.hash = hashEntry(entry, prevHash);
  fs.appendFileSync(LOG_JSONL, JSON.stringify(entry) + '\n');
  return entry.hash;
}

/**
 * Log an action — BEFORE execution
 */
function logAction({ actionType, category, description, rationale = null, sessionId = null, metadata = null, stateSnapshot = null }) {
  const timestamp = new Date().toISOString();
  const prevHash = getLastHash('actions');
  
  // Build entry (without hash)
  const entry = {
    timestamp,
    sessionId,
    actionType,
    category,
    description,
    rationale,
    actor: 'nova',
    outcome: 'pending',
    outcomeDetail: null,
    metadata: metadata ? { ...metadata, stateSnapshot } : { stateSnapshot }
  };
  
  const entryHash = hashEntry(entry, prevHash);
  
  const stmt = db.prepare(`
    INSERT INTO actions (timestamp, session_id, action_type, category, description, rationale, metadata, entry_hash, prev_hash, actor)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'nova')
  `);
  
  const result = stmt.run(
    timestamp, sessionId, actionType, category, description, rationale,
    JSON.stringify(entry.metadata), entryHash, prevHash
  );
  
  entry.id = result.lastInsertRowid;
  
  // Append to JSONL with chain
  const jsonlHash = appendJsonl(entry, prevHash);
  
  // Update meta table with latest hash
  db.prepare('INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)').run('actions_last_hash', jsonlHash);
  
  return { id: entry.id, hash: jsonlHash, prevHash };
}

/**
 * Log outcome of an existing action — AFTER completion
 * Note: Can't use UPDATE due to append-only trigger. Instead, log a new "outcome" entry.
 */
function logOutcome(actionId, outcome, outcomeDetail = null) {
  const timestamp = new Date().toISOString();
  const prevHash = getLastHash('actions');
  
  // Get the original action for context
  const original = db.prepare('SELECT * FROM actions WHERE id = ?').get(actionId);
  if (!original) throw new Error(`Action ${actionId} not found`);
  
  const entry = {
    timestamp,
    type: 'outcome',
    refId: actionId,
    originalAction: original.action_type,
    description: `[OUTCOME] ${original.description}`,
    outcome,
    outcomeDetail,
    actor: 'nova',
    metadata: { refActionId: actionId }
  };
  
  const entryHash = hashEntry(entry, prevHash);
  
  // Log as new entry referencing the original
  const stmt = db.prepare(`
    INSERT INTO actions (timestamp, action_type, category, description, rationale, outcome, outcome_detail, metadata, entry_hash, prev_hash, actor)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'nova')
  `);
  
  const result = stmt.run(
    timestamp, 'outcome_recorded', original.category,
    `[OUTCOME] ${original.description}`, `Outcome of action #${actionId}`,
    outcome, outcomeDetail, JSON.stringify({ refActionId: actionId }),
    entryHash, prevHash
  );
  
  appendJsonl(entry, prevHash);
  db.prepare('INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)').run('actions_last_hash', hashEntry(entry, prevHash));
  
  return { id: result.lastInsertRowid, hash: hashEntry(entry, prevHash) };
}

/**
 * Log a decision with context and options considered
 */
function logDecision({ decisionType, context, optionsConsidered = null, choice, rationale, confidence = null, sessionId = null, stateSnapshot = null }) {
  const timestamp = new Date().toISOString();
  const prevHash = getLastHash('decisions');
  
  const entry = {
    timestamp,
    sessionId,
    decisionType,
    context,
    optionsConsidered,
    choice,
    rationale,
    confidence,
    metadata: { stateSnapshot }
  };
  
  const entryHash = hashEntry(entry, prevHash);
  
  const stmt = db.prepare(`
    INSERT INTO decisions (timestamp, session_id, decision_type, context, options_considered, choice, rationale, confidence, metadata, entry_hash, prev_hash)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);
  
  const result = stmt.run(
    timestamp, sessionId, decisionType, context,
    optionsConsidered ? JSON.stringify(optionsConsidered) : null,
    choice, rationale, confidence,
    JSON.stringify({ stateSnapshot }),
    entryHash, prevHash
  );
  
  entry.id = result.lastInsertRowid;
  appendJsonl(entry, prevHash);
  db.prepare('INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)').run('decisions_last_hash', hashEntry(entry, prevHash));
  
  return { id: entry.id, hash: hashEntry(entry, prevHash) };
}

/**
 * Query actions with filters
 */
function queryActions({ actionType = null, category = null, outcome = null, since = null, limit = 100, sessionId = null } = {}) {
  let sql = 'SELECT * FROM actions WHERE 1=1';
  const params = [];
  if (actionType) { sql += ' AND action_type = ?'; params.push(actionType); }
  if (category) { sql += ' AND category = ?'; params.push(category); }
  if (outcome) { sql += ' AND outcome = ?'; params.push(outcome); }
  if (sessionId) { sql += ' AND session_id = ?'; params.push(sessionId); }
  if (since) { sql += ' AND timestamp >= ?'; params.push(since); }
  sql += ' ORDER BY timestamp DESC LIMIT ?';
  params.push(limit);
  return db.prepare(sql).all(...params);
}

/**
 * Query decisions
 */
function queryDecisions({ decisionType = null, since = null, limit = 50 } = {}) {
  let sql = 'SELECT * FROM decisions WHERE 1=1';
  const params = [];
  if (decisionType) { sql += ' AND decision_type = ?'; params.push(decisionType); }
  if (since) { sql += ' AND timestamp >= ?'; params.push(since); }
  sql += ' ORDER BY timestamp DESC LIMIT ?';
  params.push(limit);
  return db.prepare(sql).all(...params);
}

/**
 * Get summary stats
 */
function getSummary(days = 7) {
  const since = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();
  
  const total = db.prepare('SELECT COUNT(*) as count FROM actions WHERE timestamp >= ?').get(since);
  const byOutcome = db.prepare(`SELECT outcome, COUNT(*) as count FROM actions WHERE timestamp >= ? GROUP BY outcome`).all(since);
  const byCategory = db.prepare(`SELECT category, COUNT(*) as count FROM actions WHERE timestamp >= ? GROUP BY category ORDER BY count DESC`).all(since);
  const decisions = db.prepare('SELECT COUNT(*) as count FROM decisions WHERE timestamp >= ?').get(since);
  const pending = db.prepare(`SELECT COUNT(*) as count FROM actions WHERE outcome = 'pending'`).get();
  const stalePending = getStalePending();
  
  return {
    period: `last ${days} days`,
    totalActions: total.count,
    byOutcome: Object.fromEntries(byOutcome.map(r => [r.outcome, r.count])),
    byCategory: Object.fromEntries(byCategory.map(r => [r.category, r.count])),
    totalDecisions: decisions.count,
    pending: pending.count,
    stalePending: stalePending.length
  };
}

/**
 * Find entries stuck in non-terminal state for > 48 hours
 */
function getStalePending(maxAgeHours = 48) {
  const cutoff = new Date(Date.now() - maxAgeHours * 60 * 60 * 1000).toISOString();
  return db.prepare(`
    SELECT id, timestamp, action_type, category, description, outcome
    FROM actions
    WHERE outcome = 'pending' AND timestamp < ?
    ORDER BY timestamp ASC
  `).all(cutoff);
}

/**
 * Verify hash chain integrity
 */
function verifyIntegrity() {
  const actions = db.prepare('SELECT * FROM actions ORDER BY id ASC').all();
  const decisions = db.prepare('SELECT * FROM decisions ORDER BY id ASC').all();
  
  let prevHash = genesisHash();
  let broken = [];
  
  for (const row of actions) {
    const expected = hashEntry({
      timestamp: row.timestamp,
      sessionId: row.session_id,
      actionType: row.action_type,
      category: row.category,
      description: row.description,
      rationale: row.rationale,
      actor: row.actor,
      outcome: row.outcome,
      outcomeDetail: row.outcome_detail,
      metadata: row.metadata ? JSON.parse(row.metadata) : null
    }, prevHash);
    
    if (expected !== row.entry_hash) {
      broken.push({ table: 'actions', id: row.id, expected, actual: row.entry_hash });
    }
    prevHash = row.entry_hash;
  }
  
  prevHash = genesisHash();
  for (const row of decisions) {
    const expected = hashEntry({
      timestamp: row.timestamp,
      sessionId: row.session_id,
      decisionType: row.decision_type,
      context: row.context,
      optionsConsidered: row.options_considered ? JSON.parse(row.options_considered) : null,
      choice: row.choice,
      rationale: row.rationale,
      confidence: row.confidence,
      metadata: row.metadata ? JSON.parse(row.metadata) : null
    }, prevHash);
    
    if (expected !== row.entry_hash) {
      broken.push({ table: 'decisions', id: row.id, expected, actual: row.entry_hash });
    }
    prevHash = row.entry_hash;
  }
  
  return { valid: broken.length === 0, broken };
}

/**
 * Print readable summary
 */
function printSummary(days = 7) {
  const s = getSummary(days);
  const stale = getStalePending();
  
  console.log(`\n=== Nova Action Log Summary (${s.period}) ===`);
  console.log(`Total actions: ${s.totalActions}`);
  console.log(`Total decisions: ${s.totalDecisions}`);
  console.log(`Pending outcomes: ${s.pending}`);
  if (s.stalePending > 0) console.log(`⚠️  STALE PENDING: ${s.stalePending} entries >48h old`);
  
  if (Object.keys(s.byOutcome).length) {
    console.log('\nBy outcome:');
    for (const [k, v] of Object.entries(s.byOutcome)) console.log(`  ${k}: ${v}`);
  }
  if (Object.keys(s.byCategory).length) {
    console.log('\nBy category:');
    for (const [k, v] of Object.entries(s.byCategory)) console.log(`  ${k}: ${v}`);
  }
  
  if (stale.length > 0) {
    console.log('\n⚠️  STALE PENDING ENTRIES:');
    for (const e of stale) {
      console.log(`  #${e.id} | ${e.timestamp} | ${e.description.slice(0, 60)}`);
    }
  }
}

if (require.main === module) {
  console.log('Nova Action Logger v2 — Hash Chain + Append-Only');
  console.log('DB:', LOG_DB);
  console.log('JSONL:', LOG_JSONL);
  
  const integrity = verifyIntegrity();
  console.log('\nIntegrity check:', integrity.valid ? '✅ PASSED' : '❌ FAILED');
  if (!integrity.valid) {
    console.log('Broken entries:', integrity.broken);
  }
  
  printSummary(30);
}

module.exports = {
  logAction,
  logOutcome,
  logDecision,
  queryActions,
  queryDecisions,
  getSummary,
  getStalePending,
  verifyIntegrity,
  printSummary
};
