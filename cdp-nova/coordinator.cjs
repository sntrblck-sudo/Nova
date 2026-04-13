#!/usr/bin/env node
/**
 * Nova's Idea Coordinator
 * Reads the latest idea from novas-choice.json, classifies it by tier,
 * and either queues it for AUTOMATIC execution or surfaces it to Sen.
 *
 * AUTOMATIC ideas → written to idea_queue.jsonl → picked up by Nova's heartbeat
 * SURFACE ideas → Telegram message to Sen → waits for approval
 * ASK ideas → Telegram message to Sen → waits for guidance
 *
 * Usage: node coordinator.cjs
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

const CHOICE_FILE = path.join(__dirname, 'social-manager', 'novas-choice.json');
const LOG_FILE    = path.join(__dirname, 'social-manager', 'coordinator.log');
const QUEUE_FILE  = path.join(__dirname, 'social-manager', 'idea_queue.jsonl');
const TG_CHAT_ID  = '8544939129';

function log(msg) {
  const ts = new Date().toISOString();
  const line = `[${ts}] ${msg}`;
  console.log(line);
  fs.appendFileSync(LOG_FILE, line + '\n');
}

async function telegramSend(text) {
  const token = process.env.NOVA_TELEGRAM_BOT_TOKEN;
  if (!token) {
    console.warn('⚠️ NOVA_TELEGRAM_BOT_TOKEN not set — skipping TG');
    return;
  }
  return new Promise((resolve, reject) => {
    const url = `https://api.telegram.org/bot${token}/sendMessage?chat_id=${TG_CHAT_ID}&text=${encodeURIComponent(text)}&parse_mode=HTML`;
    https.get(url, res => {
      let d = ''; res.on('data', c => d += c);
      res.on('end', () => { try { resolve(JSON.parse(d)); } catch(e) { reject(e); } });
    }).on('error', reject);
  });
}

function classifyIdea(idea) {
  const lower = idea.toLowerCase();

  const askSignals = ['build', 'create', 'design', 'architect', 'new system', 'new skill'];
  if (askSignals.some(s => lower.includes(s)) && !lower.includes('post')) {
    return 'ASK';
  }

  const surfaceSignals = [
    'post', 'send', 'tip', 'pay', 'transfer', 'bridge', 'swap',
    'withdraw', 'deploy', 'announce', 'buy', 'sell', 'trade', 'email', 'discord'
  ];
  if (surfaceSignals.some(s => lower.includes(s))) {
    return 'SURFACE';
  }

  return 'AUTOMATIC';
}

function loadChoice() {
  try {
    return JSON.parse(fs.readFileSync(CHOICE_FILE, 'utf8'));
  } catch {
    return null;
  }
}

async function main() {
  log('=== Coordinator starting ===');

  const choice = loadChoice();
  if (!choice?.task) {
    log('⚠️ No choice file or empty task');
    return;
  }

  const today = new Date().toISOString().slice(0, 10);

  // Skip if already handled today
  if (choice.date === today && choice.status === 'completed') {
    log(`✅ Already completed: "${choice.task}"`);
    return;
  }

  log(`📋 Idea: "${choice.task}"`);

  const tier = classifyIdea(choice.task);
  log(`🏷️  Tier: ${tier}`);

  choice.tier = tier;
  choice.status = 'processing';
  choice.coordinatorStarted = new Date().toISOString();
  fs.writeFileSync(CHOICE_FILE, JSON.stringify(choice, null, 2));

  if (tier === 'AUTOMATIC') {
    const queueId = `${Date.now()}`;
    const queueEntry = {
      id: queueId,
      idea: choice.task,
      tier,
      createdAt: new Date().toISOString(),
      status: 'queued'
    };
    fs.appendFileSync(QUEUE_FILE, JSON.stringify(queueEntry) + '\n');
    choice.status = 'queued';
    choice.queuedAt = new Date().toISOString();
    log(`📝 Queued for heartbeat: ${queueId}`);
    fs.writeFileSync(CHOICE_FILE, JSON.stringify(choice, null, 2));
    log('⚡ AUTOMATIC — queued. Nova will pick it up on next heartbeat.');

  } else if (tier === 'SURFACE') {
    const msg =
`🤔 <b>Nova chose:</b> ${choice.task}

<i>She wants to act on this. Reply yes/no to approve/skip.</i>`;
    try {
      await telegramSend(msg);
      log('📱 Surfaced to Sen');
      choice.status = 'awaiting_approval';
    } catch(e) {
      log(`❌ Telegram error: ${e.message}`);
    }
    fs.writeFileSync(CHOICE_FILE, JSON.stringify(choice, null, 2));

  } else if (tier === 'ASK') {
    const msg =
`💡 <b>Nova's idea — needs your input:</b>

${choice.task}

<i>Reply with guidance and Nova will execute.</i>`;
    try {
      await telegramSend(msg);
      log('📱 Asked Sen');
      choice.status = 'awaiting_guidance';
    } catch(e) {
      log(`❌ Telegram error: ${e.message}`);
    }
    fs.writeFileSync(CHOICE_FILE, JSON.stringify(choice, null, 2));
  }

  log('=== Coordinator done ===');
}

main().catch(e => {
  console.error('Error:', e.message);
  process.exit(1);
});
