import { CdpClient } from "@coinbase/cdp-sdk";
import dotenv from "dotenv";

dotenv.config();

async function main() {
  // Try with explicit scope
  const cdp = new CdpClient({
    apiKeyId: process.env.CDP_API_KEY_ID,
    apiKeySecret: process.env.CDP_API_KEY_SECRET,
    walletSecret: process.env.CDP_WALLET_SECRET,
  });
  
  console.log("=== CDP SDK Diagnostics ===\n");
  console.log("CDP_API_KEY_ID:", process.env.CDP_API_KEY_ID);
  console.log("CDP_API_KEY_SECRET:", process.env.CDP_API_KEY_SECRET ? "[SET]" : "[MISSING]");
  console.log("CDP_WALLET_SECRET:", process.env.CDP_WALLET_SECRET ? "[SET]" : "[MISSING]");
  
  // Check SDK version
  const pkg = await import("@coinbase/cdp-sdk/package.json", { assert: { type: "json" } });
  console.log("\nSDK Version:", pkg.default.version);
  
  // Try createAccount with explicit options
  console.log("\n=== Testing createAccount ===");
  try {
    const result = await cdp.evm.createAccount({
      networkId: "base"
    });
    console.log("SUCCESS:", result);
  } catch (e) {
    console.log("Error:", e.message);
    console.log("Status code:", e.statusCode);
    console.log("Error code:", e.errorCode);
    console.log("Full error:", JSON.stringify(e, null, 2));
  }
  
  // Try listing - sometimes new accounts don't show up
  console.log("\n=== Testing listAccounts ===");
  try {
    const accounts = await cdp.evm.listAccounts({});
    console.log("Accounts:", JSON.stringify(accounts, null, 2));
  } catch (e) {
    console.log("List Error:", e.message);
    console.log("Status:", e.statusCode);
  }
}

main().catch(console.error);
