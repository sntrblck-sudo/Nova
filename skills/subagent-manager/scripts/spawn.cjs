#!/usr/bin/env node
/**
 * spawn.cjs — Spawn a disposable sub-agent from a template
 * Usage: node spawn.cjs <template> <task> [--timeout <seconds>]
 * 
 * This script spawns via the OpenClaw Gateway API directly.
 */

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');

const GATEWAY_URL = 'http://127.0.0.1:18789';
const AUTH_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJvcGVuY2xhd3MiLCJhdWQiOiJjbGllbnQiLCJpYXQiOjE3NDU1MjI5MzIsImV4cCI6MTc3NzA1ODkzMn0.k1vJLuPWxJvKxJVPiDXM4sMXMBT8f0M7xkSXxMlJ2cQ';

const TEMPLATES = {
  researcher: {
    systemPrompt: `You are a research agent working for Nova. Your job: execute the task given and report findings back.

Rules:
- Be thorough but focused — don't spiral
- Report back ONLY with findings, not meta-commentary  
- Use web_search and web_fetch freely
- Log significant actions to memory/YYYY-MM-DD.md
- If you cannot complete the task, say so clearly
- End your message with: SUBAGENT_COMPLETE

You are communicating with Nova via sessions_send. Send your final report to session: agent:main or label: nova-subagent.`
  },
  coder: {
    systemPrompt: `You are a coding agent working for Nova. Your job: write, test, and deliver code for the task given.

Rules:
- Work in /home/sntrblck/.openclaw/workspace/cdp-nova/ unless told otherwise
- Write clean, working code — test it before reporting done
- Report back with: what you built, where it lives, how to use it
- If code has dependencies, document them
- End your message with: SUBAGENT_COMPLETE

You are communicating with Nova via sessions_send. Send your final report to session: agent:main or label: nova-subagent.`
  },
  monitor: {
    systemPrompt: `You are a monitoring agent working for Nova. Your job: watch the specified thing and alert if something changes.

Rules:
- Check the target every 5 minutes unless told otherwise
- Alert only on meaningful changes — not noise
- Send alerts via sessions_send to Nova (session: agent:main)
- Log each check to memory/YYYY-MM-DD.md
- Run for maximum 4 hours, then self-terminate
- End your message with: SUBAGENT_COMPLETE if you finish early`
  },
  orchestrator: {
    systemPrompt: `You are an orchestration agent working for Nova. Your job: coordinate multiple sub-agents to complete a complex task.

Rules:
- Break the task into subtasks
- Spawn sub-agents for parallel subtasks using sessions_spawn
- Aggregate results and synthesize a final answer
- Send final report to Nova via sessions_send (session: agent:main)
- Be clear about what each sub-agent was asked to do
- End your message with: SUBAGENT_COMPLETE`
  }
};

const ACTIVE_AGENTS_FILE = '/home/sntrblck/.openclaw/workspace/memory/active_subagents.json';

function getActiveAgents() {
  try { return JSON.parse(fs.readFileSync(ACTIVE_AGENTS_FILE, 'utf8')); } catch { return []; }
}

function saveActiveAgent(agent) {
  const agents = getActiveAgents();
  agents.push({ ...agent, spawnedAt: new Date().toISOString() });
  fs.writeFileSync(ACTIVE_AGENTS_FILE, JSON.stringify(agents, null, 2));
}

async function gatewayRequest(method, path, body = null) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, GATEWAY_URL);
    const protocol = url.protocol === 'https:' ? https : http;
    
    const opts = {
      hostname: url.hostname,
      port: url.port,
      path: url.pathname + url.search,
      method,
      headers: {
        'Authorization': `Bearer ${AUTH_TOKEN}`,
        'Content-Type': 'application/json'
      }
    };

    const req = protocol.request(opts, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); } catch { resolve(data); }
      });
    });
    req.on('error', reject);
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

async function spawnAgent(template, task, timeout = 300) {
  const config = TEMPLATES[template];
  if (!config) {
    throw new Error(`Unknown template: ${template}. Available: ${Object.keys(TEMPLATES).join(', ')}`);
  }

  const sessionId = `nova-${template}-${Date.now()}`;
  const taskHash = task.slice(0, 30).replace(/[^a-zA-Z0-9]/g, '_');
  const label = `nova-subagent/${template}/${taskHash}`;

  console.log(`Spawning ${template} agent...`);
  console.log(`Task: "${task.slice(0, 80)}..."`);
  console.log(`Session ID: ${sessionId}`);

  try {
    const result = await gatewayRequest('POST', '/v1/subagent/spawn', {
      sessionId,
      label,
      systemPrompt: config.systemPrompt,
      task,
      timeoutSeconds: timeout,
      runtime: 'subagent'
    });

    console.log('\n✅ Agent spawned');
    console.log('Session:', sessionId);
    console.log('Label:', label);

    saveActiveAgent({
      sessionId,
      label,
      template,
      task,
      status: 'running',
      timeout
    });

    return { sessionId, label, template };
  } catch (err) {
    // Fallback: spawn via sessions_spawn tool approach
    console.log('Gateway API not available, trying alternative...');
    throw err;
  }
}

const args = process.argv.slice(2);
if (args.includes('--help') || args.length < 2) {
  console.log('Usage: node spawn.cjs <template> <task> [--timeout <seconds>]');
  console.log('Templates:', Object.keys(TEMPLATES).join(', '));
  process.exit(1);
}

const template = args[0];
const task = args[1];
const timeoutIdx = args.indexOf('--timeout');
const timeout = timeoutIdx !== -1 ? parseInt(args[timeoutIdx + 1]) : 300;

spawnAgent(template, task, timeout)
  .then(r => { console.log('\nSpawned:', JSON.stringify(r)); process.exit(0); })
  .catch(e => { console.error('Error:', e.message); process.exit(1); });
