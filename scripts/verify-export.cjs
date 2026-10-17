// Uses the same parser and importer shipped with the pinned Bruno CLI.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const { parseRequest, parseEnvironment } = require('@usebruno/filestore');
const { createCollectionFromBrunoObject } = require('@usebruno/cli/src/utils/collection');
const { collectionSchema } = require('@usebruno/schema');
const root = path.resolve(__dirname, '..');
const source = path.join(root, 'bruno');
const exported = path.join(root, 'exports', 'Auntie-Som-Lab.json');
const bru = { format: 'bru' };

function items(directory) {
  return fs.readdirSync(directory, { withFileTypes: true })
    .filter(entry => entry.name !== 'environments' && entry.name !== 'bruno.json' && entry.name !== 'collection.bru' && entry.name !== 'folder.bru')
    .map(entry => {
      const file = path.join(directory, entry.name);
      if (entry.isDirectory()) return { name: entry.name, type: 'folder', items: items(file) };
      assert(entry.name.endsWith('.bru'), `Unexpected collection file ${entry.name}`);
      return parseRequest(fs.readFileSync(file, 'utf8'), bru);
    }).sort((a, b) => a.type === 'folder' ? a.name.localeCompare(b.name) : a.seq - b.seq);
}

function removeUids(value) {
  if (Array.isArray(value)) return value.map(removeUids);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).filter(([key]) => key !== 'uid').map(([key, child]) => [key, removeUids(child)]));
  return value;
}

function addUids(value, location = 'collection') {
  if (Array.isArray(value)) return value.map((child, index) => addUids(child, `${location}/${index}`));
  if (value && typeof value === 'object') {
    const result = Object.fromEntries(Object.entries(value).map(([key, child]) => [key, addUids(child, `${location}/${key}`)]));
    if ('name' in result || location === 'collection') result.uid = createHash('sha256').update(location).digest('hex').slice(0, 21);
    return result;
  }
  return value;
}

async function main() {
  const environment = { name: 'local', ...parseEnvironment(fs.readFileSync(path.join(source, 'environments/local.example.bru'), 'utf8'), bru) };
  const collection = addUids({ version: '1', name: 'Auntie Som Lab', items: items(source), environments: [environment] });
  // Validate against Bruno's import schema before publishing an importable file.
  collectionSchema.validateSync(collection, { abortEarly: false });
  if (process.argv.includes('--write')) {
    fs.mkdirSync(path.dirname(exported), { recursive: true });
    fs.writeFileSync(exported, JSON.stringify(collection, null, 2) + '\n');
  }
  const saved = JSON.parse(fs.readFileSync(exported, 'utf8'));
  collectionSchema.validateSync(saved, { abortEarly: false });
  assert.deepEqual(removeUids(saved), removeUids(collection), 'Export differs from native requests or environment template');
  assert.equal(saved.environments[0].variables.find(variable => variable.name === 'accessToken').value, '');
  fs.mkdirSync(path.join(root, '.local'), { recursive: true });
  const roundtrip = fs.mkdtempSync(path.join(root, '.local', 'roundtrip-'));
  await createCollectionFromBrunoObject(saved, roundtrip, { format: 'bru' });
  fs.copyFileSync(path.join(source, 'environments/local.example.bru'), path.join(roundtrip, 'environments/local.example.bru'));
  assert.deepEqual(removeUids(items(roundtrip)), removeUids(collection.items), 'Reimport changed requests, scripts, or assertions');
  const importedEnvironment = parseEnvironment(fs.readFileSync(path.join(roundtrip, 'environments/local.bru'), 'utf8'), bru);
  assert.deepEqual(removeUids(importedEnvironment.variables), removeUids(environment.variables));
  const count = collection.items.reduce((total, folder) => total + folder.items.length, 0);
  const record = { requests: count, folders: collection.items.length, schemaValidated: true, requestsScriptsAssertionsAndVariablesPreserved: true, generatedTokensExcluded: true, method: 'Bruno 4.2.1 filestore parser, collection schema, and CLI collection importer', reimportPath: roundtrip };
  const executionReport = path.join(root, 'reports/reimport-results.json');
  if (fs.existsSync(executionReport)) {
    const nativeResults = JSON.parse(fs.readFileSync(path.join(root, 'reports/audit-results.json'), 'utf8'));
    const importedResults = JSON.parse(fs.readFileSync(executionReport, 'utf8'));
    const comparable = report => report.results.map(result => ({ scenario: result.scenario, name: result.name, status: result.status, tests: result.tests.map(test => ({ description: test.description, status: test.status })), assertions: result.assertions }));
    assert.deepEqual(comparable(importedResults), comparable(nativeResults), 'Native and reimported execution results differ');
    record.archivedReimportExecution = { requests: importedResults.requests, checks: importedResults.checks, passed: importedResults.passed, failed: importedResults.failed, matchesNative: true };
  }
  fs.writeFileSync(path.join(root, '.local/roundtrip-path.txt'), roundtrip);
  fs.mkdirSync(path.join(root, 'reports'), { recursive: true });
  const { reimportPath, ...publicRecord } = record;
  fs.writeFileSync(path.join(root, 'reports/export-verification.json'), JSON.stringify(publicRecord, null, 2) + '\n');
  console.log(`Verified ${count} requests in ${collection.items.length} folders; scripts, assertions, and variables preserved.`);
  console.log(`Reimported collection: ${roundtrip}`);
}

main().catch(error => { console.error(error.errors || error.message); process.exitCode = 1; });
