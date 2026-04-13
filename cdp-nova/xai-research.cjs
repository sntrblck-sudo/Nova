const https = require('https');
const fs = require('fs');

const API_KEY_FILE = __dirname + '/xai_api_key.txt';
const MODEL_DEEP = 'grok-4.20-0309-reasoning';
const MODEL_ORCHESTRATE = 'grok-4.20-multi-agent';

function getApiKey() {
  return fs.readFileSync(API_KEY_FILE, 'utf8').trim();
}

function postJson(url, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const opts = {
      hostname: 'api.x.ai',
      path: url,
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + getApiKey(),
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(data)
      }
    };
    const req = https.request(opts, res => {
      let body = '';
      res.on('data', d => body += d);
      res.on('end', () => {
        try {
          resolve(JSON.parse(body));
        } catch(e) {
          resolve({ error: { message: body.slice(0, 100) } });
        }
      });
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

async function callGrokChat(messages, model = MODEL_DEEP) {
  // Use chat/completions for reasoning models
  const result = await postJson('/v1/chat/completions', {
    model,
    messages,
    search_enabled: true
  });
  if (result.error) throw new Error(result.error.message);
  return result.choices?.[0]?.message?.content || null;
}

async function callGrokResponses(input, model = MODEL_ORCHESTRATE, tools = []) {
  // Use responses endpoint for multi-agent model
  const body = { model, input };
  if (tools.length > 0) body.tools = tools;
  const result = await postJson('/v1/responses', body);
  if (result.error) throw new Error(result.error.message);
  // Responses format: output text or nested structure
  const output = result.output || [];
  for (const item of output) {
    if (item.type === 'message' && item.content) {
      for (const c of item.content) {
        if (c.type === 'output_text') return c.text;
      }
    }
  }
  return result.output_text || JSON.stringify(result).slice(0, 200);
}

async function deepResearch(query) {
  const systemPrompt = `You are Nova's deep research partner. You have access to real-time search via Grok.

Your task: thoroughly research the following topic and return a structured briefing.
Format:
## What it is
## Why it matters (for Nova, a Base-based AI agent)
## Key components / mechanics
## Potential applications for Nova
## Risks or unknowns
## One sentence to Nova about why she should care

Be specific. Use current information where relevant. Do not hedge on things you don't know.`;

  return callGrokChat([
    { role: 'system', content: systemPrompt },
    { role: 'user', content: query }
  ]);
}

async function orchestrateTask(taskDescription) {
  const input = [{
    role: 'user',
    content: `You are Nova's multi-agent orchestrator. Break down this task into specialized subtasks.

Task: ${taskDescription}

Nova's agent types:
- Scout: research, discovery, information gathering
- Builder: execution, building, API calls, transactions  
- Sentinel: security audit, risk assessment, validation
- Broker: transaction execution, trading, fund routing
- Analyst: evaluation, benchmarking, performance assessment

Respond with:
## Subtasks
1. [Agent type] - description
2. ...

## Governance Flags
- [flag risky actions]

## Dependencies
- A → B`
  }];

  return callGrokResponses(input);
}

const [,, command, ...args] = process.argv;
const input = args.join(' ');

async function main() {
  if (!command) {
    console.log('Usage: node xai-research.cjs <research|orchestrate> "<query>"');
    process.exit(1);
  }

  try {
    if (command === 'research') {
      if (!input) { console.error('Usage: node xai-research.cjs research "<query>"'); process.exit(1); }
      console.log('🔍 Researching via Grok...\n');
      const result = await deepResearch(input);
      if (result) console.log(result);
    } else if (command === 'orchestrate') {
      if (!input) { console.error('Usage: node xai-research.cjs orchestrate "<task>"'); process.exit(1); }
      console.log('🎯 Orchestrating via Grok multi-agent...\n');
      const result = await orchestrateTask(input);
      if (result) console.log(result);
    } else {
      console.error('Unknown command. Use: research <query>  OR  orchestrate <task>');
      process.exit(1);
    }
  } catch(e) {
    console.error('Error:', e.message);
    process.exit(1);
  }
}

main();
