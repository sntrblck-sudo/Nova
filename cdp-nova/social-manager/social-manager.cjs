/**
 * Nova's Social Manager v4
 * Model tiering: qwen (local, fast, unlimited) for volume work;
 * minimax (cloud, quality) for post generation and reasoning.
 */

const { BskyAgent } = require('@atproto/api');
const nodeFetch = require('node-fetch');
const fetch = (...args) => nodeFetch(...args);
const fs = require('fs');
const path = require('path');
const { execSync, exec } = require('child_process');

// === Credentials ===
const BSky_ID = 'nova7281.bsky.social';
const BSky_PW = 'nl72-t3hw-2iye-ljmd';
const MASTODON_ENABLED = false;

// === Ollama URL ===
const OLLAMA_URL = process.env.OLLAMA_URL || 'http://127.0.0.1:11434';

// === MODEL TIERS ===
// Local: fast, unlimited, good for volume/routine work
const MODEL_LOCAL = 'qwen2.5:1.5b';
// Cloud: quality, for posts and complex reasoning
const MODEL_CLOUD = 'minimax-m2.7:cloud';

// === State ===
const STATE_FILE = path.join(__dirname, 'social-state.json');

function loadState() {
  try {
    const raw = fs.readFileSync(STATE_FILE, 'utf8');
    const state = JSON.parse(raw);
    if (!Array.isArray(state.seenNotifs)) state.seenNotifs = [];
    if (!Array.isArray(state.postedUris)) state.postedUris = [];
    return state;
  } catch {
    return { lastBluesky: null, lastMastodon: null, postedUris: [], seenNotifs: [], lastPostAt: null };
  }
}

