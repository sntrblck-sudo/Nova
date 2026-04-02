import { createPublicClient, createWalletClient, http } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { base } from "viem/chains";
import { readFileSync } from "fs";

const walletData = JSON.parse(readFileSync("./nova-wallet.json", "utf8"));
const account = privateKeyToAccount(walletData.privateKey);

const publicClient = createPublicClient({
  chain: base,
  transport: http(),
});

const walletClient = createWalletClient({
  account,
  chain: base,
  transport: http(),
});

async function main() {
  console.log("Nova's EOA Address:", account.address);
  
  // Get balance using public client
  const balance = await publicClient.getBalance({
    address: account.address,
  });
  
  console.log("Current Balance:", Number(balance) / 1e18, "ETH");
  
  if (Number(balance) === 0) {
    console.log("\n⚠️  Wallet is empty - send funds to this address to enable transactions!");
    console.log("Address to send to: ", account.address);
  } else {
    console.log("\n✅ Wallet has funds - ready to transact!");
  }
}

main().catch(console.error);
