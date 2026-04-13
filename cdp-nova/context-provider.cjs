#!/usr/bin/env node
/**
 * Nova's Idea Context Provider
 * Bundles context for novas-choice.cjs — recent ideas, active tasks,
 * today's choice, queue state — so the LLM generates genuinely new ideas.
 *
 * Usage: node context-provider.cjs
 */

const fs = require('fs');
const path = require('path');

const IDEAS_FILE   = path.join(__dirname, 'social-manager', 'novas-ideas.json');
const CHOICE_FILE = path.join(__dirname, 'social-manager', 'novas-choice.json');
const QUEUE_FILE  = path.join(__dirname, 'social-manager', 'idea_queue.jsonl');
const STATE_FILE  = path.join(__dirname, 'social-manager', 'social-state.json');
const MEMORY_DIR = path.join(__dirname, '..', 'memory');
const MEMORY_FILE = path.join(MEMORY_DIR, '2026-04-09.md');

function loadJSON(file, fallback = null) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch { return fallback; }
}

function getRecentIdeas(days = 7) {
  const ideas = loadJSON(IDEAS_FILE, []);
  const cutoff = Date.now() - days * 24 * 3600000;
  return ideas.filter(i => new Date(i.timestamp).getTime() > cutoff);
}

function getTodaysChoice() {
  return loadJSON(CHOICE_FILE, null);
}

function getQueueState() {
  try {
    const lines = fs.readFileSync(QUEUE_FILE, 'utf8').split('\n').filter(Boolean);
    const queued = lines.map(l => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean);
    return {
      queued: queued.length,
      items: queued.map(q => ({ id: q.id, idea: q.idea, status: q.status }))
    };
  } catch {
    return { queued: 0, items: [] };
  }
}

function getBlueskyRecentPosts() {
  const state = loadJSON(STATE_FILE, {});
  return state.lastPosts || [];
}

function getTodayMemory() {
  try {
    const mem = fs.readFileSync(MEMORY_FILE, 'utf8');
    // Extract key items from today's memory
    const lines = mem.split('\n').filter(l => l.trim() && l.startsWith('##'));
    return lines.join('\n');
  } catch {
    return 'No memory file found';
  }
}

function getActiveTasks() {
  // Check what's currently running or recently spawned
  const running = [];
  // supervisor + listener are infrastructure, not tasks
  // Check coordinator state
  const choice = getTodaysChoice();
  if (choice?.status === 'processing' || choice?.status === 'queued') {
    running.push({ what: choice.task, status: choice.status });
  }
  return running;
}

function buildContext() {
  const recentIdeas = getRecentIdeas(7);
  const todaysChoice = getTodaysChoice();
  const queue = getQueueState();
  const memory = getTodayMemory();

  const recentIdeaList = recentIdeas.length > 0
    ? recentIdeas.map(i => `- ${i.idea} (${new Date(i.timestamp).toISOString().slice(0,10)})`).join('\n')
    : 'None yet';

  const todaysIdeaText = todaysChoice
    ? `Today (${todaysChoice.date}): "${todaysChoice.task}" — status: ${todaysChoice.status}`
    : 'No choice made today yet';

  const queueText = queue.queued > 0
    ? `${queue.queued} queued item(s): ${queue.items.map(q => `"${q.idea}"`).join(', ')}`
    : 'Queue is empty';

  const activeText = getActiveTasks().length > 0
    ? getActiveTasks().map(t => `- ${t.what} (${t.status})`).join('\n')
    : 'None';

  const memoryText = memory.length > 100 ? memory : 'No significant history today';

  return {
    recentIdeas: recentIdeaList,
    todaysIdea: todaysIdeaText,
    queueState: queueText,
    activeTasks: activeText || 'None',
    todayMemory: memoryText,
    generatedAt: new Date().toISOString()
  };
}

// Returns a string suitable for injecting into the LLM prompt
function buildPromptSection() {
  const ctx = buildContext();
  return `
== Nova's Recent Context (avoid repeating these) ==
Recent ideas from the past week:
${ctx.recentIdeas}

${ctx.todaysIdea}
${ctx.queueState !== 'Queue is empty' ? `Current execution queue: ${ctx.queueState}` : ''}
Active/in-progress tasks: ${ctx.activeTasks}

Today's memory:
${ctx.todayMemory}

== Instruction ==
Generate a NEW idea that is genuinely different from everything above.
Do NOT repeat or closely echo anything already picked or queued.
Pick something that would genuinely interest Nova given where she is right now.
`.trim();
}

// Simple version that returns the raw context object
function getContext() {
  return buildContext();
}

module.exports = { buildContext, buildPromptSection, getContext };

// CLI test
if (require.main === module) {
  const ctx = getContext();
  console.log('=== Context ===');
  console.log('Recent ideas:\n' + ctx.recentIdeas);
  console.log("\nToday's idea:", ctx.todaysIdea);
  console.log('Queue:', ctx.queueState);
  console.log('Active:', ctx.activeTasks);
  console.log("\n=== Prompt Section ===");
  console.log(buildPromptSection());
}
