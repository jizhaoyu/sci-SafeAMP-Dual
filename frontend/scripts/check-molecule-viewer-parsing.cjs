// Exercise Molecule2DViewer SMILES parsing with TypeScript transpilation
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');

const filename = path.resolve(__dirname, '../src/components/Molecule2DViewer.tsx');
const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: { 
    module: ts.ModuleKind.CommonJS, 
    target: ts.ScriptTarget.ES2022,
    jsx: ts.JsxEmit.ReactJSX
  },
}).outputText;

function loadViewerModule() {
  const loaded = new Module(filename, module);
  loaded.filename = filename;
  loaded.paths = Module._nodeModulePaths(path.dirname(filename));
  loaded._compile(compiled, filename);
  return loaded.exports;
}

const { parseSmilesTo2D } = loadViewerModule();

// Test 1: Pyrrole ring c1cc[nH]c1 should have 5 nodes (4 C, 1 N) and no H node
const pyrrole = parseSmilesTo2D('c1cc[nH]c1');
assert.equal(pyrrole.nodes.length, 5, 'Pyrrole should have exactly 5 heavy atom nodes');
assert.deepEqual(
  pyrrole.nodes.map(n => n.symbol),
  ['C', 'C', 'C', 'N', 'C'],
  'Pyrrole atoms should be C, C, C, N, C'
);
assert.equal(pyrrole.nodes[3].symbol, 'N');
assert.equal(pyrrole.nodes[3].isHetero, true);
assert.equal(pyrrole.bonds.length, 5, 'Pyrrole should have 5 bonds forming a closed ring');

// Test 2: Imidazole c1n[nH]cc1 should have 5 nodes and no H node
const imidazole = parseSmilesTo2D('c1n[nH]cc1');
assert.equal(imidazole.nodes.length, 5, 'Imidazole should have exactly 5 heavy atom nodes');
assert.deepEqual(
  imidazole.nodes.map(n => n.symbol),
  ['C', 'N', 'N', 'C', 'C']
);

// Test 3: Stereocenters with [C@@H] like L-Valine CC(C)[C@@H](N)C(=O)O
const valine = parseSmilesTo2D('CC(C)[C@@H](N)C(=O)O');
assert.equal(valine.nodes.length, 8, 'Valine should have 8 heavy atoms (5 C, 1 N, 2 O)');
assert.ok(!valine.nodes.some(n => n.symbol === 'H'), 'Valine should not contain explicit H node');
const valineSymbols = valine.nodes.map(n => n.symbol);
assert.equal(valineSymbols.filter(s => s === 'C').length, 5);
assert.equal(valineSymbols.filter(s => s === 'N').length, 1);
assert.equal(valineSymbols.filter(s => s === 'O').length, 2);

// Test 4: Charged group with [O-] like Acetate CC(=O)[O-]
const acetate = parseSmilesTo2D('CC(=O)[O-]');
assert.equal(acetate.nodes.length, 4, 'Acetate should have 4 heavy atoms (2 C, 2 O)');
assert.deepEqual(acetate.nodes.map(n => n.symbol), ['C', 'C', 'O', 'O']);

console.log('All 4 Molecule2DViewer SMILES bracket parsing tests passed successfully!');
