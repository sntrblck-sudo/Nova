import { CdpClient } from "@coinbase/cdp-sdk";
import dotenv from "dotenv";
import axios from "axios";

dotenv.config();

async function main() {
  const cdp = new CdpClient({
    apiKeyId: process.env.CDP_API_KEY_ID,
    apiKeySecret: process.env.CDP_API_KEY_SECRET,
    walletSecret: process.env.CDP_WALLET_SECRET,
  });
  
  console.log("Testing API key auth...");
  
  // Try to list accounts first to verify auth works
  try {
    const response = await axios.get("https://api.cdp.coinbase.com/server/v1/accounts", {
      headers: {
        "Content-Type": "application/json",
      },
      // The SDK should handle auth automatically
    });
    console.log("Response:", response.data);
  } catch (error) {
    console.log("Direct API error:", error.response?.data || error.message);
  }
  
  console.log("\nTrying to create account...");
  try {
    const account = await cdp.evm.createAccount();
    console.log(`SUCCESS! Nova's EVM Account: ${account.address}`);
  } catch (error) {
    console.log("Account creation error:", error.message);
    if (error.response) {
      console.log("Status:", error.response.status);
      console.log("Data:", JSON.stringify(error.response.data));
    }
  }
  
  await cdp.close();
}

main().catch(console.error);
