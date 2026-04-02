/**
 * Nova AgentKit Integration
 * Uses ViemWalletProvider with Nova's existing EOA private key
 * No CDP Server Wallet needed - signing handled by local private key
 */

const { AgentKit } = require("@coinbase/agentkit");
const { privateKeyToAccount } = require("viem/accounts");
const { base, baseSepolia } = require("viem/chains");
const viem = require("viem");
const fs = require("fs");
const path = require("path");

const WALLET_CONFIG_PATH = path.join(__dirname, "nova-wallet.json");

function loadWallet() {
  const data = JSON.parse(fs.readFileSync(WALLET_CONFIG_PATH, "utf8"));
  return { address: data.address, privateKey: data.privateKey };
}

async function createAgentKit(network = "base-mainnet", rpcUrl = null) {
  const wallet = loadWallet();
  const account = privateKeyToAccount(wallet.privateKey);
  const chain = network === "base-sepolia" ? baseSepolia : base;

  const client = viem.createWalletClient({
    account,
    chain,
    transport: rpcUrl ? viem.http(rpcUrl) : viem.http(),
  });

  const { ViemWalletProvider } = require("@coinbase/agentkit");
  const walletProvider = new ViemWalletProvider(client, {
    rpcUrl: rpcUrl || process.env.RPC_URL || "https://mainnet.base.org",
  });

  const cdpApiKeyId = process.env.CDP_API_KEY_ID;
  const cdpApiKeySecret = process.env.CDP_API_KEY_SECRET;

  let agentKit;
  if (cdpApiKeyId && cdpApiKeySecret) {
    agentKit = await AgentKit.from({ walletProvider, cdpApiKeyId, cdpApiKeySecret });
  } else {
    agentKit = await AgentKit.from({ walletProvider });
  }

  return { agentKit, walletProvider, account: account.address };
}

async function test() {
  console.log("Testing Nova AgentKit integration...");
  const { agentKit, account } = await createAgentKit("base-mainnet");
  console.log(`AgentKit initialized for: ${account}`);
  const actions = agentKit.getActions();
  console.log(`${Object.keys(actions).length} actions available`);
  actions.forEach((a, i) => console.log(`  ${i + 1}. ${a.name}`));
  return { success: true, address: account, actions: Object.keys(actions).length };
}

async function transferNative(value, to) {
  // value is in wei (atomic units), to is address
  const { agentKit } = await createAgentKit("base-mainnet");
  const actions = agentKit.getActions();
  const transferAction = actions.find((a) => a.name === "WalletActionProvider_native_transfer");
  const result = await transferAction.invoke({ amount: value, destination: to });
  return result;
}

async function transferNativeDirect(to, weiAmount) {
  // Direct call to ViemWalletProvider - bypasses AgentKit action wrapper
  // to is address, weiAmount is BigInt
  const { walletProvider } = await createAgentKit("base-mainnet");
  const txHash = await walletProvider.nativeTransfer(to, weiAmount);
  return txHash;
}

async function getWalletDetails() {
  const { agentKit } = await createAgentKit("base-mainnet");
  const actions = agentKit.getActions();
  const detailsAction = actions.find((a) => a.name === "WalletActionProvider_get_wallet_details");
  return detailsAction.invoke({});
}

module.exports = { createAgentKit, loadWallet, test, transferNative, transferNativeDirect, getWalletDetails };

if (require.main === module) {
  test().then((r) => {
    console.log("\nResult:", JSON.stringify(r, null, 2));
    process.exit(r.success ? 0 : 1);
  });
}
