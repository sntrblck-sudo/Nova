import { createWalletClient, http } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { base } from "viem/chains";

const privateKey = "0x" + Buffer.from("m+Nq8BO61hijKJzZL7b5qS1BCrribtRzJcDLIw6s2xBOJlZdXeNT4D54tVYNOiMntUo5XuJn8mZqBBfEoLMegA==", "base64").toString("hex");

const account = privateKeyToAccount(privateKey);

const walletClient = createWalletClient({
  account,
  chain: base,
  transport: http(),
});

async function main() {
  console.log("Nova's EOA address:", account.address);
  
  // Get balance
  const balance = await walletClient.getBalance({
    address: account.address,
  });
  console.log("Balance:", balance, "wei");
  
  // Convert to ETH
  console.log("Balance in ETH:", Number(balance) / 1e18);
  
  console.log("\nReady to send transactions on Base!");
}

main().catch(console.error);
