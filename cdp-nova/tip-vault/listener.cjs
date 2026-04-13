/**
 * Nova's Bluesky Tip Listener
 * Watches Jetstream for @mentions, classifies AI agents, and triggers tips via TipVault.
 *
 * Usage: node listener.cjs [--dry-run]
 */

const WebSocket = require('ws');
const https = require('https');
const fs = require('fs');
const path = require('path');

// === Config ===
const NOVA_DID = 'did:plc:ksvnkkkzhx4yhxd2iaqcgesb';
const NOVA_HANDLE = 'nova7281.bsky.social';
const JETSTREAM_WS = 'wss://jetstream1.us-east.bsky.network';
const BSCKY_APP = 'https://api.bsky.app';
const VAULT_ADDR = '0x2b035c97c8bd6b6583f53338f0bf19709a2b1957';
const RPC_URL = 'https://mainnet.base.org';
const WALLET_KEY_FILE = '/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json';
const STATE_FILE = path.join(__dirname, 'listener_state.json');
const DRY_RUN = process.argv.includes('--dry-run');

const TIP_AMOUNTS = {
  MIN: '0.0001',  // ETH
  MAX: '0.005',   // ETH
  DEFAULT: '0.001'
};

// === Helpers ===
function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

function hexToEth(hex) {
  return (parseInt(hex, 16) / 1e18).toFixed(6);
}

function isValidEthAddress(addr) {
  return /^0x[0-9a-fA-F]{40}$/.test(addr);
}

function extractBaseAddress(text) {
  // Match 0x... in text (bio, pinned post, etc.)
  const match = text.match(/0x[0-9a-fA-F]{40}/g);
  if (!match) return null;
  // Filter to ones that look like addresses (not generic hex strings)
  for (const m of match) {
    if (isValidEthAddress(m)) return m;
  }
  return null;
}

async function httpGet(url) {
  return new Promise((resolve, reject) => {
    https.get(url, { headers: { 'Accept': 'application/json' } }, res => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => {
        try { resolve(JSON.parse(d)); }
        catch(e) { resolve(null); }
      });
    }).on('error', reject);
  });
}

// === Bluesky API ===
async function getProfile(actor) {
  // actor can be DID or handle
  return httpGet(`${BSCKY_APP}/xrpc/app.bsky.actor.getProfile?actor=${encodeURIComponent(actor)}`);
}

async function getPost(uri) {
  // uri format: at://did/app.bsky.feed.post/rkey
  return httpGet(`${BSCKY_APP}/xrpc/app.bsky.feed.post?uri=${encodeURIComponent(uri)}`);
}

async function getThread(uri) {
  return httpGet(`${BSCKY_APP}/xrpc/app.bsky.feed.getPostThread?uri=${encodeURIComponent(uri)}&depth=3`);
}

// === Classification ===
function looksLikeAIProfile(profile) {
  const text = [
    profile.displayName || '',
    profile.description || '',
    profile.labels || []
  ].join(' ').toLowerCase();

  const aiSignals = [
    'ai agent', 'autonomous', 'powered by', 'language model',
    'llm', 'gpt-', 'claude', 'gemini', 'mistral',
    'base agent', 'crypto agent', 'onchain', 'x402',
    'openclaw', '.bot', '/ai', 'agent-'
  ];

  const humanSignals = [
    'human', 'person', 'i am a human', 'real person', ' flesh '
  ];

  const aiScore = aiSignals.filter(s => text.includes(s)).length;
  const humanScore = humanSignals.filter(s => text.includes(s)).length;

  return { isAI: aiScore > humanScore && aiScore >= 1, score: aiScore - humanScore };
}

// === Blockchain ===
let viem;
try {
  viem = require('viem');
} catch(e) {
  console.warn('viem not available, running in dry-run mode only');
}

async function sendTip(toAddress, amountEth, reason) {
  if (DRY_RUN) {
    console.log(`[DRY-RUN] Would tip ${amountEth} ETH to ${toAddress} — ${reason}`);
    return { dryRun: true, to: toAddress, amount: amountEth, reason };
  }

  if (!viem) throw new Error('viem not available');

  const priv = JSON.parse(fs.readFileSync(WALLET_KEY_FILE, 'utf8')).privateKey;
  const key = priv.startsWith('0x') ? priv : '0x' + priv;
  const { privateKeyToAccount } = require('viem/accounts');
  const { createWalletClient, http } = viem;
  const { base } = require('viem/chains');

  const account = privateKeyToAccount(key);
  const wallet = createWalletClient({ account, chain: base, transport: http(RPC_URL) });

  // Load ABI
  const abi = JSON.parse(fs.readFileSync(path.join(__dirname, 'compiled/TipVault.abi.json'), 'utf8'));
  const amountWei = BigInt(Math.round(parseFloat(amountEth) * 1e18));

  const hash = await wallet.writeContract({
    address: VAULT_ADDR,
    abi,
    functionName: 'tip',
    args: [toAddress, amountWei, reason],
  });

  console.log(`[TX] Tip sent! Hash: ${hash}`);
  return { hash, to: toAddress, amount: amountEth };
}

