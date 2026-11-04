const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const source = fs.readFileSync(path.join(__dirname, '../src/utils/cartMetrics.ts'), 'utf8');
const exportsObject = {};
vm.runInNewContext(ts.transpileModule(source, {compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText, {exports:exportsObject});
const cases = [
  [{kind:'small_molecule', pkd:6.2274, tsi:3.03}, 6.2274],
  [{kind:'small_molecule', pkd:0, tsi:3.03}, 0],
  [{kind:'small_molecule', tsi:8.88}, null],
  [{kind:'peptide', pkd:8.88, tsi:0.75}, 0.75],
];
for (const [input, expected] of cases) assert.equal(exportsObject.cartScore(input), expected);
console.log('4 cart metric behavioral cases passed');
