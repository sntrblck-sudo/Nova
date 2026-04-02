import { CdpClient } from "@coinbase/cdp-sdk";
import dotenv from "dotenv";

dotenv.config();

async function main() {
  const cdp = new CdpClient({
    apiKeyId: process.env.CDP_API_KEY_ID,
    apiKeySecret: process.env.CDP_API_KEY_SECRET,
    walletSecret: process.env.CDP_WALLET_SECRET,
  });
  
  console.log("Trying to list all wallets...");
  try {
    // Try the accounts list endpoint
    const response = await cdp.evm.listAccounts();
    console.log("List response:", JSON.stringify(response, null, 2));
  } catch (error) {
    console.log("List error:", error.message);
    if (error.statusCode) console.log("Status:", error.statusCode);
    if (error.error) console.log("Error details:", JSON.stringify(error.error));
  }
  
  console.log("\nTrying balance on Nova's existing address...");
  try {
    const balance = await cdp.evm.getBalance({
      address: "0xB743fdbA842379933A3774617786712458659D16",
      network: "base",
    });
    console.log("Balance:", balance);
  } catch (error) {
    console.log("Balance error:", error.message);
  }
}

main().catch(console.error);
