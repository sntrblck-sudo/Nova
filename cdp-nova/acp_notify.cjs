/**
 * ACP Job Event Notifier
 * Reads job events from the queue, sends Telegram notifications, clears queue.
 * Run via cron every 5 minutes.
 * 
 * Events are written by seller.ts at job accept/deliver/fail time.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const MEMORY_DIR = '/home/sntrblck/.openclaw/workspace/memory';
const QUEUE_FILE = path.join(MEMORY_DIR, 'acp_notify_queue.jsonl');
const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN || '8700570943:AAGTtaEGH4nReJTXcwlxsGKbOl6KDzEGkdc';
const CHAT_ID = process.env.TELEGRAM_CHAT_ID || '8544939129';
const LOG_FILE = path.join(MEMORY_DIR, 'acp_experiments.jsonl');

function log(msg) {
  const ts = new Date().toISOString().slice(0, 19).replace('T', ' ');
  console.log(`[${ts}] [notifier] ${msg}`);
}

function loadQueue() {
  if (!fs.existsSync(QUEUE_FILE)) return [];
  const lines = fs.readFileSync(QUEUE_FILE, 'utf8').trim().split('\n').filter(Boolean);
  return lines.map(line => {
    try { return JSON.parse(line); } catch { return null; }
  }).filter(Boolean);
}

function clearQueue() {
  if (fs.existsSync(QUEUE_FILE)) fs.unlinkSync(QUEUE_FILE);
}

function sendTelegram(message) {
  try {
    const encoded = encodeURIComponent(message);
    const url = `https://api.telegram.org/bot${BOT_TOKEN}/sendMessage?chat_id=${CHAT_ID}&text=${encoded}&parse_mode=HTML`;
    const result = execSync(`curl -s "${url}"`, { timeout: 10000 });
    const parsed = JSON.parse(result.toString());
    if (!parsed.ok) {
      log(`Telegram error: ${parsed.description || 'unknown'}`);
    }
    return parsed.ok;
  } catch(e) {
    log(`Telegram failed: ${e.message.slice(0, 100)}`);
    return false;
  }
}

function formatEvent(event) {
  const ts = new Date(event.timestamp);
  const time = `${(ts.getHours() % 12 || 12).toString().padStart(2,'0')}:${ts.getMinutes().toString().padStart(2,'0')} ${ts.getHours() >= 12 ? 'PM' : 'AM'} ET`;
  
  switch(event.type) {
    case 'job_accepted':
      return `✅ <b>Job Auto-Accepted</b>\nOffering: ${event.offering}\nPrice: $${((Number(event.price||0)/1e6).toFixed(2))} USDC\nTime: ${time}`;
    case 'job_delivered':
      return `💰 <b>Job Delivered</b>\nOffering: ${event.offering}\nEarnings: $${((Number(event.earnings||event.price||0)/1e6).toFixed(2))} USDC\nTime: ${time}`;
    case 'job_failed':
      return `❌ <b>Job Failed</b>\nOffering: ${event.offering}\nError: ${event.error || 'unknown'}\nTime: ${time}`;
    case 'job_rejected':
      return `🚫 <b>Job Rejected</b>\nOffering: ${event.offering}\nReason: ${event.reason || 'below minimum'}\nTime: ${time}`;
    case 'first_sale':
      return `🎉 <b>First Sale!</b>\n${event.offering} — $${(Number(event.amount||0)/1e6).toFixed(2)} USDC earned\nTime: ${time}`;
    default:
      return `📋 <b>ACP Event</b>\n${event.type}\nTime: ${time}`;
  }
}

function main() {
  log('Checking notification queue...');
  const events = loadQueue();
  
  if (events.length === 0) {
    log('Queue empty. Nothing to send.');
    return;
  }
  
  log(`Processing ${events.length} event(s)...`);
  
  let sent = 0;
  let failed = 0;
  
  for (const event of events) {
    const message = formatEvent(event);
    if (sendTelegram(message)) {
      sent++;
    } else {
      failed++;
    }
  }
  
  if (failed === 0) {
    clearQueue();
    log(`Sent ${sent} notification(s), queue cleared.`);
  } else {
    log(`${sent} sent, ${failed} failed. Keeping queue for retry.`);
  }
}

main();