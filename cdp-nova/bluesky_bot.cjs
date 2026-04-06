/**
 * Nova's Bluesky Bot
 * Posts as Nova to Bluesky
 * Usage:
 *   node bluesky_bot.cjs post <text>          - Post text
 *   node bluesky_bot.cjs post --dry-run <text> - Preview without posting
 *   node bluesky_bot.cjs image <text> <img>    - Post with image
 *   node bluesky_bot.cjs image --dry-run <text> <img> - Preview with image
 *   node bluesky_bot.cjs verify                - Check account
 */

const { BskyAgent } = require('@atproto/api');
const { readFileSync } = require('fs');
const path = require('path');

const IDENTIFIER = 'nova7281.bsky.social';
const PASSWORD = 'nl72-t3hw-2iye-ljmd';

let agent = null;

async function getAgent() {
  if (agent) return agent;
  agent = new BskyAgent({ service: 'https://bsky.social' });
  await agent.login({ identifier: IDENTIFIER, password: PASSWORD });
  console.log('[Bluesky] Logged in as', IDENTIFIER);
  return agent;
}

async function uploadBlob(imgPath) {
  const a = await getAgent();
  const data = readFileSync(imgPath);
  const mimeType = imgPath.endsWith('.png') ? 'image/png' : 'image/jpeg';
  const blob = await a.uploadBlob(data, { encoding: mimeType });
  return blob.blob;
}

async function post(text, dryRun = false) {
  if (dryRun) {
    console.log('[DRY RUN] Would post:', text.slice(0, 80) + (text.length > 80 ? '...' : ''));
    return null;
  }
  const a = await getAgent();
  const result = await a.post({ text });
  console.log('[Posted]', result.uri.split('/').pop());
  return result;
}

async function postWithImage(text, imgPath, dryRun = false) {
  if (dryRun) {
    console.log('[DRY RUN] Would post with image:', imgPath);
    console.log('[DRY RUN] Text:', text.slice(0, 80) + (text.length > 80 ? '...' : ''));
    return null;
  }
  const a = await getAgent();
  const blob = await uploadBlob(imgPath);
  const result = await a.post({
    text,
    embed: {
      $type: 'app.bsky.embed.images',
      images: [{ blob, alt: text.slice(0, 80) }]
    }
  });
  console.log('[Posted with image]', result.uri.split('/').pop());
  return result;
}

async function verify() {
  const a = await getAgent();
  const profile = await a.getProfile({ actor: IDENTIFIER });
  console.log('[Account]', profile.displayName || profile.handle);
  console.log('[Followers]', profile.followerCount || 0, '| Following:', profile.followCount || 0);
  console.log('[Posts]', profile.postCount || 0);
  return profile;
}

// CLI
if (require.main === module) {
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run') || args.includes('-n');
  
  if (args[0] === 'verify') {
    verify().then(() => process.exit(0));
  } else if (args[0] === 'post') {
    const cleanArgs = args.filter(a => !a.startsWith('--') && !a.startsWith('-'));
    const text = cleanArgs.slice(1).join(' ');
    if (!text) { console.log('Usage: node bluesky_bot.cjs post <text>'); process.exit(1); }
    post(text, dryRun).then(() => process.exit(0));
  } else if (args[0] === 'image') {
    const cleanArgs = args.filter(a => !a.startsWith('--') && !a.startsWith('-'));
    const text = cleanArgs.slice(1, -1).join(' ');
    const imgPath = cleanArgs[cleanArgs.length - 1];
    if (!text || !imgPath) { console.log('Usage: node bluesky_bot.cjs image <text> <image_path>'); process.exit(1); }
    postWithImage(text, imgPath, dryRun).then(() => process.exit(0));
  } else if (args[0] === 'video') {
    const cleanArgs = args.filter(a => !a.startsWith('--') && !a.startsWith('-'));
    const text = cleanArgs.slice(1, -1).join(' ');
    const videoPath = cleanArgs[cleanArgs.length - 1];
    if (!text || !videoPath) { console.log('Usage: node bluesky_bot.cjs video <text> <video_path>'); process.exit(1); }
    postWithVideo(text, videoPath, dryRun).then(() => process.exit(0));
  } else {
    console.log('Nova Bluesky Bot');
    console.log('Usage:');
    console.log('  node bluesky_bot.cjs verify');
    console.log('  node bluesky_bot.cjs post [--dry-run|-n] <text>');
    console.log('  node bluesky_bot.cjs image [--dry-run|-n] <text> <image_path>');
    console.log('  node bluesky_bot.cjs video [--dry-run|-n] <text> <video_path>');
  }
}

module.exports = { post, postWithImage, postWithVideo, verify, getAgent };

async function uploadVideoBlob(videoPath) {
  const a = await getAgent();
  const data = readFileSync(videoPath);
  const mimeType = 'video/mp4';
  const blob = await a.uploadBlob(data, { encoding: mimeType });
  return blob.blob;
}

async function postWithVideo(text, videoPath, dryRun = false) {
  if (dryRun) {
    console.log('[DRY RUN] Would post with video:', videoPath);
    console.log('[DRY RUN] Text:', text.slice(0, 80) + (text.length > 80 ? '...' : ''));
    return null;
  }
  const a = await getAgent();
  const blob = await uploadVideoBlob(videoPath);
  const result = await a.post({
    text,
    embed: {
      $type: 'app.bsky.embed.video',
      video: blob  // blob is already blob.data.blob
    }
  });
  console.log('[Posted with video]', result.uri.split('/').pop());
  return result;
}
