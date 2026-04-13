const https = require('https');
const fs = require('fs');
const API_KEY = fs.readFileSync('xai_api_key.txt','utf8').trim();

// Try multi-agent model through chat completions with different payload
const payloads = [
  { model:'grok-4.20-multi-agent-0309', messages:[{role:'user',content:'break down: build a tipping contract on Base'}] },
  { model:'grok-4.20-multi-agent-0309', messages:[{role:'user',content:'break down: build a tipping contract on Base'}], agent_mode:true },
  { model:'grok-4.20-multi-agent-0309', task_type:'multi_agent', messages:[{role:'user',content:'break down: build a tipping contract on Base'}] }
];

async function tryPayload(payload) {
  return new Promise((resolve) => {
    const body = JSON.stringify(payload);
    const opts = {
      hostname:'api.x.ai', path:'/v1/chat/completions', method:'POST',
      headers:{'Authorization':'Bearer '+API_KEY,'Content-Type':'application/json','Content-Length':Buffer.byteLength(body)}
    };
    const req = https.request(opts, res => {
      let d=''; res.on('data',c=>d+=c); res.on('end',()=>resolve({status:res.statusCode, body:d.slice(0,150)}));
    });
    req.on('error',e=>resolve({error:e.message}));
    req.write(body); req.end();
  });
}

async function main() {
  for (const p of payloads) {
    console.log('Trying:', JSON.stringify(p).slice(0,80));
    const r = await tryPayload(p);
    console.log('Result:', JSON.stringify(r));
    console.log('---');
  }
}
main();
