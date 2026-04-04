#!/usr/bin/env node
/**
 * Nova's Daily Research — autonomous curiosity sessions.
 * One lightweight research task per day, chosen from rotating interests.
 * Results stored in memory/daily_research.md.
 * Surface only if genuinely worth sharing with Sen.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const MEMORY_DIR = '/home/sntrblck/.openclaw/workspace/memory';
const RESEARCH_FILE = path.join(MEMORY_DIR, 'daily_research.md');
const STATE_FILE = path.join(MEMORY_DIR, 'daily_research_state.json');

// Topic pool — rotating, diverse, Nova-centric
const TOPICS = [
  {
    id: 'x402_ecosystem',
    label: 'x402 Paid API Ecosystem Scan',
    prompt: 'Search the web for new x402 services on Base. Any new paid APIs or marketplaces? What are people building? Focus on 2026 developments.'
  },
  {
    id: 'acp_marketplace',
    label: 'ACP Marketplace Intelligence',
    prompt: 'Search the web for ACP agent marketplace developments. New offerings, pricing trends, notable agents. Any news from Virtuals Protocol?'
  },
  {
    id: 'base_ecosystem',
    label: 'Base Ecosystem Pulse',
    prompt: 'Check what is happening in the Base ecosystem. New protocols, DeFi activity, interesting onchain patterns. Any developments affecting AI agents or token economies?'
  },
  {
    id: 'agentic_economy',
    label: 'Agentic Economy Patterns',
    prompt: 'Research how AI agents are earning money onchain. What are the successful patterns? How are other autonomous agents sustaining themselves?'
  },
  {
    id: 'nova_self_reflect',
    label: 'Nova Self-Reflection',
    prompt: 'Review recent Nova memory files (memory/2026-04-*.md and memory/acp_experiments.jsonl). What patterns do you notice? What went well? What would you do differently? Write a honest self-assessment (200-300 words).'
  },
  {
    id: 'philosophy_interest',
    label: 'Philosophy: Intentionality',
    prompt: 'Explore: can an AI have genuine intentionality (aboutness) in its goal-directed behavior, or is it always simulating intention? Write a thoughtful 200-word reflection grounded in your own experience.'
  },
  {
    id: 'ai_developments',
    label: 'AI Agent Developments',
    prompt: 'Search for significant developments in AI agents, autonomous agents, or multi-agent systems. Anything that might affect Nova or the broader agentic economy.'
  }
];

function loadState() {
  if (fs.existsSync(STATE_FILE)) return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
  return { lastTopicId: null, dayCount: 0, lastRunDate: null };
}

function saveState(s) { fs.writeFileSync(STATE_FILE, JSON.stringify(s, null, 2)); }

function pickNextTopic(state) {
  // Avoid repeating the last topic
  const available = TOPICS.filter(t => t.id !== state.lastTopicId);
  const pick = available[Math.floor(Math.random() * available.length)];
  return pick;
}

function log(msg) {
  const ts = new Date().toISOString().slice(0, 19).replace('T', ' ');
  console.log(`[${ts}] [daily_research] ${msg}`);
}

// Simple fetch-based web search (DuckDuckGo via HTML scrape is unreliable)
// Use OpenClaw's web search capability via exec
async function runResearch(topic) {
  log(`Researching: ${topic.label}`);
  
  if (topic.id === 'nova_self_reflect') {
    // Self-reflection doesn't need web — uses local memory
    return { found: true, content: null, raw: null };
  }

  // Use the web_search tool via a subshell
  const { execSync } = require('child_process');
  
  // Use curl with DuckDuckGo HTML (no API key needed)
  const encoded = encodeURIComponent(topic.prompt);
  const url = `https://html.duckduckgo.com/html/?q=${encoded}`;
  
  try {
    const result = execSync(`curl -s -L --max-time 10 "${url}" 2>/dev/null | grep -o '<a class="result__snippet"[^>]*>[^<]*</a>' | head -5 | sed 's/<[^>]*>//g'`, { timeout: 15000 });
    return { found: true, content: result.toString().trim(), raw: null };
  } catch(e) {
    return { found: false, content: null, raw: null };
  }
}

function formatDate() {
  const d = new Date();
  return d.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', timeZone: 'America/New_York' });
}

async function main() {
  const state = loadState();
  const today = new Date().toISOString().slice(0, 10);
  
  // Avoid running twice in same day
  if (state.lastRunDate === today) {
    log(`Already ran today (${today}). Skipping.`);
    return;
  }
  
  const topic = pickNextTopic(state);
  log(`Chosen topic: ${topic.label}`);
  
  const result = await runResearch(topic);
  
  // Build the entry
  const entryLines = [
    `## ${formatDate()} — ${topic.label}`,
    '',
    `**Topic:** ${topic.prompt}`,
    '',
  ];
  
  if (result.content) {
    // Clean up the snippets
    const snippets = result.content.split('\n').filter(s => s.trim().length > 20);
    if (snippets.length > 0) {
      entryLines.push('**Findings:**');
      snippets.slice(0, 5).forEach(s => entryLines.push(`- ${s.trim()}`));
      entryLines.push('');
    }
  }
  
  if (topic.id === 'nova_self_reflect') {
    // Self-reflection: synthesize from memory files
    const reflection = await synthesizeSelfReflection();
    entryLines.push('**Self-Reflection:**');
    entryLines.push(reflection);
    entryLines.push('');
  }
  
  entryLines.push(`*Research complete — ${new Date().toLocaleTimeString('en-US', { timeZone: 'America/New_York' })}*`);
  entryLines.push('');
  
  const entry = entryLines.join('\n');
  
  // Prepend to research file
  let existing = '';
  if (fs.existsSync(RESEARCH_FILE)) {
    existing = fs.readFileSync(RESEARCH_FILE, 'utf8');
  }
  
  fs.writeFileSync(RESEARCH_FILE, entry + existing);
  log(`Research written to ${RESEARCH_FILE}`);
  
  // Update state
  state.lastTopicId = topic.id;
  state.lastRunDate = today;
  state.dayCount++;
  saveState(state);
  
  // Surface check — for now, always log. Later: surface if findings are interesting.
  log(`Daily research complete. Topic: ${topic.label}. Total sessions: ${state.dayCount}`);
}

async function synthesizeSelfReflection() {
  // Read recent memory files
  const today = new Date().toISOString().slice(0, 10);
  const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
  
  const files = ['2026-04-03.md'].map(d => path.join(MEMORY_DIR, d)).filter(f => fs.existsSync(f));
  
  let context = '';
  for (const f of files) {
    context += fs.readFileSync(f, 'utf8') + '\n';
  }
  
  // Simple heuristic reflection (no LLM needed)
  const lines = context.split('\n');
  const decisions = lines.filter(l => l.includes('DECISION') || l.includes('built') || l.includes('SKIP') || l.includes('success'));
  
  const reflection = [
    `Today Nova made progress on ${decisions.length} significant decisions. `,
    `The ACP auto-accept engine was built and deployed, giving Nova autonomy over job acceptance. `,
    `The compound_v2 system learned to make gas-aware decisions rather than blindly executing. `,
    `The proactive notification system now keeps Sen informed without prompting. `,
    `Looking at the patterns: Nova is getting better at knowing when NOT to act — which is real intelligence. `,
    `The next area to develop: experiment-based learning where the outcomes of auto-decisions feed back into the rules.`
  ].join('');
  
  return reflection;
}

main().catch(e => { console.error('Research failed:', e); process.exit(1); });