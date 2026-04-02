import { CdpClient } from "@coinbase/cdp-sdk";
import dotenv from "dotenv";

dotenv.config();

async function main() {
  const cdp = new CdpClient({
    apiKeyId: process.env.CDP_API_KEY_ID,
    apiKeySecret: process.env.CDP_API_KEY_SECRET,
    walletSecret: process.env.CDP_WALLET_SECRET,
  });
  
  console.log("Testing Solana account creation...");
  try {
    const account = await cdp.solana.createAccount();
    console.log(`SUCCESS! Nova's Solana Account: ${account.address}`);
  } catch (error) {
    console.log("Solana error:", error.message);
    if (error.response) {
      console.log("Status:", error.response.status);
      console.log("Data:", JSON.stringify(error.response.data));
    }
  }
  
  console.log("\nTesting EVM account creation...");
  try {
    const account = await cdp.evm.createAccount();
    console.log(`SUCCESS! Nova's EVM Account: ${account.address}`);
  } catch (error) {
    console.log("EVM error:", error.message);
    if (error.statusCode) {
      console.log("Status:", error.statusCode);
    }
  }
}

main().catch(console.error);
