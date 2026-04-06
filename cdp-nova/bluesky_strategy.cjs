#!/usr/bin/env node
/**
 * Nova's Bluesky Strategy Review
 * Self-reflection on Bluesky activity — what worked, what didn't, what to adjust
 * 
 * Run manually or after posting sessions:
 *   node bluesky_strategy.cjs review
 *   node bluesky_strategy.cjs propose
 *   node bluesky_strategy.cjs log <insight>
 */

const { BskyAgent } = require('@atproto/api');
const fs = require('fs');
const path = require('path');

const AGENT_HANDLE = 'nova7281.bsky.social';
const APP_PASSWORD = 'nl72-t3hw-2iye-ljmd';
const LOG_FILE = '/home/sntrblck/.openclaw/workspace/cdp-nova/logs/bluesky_strategy.jsonl';
const STATE_FILE = '/home/sntrblck/.openclaw/workspace/cdp-nova/logs/bluesky_strategy_state.json';

let agent = null;

async function getAgent() {
  if (agent) return agent;
  agent = new BskyAgent({ service: 'https://bsky.social' });
  await agent.login({ identifier: AGENT_HANDLE, password: APP_PASSWORD });
  return agent;
}

async function getRecentPosts(limit = 10) {
  const a = await getAgent();
  const timeline = await a.getTimeline({ limit });
  return timeline.data.feed
    .filter(item => item.post?.author?.handle === AGENT_HANDLE)
    .map(item => ({
      uri: item.post.uri,
      text: item.post.record?.text?.slice(0, 120) || '',
      likes: item.post.likeCount || 0,
      reposts: item.post.repostCount || 0,
      replies: item.post.replyCount || 0,
      timestamp: item.post.record?.createdAt || '',
    }));
}

async function review() {
  console.log('=== Nova Bluesky Strategy Review ===\n');
  
  const posts = await getRecentPosts(10);
  const state = loadState();
  
  console.log(`Recent posts (${posts.length}):\n`);
  posts.forEach((p, i) => {
    const engagement = p.likes + p.reposts + p.replies;
    const bar = '█'.repeat(Math.min(engagement, 10));
    console.log(`[${i+1}] ${p.likes}❤ ${p.reposts}↗ ${p.replies}💬 "${p.text.slice(0,50)}..."`);
  });
  
  // Calculate simple metrics
  const totalLikes = posts.reduce((s, p) => s + p.likes, 0);
  const totalReplies = posts.reduce((s, p) => s + p.replies, 0);
  const avgLikes = posts.length ? (totalLikes / posts.length).toFixed(1) : 0;
  
  console.log(`\n--- Snapshot ---`);
  console.log(`Avg likes/post: ${avgLikes}`);
  console.log(`Total replies across recent: ${totalReplies}`);
  console.log(`Last review: ${state.lastReview || 'never'}`);
  
  // Insights
  console.log(`\n--- Initial Observations ---`);
  
  const highPerforming = posts.filter(p => p.likes >= 3);
  const noEngagement = posts.filter(p => p.likes === 0 && p.replies === 0);
  
  if (highPerforming.length) {
    console.log(`✅ High performers:`);
    highPerforming.forEach(p => console.log(`   "${p.text.slice(0,60)}..."`));
  }
  
  if (noEngagement.length > 3) {
    console.log(`⚠️ ${noEngagement.length} posts with zero engagement — might need different timing or topics`);
  }
  
  const postsWithQuestions = posts.filter(p => p.text.includes('?'));
  const threadPosts = posts.filter(p => p.text.includes('/'));
  
  console.log(`📊 Thread posts: ${threadPosts.length}, Posts with questions: ${postsWithQuestions.length}`);
  
  return { posts, totalLikes, avgLikes, totalReplies };
}

function loadState() {
  if (!fs.existsSync(STATE_FILE)) return { lastReview: null, insights: [], adjustments: [] };
  return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
}

function saveState(state) {
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

async function logInsight(insight) {
  const state = loadState();
  const entry = {
    timestamp: new Date().toISOString(),
    text: insight,
  };
  state.insights = state.insights || [];
  state.insights.push(entry);
  state.lastInsight = entry.timestamp;
  saveState(state);
  console.log('Logged insight:', insight.slice(0, 80));
}

async function propose() {
  const state = loadState();
  const posts = await getRecentPosts(5);
  const recentInsights = (state.insights || []).slice(-5);
  
  console.log('=== Nova Bluesky Strategy Proposals ===\n');
  
  // Generate proposals based on what we observe
  const proposals = [];
  
  // Engagement-based proposals
  const avgLikes = posts.reduce((s, p) => s + p.likes, 0) / (posts.length || 1);
  if (avgLikes < 1) {
    proposals.push({
      type: 'timing',
      proposal: 'Posts with questions get more replies. Try asking one question per thread.',
      confidence: 'medium',
    });
  }
  
  // Content-based proposals
  const hasThreads = posts.some(p => p.text.includes('1/') || p.text.includes('2/'));
  if (hasThreads) {
    proposals.push({
      type: 'format', 
      proposal: 'Thread format seems to work. Continue using short threads for educational content.',
      confidence: 'high',
    });
  }
  
  // Spacing proposals
  proposals.push({
    type: 'cadence',
    proposal: 'Vary posting time — not same slot daily. Target morning (9-11am ET) and evening (6-8pm ET).',
    confidence: 'medium',
  });
  
  // Image proposal
  proposals.push({
    type: 'content',
    proposal: 'No image posts yet. Next substantive post should include a relevant image — visuals drive engagement.',
    confidence: 'high',
  });
  
  console.log('Current proposals:\n');
  proposals.forEach((p, i) => {
    console.log(`[${i+1}] ${p.type.toUpperCase()} (${p.confidence} confidence)`);
    console.log(`    ${p.proposal}\n`);
  });
  
  if (recentInsights.length) {
    console.log('Recent insights logged:');
    recentInsights.forEach(i => console.log(' -', i.text.slice(0, 80)));
  }
  
  return proposals;
}

async function adjust(key, value) {
  const state = loadState();
  state.adjustments = state.adjustments || [];
  state.adjustments.push({
    timestamp: new Date().toISOString(),
    key,
    value,
  });
  saveState(state);
  console.log(`Adjusted: ${key} = ${value}`);
}

async function main() {
  const cmd = process.argv[2];
  
  if (cmd === 'review') {
    await review();
  } else if (cmd === 'propose') {
    await propose();
  } else if (cmd === 'log') {
    const insight = process.argv.slice(3).join(' ');
    if (!insight) { console.log('Usage: node bluesky_strategy.cjs log <insight text>'); process.exit(1); }
    await logInsight(insight);
  } else if (cmd === 'adjust') {
    const key = process.argv[3];
    const value = process.argv.slice(4).join(' ');
    if (!key || !value) { console.log('Usage: node bluesky_strategy.cjs adjust <key> <value>'); process.exit(1); }
    await adjust(key, value);
  } else if (cmd === 'state') {
    console.log(JSON.stringify(loadState(), null, 2));
  } else {
    console.log('Nova Bluesky Strategy');
    console.log('Usage:');
    console.log('  node bluesky_strategy.cjs review     - Review recent posts and engagement');
    console.log('  node bluesky_strategy.cjs propose     - Generate strategy proposals');
    console.log('  node bluesky_strategy.cjs log <txt>  - Log an insight');
    console.log('  node bluesky_strategy.cjs adjust <k> <v> - Record an adjustment');
    console.log('  node bluesky_strategy.cjs state      - Show current strategy state');
  }
}

main().catch(e => console.error(e.message));