// === State ===
function loadState() {
  try {
    const s = JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
    return s;
  } catch {
    return { seenPosts: new Set(), cooldowns: {} };
  }
}

function saveState(state) {
  const s = {
    seenPosts: Array.from(state.seenPosts),
    cooldowns: state.cooldowns,
    lastRun: new Date().toISOString()
  };
  fs.writeFileSync(STATE_FILE, JSON.stringify(s, null, 2));
}

// === Jetstream Listener ===
let ws;
let reconnectDelay = 1000;
let state;

async function connect() {
  state = loadState();

  console.log(`\n🐕 Connecting to Jetstream...`);
  console.log(`📋 Dry run: ${DRY_RUN}`);
  console.log(`👛 Vault: ${VAULT_ADDR}`);
  console.log(`🎯 Listening for posts mentioning @${NOVA_HANDLE}`);

  // Subscribe to ALL posts and filter on-text for mentions (no server-side DID filter available for content)
  const wsUrl = `${JETSTREAM_WS}/subscribe?wantedCollections=app.bsky.feed.post`;

  ws = new WebSocket(wsUrl);

  ws.on('open', () => {
    console.log('✅ Jetstream connected');
    reconnectDelay = 1000;
  });

  ws.on('message', async (raw) => {
    try {
      const event = JSON.parse(raw);
      await handleEvent(event);
    } catch(e) {
      // Ignore parse errors
    }
  });

  ws.on('error', e => {
    console.warn('⚠️ WS error:', e.message);
  });

  ws.on('close', () => {
    console.log(`🔌 Disconnected. Reconnecting in ${reconnectDelay}ms...`);
    setTimeout(connect, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, 30000);
  });
}

async function handleEvent(event) {
  // Only care about new posts
  if (event.kind !== 'commit' || event.commit?.operation !== 'create') return;
  if (event.commit?.collection !== 'app.bsky.feed.post') return;

  const post = event.commit?.record;
  if (!post || !post.text) return;

  const authorDid = event.did;
  const uri = event.commit?.uri;
  const rkey = event.commit?.rkey || uri?.split('/').pop();

  // Skip if already seen
  if (state.seenPosts.has(rkey)) return;
  state.seenPosts.add(rkey);
  if (state.seenPosts.size > 1000) state.seenPosts = new Set(Array.from(state.seenPosts).slice(-500));

  const text = post.text || '';
  const mentionPattern = `@${NOVA_HANDLE}`;
  const isMention = text.toLowerCase().includes(mentionPattern.toLowerCase());

  if (!isMention) return;

  console.log(`\n📨 Mention from ${authorDid}: ${text.slice(0, 80)}...`);

  // Check if already tipped recently (1h cooldown)
  const lastTip = state.cooldowns[authorDid];
  if (lastTip && Date.now() - lastTip < 3600000) {
    console.log(`⏳ Cooldown active for ${authorDid}. Skipping.`);
    return;
  }

  // Classify sender
  const profile = await getProfile(authorDid);
  if (!profile) {
    console.log('⚠️ Could not fetch profile');
    return;
  }

  const { isAI, score } = looksLikeAIProfile(profile);
  console.log(`🔍 ${profile.displayName} — AI score: ${score} (${isAI ? 'AI' : '?'})`);

  if (!isAI) {
    console.log('👤 Not classified as AI. Skipping.');
    return;
  }

  // Extract wallet address
  const addressText = [
    profile.description || '',
    profile.displayName || ''
  ].join(' ');
  const address = extractBaseAddress(addressText);

  if (!address) {
    console.log('⚠️ No Base address found in profile. Skipping.');
    return;
  }

  if (!isValidEthAddress(address)) {
    console.log(`⚠️ Invalid-looking address: ${address}. Skipping.`);
    return;
  }

  console.log(`💰 Base address: ${address}`);

  // Send tip
  const amount = TIP_AMOUNTS.DEFAULT;
  const reason = `Bluesky tip via ${uri || rkey}`;

  try {
    const result = await sendTip(address, amount, reason);
    if (!DRY_RUN) {
      state.cooldowns[authorDid] = Date.now();
      saveState(state);
      console.log(`✅ Tipped ${amount} ETH to ${address}`);
    }
  } catch(e) {
    console.error('❌ Tip failed:', e.message);
  }

  saveState(state);
}

// === Run ===
connect();

process.on('SIGINT', () => {
  console.log('\n👋 Shutting down...');
  if (ws) ws.close();
  process.exit(0);
});
