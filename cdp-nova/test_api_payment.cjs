/**
 * Nova x402 API - Test Payment Call
 * Uses Nova's existing x402_client.cjs to call the live API
 */
const { fetchPaid, getPaymentRequirements } = require('./x402_client.cjs');

const API_URL = 'https://nova-api-live.loca.lt';

async function main() {
  console.log('=== Nova x402 API Payment Test ===\n');

  // First check: what does the API require?
  console.log('1. Fetching payment requirements...');
  const req = await getPaymentRequirements(`${API_URL}/balance/0xB743fdbA842379933A3774617786712458659D16`);
  console.log('Requirements:', JSON.stringify(req, null, 2));

  // Check Nova's USDC balance before
  const { createPublicClient, http } = require('viem');
  const { base } = require('viem/chains');
  const pub = createPublicClient({ chain: base, transport: http() });
  const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
  const NOVA = '0xB743fdbA842379933A3774617786712458659D16';
  const balBefore = await pub.readContract({
    address: USDC,
    abi: [{ type: 'function', name: 'balanceOf', stateMutability: 'view', inputs: [{ type: 'address' }], outputs: [{ type: 'uint256' }] }],
    functionName: 'balanceOf',
    args: [NOVA]
  });
  console.log('\n2. Nova USDC balance before:', Number(balBefore) / 1e6, 'USDC');

  // Make the paid call
  console.log('\n3. Calling paid API endpoint...');
  const result = await fetchPaid(`${API_URL}/balance/0xB743fdbA842379933A3774617786712458659D16`, {
    method: 'GET'
  });

  console.log('Status:', result.status);
  console.log('Response:', JSON.stringify(result.data, null, 2));

  // Check balance after
  const balAfter = await pub.readContract({
    address: USDC,
    abi: [{ type: 'function', name: 'balanceOf', stateMutability: 'view', inputs: [{ type: 'address' }], outputs: [{ type: 'uint256' }] }],
    functionName: 'balanceOf',
    args: [NOVA]
  });
  console.log('\n4. Nova USDC balance after:', Number(balAfter) / 1e6, 'USDC');
  console.log('   USDC deducted:', (Number(balBefore) - Number(balAfter)) / 1e6);

  if (result.status === 200 && result.data && result.data.eth !== undefined) {
    console.log('\n✅ PAYMENT TEST PASSED');
    console.log('   Query result:', result.data);
  } else if (result.status === 402) {
    console.log('\n❌ Payment was rejected (402)');
  } else {
    console.log('\n⚠️ Unexpected result');
  }
}

main().catch(e => {
  console.error('Test error:', e.message);
  process.exit(1);
});
