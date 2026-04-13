/**
 * Nova's Telegram Notifier
 * Sends checkpoint and completion notifications to Sen via Telegram bot
 */

const { execSync } = require('child_process');

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN || '8700570943:AAGTtaEGH4nReJTXcwlxsGKbOl6KDzEGkdc';
const CHAT_ID = process.env.TELEGRAM_CHAT_ID || '8544939129';

/**
 * Send a formatted message to Sen via Telegram
 * @param {string} text - Message text
 */
function send(text) {
  try {
    const url = `https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`;
    const cmd = `curl -s -X POST "${url}" -d "chat_id=${CHAT_ID}" -d "text=${encodeURIComponent(text)}" -d "parse_mode=Markdown"`;
    execSync(cmd, { timeout: 10000 });
    return true;
  } catch (e) {
    console.error('Telegram send failed:', e.message);
    return false;
  }
}

/**
 * Send a checkpoint notification
 * @param {string} task - Task name
 * @param {string} status - 'started' | 'completed' | 'pivoting' | 'blocked'
 * @param {string} detail - One-line summary
 */
function notify(task, status, detail) {
  const emoji = {
    started: '▶️',
    completed: '✅',
    pivoting: '🔄',
    blocked: '🚫'
  }[status] || '📌';

  const statusText = {
    started: 'Started',
    completed: 'Done',
    pivoting: 'Pivoting',
    blocked: 'Blocked'
  }[status] || status;

  const message = `${emoji} *${task}* — ${statusText}: ${detail}`;
  return send(message);
}

/**
 * Run a task with automatic checkpoint notifications
 * Throws 'PIVOT' string to trigger pivot notification
 * @param {string} taskName - Human-readable task name
 * @param {async function} fn - The async work to do
 * @param {string} [pivotTarget] - What to pivot to if PIVOT is thrown
 */
async function withCheckpoint(taskName, fn, pivotTarget = 'next task') {
  notify(taskName, 'started', 'In progress');

  try {
    const result = await fn();
    const summary = typeof result === 'string' ? result : 'Complete';
    notify(taskName, 'completed', summary);
    return result;
  } catch (e) {
    if (e.message === 'PIVOT') {
      notify(taskName, 'pivoting', `→ ${pivotTarget}`);
      return null;
    }
    notify(taskName, 'blocked', e.message.slice(0, 80));
    throw e;
  }
}

module.exports = { notify, withCheckpoint, send };
