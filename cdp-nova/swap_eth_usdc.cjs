const { createPublicClient, http, createWalletClient, encodeFunctionData } = require('viem');
const { privateKeyToAccount } = require('viem/accounts');
const { base } = require('viem/chains');
const fs = require('fs');

const wallet = JSON.parse(fs.readFileSync('nova-wallet.json', 'utf8'));
const account = privateKeyToAccount(wallet.privateKey);
const pub = createPublicClient({ chain: base, transport: http() });
const walletClient = createWalletClient({ account, chain: base, transport: http() });

const ROUTER = '0x4752ba5DBc23f44D87826276BF6Fd6b1C372ad24';
const WETH = '0x4200000000000000000000000000000000000006';
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';

const ethAmount = BigInt('5000000000000000'); // 0.005 ETH

const routerAbi = [
  {
    name: 'swapExactETHForTokens',
    type: 'function',
    inputs: [
      { name: 'amountOutMin', type: 'uint256' },
      { name: 'path', type: 'address[]' },
      { name: 'to', type: 'address' },
      { name: 'deadline', type: 'uint256' }
    ],
    outputs: [{ type: 'uint256[]' }]
  }
];

async function main() {
  const ethBal = await pub.getBalance({ address: account.address });
  console.log('Nova EOA:', account.address);
  console.log('ETH balance:', Number(ethBal) / 1e18);

  if (ethBal < ethAmount) {
    console.error('Insufficient ETH');
    process.exit(1);
  }

  // Get estimated output (with 1% slippage applied)
  const amounts = await pub.readContract({
    address: ROUTER,
    abi: [{ type: 'function', name: 'getAmountsOut', inputs: [{ type: 'uint256' }, { type: 'address[]' }], outputs: [{ type: 'uint256[]' }] }],
    functionName: 'getAmountsOut',
    args: [ethAmount, [WETH, USDC]]
  });
  const estimatedUSDC = Number(amounts[1]) / 1e6;
  const minUSDC = BigInt(Math.floor(Number(amounts[1]) * 0.99)); // 1% slippage
  console.log('Estimated USDC out:', estimatedUSDC.toFixed(2), '(min:', Number(minUSDC)/1e6, ')');

  const deadline = BigInt(Math.floor(Date.now() / 1000) + 600);

  const data = encodeFunctionData({
    abi: routerAbi,
    functionName: 'swapExactETHForTokens',
    args: [minUSDC, [WETH, USDC], account.address, deadline]
  });

  const gasPrice = await pub.getGasPrice();
  const gasEst = await pub.estimateGas({
    to: ROUTER,
    value: ethAmount,
    data,
    account: account.address
  }).catch(() => BigInt(150000));

  console.log('Gas estimate:', gasEst.toString());

  const hash = await walletClient.sendTransaction({
    to: ROUTER,
    value: ethAmount,
    data,
    gasPrice,
    gas: gasEst + BigInt(20000)
  });

  console.log('TX hash:', hash);
  console.log('https://basescan.org/tx/' + hash);
}

main().catch(e => console.error('Error:', e.message));
