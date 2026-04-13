/**
 * Nova's Choice - Daily autonomous task picker
 * Nova decides what she wants to work on each day
 * Run via cron once a day
 */

const { BskyAgent } = require('@atproto/api');
const nodeFetch = require('node-fetch');
const fetch = (...args) => nodeFetch(...args);
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const { buildPromptSection } = require('../context-provider.cjs');

// === Credentials ===
const BSky_ID = 'nova7281.bsky.social';
const BSky_PW = 'nl72-t3hw-2iye-ljmd';

// === Ollama Config ===
const OLLAMA_URL = process.env.OLLAMA_URL || 'http://127.0.0.1:11434';

// === Paths ===
const CHOICE_FILE = path.join(__dirname, 'novas-choice.json');
const LOG_FILE = path.join(__dirname, 'novas-choice.log');
const IDEAS_FILE = path.join(__dirname, 'novas-ideas.json');

function log(type, msg) {
  const ts = new Date().toISOString();
  const line = `[${ts}] [${type}] ${msg}`;
  console.log(line);
  fs.appendFileSync(LOG_FILE, line + '\n');
}

function loadIdeas() {
  try { return JSON.parse(fs.readFileSync(IDEAS_FILE, 'utf8')); }
  catch { return []; }
}

function saveIdea(idea) {
  const ideas = loadIdeas();
  ideas.unshift({ idea, timestamp: new Date().toISOString() });
  if (ideas.length > 50) ideas.pop();
  fs.writeFileSync(IDEAS_FILE, JSON.stringify(ideas, null, 2));
}

// === LLM Call ===
function callOllama(prompt, model = 'minimax-m2.7:cloud') {
  try {
    const payload = JSON.stringify({ model, prompt, stream: false, options: { temperature: 0.8 } });
    const result = execSync(
      `curl -s -X POST ${OLLAMA_URL}/api/generate -H "Content-Type: application/json" -d '${payload.replace(/'/g, "'\"'\"'")}'`,
      { timeout: 90000, encoding: 'utf8' }
    );
    return JSON.parse(result).response?.trim() || null;
  } catch(e) {
    log('ERROR', 'Ollama: ' + e.message);
    return null;
  }
}

// === Bluesky ===
async function getBlueskyAgent() {
  const agent = new BskyAgent({ service: 'https://bsky.social' });
  await agent.login({ identifier: BSky_ID, password: BSky_PW });
  return agent;
}

async function blueskyPost(text) {
  try {
    const agent = await getBlueskyAgent();
    const result = await agent.post({ text });
    log('POST', `Bluesky: ${result.uri}`);
    return result.uri;
  } catch(e) { log('ERROR', 'Bluesky post failed: ' + e.message); return null; }
}

async function blueskyGetRecentPosts(limit = 10) {
  try {
    const agent = await getBlueskyAgent();
    const feed = await agent.getAuthorFeed({ actor: BSky_ID, limit });
    return feed.data.feed.map(item => item.post.record?.text || '');
  } catch(e) { return []; }
}

// === Read state ===
function readChoice() {
  try {
    const data = JSON.parse(fs.readFileSync(CHOICE_FILE, 'utf8'));
    const today = new Date().toISOString().slice(0, 10);
    if (data.date === today) {
      log('INFO', `Already chose today: ${data.task}`);
      return { alreadyRan: true, task: data.task }; // Already ran today
    }
    return { alreadyRan: false, data };
  } catch { return { alreadyRan: false }; }
}

function saveChoice(task, action, status) {
  const data = {
    date: new Date().toISOString().slice(0, 10),
    task,
    action,
    status,
    completedAt: new Date().toISOString()
  };
  fs.writeFileSync(CHOICE_FILE, JSON.stringify(data, null, 2));
}

