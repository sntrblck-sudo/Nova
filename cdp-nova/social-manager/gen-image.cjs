#!/usr/bin/env node
// gen-image.cjs — Generate consistent-styled images for Nova's Bluesky posts
// Usage: node gen-image.cjs "post concept" [type] [output-path]
// Types: identity, build, thread, custom
// Default type: identity
//
// Provider stack:
//   1. xAI Grok Imagine (primary — fast, reliable, credits available)
//   2. Pollinations (fallback — free, no auth, but flaky)
//   3. Fail gracefully — return null, caller posts text-only

const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

const MEDIA_DIR = path.join(__dirname, '..', '..', 'media', 'bluesky-images');
if (!fs.existsSync(MEDIA_DIR)) fs.mkdirSync(MEDIA_DIR, { recursive: true });

const XAI_API_KEY = process.env.XAI_API_KEY;

// Nova's visual aesthetic — consistent palette and style
const STYLES = {
  identity: {
    prefix: 'Abstract digital art, violet and amber glow, cosmic nebula textures,',
    suffix: 'dark background, ethereal, minimal, contemplative, high contrast, digital painting',
  },
  build: {
    prefix: 'Futuristic data visualization, neon violet and cyan on dark,',
    suffix: 'holographic interface, sleek, dark background, high contrast, digital art',
  },
  thread: {
    prefix: 'Cinematic wide shot, violet and cyan neon lighting,',
    suffix: 'atmospheric, moody, film grain, dark background, establishing shot, digital art',
  },
  custom: {
    prefix: '',
    suffix: 'digital art, high quality, dark background with violet accents',
  },
};

function buildPrompt(concept, type) {
  const style = STYLES[type] || STYLES.identity;
  if (type === 'custom') {
    return `${concept}, ${style.suffix}`;
  }
  return `${style.prefix} ${concept}, ${style.suffix}`;
}

function httpsPost(url, headers, body) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const data = JSON.stringify(body);
    const opts = {
      hostname: u.hostname,
      path: u.pathname + u.search,
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) },
    };
    const req = https.request(opts, (res) => {
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => {
        const buf = Buffer.concat(chunks);
        resolve({ status: res.statusCode, body: buf.toString() });
      });
    });
    req.on('error', reject);
    req.setTimeout(30000, () => { req.destroy(); reject(new Error('timeout')); });
    req.write(data);
    req.end();
  });
}

function download(url) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https') ? https : http;
    mod.get(url, { timeout: 15000 }, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        return download(res.headers.location).then(resolve).catch(reject);
      }
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => resolve(Buffer.concat(chunks)));
      res.on('error', reject);
    }).on('error', reject);
  });
}

function isValidImage(buf) {
  return buf[0] === 0xFF || buf[0] === 0x89 || buf[0] === 0x47; // JPEG, PNG, GIF
}

// --- Provider 1: xAI Grok Imagine ---
async function generateGrok(prompt) {
  if (!XAI_API_KEY) return null;

  const res = await httpsPost('https://api.x.ai/v1/images/generations', {
    Authorization: `Bearer ${XAI_API_KEY}`,
  }, {
    model: 'grok-imagine-image',
    prompt,
    n: 1,
    response_format: 'b64_json',
  });

  if (res.status !== 200) {
    console.log(`[gen-image] Grok HTTP ${res.status}, skipping`);
    return null;
  }

  const data = JSON.parse(res.body);
  const b64 = data.data?.[0]?.b64_json;
  if (!b64) {
    console.log('[gen-image] Grok returned no image data, skipping');
    return null;
  }

  return Buffer.from(b64, 'base64');
}

// --- Provider 2: Pollinations ---
async function generatePollinations(prompt) {
  const seed = Math.floor(Math.random() * 100000);
  const encoded = encodeURIComponent(prompt);
  const url = `https://image.pollinations.ai/prompt/${encoded}?width=1200&height=675&nologo=true&seed=${seed}`;

  for (let attempt = 1; attempt <= 2; attempt++) {
    try {
      const buf = await download(url);
      if (isValidImage(buf)) return buf;
      console.log(`[gen-image] Pollinations attempt ${attempt}: non-image response, retrying...`);
    } catch (e) {
      console.log(`[gen-image] Pollinations attempt ${attempt}: ${e.message}`);
    }
  }
  return null;
}

// --- Main ---
async function generateImage(concept, type = 'identity', outputPath = null) {
  const prompt = buildPrompt(concept, type);
  const timestamp = Date.now();
  const filename = `nova-${type}-${timestamp}.jpg`;
  const filepath = outputPath || path.join(MEDIA_DIR, filename);

  console.log(`[gen-image] Type: ${type}`);
  console.log(`[gen-image] Prompt: ${prompt}`);

  // Try providers in order
  const providers = [
    { name: 'Grok', fn: () => generateGrok(prompt) },
    { name: 'Pollinations', fn: () => generatePollinations(prompt) },
  ];

  for (const provider of providers) {
    const start = Date.now();
    try {
      console.log(`[gen-image] Trying ${provider.name}...`);
      const imgData = await provider.fn();
      if (imgData && isValidImage(imgData)) {
        fs.writeFileSync(filepath, imgData);
        const elapsed = ((Date.now() - start) / 1000).toFixed(1);
        const sizeKB = (imgData.length / 1024).toFixed(0);
        console.log(`[gen-image] Done via ${provider.name} in ${elapsed}s — ${sizeKB}KB → ${filepath}`);
        return filepath;
      }
    } catch (e) {
      console.log(`[gen-image] ${provider.name} failed: ${e.message}`);
    }
  }

  console.log('[gen-image] All providers failed — returning null (post text-only)');
  return null;
}

// CLI
const args = process.argv.slice(2);
if (args.length === 0) {
  console.log('Usage: node gen-image.cjs "post concept" [type] [output-path]');
  console.log('Types: identity, build, thread, custom');
  process.exit(1);
}

const concept = args[0];
const type = args[1] || 'identity';
const outputPath = args[2] || null;

generateImage(concept, type, outputPath).then((result) => {
  if (!result) process.exit(1);
}).catch((err) => {
  console.error('[gen-image] Fatal:', err.message);
  process.exit(1);
});