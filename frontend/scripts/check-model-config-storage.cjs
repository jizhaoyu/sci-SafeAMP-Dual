// Exercise the actual TypeScript store with isolated in-memory localStorage.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');

const filename = path.resolve(__dirname, '../src/store/useAppStore.ts');
const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const cache = new Map();
global.localStorage = {
  getItem: (key) => cache.get(key) ?? null,
  setItem: (key, value) => cache.set(key, value),
  removeItem: (key) => cache.delete(key),
};
global.window = { localStorage: global.localStorage };

function loadStore() {
  const loaded = new Module(filename, module);
  loaded.filename = filename;
  loaded.paths = Module._nodeModulePaths(path.dirname(filename));
  loaded._compile(compiled, filename);
  return loaded.exports.useAppStore;
}

const name = 'dti-lab-workspace-v1';
cache.set(name, JSON.stringify({ version: 4, state: {
  apiKey: 'legacy-secret-fixture', apiBase: 'https://api.deepseek.com/v1',
  modelName: 'deepseek-chat', llmProvider: 'deepseek', temperature: 0.3,
  activeSequence: 'FIXTURE', activePeptideName: 'Fixture', cart: [],
} }));
const store = loadStore();
assert.equal(store.getState().apiKey, '');
assert.equal(store.getState().temperature, 0.3);
let persisted = JSON.parse(cache.get(name));
assert.equal(persisted.version, 5);
assert.equal(Object.hasOwn(persisted.state, 'apiKey'), false);
store.getState().setLLMConfig({ apiKey: 'current-secret-fixture', modelName: 'fixture-model' });
assert.equal(store.getState().apiKey, 'current-secret-fixture');
persisted = JSON.parse(cache.get(name));
assert.equal(Object.hasOwn(persisted.state, 'apiKey'), false);
assert.equal(persisted.state.modelName, 'fixture-model');
const reopened = loadStore();
assert.equal(reopened.getState().apiKey, '');
assert.equal(reopened.getState().modelName, 'fixture-model');
console.log('PASS: legacy credential removed, key remains in memory only, nonsecret settings preserved across reload');
