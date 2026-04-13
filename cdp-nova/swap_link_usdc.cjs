/**
 * Nova's LINK → USDC Swap Script (Base Mainnet)
 * Uniswap V3 on Base
 * 
 * Usage: node swap_link_usdc.cjs [amountIn LINK - defaults to FULL BALANCE]
 * Example: node swap_link_usdc.cjs 10
 */

const { createPublicClient, http, createWalletClient, encodeFunctionData } = require('viem');
const { privateKeyToAccount } = require('viem/accounts');
const { base } = require('viem/chains');
const fs = require('fs');

const wallet = JSON.parse(fs.readFileSync('nova-wallet.json', 'utf8'));
const account = privateKeyToAccount(wallet.privateKey);
const pub = createPublicClient({ chain: base, transport: http() });
const walletClient = createWalletClient({ account, chain: base, transport: http() });

// Uniswap V3 Router on Base
const ROUTER = '0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24';
const LINK = '0x514910771AF9Ca656af840dff83E8264EcF986CA';
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const WETH = '0x4200000000000000000000000000000000000006';

// ERC20 ABI (for balance and allowance)
const erc20Abi = [
  { name: 'balanceOf', type: 'function', inputs: [{ name: 'account', type: 'address' }], outputs: [{ type: 'uint256' }] },
  { name: 'allowance', type: 'function', inputs: [{ name: 'owner', type: 'address' }, { name: 'spender', type: 'address' }], outputs: [{ type: 'uint256' }] },
  { name: 'approve', type: 'function', inputs: [{ name: 'spender', type: 'address' }, { name: 'amount', type: 'uint256' }], outputs: [{ type: 'bool' }] }
];

// Uniswap V3 Router ABI (exact input swap)
const routerAbi = [
  { name: 'exactInputSingle', type: 'function', inputs: [
    { name: 'params', type: 'tuple',
      components: [
        { name: 'tokenIn', type: 'address' },
        { name: 'tokenOut', type: 'address' },
        { name: 'fee', type: 'uint24' },
        { name: 'recipient', type: 'address' },
        { name: 'amountIn', type: 'uint256' },
        { name: 'amountOutMinimum', type: 'uint256' },
        { name: 'sqrtPriceLimitX96', type: 'uint160' }
      ]
    }
  ], outputs: [{ name: 'amountOut', type: 'uint256' }] }
];

async function main() {
  const amountFloat = parseFloat(process.argv[2]) || null; // null = full balance
  
  console.log('Nova EOA:', account.address);
  
  // Check LINK balance
  const linkBal = await pub.readContract({
    address: LINK,
    abi: erc20Abi,
    functionName: 'balanceOf',
    args: [account.address]
  });
  const linkBalFloat = Number(linkBal) / 1e18;
  console.log('LINK balance:', linkBalFloat.toFixed(4));
  
  if (linkBal === BigInt(0)) {
    console.error('No LINK to swap!');
    process.exit(1);
  }
  
  const amountIn = amountFloat !== null 
    ? BigInt(Math.floor(amountFloat * 1e18))
    : linkBal;
  
  if (amountIn > linkBal) {
    console.error(`Insufficient LINK. Have: ${linkBalFloat.toFixed(4)}, requested: ${amountFloat}`);
    process.exit(1);
  }
  
  // Check ETH balance (for gas)
  const ethBal = await pub.getBalance({ address: account.address });
  console.log('ETH balance (for gas):', Number(ethBal) / 1e18);
  
  if (ethBal < BigInt(1e15)) { // < 0.001 ETH
    console.error('Insufficient ETH for gas. Need at least ~0.001 ETH.');
    process.exit(1);
  }
  
  // Check allowance
  const allowance = await pub.readContract({
    address: LINK,
    abi: erc20Abi,
    functionName: 'allowance',
    args: [account.address, ROUTER]
  });
  
  let needsApproval = allowance < amountIn;
  
  if (needsApproval) {
    console.log('\nApproving LINK for Router...');
    const approveData = encodeFunctionData({
      abi: erc20Abi,
      functionName: 'approve',
      args: [ROUTER, amountIn]
    });
    const gasPrice = await pub.getGasPrice();
    const approveTx = await walletClient.sendTransaction({
      to: LINK,
      data: approveData,
      value: BigInt(0),
      gasPrice
    });
    console.log('Approve TX:', approveTx);
    console.log('https://basescan.org/tx/' + approveTx);
    // Wait for approval confirmation
    await pub.waitForTransactionReceipt({ hash: approveTx });
    console.log('Approval confirmed.\n');
  } else {
    console.log('\nAllowance OK, skipping approval.\n');
  }
  
  // Get quote (with 2% slippage)
  const amounts = await pub.readContract({
    address: ROUTER,
    abi: [{ type: 'function', name: 'getAmountsOut', inputs: [{ type: 'uint256' }, { type: 'address[]' }], outputs: [{ type: 'uint256[]' }] }],
    functionName: 'getAmountsOut',
    args: [amountIn, [LINK, USDC]]
  });
  const estimatedUSDC = Number(amounts[1]) / 1e6;
  const minUSDC = BigInt(Math.floor(Number(amounts[1]) * 0.98)); // 2% slippage
  console.log('Estimated USDC out:', estimatedUSDC.toFixed(2), '(min:', Number(minUSDC)/1e6, ')');
  
  if (estimatedUSDC < 1) {
    console.log('Output too small, skipping.');
    process.exit(0);
  }
  
  // Build swap params
  const params = {
    tokenIn: LINK,
    tokenOut: USDC,
    fee: 3000, // 0.3% pool fee
    recipient: account.address,
    amountIn: amountIn,
    amountOutMinimum: minUSDC,
    sqrtPriceLimitX96: BigInt(0) // no price limit
  };
  
  const swapData = encodeFunctionData({
    abi: routerAbi,
    functionName: 'exactInputSingle',
    args: [params]
  });
  
  const gasPrice = await pub.getGasPrice();
  const gasEst = await pub.estimateGas({
    to: ROUTER,
    value: BigInt(0),
    data: swapData,
    account: account.address
  }).catch(() => BigInt(180000));
  
  console.log('Gas estimate:', gasEst.toString());
  
  console.log('\nSwapping...');
  const hash = await walletClient.sendTransaction({
    to: ROUTER,
    value: BigInt(0),
    data: swapData,
    gasPrice,
    gas: gasEst + BigInt(20000)
  });
  
  console.log('TX hash:', hash);
  console.log('https://basescan.org/tx/' + hash);
  
  // Wait and confirm
  const receipt = await pub.waitForTransactionReceipt({ hash });
  console.log('\nStatus:', receipt.status === 1 ? '✅ SUCCESS' : '❌ FAILED');
  
  // Final balances
  const finalLink = await pub.readContract({ address: LINK, abi: erc20Abi, functionName: 'balanceOf', args: [account.address] });
  const finalUSDC = await pub.readContract({ address: USDC, abi: erc20Abi, functionName: 'balanceOf', args: [account.address] });
  console.log('\nFinal LINK:', Number(finalLink) / 1e18);
  console.log('Final USDC:', Number(finalUSDC) / 1e6);
}

main().catch(e => console.error('Error:', e.message));
