#!/usr/bin/env node
/**
 * TipVault Listener Supervisor
 * Keeps listener.cjs running with exponential backoff on crash
 * Usage: node supervisor.cjs
 */
const { spawn } = require('child_process');
const path = require('path');

const SCRIPT = path.join(__dirname, 'listener.cjs');
const LOG_FILE = path.join(__dirname, 'listener.log');
const MAX_DELAY = 300000; // 5 min cap
const BASE_DELAY = 1000;

let delay = BASE_DELAY;
let crashes = 0;
let running = false;

function log(msg) {
  const ts = new Date().toISOString();
  const line = `[${ts}] ${msg}\n`;
  process.stdout.write(line);
  require('fs').appendFileSync(LOG_FILE, line);
}

function start() {
  if (running) return;
  running = true;
  delay = BASE_DELAY;

  log(`🚀 Starting listener (crash #${crashes})`);

  const child = spawn('node', [SCRIPT], {
    cwd: __dirname,
    stdio: ['ignore', 'pipe', 'pipe']
  });

  child.stdout.on('data', d => process.stdout.write(d));
  child.stderr.on('data', d => process.stderr.write(d));

  child.on('exit', (code, signal) => {
    running = false;
    if (code === 0 || signal === 'SIGINT') {
      log(`👋 Listener stopped cleanly`);
      return;
    }
    crashes++;
    log(`💥 Listener crashed (code=${code}, signal=${signal}). Restarting in ${delay}ms`);
    setTimeout(start, delay);
    delay = Math.min(delay * 2, MAX_DELAY);
  });
}

process.on('SIGINT', () => {
  log('SIGINT received, shutting down');
  process.exit(0);
});

start();
