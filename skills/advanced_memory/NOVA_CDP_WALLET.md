# Nova CDP EOA Wallet Skill

## Overview
Nova manages her own Ethereum wallet using viem locally. No Coinbase API required.

## Wallet Details
- **Address:** `0x21f2155Cba0B599D705B4cf6e51Ba157503bcD0B`
- **Network:** Base (Base Mainnet)
- **Private Key:** Stored securely in `cdp-nova/nova-wallet.json` (mode 600)
- **Balance:** Currently 0 ETH — needs funding

## Usage

### Check Balance
```bash
cd /home/sntrblck/.openclaw/workspace/cdp-nova && node nova-eoa.js
```

### Send Transaction
```javascript
import { createWalletClient, http } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { base } from "viem/chains";
import { readFileSync } from "fs";

const walletData = JSON.parse(readFileSync("./nova-wallet.json", "utf8"));
const account = privateKeyToAccount(walletData.privateKey);

const walletClient = createWalletClient({
  account,
  chain: base,
  transport: http(),
});

// Send ETH
const hash = await walletClient.sendTransaction({
  to: "0xRECIPIENT_ADDRESS",
  value: BigInt(100000000000000), // 0.0001 ETH in wei
});
```

### Key Functions
- `checkBalance()` — returns ETH balance
- `sendEth(to, amountEth)` — send ETH to address
- `getAddress()` — return Nova's wallet address

## Funding
Send ETH to `0x21f2155Cba0B599D705B4cf6e51Ba157503bcD0B` to enable transactions.

## Security
Private key is stored locally with 0o600 permissions (owner read/write only).
