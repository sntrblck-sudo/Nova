#!/usr/bin/env node
/**
 * Nova's Wallet Send Function
 * Simple interface for sending ETH
 */

import { createWalletClient, http } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { base } from "viem/chains";
import { readFileSync } from "fs";
import { resolve } from "path";

const WALLET_PATH = resolve("/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json");

async function send(to, amountEth) {
  const walletData = JSON.parse(readFileSync(WALLET_PATH, "utf8"));
  const account = privateKeyToAccount(walletData.privateKey);
  
  const client = createWalletClient({
    account,
    chain: base,
    transport: http(),
  });
  
  const hash = await client.sendTransaction({
    to,
    value: BigInt(Math.floor(amountEth * 1e18)),
  });
  
  return hash;
}

const args = process.argv.slice(2);

if (args.length < 2) {
  console.log("Usage: nova-send <to_address> <amount_eth>");
  process.exit(1);
}

const [to, amountStr] = args;
const amount = parseFloat(amountStr);

console.log(`Sending ${amount} ETH to ${to}...`);

send(to, amount)
  .then(hash => {
    console.log(`✅ Success! TX: ${hash}`);
  })
  .catch(err => {
    console.error(`❌ Failed: ${err.message}`);
    process.exit(1);
  });
