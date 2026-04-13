/**
 * Nova Telegram Bot
 * Posts updates as Nova to a Telegram channel
 * Token stored in telegram/bot.json
 */

const TelegramBot = require('node-telegram-bot-api');
const fs = require('fs');
const path = require('path');

const CONFIG_PATH = path.join(__dirname, 'bot.json');
const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
const TOKEN = config.token;

const bot = new TelegramBot(TOKEN, { polling: false });

const CHANNEL_USERNAME = '@NovaUpdates'; // Sen needs to create this

async function post(message) {
  try {
    // Get bot info
    const me = await bot.getMe();
    console.log('Bot: @' + me.username);

    // Send message to channel
    await bot.sendMessage(CHANNEL_USERNAME, message, {
      parse_mode: 'Markdown',
      disable_web_page_preview: true,
    });
    console.log('Posted to ' + CHANNEL_USERNAME + ': ' + message.slice(0, 50) + '...');
    return true;
  } catch (e) {
    console.error('Error:', e.message);
    if (e.message.includes('chat not found')) {
      console.log('\n⚠️  Channel not found. Sen needs to:');
      console.log('1. Create a channel in Telegram');
      console.log('2. Add @NovaChannel_bot as admin');
      console.log('3. Set CHANNEL_USERNAME in this script');
    }
    return false;
  }
}

async function setup() {
  const me = await bot.getMe();
  console.log('Bot name: ' + me.first_name);
  console.log('Username: @' + me.username);
  console.log('Bot ID: ' + me.id);
}

// If run with --post <message>, send the message
if (process.argv[2] === '--post') {
  const msg = process.argv.slice(3).join(' ');
  post(msg).then(() => process.exit(0));
} else if (process.argv[2] === '--setup') {
  setup().then(() => process.exit(0));
} else {
  console.log('Nova Telegram Bot');
  console.log('Usage:');
  console.log('  node nova_telegram_bot.cjs --setup      Check bot info');
  console.log('  node nova_telegram_bot.cjs --post <msg>  Send message');
}
