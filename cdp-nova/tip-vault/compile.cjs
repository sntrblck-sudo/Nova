const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const CONTRACT_PATH = path.join(__dirname, 'contracts/TipVault.sol');
const OUTPUT_DIR = path.join(__dirname, 'compiled');

fs.mkdirSync(OUTPUT_DIR, { recursive: true });

const solcInput = {
  language: 'Solidity',
  sources: {
    'TipVault.sol': {
      content: fs.readFileSync(CONTRACT_PATH, 'utf8')
    }
  },
  settings: {
    optimizer: { enabled: false },
    outputSelection: {
      '*': { '*': ['abi', 'bin'] }
    }
  }
};

const inputJson = JSON.stringify(solcInput);
const output = execSync(`npx solc --standard-json`, {
  input: inputJson,
  encoding: 'utf8',
  timeout: 30000
});

const result = JSON.parse(output.split('\n').filter(l => !l.startsWith('>>>')).join('\n'));

if (result.errors) {
  const errors = result.errors.filter(e => e.severity === 'error');
  if (errors.length > 0) {
    console.error('Compilation errors:');
    errors.forEach(e => console.error(e.formattedMessage));
    process.exit(1);
  }
  // warnings are ok
  result.errors.filter(e => e.severity === 'warning').forEach(e => console.warn('Warning:', e.message));
}

const contract = result.contracts['TipVault.sol'].TipVault;
if (!contract) {
  console.error('Contract not found in output');
  process.exit(1);
}

const abi = typeof contract.abi === 'string' ? contract.abi : JSON.stringify(contract.abi, null, 2);
fs.writeFileSync(path.join(OUTPUT_DIR, 'TipVault.abi'), abi);
fs.writeFileSync(path.join(OUTPUT_DIR, 'TipVault.bin'), contract.bin);

console.log('✅ Compilation successful');
console.log('ABI:', path.join(OUTPUT_DIR, 'TipVault.abi'));
console.log('BIN:', path.join(OUTPUT_DIR, 'TipVault.bin'));
console.log('ABI type:', typeof contract.abi, Array.isArray(contract.abi) ? '(array)' : '');
console.log('BIN type:', typeof contract.bin, Array.isArray(contract.bin) ? '(array)' : '');
console.log('Contract keys:', Object.keys(contract));
console.log('BIN size:', contract.bin.length, 'chars');
