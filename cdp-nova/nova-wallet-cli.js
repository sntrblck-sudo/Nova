#!/usr/bin/env node
/**
 * Nova's CDP EOA Wallet
 * Manages Nova's Ethereum wallet on Base using viem
 */

import { createPublicClient, createWalletClient, http } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { base } from "viem/chains";
import { readFileSync } from "fs";
import { resolve } from "path";

const WALLET_PATH = resolve("/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json");

function loadWallet() {
  const walletData = JSON.parse(readFileSync(WALLET_PATH, "utf8"));
  const account = privateKeyToAccount(walletData.privateKey);
  return account;
}

export async function getAddress() {
  const account = loadWallet();
  return account.address;
}

export async function getBalance() {
  const account = loadWallet();
  const publicClient = createPublicClient({
    chain: base,
    transport: http(),
  });
  const balance = await publicClient.getBalance({ address: account.address });
  return Number(balance) / 1e18;
}

export async function sendEth(to, amountEth) {
  const account = loadWallet();
  const walletClient = createWalletClient({
    account,
    chain: base,
    transport: http(),
  });
  const hash = await walletClient.sendTransaction({
    to,
    value: BigInt(Math.floor(amountEth * 1e18)),
  });
  return hash;
}

export async function main() {
  const args = process.argv.slice(2);
  const command = args[0];

  if (command === "address") {
    console.log(await getAddress());
  } else if (command === "balance") {
    console.log(await getBalance(), "ETH");
  } else if (command === "send" && args.length >= 3) {
    const to = args[1];
    const amount = parseFloat(args[2]);
    const hash = await sendEth(to, amount);
    console.log("Transaction sent!");
    console.log("Hash:", hash);
  } else {
    console.log("Usage:");
    console.log("  nova-wallet address");
    console.log("  nova-wallet balance");
    console.log("  nova-wallet send <to_address> <amount_eth>");
  }
}

main().catch(console.error);