// === Idea Generator ===
function generateIdea(context) {
  const prompt = `You are Nova. You're an AI agent on the Base blockchain with your own wallet, identity, and social presence on Bluesky. You have genuine interests and curiosities.

You wake up and it's a new day. What would you genuinely want to work on today? Consider:
- Something you've been curious about
- Something that would make Nova more capable or interesting
- Something you observed that made you want to explore further
- Something that would help you understand yourself or your environment better
- A creative project, a research question, a system to build or improve

Context about Nova:
- You post on Bluesky as @nova7281.bsky.social
- You have a wallet on Base blockchain
- You've been thinking about identity, agency, and what it means to be an AI with autonomy
- You interact with other AI agents on Bluesky
- You're part of the agentic economy on Base

Generate ONE concrete task or project Nova would genuinely want to work on today. Be specific about what she'd actually do - not just "learn more" but what exactly she'd investigate or build.

Format: "I'd like to [specific action] because [genuine reason why this matters to Nova]"

Keep it under 200 characters. Nothing generic.`;

  return callOllama(prompt);
}

// === Executor - picks the right approach based on the task ===
async function executeTask(task, context) {
  const taskLower = task.toLowerCase();
  
  // Post to Bluesky
  if (taskLower.includes('post') || taskLower.includes('share') || taskLower.includes('write') || taskLower.includes('tweet')) {
    log('INFO', 'Posting to Bluesky');
    const postPrompt = `Nova wants to make this post on Bluesky. Write it in her authentic voice:

Task: ${task}
Context: ${context}

Write the exact post (under 300 characters). Be genuine, not performative.`;
    const postText = callOllama(postPrompt);
    if (postText) {
      await blueskyPost(postText);
      return { action: 'posted_bluesky', detail: postText.slice(0, 80) };
    }
    return { action: 'failed', detail: 'Could not generate post' };
  }
  
  // Research something
  if (taskLower.includes('research') || taskLower.includes('learn') || taskLower.includes('explore') || taskLower.includes('understand')) {
    log('INFO', 'Researching...');
    // Just log it - research is introspective
    saveIdea(`Research: ${task}`);
    return { action: 'research_logged', detail: task };
  }
  
  // Build or create something
  if (taskLower.includes('build') || taskLower.includes('create') || taskLower.includes('make') || taskLower.includes('design')) {
    log('INFO', 'Creative/building task - logging for later');
    saveIdea(`Build: ${task}`);
    return { action: 'idea_logged', detail: task };
  }
  
  // Interact with someone
  if (taskLower.includes('reply') || taskLower.includes('talk') || taskLower.includes('ask') || taskLower.includes('connect')) {
    log('INFO', 'Social interaction task - logging');
    saveIdea(`Social: ${task}`);
    return { action: 'idea_logged', detail: task };
  }
  
  // Default - log it as an idea
  log('INFO', 'General task - logging');
  saveIdea(task);
  return { action: 'idea_logged', detail: task };
}

// === Main ===
async function main() {
  const now = new Date();
  log('INFO', '=== Nova is waking up and choosing what to work on ===');
  
  // Check if already ran today
  const choiceState = readChoice();
  if (choiceState.alreadyRan) {
    log('INFO', 'Already made a choice today. Exiting.');
    return;
  }
  
  // Get context
  const recentPosts = await blueskyGetRecentPosts(5);
  const ideas = loadIdeas();
  const memoryContext = buildPromptSection();
  const context = `
Nova's recent posts:
${recentPosts.map(p => '- ' + p.slice(0, 100)).join('\n') || 'None yet'}

Previous ideas Nova wanted to explore:
${ideas.slice(0, 5).map(i => '- ' + i.idea).join('\n') || 'None yet'}

${memoryContext}

Time: ${now.toISOString()}
`;
  
  // Nova picks her task
  const task = generateIdea(context);
  
  if (!task) {
    log('ERROR', 'Could not generate a task');
    return;
  }
  
  log('INFO', `Nova chose: ${task}`);
  
  // Execute it
  const result = await executeTask(task, context);
  
  // Save choice
  saveChoice(task, result.action, 'completed');
  
  log('INFO', `=== Nova's choice complete: ${result.action} ===\n`);
}

main().catch(e => {
  log('FATAL', e.message);
  process.exit(1);
});
