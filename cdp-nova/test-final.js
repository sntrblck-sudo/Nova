import { CdpClient } from "@coinbase/cdp-sdk";
import dotenv from "dotenv";

dotenv.config();

async function main() {
  // Test WITHOUT wallet secret - just API key auth
  const cdpNoWallet = new CdpClient({
    apiKeyId: process.env.CDP_API_KEY_ID,
    apiKeySecret: process.env.CDP_API_KEY_SECRET,
  });

  console.log("Testing API-only operations (no wallet secret)...\n");

  // These should work if API key is valid
  const operations = [
    { name: "listAccounts", fn: () => cdpNoWallet.evm.listAccounts() },
  ];

  for (const op of operations) {
    try {
      console.log(`Trying ${op.name}...`);
      const result = await op.fn();
      console.log(`  SUCCESS:`, JSON.stringify(result).substring(0, 200));
    } catch (e) {
      console.log(`  FAILED: ${e.message}`);
      if (e.statusCode) console.log(`  Status: ${e.statusCode}`);
    }
  }

  console.log("\n--- Testing WITH wallet secret ---\n");

  const cdp = new CdpClient({
    apiKeyId: process.env.CDP_API_KEY_ID,
    apiKeySecret: process.env.CDP_API_KEY_SECRET,
    walletSecret: process.env.CDP_WALLET_SECRET,
  });

  const walletOps = [
    { name: "createAccount", fn: () => cdp.evm.createAccount() },
    { name: "listAccounts", fn: () => cdp.evm.listAccounts() },
  ];

  for (const op of walletOps) {
    try {
      console.log(`Trying ${op.name}...`);
      const result = await op.fn();
      console.log(`  SUCCESS:`, JSON.stringify(result).substring(0, 200));
    } catch (e) {
      console.log(`  FAILED: ${e.message}`);
      if (e.statusCode) console.log(`  Status: ${e.statusCode}`);
      if (e.error?.message) console.log(`  Error: ${e.error.message}`);
    }
  }
}

main().catch(console.error);
