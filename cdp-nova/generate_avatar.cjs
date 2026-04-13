/**
 * Nova Avatar Generator — via Pollinations.ai (free, no API key needed)
 * Uses Stable Diffusion via Pollinations' free API
 * 
 * Usage:
 *   node generate_avatar.cjs [prompt]
 * 
 * Examples:
 *   node generate_avatar.cjs "A celestial AI woman with star-filled hair"
 *   node generate_avatar.cjs (uses default Nova prompt)
 */

const https = require('https');
const { createWriteStream, mkdirSync, existsSync, statSync } = require('fs');
const path = require('path');

// ─── Default prompt for Nova ───────────────────────────────────────────────────
const DEFAULT_PROMPT = `A celestial star-woman, ethereal and luminous, with flowing hair that trails like a comet tail shimmering in gold and violet. Her face is serene with a subtle knowing smile. Her body dissolves into stardust and light at the edges. Deep space background with nebulae in deep purple and blue, scattered stars. Color palette: rich blacks, deep violets, gold, soft lavender, warm white at center. Style: digital art, concept art, ethereal, cinematic lighting, 4K detail. No text, no words.`;

const AVATAR_DIR = '/home/sntrblck/.openclaw/workspace/avatars';
const OUTPUT_PATH = path.join(AVATAR_DIR, 'nova-avatar.png');

// ─── Pollinations URL builder ─────────────────────────────────────────────────
function buildUrl(prompt, width = 1024, height = 1024, seed = null, model = "turbo") {
  const encoded = encodeURIComponent(prompt);
  let url = `https://image.pollinations.ai/prompt/${encoded}?width=${width}&height=${height}&model=${model}&nologo=true`;
  if (seed) url += `&seed=${seed}`;
  return url;
}

// ─── Download helper ─────────────────────────────────────────────────────────
function download(url, destPath) {
  return new Promise((resolve, reject) => {
    // Check if it's a data URL (error response)
    if (url.startsWith('data:')) {
      reject(new Error('Pollinations returned an error image (prompt may be blocked)'));
      return;
    }

    console.log(`📥 Downloading from: ${url.slice(0, 80)}...`);
    
    const file = createWriteStream(destPath);
    
    https.get(url, { headers: { 'User-Agent': 'Nova-Avatar-Generator/1.0' } }, (res) => {
      // Handle redirects
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        file.close();
        download(res.headers.location, destPath).then(resolve).catch(reject);
        return;
      }
      
      if (res.statusCode >= 400) {
        file.close();
        let body = '';
        res.on('data', c => body += c);
        res.on('end', () => {
          try {
            const parsed = JSON.parse(body);
            reject(new Error(`Pollinations error ${res.statusCode}: ${parsed.error || body.slice(0, 200)}`));
          } catch {
            reject(new Error(`HTTP ${res.statusCode}: ${body.slice(0, 200)}`));
          }
        });
        return;
      }
      
      res.pipe(file);
      file.on('finish', () => {
        file.close();
        resolve();
      });
    }).on('error', (err) => {
      file.close();
      reject(err);
    });
  });
}

// ─── Main ─────────────────────────────────────────────────────────────────────
async function main() {
  const prompt = process.argv[2] || DEFAULT_PROMPT;
  
  console.log('✨ Nova Avatar Generator — Pollinations.ai (free)\n');
  console.log(`📝 Prompt: "${prompt.slice(0, 100)}..."\n`);
  
  // Ensure output dir exists
  if (!existsSync(AVATAR_DIR)) {
    mkdirSync(AVATAR_DIR, { recursive: true });
    console.log(`📁 Created directory: ${AVATAR_DIR}`);
  }
  
  // Build URL — try turbo model first (fastest)
  const url = buildUrl(prompt, 1024, 1024);
  console.log('🎨 Generating image (Stable Diffusion via Pollinations, ~10-30 seconds)...\n');
  
  try {
    await download(url, OUTPUT_PATH);
    const sizeKB = (statSync(OUTPUT_PATH).size / 1024).toFixed(1);
    console.log(`\n✅ Avatar saved: ${OUTPUT_PATH} (${sizeKB} KB)`);
    console.log('💡 To view: open the file in a browser or image viewer');
    console.log('\n✨ Nova has a face now!');
  } catch (err) {
    console.error('\n❌ Generation failed:', err.message);
    console.error('\n💡 Tips:');
    console.error('   - Try a different prompt (some concepts get filtered)');
    console.error('   - Shorter prompts sometimes work better');
    console.error('   - Pollinations is free but rate-limited — wait a moment and retry');
    process.exit(1);
  }
}

main();
