import { createPublicClient, http } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { base } from "viem/chains";
import { readFileSync } from "fs";

const walletData = JSON.parse(readFileSync("./nova-wallet.json", "utf8"));
const account = privateKeyToAccount(walletData.privateKey);

const publicClient = createPublicClient({
  chain: base,
  transport: http(),
});

const balance = await publicClient.getBalance({ address: account.address });
console.log((Number(balance) / 1e18).toString());
