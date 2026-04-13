#!/usr/bin/env node
/**
 * Import a PKCS#8 PEM key and save as Nova's wallet
 * Handles the PEM format: extract raw 32-byte secp256k1 key
 */
const { privateKeyToAccount } = require('viem/accounts');
const { writeFileSync } = require('fs');

const PEM = 'MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgigbVVicVZZtSSTBd/hthFxfoiMPXWNNQeRGl1V6DfcqhRANCAASsP+D6XdEy3CWk6LcTpw+g8FyjuNAUowIEd2M3WToTvxvXq3GIVMXX2zVw0u5QKniDxqkY+OqntSVDhKkq7Ces';

// Decode base64 PEM to get raw bytes
const buf = Buffer.from(PEM, 'base64');
// PKCS#8 format: 16-byte header + 32-byte private key at the end
// The last 32 bytes are the actual secp256k1 private key
const rawKey = buf.slice(-32);
const rawHex = '0x' + rawKey.toString('hex');

console.log('Extracted raw key:', rawHex);
console.log('Key length:', rawKey.length, 'bytes');

// Derive address
const account = privateKeyToAccount(rawHex);
console.log('Address:', account.address);

// Save as Nova wallet
const wallet = {
  privateKey: rawHex,
  address: account.address,
};
writeFileSync('/home/sntrblck/.openclaw/workspace/cdp-nova/cdp-wallet-imported.json', JSON.stringify(wallet, null, 2));
console.log('Saved to cdp-wallet-imported.json');
console.log('\nIMPORTANT: Verify this is the correct key before using!');
console.log('Run: node -e "const {createPublicClient,http}=require(\"viem\");const{base}=require(\"viem/chains\");const pub=createPublicClient({chain:base,transport:http()});pub.getBalance({address:\"' + account.address + '\"}).then(b=>console.log(\"Balance:\",Number(b)/1e18))"');
