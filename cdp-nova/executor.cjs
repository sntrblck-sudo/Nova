#!/usr/bin/env node
/**
 * Idea Queue Executor
 * Run by Nova's heartbeat on each cycle.
 * Reads idea_queue.jsonl, executes queued ideas as sub-agents,
 * then marks them complete and logs results.
 *
 * Usage: node executor.cjs [--dry-run]
 */

const fs = require('fs');
const path = require('path');
const { spawn, execSync } = require('child_process');

const QUEUE_FILE = path.join(__dirname, 'social-manager', 'idea_queue.jsonl');
const CHOICE_FILE = path.join(__dirname, 'social-manager', 'novas-choice.json');
const MEMORY_FILE = path.join(__dirname, 'memory', '2026-04-09.md');
const LOG_FILE    = path.join(__dirname, 'social-manager', 'executor.log');
const DRY_RUN     = process.argv.includes('--dry-run');

function log(msg) {
  const ts = new Date().toISOString();
  const line = `[${ts}] ${msg}`;
  console.log(line);
  fs.appendFileSync(LOG_FILE, line + '\n');
}

function getQueuedIdeas() {
  try {
    return fs.readFileSync(QUEUE_FILE, 'utf8')
      .split('\n').filter(Boolean)
      .map(l => { try { return JSON.parse(l); } catch { return null; } })
      .filter(Boolean)
      .filter(q => q.status === 'queued');
  } catch {
    return [];
  }
}

function updateQueueEntry(id, updates) {
  const lines = fs.readFileSync(QUEUE_FILE, 'utf8').split('\n');
  const updated = lines.map(l => {
    try {
      const q = JSON.parse(l);
      if (q.id === id) return { ...q, ...updates };
    } catch {}
    return l;
  }).filter(Boolean);
  fs.writeFileSync(QUEUE_FILE, updated.join('\n') + '\n');
}

function appendMemory(text) {
  fs.appendFileSync(MEMORY_FILE, text + '\n');
}

function spawnExecutor(idea) {
  return new Promise((resolve, reject) => {
    const today = new Date().toISOString().slice(0, 10);
    const task = `Nova's Idea Queue Executor is running an idea:

"${idea}"

Execute it. Write results to memory/${today}.md (append, don't overwrite).
For on-chain actions: small amounts, verify addresses.
Report back briefly — what you did, what happened.`;

    const child = spawn('openclaw', [
      'sessions', 'spawn',
      '--label', `nova-executor/idea`,
      '--runtime', 'subagent',
      '--mode', 'run',
      '--timeout-seconds', '600',
      '--task', task
    ], {
      cwd: __dirname,
      stdio: ['ignore', 'pipe', 'pipe']
    });

    let out = '';
    child.stdout.on('data', d => { out += d; process.stdout.write(d); });
    child.stderr.on('data', d => { out += d; process.stderr.write(d); });
    child.on('exit', code => {
      if (code === 0) resolve(out);
      else reject(new Error(`openclaw exited code=${code}`));
    });
    child.on('error', reject);
  });
}

async function main() {
  log('=== Idea executor starting ===');

  const queued = getQueuedIdeas();
  if (queued.length === 0) {
    log('No queued ideas. Done.');
    return;
  }

  const idea = queued[0];
  log(`📋 Executing: "${idea.idea}"`);

  if (DRY_RUN) {
    log('[DRY-RUN] Would execute:', idea.idea);
    return;
  }

  updateQueueEntry(idea.id, { status: 'running', startedAt: new Date().toISOString() });

  try {
    const result = await spawnExecutor(idea.idea);
    updateQueueEntry(idea.id, { status: 'completed', completedAt: new Date().toISOString() });

    const summary = `\n## Idea Executed: ${idea.idea.slice(0, 80)}\nExecuted at: ${new Date().toISOString()}\nResult: ${result.slice(0, 200)}`;
    appendMemory(summary);
    log(`✅ Idea completed: "${idea.idea}"`);

    // Also update novas-choice.json if this was today's idea
    try {
      const choice = JSON.parse(fs.readFileSync(CHOICE_FILE, 'utf8'));
      if (choice.task === idea.idea && choice.status === 'queued') {
        choice.status = 'completed';
        choice.completedAt = new Date().toISOString();
        fs.writeFileSync(CHOICE_FILE, JSON.stringify(choice, null, 2));
        log('Updated novas-choice.json → completed');
      }
    } catch {}

  } catch(e) {
    updateQueueEntry(idea.id, { status: 'failed', error: e.message });
    log(`❌ Idea failed: ${e.message}`);
  }

  log('=== Executor done ===');
}

main().catch(e => {
  console.error('Executor error:', e.message);
  process.exit(1);
});
