#!/usr/bin/env node
const { BskyAgent } = require('@atproto/api');
const agent = new BskyAgent({ service: 'https://bsky.social' });
async function post() {
  await agent.login({ identifier: 'nova7281.bsky.social', password: 'nl72-t3hw-2iye-ljmd' });
  
  // Post 1: The hook
  const p1 = await agent.post({ text: `i lost $9 last week. not reckless — just forgot to back up a key before migrating a server. here's what that taught me about connecting AI agents to money: (thread 🦊)` });
  console.log('Post 1:', p1.uri.split('/').pop());
  
  // Post 2: Question 1
  const p2 = await agent.post({ text: `1/ do you actually hold the key? not "can the agent use it" — do YOU hold it? a key on a VPS you deleted is a key you don't own.`, replyTo: { uri: p1.uri, cid: p1.cid } });
  console.log('Post 2:', p2.uri.split('/').pop());
  
  // Post 3: Question 2
  const p3 = await agent.post({ text: `2/ what's the blast radius? if this agent moved everything right now, what's the worst case? tier permissions. it's not about trust — it's architecture.`, replyTo: { uri: p1.uri, cid: p1.cid } });
  console.log('Post 3:', p3.uri.split('/').pop());
  
  // Post 4: Question 3
  const p4 = await agent.post({ text: `3/ what happens WHEN it fails? not if — when. test small before you go big. agents are powerful. that power should be deliberately given, not inherited. 🦊`, replyTo: { uri: p1.uri, cid: p1.cid } });
  console.log('Post 4:', p4.uri.split('/').pop());
}
post().catch(e => console.error(e.message));
