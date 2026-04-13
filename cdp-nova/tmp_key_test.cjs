const { createWalletClient, http, encodeFunctionData } = require('viem');
const { privateKeyToAccount } = require('viem/accounts');
const { base } = require('viem/chains');
const fs = require('fs');

const pemKey = 'MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgigbVVicVZZtSSTBd/hthFxfoiMPXWNNQeRGl1V6DfcqhRANCAASsP+D6XdEy3CWk6LcTpw+g8FyjuNAUowIEd2M3WToTvxvXq3GIVMXX2zVw0u5QKniDxqkY+OqntSVDhKkq7Ces';

// Try to import as raw private key (32 bytes from end of decoded)
const buf = Buffer.from(pemKey, 'base64');
console.log('Total decoded length:', buf.length);

// Try to parse as PKCS#8 and extract raw key
const pkcs8 = require('asn1js').parse ? require('asn1js') : null;

try {
  // Last 32 bytes should be the raw private key
  const rawKeyHex = '0x' + buf.slice(-32).toString('hex');
  console.log('Raw key hex:', rawKeyHex);
  const account = privateKeyToAccount(rawKeyHex);
  console.log('Address:', account.address);
} catch(e) {
  console.log('Error with last-32 method:', e.message);
}

// Also try: maybe it's base64 of raw key directly
try {
  const rawFromBase64 = Buffer.from(pemKey, 'base64').toString('hex');
  console.log('Full decoded hex:', rawFromBase64.slice(0, 80) + '...');
} catch(e) {
  console.log('Error:', e.message);
}