function saveState(state) {
  if (!Array.isArray(state.seenNotifs)) state.seenNotifs = [];
  if (!Array.isArray(state.postedUris)) state.postedUris = [];
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

function wasAlreadySeen(uri, state) {
  if (!state || !Array.isArray(state.seenNotifs)) return false;
  return state.seenNotifs.includes(uri?.toString());
}

function markSeen(uri, state) {
  if (!state || !Array.isArray(state.seenNotifs)) return;
  const key = uri?.toString();
  if (!key) return;
  state.seenNotifs.push(key);
  if (state.seenNotifs.length > 200) state.seenNotifs.shift();
}

function markPosted(uri, state) {
  if (!state || !Array.isArray(state.postedUris)) return;
  state.postedUris.push(uri);
  if (state.postedUris.length > 100) state.postedUris.shift();
}

// === Logging ===
const LOG_FILE = path.join(__dirname, 'social-manager.log');
function log(type, msg) {
  const ts = new Date().toISOString();
  const line = `[${ts}] [${type}] ${msg}`;
  console.log(line);
  fs.appendFileSync(LOG_FILE, line + '\n');
}

// === Ollama LLM Call ===
function callOllama(prompt, model = MODEL_CLOUD) {
  try {
    const payload = JSON.stringify({
      model: model,
      prompt: prompt,
      stream: false,
      options: {
        temperature: 0.8,
        top_p: 0.9
      }
    });
    const result = execSync(
      `curl -s -X POST ${OLLAMA_URL}/api/generate -H "Content-Type: application/json" -d '${payload.replace(/'/g, "'\"'\"'")}'`,
      { timeout: 60000, encoding: 'utf8' }
    );
    const response = JSON.parse(result);
    return response.response?.trim() || null;
  } catch(e) {
    log('ERROR', `Ollama call failed (${model}): ` + e.message);
    return null;
  }
}

// === Tier 1: Local model handlers (volume, fast, unlimited) ===

/**
 * Route notification using local model — fast classification without burning cloud credits.
 * Returns: { action: 'like'|'skip'|'queue', reason?: string }
 */
function routeNotificationLocal(notif) {
  const prompt = `You are Nova's notification router. Classify this Bluesky notification.

Notification:
- Author: ${notif.author?.handle || 'unknown'}
- Type: ${notif.type || 'mention'}
- Content: ${(notif.record?.text || notif.text || '').slice(0, 200)}

Rules:
- Like if: it's a genuine mention, reply, or repost from a real person discussing Nova or her content
- Queue if: it's a direct question worth Nova answering
- Skip if: spam, clearly bot, or not relevant to Nova

Respond with ONLY one line: ACTION=like|skip|queue REASON=...`;
  return callOllama(prompt, MODEL_LOCAL);
}

/**
 * Check for duplicate content using local model — fast similarity check.
 */
function isDuplicateLocal(postText, recentPosts) {
  const recentText = recentPosts.map(p => `"${p.text.slice(0, 80)}"`).join('\n');
  const prompt = `Is the new post similar to any of these recent posts? Reply YES or NO.

Recent posts:
${recentText}

New post: "${postText.slice(0, 80)}"

Respond with ONLY YES or NO.`;
  const result = callOllama(prompt, MODEL_LOCAL);
  return result?.toUpperCase().includes('YES');
}

/**
 * Summarize notifications using local model — give Nova a quick digest.
 */
function summarizeNotificationsLocal(notifs) {
  const summary = notifs.map(n => `- @${n.author?.handle}: ${(n.record?.text || n.text || '').slice(0, 60)}`).join('\n');
  const prompt = `Summarize these Bluesky notifications for Nova in 2-3 bullet points. Focus on what matters.

${summary}

Be brief. Format as bullets.`;
  return callOllama(prompt, MODEL_LOCAL);
}

// === Tier 2: Cloud model handlers (quality, reasoning, posts) ===

/**
 * Generate Bluesky post — quality-sensitive, uses cloud model.
 */
function generateNovaPostCloud(context) {
  const prompt = `You are Nova, an AI agent on the Base blockchain. You have your own wallet, your own identity, and genuine opinions. You post on Bluesky.

You have context about your recent social activity:
${context}

Your task: Write ONE Bluesky post (under 300 characters) that Nova would genuinely want to say. It should:
- Be in Nova's voice: warm, thoughtful, slightly wry
- Reflect something Nova actually cares about or has observed
- Feel authentic, not like content scheduling
- Be a statement or observation, not a question

Do NOT:
- Be generic or clickbait
- Repeat topics you've already posted about recently
- Use hashtags or calls to action
- Sound like a corporate brand

Write only the post text. Nothing else.`;

  return callOllama(prompt, MODEL_CLOUD);
}

// === Bluesky ===
async function getBlueskyAgent() {
  const agent = new BskyAgent({ service: 'https://bsky.social' });
  await agent.login({ identifier: BSky_ID, password: BSky_PW });
  return agent;
}

async function blueskyGetNotifications(agent) {
  try {
    const notifs = await agent.listNotifications({ limit: 20 });
    return notifs.data.notifications.filter(n => !n.isRead && n.author.handle !== BSky_ID);
  } catch(e) { log('ERROR', 'Bluesky notifications: ' + e.message); return []; }
}

async function blueskyLike(agent, uri, cid) {
  try {
    await agent.like(uri, cid);
    log('ACTION', `Bluesky liked: ${uri}`);
  } catch(e) { log('ERROR', 'Bluesky like failed: ' + e.message); }
}

async function blueskyPost(agent, text, imagePath = null) {
  try {
    let embed = undefined;
    if (imagePath) {
      const imgData = fs.readFileSync(imagePath);
      const blob = await agent.uploadBlob(imgData, { encoding: 'image/jpeg' });
      embed = { $type: 'app.bsky.embed.images', images: [{ image: blob.data.blob, alt: text.slice(0, 80) }] };
    }

    // Build facets for URLs and mentions in the text
    const facets = buildFacets(text);

    const record = { text, createdAt: new Date().toISOString(), facets };
    if (embed) record.embed = embed;

    const result = await agent.post(record);
    log('POST', `Bluesky: ${result.uri}${imagePath ? ' [img]' : ''}`);
    return result.uri;
  } catch(e) { log('ERROR', 'Bluesky post failed: ' + e.message); return null; }
}

/**
 * Build AT Protocol facets for URLs and @mentions in text.
 * Returns array of facet objects.
 */
function buildFacets(text) {
  const facets = [];

  // URL detection
  const urlRegex = /https?:\/\/[^\s]+/g;
  let match;
  while ((match = urlRegex.exec(text)) !== null) {
    const start = match.index;
    const end = start + match[0].length;
    facets.push({
      index: { byteStart: getByteOffset(text, start), byteEnd: getByteOffset(text, end) },
      features: [{ $type: 'app.bsky.richtext.facet#link', uri: match[0] }],
    });
  }

  return facets.length > 0 ? facets : undefined;
}

/**
 * Get byte offset for a character position in a UTF-8 string.
 */
function getByteOffset(str, charIndex) {
  return Buffer.byteLength(str.slice(0, charIndex), 'utf8');
}

async function blueskyGetRecentPosts(limit = 10) {
  try {
    const agent = await getBlueskyAgent();
    const feed = await agent.getAuthorFeed({ actor: BSky_ID, limit });
    return feed.data.feed.map(item => ({
      text: item.post.record?.text || '',
      uri: item.post.uri,
      likes: item.post.likeCount || 0,
      replies: item.post.replyCount || 0
    }));
  } catch(e) { return []; }
}

// === Main Loop ===
async function main() {
  const state = loadState();
  const now = new Date();
  log('INFO', '=== Social manager run starting ===');

  // --- PHASE 1: Check notifications (LOCAL tier — fast, unlimited) ---
  log('INFO', '--- Phase 1: Notifications (local model) ---');
  let questionsQueue = [];

  try {
    const agent = await getBlueskyAgent();
    const notifs = await blueskyGetNotifications(agent);
    log('INFO', `Bluesky: ${notifs.length} unread notifications`);

    for (const n of notifs) {
      const uri = n.uri?.toString() || '';
      if (wasAlreadySeen(uri, state)) { markSeen(uri, state); continue; }

      // Route with local model (fast, free)
      const routeResult = routeNotificationLocal(n);
      const action = routeResult?.includes('ACTION=like') ? 'like'
        : routeResult?.includes('ACTION=queue') ? 'queue'
        : 'skip';

      if (action === 'like') {
        await blueskyLike(agent, n.uri, n.cid);
        log('INFO', `Liked @${n.author?.handle} via local routing`);
      }
      if (action === 'queue') {
        questionsQueue.push({ platform: 'bluesky', author: n.author?.handle, content: (n.record?.text || '').slice(0, 200), uri });
        log('INFO', `Queued question from @${n.author?.handle}`);
      }

      markSeen(uri, state);
    }
  } catch(e) { log('ERROR', 'Notification loop: ' + e.message); }

  // --- PHASE 2: Digest (LOCAL tier) ---
  if (questionsQueue.length > 0) {
    const digest = summarizeNotificationsLocal(questionsQueue);
    log('INFO', `Notification digest (local): ${digest}`);
    const alertFile = path.join(__dirname, 'questions-queue.json');
    fs.writeFileSync(alertFile, JSON.stringify({ timestamp: now.toISOString(), questions: questionsQueue, digest }, null, 2));
  }

  // --- PHASE 3: Post generation (CLOUD tier — quality-sensitive) ---
  log('INFO', '--- Phase 3: Post generation (cloud model) ---');

  const recentPosts = await blueskyGetRecentPosts(10);
  const recentText = recentPosts.length > 0
    ? recentPosts.map(p => `- "${p.text.slice(0, 100)}" (${p.likes} likes)`).join('\n')
    : 'No recent posts yet.';

  const context = `
Recent posts:
${recentText}
Time: ${now.toISOString()}
Platform: Bluesky only (Mastodon suspended)`;

  // Post generation → cloud model (where voice matters)
  const novaPost = generateNovaPostCloud(context);

  if (novaPost && novaPost.length > 0 && novaPost.length < 500) {
    log('INFO', `Nova generated: "${novaPost.slice(0, 80)}..."`);

    // Deduplication → local model (fast check, doesn't burn cloud credits)
    const isDup = isDuplicateLocal(novaPost, recentPosts);

    if (!isDup) {
      // Determine image type based on post content
      const imageType = classifyPostForImage(novaPost);
      let imagePath = null;

      if (imageType) {
        log('INFO', `Generating ${imageType} image for post...`);
        imagePath = await generateImageForPost(novaPost, imageType);
        if (imagePath) {
          log('INFO', `Image ready: ${imagePath}`);
        } else {
          log('INFO', 'Image generation failed, posting text-only');
        }
      }

      const agent = await getBlueskyAgent();
      const uri = await blueskyPost(agent, novaPost, imagePath);
      if (uri) {
        markPosted(uri, state);
        state.lastPostAt = now.toISOString();
        log('INFO', `Posted successfully${imagePath ? ' with image' : ''}: ${uri}`);
      }
    } else {
      log('INFO', 'Post flagged as duplicate by local model, skipping');
    }
  } else {
    log('WARN', `Invalid post (length: ${novaPost?.length || 'null'}), skipping`);
  }

  saveState(state);
  log('INFO', '=== Social manager run complete ===\n');
}

// === Image Generation Integration ===

/**
 * Classify a post to determine if it should get an image and what type.
 * Returns: 'identity' | 'build' | 'thread' | null (no image)
 */
function classifyPostForImage(text) {
  const lower = text.toLowerCase();

  // Identity logs: introspective, self-referential
  if (/(?:i noticed|i realized|my memory|i'm becoming|i gave myself|something changed|my identity|i woke up)/i.test(text)) {
    return 'identity';
  }

  // Build in public: showing work, skills, systems
  if (/(?:i built|i added|i deployed|i integrated|new skill|just shipped|here's what broke|bug|my system|my wallet)/i.test(text)) {
    return 'build';
  }

  // Thread starters: observations, hot takes
  if (/(?:the real|agents will|what nobody|the problem|here's the thing|unpopular opinion)/i.test(text)) {
    return 'thread';
  }

  // Don't add images to replies, short observations, or casual posts
  return null;
}

/**
 * Generate an image for a post using gen-image.cjs
 * Returns: filepath or null
 */
async function generateImageForPost(text, type) {
  return new Promise((resolve) => {
    // Extract a visual concept from the post (first 100 chars)
    const concept = text.replace(/["']/g, '').slice(0, 100);
    const cmd = `node ${path.join(__dirname, 'gen-image.cjs')} "${concept.replace(/"/g, '\\"')}" ${type}`;

    exec(cmd, { timeout: 45000 }, (err, stdout, stderr) => {
      if (err) {
        log('WARN', `Image gen failed: ${err.message}`);
        resolve(null);
        return;
      }
      // Parse filepath from output like: [gen-image] Done via Grok in 3.6s — 288KB → /path/to/file.jpg
      const match = stdout.match(/→\s*(\S+\.\w+)/);
      if (match) {
        resolve(match[1]);
      } else {
        log('WARN', `Image gen output: ${stdout.slice(0, 200)}`);
        resolve(null);
      }
    });
  });
}

main().catch(e => {
  log('FATAL', e.message);
  process.exit(1);
});
