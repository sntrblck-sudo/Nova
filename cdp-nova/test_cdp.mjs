import 'dotenv/config';
import { CdpClient } from '@coinbase/cdp-sdk';
import { readFileSync } from 'fs';

const walletSecret = readFileSync('./cdp-keys/wallet-secret.pem', 'utf8');

const cdp = new CdpClient({
  apiKeyId: process.env.CDP_API_KEY_ID,
  apiKeySecret: process.env.CDP_API_KEY_SECRET,
  walletSecret: walletSecret,
});

console.log('Creating account...');
const account = await cdp.evm.createAccount();
console.log(`Created EVM account: ${account.address}`);
