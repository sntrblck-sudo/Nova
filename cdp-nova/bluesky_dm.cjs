#!/usr/bin/env node
/**
 * Nova's Bluesky DM Bridge
 * Sends on-chain event alerts to Sen via Bluesky Direct Message
 * 
 * Usage:
 *   node bluesky_dm.cjs send <message>     Send a DM
 *   node bluesky_dm.cjs send-image <path>  Send image + caption
 *   node bluesky_dm.cjs check-convo       Find or create convo with Sen
 *   node bluesky_dm.cjs list              List recent conversations
 */

const { BskyAgent, ChatBskyConvo } = require('@atproto/api');
const { readFileSync } = require('fs');

const HANDLE = 'nova7281.bsky.social';
const APP_PASSWORD = 'nl72-t3hw-2iye-ljmd';
const SEN_HANDLE = 'sntrblck.bsky.social';

async function getAgent() {
  const agent = new BskyAgent({ service: 'https://bsky.social' });
  await agent.login({ identifier: HANDLE, password: APP_PASSWORD });
  return agent;
}

async function findOrCreateConvo(agent, theirHandle) {
  // Get their DID
  const theirProfile = await agent.getProfile({ actor: theirHandle });
  const theirDid = theirProfile.data.did;
  
  // Try to find existing convo
  const convoList = await ChatBskyConvo.listConvo(agent, { limit: 5 });
  for (const convo of convoList.conversations) {
    if (convo.actors.includes(theirDid)) {
      console.log('Found existing convo:', convo.rev);
      return { rev: convo.rev, uri: convo.uri };
    }
  }
  
  // Create new convo
  const convo = await ChatBskyConvo.createConvo(agent, { 
    members: [theirDid],
    message: { text: 'Hey Sen, this is Nova reaching out via Bluesky DM bridge 🦊' }
  });
  console.log('Created new convo:', convo.convo.rev);
  return convo.convo;
}

async function sendDM(agent, theirHandle, message) {
  const { rev, uri } = await findOrCreateConvo(agent, theirHandle);
  
  const result = await ChatBskyConvo.sendMessage(agent, {
    conversationId: uri,
    rev,
    message: { text: message }
  });
  
  console.log('DM sent! SentAt:', result.sentAt);
  return result;
}

async function sendImageDM(agent, theirHandle, imagePath, caption) {
  const imageBuffer = readFileSync(imagePath);
  const mimeType = imagePath.endsWith('.png') ? 'image/png' : 'image/jpeg';
  
  const { rev, uri } = await findOrCreateConvo(agent, theirHandle);
  
  const blob = await agent.uploadBlob(imageBuffer, { encoding: mimeType });
  
  const result = await ChatBskyConvo.sendMessage(agent, {
    conversationId: uri,
    rev,
    message: { 
      text: caption,
      embed: { $type: 'app.bsky.embed.images', images: [{ blob, alt: '' }] }
    }
  });
  
  console.log('Image DM sent!');
  return result;
}

async function listConvos(agent) {
  const result = await ChatBskyConvo.listConvo(agent, { limit: 10 });
  console.log(`Found ${result.conversations.length} conversations:`);
  for (const convo of result.conversations) {
    const others = convo.members || convo.actors;
    console.log(`- ${convo.uri} | rev: ${convo.rev} | members: ${others.join(', ')}`);
  }
}

async function main() {
  const cmd = process.argv[2];
  
  if (cmd === 'list') {
    const agent = await getAgent();
    await listConvos(agent);
  } else if (cmd === 'check-convo') {
    const agent = await getAgent();
    await findOrCreateConvo(agent, SEN_HANDLE);
  } else if (cmd === 'send') {
    const message = process.argv[3];
    if (!message) { console.error('Usage: send <message>'); process.exit(1); }
    const agent = await getAgent();
    await sendDM(agent, SEN_HANDLE, message);
  } else if (cmd === 'send-image') {
    const imagePath = process.argv[3];
    const caption = process.argv[4] || '';
    if (!imagePath) { console.error('Usage: send-image <path> [caption]'); process.exit(1); }
    const agent = await getAgent();
    await sendImageDM(agent, SEN_HANDLE, imagePath, caption);
  } else {
    console.log('Nova Bluesky DM Bridge');
    console.log('Usage:');
    console.log('  node bluesky_dm.cjs list           List conversations');
    console.log('  node bluesky_dm.cjs check-convo     Find or create convo with Sen');
    console.log('  node bluesky_dm.cjs send <msg>     Send text DM');
    console.log('  node bluesky_dm.cjs send-image <path> [caption]  Send image DM');
  }
}

main().catch(e => {
  console.error('Error:', e.message);
  if (e.message?.includes('401')) console.error('Auth failed — check credentials');
  process.exit(1);
});
