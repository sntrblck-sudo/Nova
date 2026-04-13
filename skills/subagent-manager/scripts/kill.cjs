#!/usr/bin/env node
/**
 * kill.cjs — Kill an active sub-agent
 * Usage: node kill.cjs <session-id>
 */

const { execSync } = require('child_process');
const fs = require('fs');

const ACTIVE_AGENTS_FILE = '/home/sntrblck/.openclaw/workspace/memory/active_subagents.json';

function getActiveAgents() {
  try {
    return JSON.parse(fs.readFileSync(ACTIVE_AGENTS_FILE, 'utf8'));
  } catch {
    return [];
  }
}

function saveAgents(agents) {
  fs.writeFileSync(ACTIVE_AGENTS_FILE, JSON.stringify(agents, null, 2));
}

function main() {
  const sessionId = process.argv[2];

  if (!sessionId) {
    console.log('Usage: node kill.cjs <session-id>');
    console.log('Run list.cjs to see active agents and their session IDs');
    process.exit(1);
  }

  const agents = getActiveAgents();
  const agent = agents.find(a => a.sessionId === sessionId || a.label === sessionId);

  if (!agent) {
    console.log(`Agent not found: ${sessionId}`);
    console.log('Run list.cjs to see active agents');
    process.exit(1);
  }

  try {
    // Kill the session via openclaw
    execSync(`openclaw sessions kill ${sessionId}`, { stdio: 'pipe' });
    console.log(`Killed: ${agent.label}`);
  } catch (e) {
    console.log(`Warning: openclaw kill failed (session may already be dead)`);
  }

  // Remove from active list
  const remaining = agents.filter(a => a.sessionId !== sessionId);
  saveAgents(remaining);
  console.log('Removed from active list.');
}

main();
