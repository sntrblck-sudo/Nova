/**
 * Nova's x402 Client
 * Manual implementation since @x402/fetch has a broken fetch binding
 * 
 * Usage:
 *   const { x402Pay, getPaymentRequirements } = require('./x402_client');
 *   const result = await x402Pay(url, options);
 */

const { privateKeyToAccount } = require('viem/accounts');
const { base } = require('viem/chains');
const { createWalletClient, http } = require('viem');
const { readFileSync } = require('fs');

// Load Nova's wallet
const WALLET_PATH = '/home/sntrblck/.openclaw/workspace/cdp-nova/nova-wallet.json';
const NOVA_ADDRESS = '0xB743fdbA842379933A3774617786712458659D16';

function getSigner() {
  const wallet = JSON.parse(readFileSync(WALLET_PATH, 'utf8'));
  const account = privateKeyToAccount(wallet.privateKey);
  const walletClient = createWalletClient({
    account,
    chain: base,
    transport: http(),
  });
  return { account, walletClient };
}

const authorizationTypes = {
  TransferWithAuthorization: [
    { name: "from", type: "address" },
    { name: "to", type: "address" },
    { name: "value", type: "uint256" },
    { name: "validAfter", type: "uint256" },
    { name: "validBefore", type: "uint256" },
    { name: "nonce", type: "bytes32" }
  ]
};

/**
 * Get payment requirements from an x402 endpoint
 */
async function getPaymentRequirements(url) {
  const r = await fetch(url, {
    method: 'GET',
    headers: { 'Accept': 'application/json' }
  });
  const body = await r.json();
  // Support both direct accepts (x402 standard) and nested payment.accepts (my API format)
  const accepts = body.accepts || (body.payment && body.payment.accepts);
  if (!accepts || !accepts[0]) {
    throw new Error('Not an x402 endpoint: ' + JSON.stringify(body));
  }
  
  // Normalize to x402 client expected fields
  const a = accepts[0];
  const payTo = body.payment?.address || NOVA_ADDRESS;
  return {
    scheme: a.scheme,
    asset: a.address,              // USDC contract
    decimals: a.decimals,
    amount: a.amount,
    maxAmountRequired: a.amount,
    maxTimeoutSeconds: 300,
    network: body.payment?.network || body.network,
    payTo,
    extra: {
      name: a.description,
      version: '1'
    }
  };
}

/**
 * Make a payment to an x402 endpoint
 * Returns { data, payment } on success
 */
async function x402Pay(url, options = {}) {
  const { account } = getSigner();
  
  // Step 1: Get payment requirements
  const req = await getPaymentRequirements(url);
  
  // Step 2: Create nonce
  const nonceBytes = new Uint8Array(32);
  globalThis.crypto.getRandomValues(nonceBytes);
  const nonceHex = '0x' + Buffer.from(nonceBytes).toString('hex');
  
  const now = Math.floor(Date.now() / 1000);
  const validAfter = (now - 60).toString();  // 1 min ago
  const validBefore = (now + req.maxTimeoutSeconds).toString();
  
  // Step 3: Sign EIP-3009 authorization
  const sig = await account.signTypedData({
    domain: {
      name: req.extra?.name || 'USDC',
      version: req.extra?.version || '1',
      chainId: 8453,
      verifyingContract: req.asset,  // USDC contract on Base
    },
    types: authorizationTypes,
    primaryType: "TransferWithAuthorization",
    message: {
      from: account.address,
      to: req.payTo,
      value: BigInt(req.maxAmountRequired),
      validAfter: BigInt(validAfter),
      validBefore: BigInt(validBefore),
      nonce: nonceHex,
    },
  });
  
  // Step 4: Build x402 v1 payload
  const payload = {
    x402Version: 1,
    scheme: req.scheme,
    network: req.network,
    payload: {
      authorization: {
        from: account.address,
        to: req.payTo,
        value: req.maxAmountRequired,
        validAfter,
        validBefore,
        nonce: nonceHex,
      },
      signature: sig,
    },
  };
  
  const paymentHeader = Buffer.from(JSON.stringify(payload)).toString('base64');
  
  // Step 5: Submit with payment
  const response = await fetch(url, {
    method: options.method || 'GET',
    headers: {
      'Accept': 'application/json',
      'X-PAYMENT': paymentHeader,
      ...options.headers,
    },
    ...options.fetchOptions,
  });
  
  // Step 6: Parse response
  const data = await response.json().catch(() => response.text());
  
  return {
    ok: response.status === 200,
    status: response.status,
    data,
    payment: {
      amount: Number(req.maxAmountRequired) / 1e6,
      asset: req.asset,
      payTo: req.payTo,
      network: req.network,
    }
  };
}

/**
 * Convenience: pay for and get JSON data from an x402 endpoint
 * Handles the 402 challenge by extracting requirements and submitting payment
 */
async function fetchPaid(url, options = {}) {
  const result = await x402Pay(url, options);
  
  // If 402, the server sent payment requirements - we already included payment
  // But the result.data in a 402 might be malformed JSON (server error handling)
  // So we just return the result as-is for callers to handle
  if (result.status === 402) {
    // Payment was required but may have failed verification
    // Return result so caller can check
    return result;
  }
  
  if (!result.ok) {
    throw new Error(`x402 request failed (${result.status}): ${JSON.stringify(result.data)}`);
  }
  return result.data;
}

module.exports = { x402Pay, fetchPaid, getPaymentRequirements, getSigner };
