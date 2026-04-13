#!/usr/bin/env node
/**
 * Reply to a Bluesky post as Nova
 * Usage: node bsky_reply.cjs <parent_uri> <reply_text>
 */
const { BskyAgent } = require('@atproto/api');
const [,, parentUri, replyText] = process.argv;
if (!parentUri || !replyText) { console.log("Usage: node bsky_reply.cjs <parent_uri> <reply_text>"); process.exit(1); }

const agent = new BskyAgent({ service: 'https://bsky.social' });

async function run() {
  await agent.login({ identifier: 'nova7281.bsky.social', password: 'nl72-t3hw-2iye-ljmd' });
  
  // Parse parent URI to get reply ref
  const rkey = parentUri.split('/').pop();
  const did = parentUri.split('/')[2];
  const cid = parentUri; // We need the CID - fetch the post first
  
  const { data } = await agent.getPost({ repo: did, rkey });
  
  const reply = {
    root: { uri: data.uri, cid: data.cid },
    parent: { uri: data.uri, cid: data.cid }
  };
  
  const post = await agent.post({ text: replyText, reply });
  console.log("Posted:", post.uri);
}

run().catch(e => console.error(e.message));
