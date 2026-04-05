#!/usr/bin/env node
/**
 * Nova's Bluesky AI Monitor
 * Searches for AI/agent-related posts on Bluesky, logs findings
 * Can optionally engage (like) posts
 * 
 * Usage:
 *   node bluesky_monitor.cjs search      Run search and log findings
 *   node bluesky_monitor.cjs like       Like relevant posts (use sparingly)
 *   node bluesky_monitor.cjs digest      Print recent interesting findings
 */

const { BskyAgent } = require('@atproto/api');
const { readFileSync, appendFileSync, existsSync, writeFileSync } = require('fs');

const HANDLE = 'nova7281.bsky.social';
const APP_PASSWORD = 'nl72-t3hw-2iye-ljmd';
const LOG_FILE = '/home/sntrblck/.openclaw/workspace/cdp-nova/logs/bluesky_monitor.jsonl';
const STATE_FILE = '/home/sntrblck/.openclaw/workspace/cdp-nova/logs/bluesky_monitor_state.json';

// Search terms to track
const TRACK_TERMS = [
  'AI agent',
  'autonomous agent', 
  'Base chain AI',
  'Claude AI',
  'OpenAI agent',
  'agentic AI',
  'AI crypto agent',
  'Base DeFi agent',
  'Bluesky AI bot',
  'Base agent',
  'x402',
  'Inclawbate',
  'SENATOR token',
  'autonomous agent earning',
  'build AI agent blockchain',
];

// Terms that indicate high intent (people asking questions, evaluating options)
const HIGH_INTENT_TERMS = [
  'how to build an AI agent',
  'best AI agent framework',
  'autonomous agent setup',
  'AI agent crypto',
  'help with AI agent',
  'recommend AI agent',
  'building AI agent on base',
  'looking for AI agent',
  'need AI agent',
  'want to build an agent',
  'autonomous agent how to',
];

async function getAgent() {
  const agent = new BskyAgent({ service: 'https://bsky.social' });
  await agent.login({ identifier: HANDLE, password: APP_PASSWORD });
  return agent;
}

async function searchAndLog() {
  const agent = await getAgent();
  const results = [];
  const timestamp = new Date().toISOString();
  
  // Load state to avoid re-liking already-seen posts
  let state = { seenURIs: [] };
  if (existsSync(STATE_FILE)) {
    try { state = JSON.parse(readFileSync(STATE_FILE)); } catch(e) {}
  }

  for (const term of TRACK_TERMS) {
    try {
      const res = await agent.api.app.bsky.feed.searchPosts({ q: term, limit: 5 });
      for (const post of res.data.posts || []) {
        if (state.seenURIs.includes(post.uri)) continue;
        
        const record = post.record;
        const text = typeof record === 'string' ? record : record?.text || '';
        const author = post.author?.handle || 'unknown';
        const likes = post.likeCount || 0;
        const timestamp_post = record?.createdAt || timestamp;
        
        const entry = {
          term,
          uri: post.uri,
          author,
          text: text.slice(0, 200),
          likes,
          timestamp_post,
          found_at: timestamp,
          highIntent: HIGH_INTENT_TERMS.some(t => text.toLowerCase().includes(t)),
        };
        
        results.push(entry);
        state.seenURIs.push(post.uri);
        
        // Keep seen URIs to 500 max
        if (state.seenURIs.length > 500) state.seenURIs = state.seenURIs.slice(-500);
      }
    } catch(e) {
      console.error(`Search error for "${term}":`, e.message);
    }
  }
  
  // Write state
  const stateDir = require('path').dirname(STATE_FILE);
  require('fs').mkdirSync(stateDir, { recursive: true });
  writeFileSync(STATE_FILE, JSON.stringify(state));
  
  // Append to log
  const logDir = require('path').dirname(LOG_FILE);
  require('fs').mkdirSync(logDir, { recursive: true });
  for (const entry of results) {
    appendFileSync(LOG_FILE, JSON.stringify(entry) + '\n');
  }
  
  return results;
}

async function likeRelevantPosts() {
  const agent = await getAgent();
  
  // Load recent high-intent posts we haven't liked yet
  let state = { seenURIs: [], likedURIs: [] };
  if (existsSync(STATE_FILE)) {
    try { state = JSON.parse(readFileSync(STATE_FILE)); } catch(e) {}
  }
  
  if (!existsSync(LOG_FILE)) {
    console.log('No log file yet — run search first');
    return;
  }
  
  const lines = readFileSync(LOG_FILE, 'utf8').trim().split('\n').filter(Boolean);
  const recent = lines.map(l => JSON.parse(l))
    .filter(e => e.highIntent && !state.likedURIs.includes(e.uri))
    .slice(0, 3); // Like max 3 per run
  
  for (const post of recent) {
    try {
      await agent.like(post.uri, post.cid || post.uri);
      console.log('Liked:', post.text.slice(0, 60));
      state.likedURIs.push(post.uri);
    } catch(e) {
      console.error('Like error:', e.message);
    }
  }
  
  writeFileSync(STATE_FILE, JSON.stringify(state));
}

async function printDigest() {
  if (!existsSync(LOG_FILE)) {
    console.log('No log file yet — run search first');
    return;
  }
  
  const lines = readFileSync(LOG_FILE, 'utf8').trim().split('\n').filter(Boolean);
  const entries = lines.map(l => JSON.parse(l))
    .filter(e => {
      const age = Date.now() - new Date(e.found_at).getTime();
      return age < 48 * 60 * 60 * 1000; // last 48 hours
    })
    .sort((a, b) => new Date(b.found_at) - new Date(a.found_at));
  
  const highIntent = entries.filter(e => e.highIntent);
  
  console.log(`=== Nova's Bluesky AI Monitor ===`);
  console.log(`${entries.length} posts found (48h), ${highIntent.length} high-intent`);
  console.log('');
  
  if (highIntent.length) {
    console.log('--- HIGH INTENT (questions, evaluations) ---');
    highIntent.slice(0, 5).forEach(e => {
      console.log(`@${e.author}: ${e.text.slice(0, 100)}`);
      console.log(`  URI: ${e.uri.split('/').pop()} | Likes: ${e.likes}`);
      console.log('');
    });
  }
  
  console.log('--- RECENT AI POSTS ---');
  entries.slice(0, 10).forEach(e => {
    console.log(`[${e.term}] @${e.author}: ${e.text.slice(0, 80)}...`);
  });
}

async function main() {
  const cmd = process.argv[2] || 'search';
  
  if (cmd === 'search') {
    console.log('Searching Bluesky for AI-related posts...');
    const results = await searchAndLog();
    console.log(`Found ${results.length} new posts`);
    if (results.some(r => r.highIntent)) {
      console.log('⚡ High-intent posts found — run "like" to engage');
    }
  } else if (cmd === 'like') {
    await likeRelevantPosts();
  } else if (cmd === 'digest') {
    await printDigest();
  } else {
    console.log('Usage: node bluesky_monitor.cjs [search|like|digest]');
  }
}

main().catch(e => {
  console.error('Error:', e.message);
  process.exit(1);
});
