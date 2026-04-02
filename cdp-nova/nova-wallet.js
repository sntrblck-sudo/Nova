import { CdpClient } from "@coinbase/cdp-sdk";
import dotenv from "dotenv";

dotenv.config();

async function main() {
  // Try with just the private key - CDP SDK might handle format conversion
  const cdp = new CdpClient({
    apiKeyId: process.env.CDP_API_KEY_ID,
    apiKeySecret: process.env.CDP_API_KEY_SECRET,
    walletSecret: process.env.CDP_WALLET_SECRET,
  });
  
  console.log("Testing with corrected credentials...");
  console.log("API Key ID:", process.env.CDP_API_KEY_ID?.substring(0, 10) + "...");
  console.log("Wallet Secret:", process.env.CDP_WALLET_SECRET?.substring(0, 20) + "...");
  
  try {
    const accounts = await cdp.evm.listAccounts();
    console.log("\nSUCCESS! Accounts:", JSON.stringify(accounts, null, 2));
  } catch (e) {
    console.log("\nFAILED:", e.message);
    if (e.statusCode) console.log("Status:", e.statusCode);
    if (e.error?.message) console.log("Error:", e.error.message);
  }
}

main().catch(console.error);
