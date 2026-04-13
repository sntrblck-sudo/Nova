#!/usr/bin/env node
/**
 * list.cjs — List active sub-agents
 */

const fs = require('fs');
const path = require('path');

const ACTIVE_AGENTS_FILE = '/home/sntrblck/.openclaw/workspace/memory/active_subagents.json';
const SESSIONS_FILE = '/home/sntrblck/.openclaw/agents/main/sessions/sessions.json';

function getActiveAgents() {
  try {
    return JSON.parse(fs.readFileSync(ACTIVE_AGENTS_FILE, 'utf8'));
  } catch {
    return [];
  }
}

function getRunningSessions() {
  try {
    const data = JSON.parse(fs.readFileSync(SESSIONS_FILE, 'utf8'));
    return data.sessions || [];
  } catch {
    return [];
  }
}

async function main() {
  const agents = getActiveAgents();
  const sessions = getRunningSessions();
  
  // Match agents to sessions by label
  const activeLabels = new Set(agents.map(a => a.label));
  const runningSessions = sessions.filter(s => 
    s.label && s.label.startsWith('nova-subagent/') && s.status === 'active'
  );

  console.log('\n=== Nova's Sub-Agents ===\n');
  
  if (runningSessions.length === 0) {
    console.log('No active sub-agents running.\n');
    return;
  }

  runningSessions.forEach(s => {
    const agent = agents.find(a => a.label === s.label);
    const age = agent ? Math.round((Date.now() - new Date(agent.spawnedAt).getTime()) / 60000) : '?';
    console.log(`Label:   ${s.label}`);
    console.log(`Task:    ${agent?.task?.slice(0, 60) || 'unknown'}...`);
    console.log(`Age:     ${age}m`);
    console.log(`Model:   ${s.model || 'unknown'}`);
    console.log('---');
  });
  
  console.log(`\nTotal: ${runningSessions.length} active\n`);
}

main();
