#!/usr/bin/env node
/**
 * Nova Email CLI
 * Usage: node nova-email.js send <to> <subject> <body>
 *        node nova-email.js status
 *        node nova-email.js templates
 */

const { ResendClient } = require('./resend_client');
const fs = require('fs');
const path = require('path');

const EMAIL_CONFIG_PATH = path.join(__dirname, '..', 'email_config.json');

function loadConfig() {
  try {
    return JSON.parse(fs.readFileSync(EMAIL_CONFIG_PATH, 'utf8'));
  } catch {
    return {};
  }
}

async function cmdSend(to, subject, body) {
  const config = loadConfig();
  const apiKey = config.apiKey || process.env.RESEND_API_KEY;
  
  if (!apiKey) {
    console.error('Error: RESEND_API_KEY not configured');
    console.error('Run: openclaw email setup');
    process.exit(1);
  }

  const client = new ResendClient(apiKey);
  
  try {
    const result = await client.send({
      to,
      subject,
      text: body,
    });
    
    if (result.error) {
      console.error('Send failed:', result.error);
      process.exit(1);
    }
    
    console.log(JSON.stringify({ success: true, id: result.data?.id }));
  } catch (err) {
    console.error('Error:', err.message);
    process.exit(1);
  }
}

async function cmdStatus() {
  const config = loadConfig();
  console.log(JSON.stringify({
    configured: !!config.apiKey,
    fromEmail: config.fromEmail || 'nova@resend.dev (default)',
    domain: config.domain || 'not configured',
  }));
}

async function cmdSetup(apiKey, fromEmail, domain) {
  const config = {
    apiKey,
    fromEmail: fromEmail || 'nova@resend.dev',
    domain: domain || null,
    updatedAt: new Date().toISOString(),
  };
  
  fs.writeFileSync(EMAIL_CONFIG_PATH, JSON.stringify(config, null, 2));
  console.log('Email configured successfully');
}

const [,, cmd, ...args] = process.argv;

(async () => {
  switch (cmd) {
    case 'send':
      await cmdSend(args[0], args[1], args[2]);
      break;
    case 'status':
      await cmdStatus();
      break;
    case 'setup':
      await cmdSetup(args[0], args[1], args[2]);
      break;
    default:
      console.log('Nova Email CLI');
      console.log('Commands:');
      console.log('  nova-email.js send <to> <subject> <body>  - Send email');
      console.log('  nova-email.js status                     - Check config');
      console.log('  nova-email.js setup <apiKey> [fromEmail] [domain] - Configure');
  }
})();
