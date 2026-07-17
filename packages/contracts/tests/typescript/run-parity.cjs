'use strict'

const fs = require('node:fs')
const path = require('node:path')

const [schemaDirectory, fixturePath, compiledRoot] = process.argv.slice(2)
if (!schemaDirectory || !fixturePath || !compiledRoot) {
  throw new Error('usage: run-parity.cjs SCHEMA_DIR FIXTURE_PATH COMPILED_ROOT')
}

const { validateSchema } = require(path.join(
  compiledRoot,
  'tests/typescript/schema-validator.js',
))
const declarations = require(path.join(compiledRoot, 'src/index.js'))

const schemas = Object.fromEntries(
  fs.readdirSync(schemaDirectory)
    .filter((name) => name.endsWith('.schema.json'))
    .map((name) => {
      const value = JSON.parse(fs.readFileSync(path.join(schemaDirectory, name), 'utf8'))
      return [value.$id, value]
    }),
)
const fixtures = JSON.parse(fs.readFileSync(fixturePath, 'utf8'))

for (const vector of fixtures.canonicalization_vectors ?? []) {
  const observed = declarations.canonicalizeJson(vector.value)
  if (observed !== vector.canonical) {
    throw new Error(`canonicalization vector ${vector.case_id} diverged`)
  }
}
for (const vector of fixtures.fingerprint_vectors ?? []) {
  const canonical = declarations.canonicalizeEvidencePreimage(vector.preimage)
  const digest = declarations.semanticFingerprintDigest(vector.preimage)
  if (canonical !== vector.canonical || digest !== vector.digest) {
    throw new Error(`fingerprint vector ${vector.case_id} diverged`)
  }
}
for (const vector of fixtures.fingerprint_validation_vectors ?? []) {
  let valid = true
  let message = ''
  try {
    declarations.validateEvidenceFingerprint(vector.record)
  } catch (error) {
    valid = false
    message = error instanceof Error ? error.message : String(error)
  }
  if (valid !== vector.valid || (vector.error && !message.includes(vector.error))) {
    throw new Error(`fingerprint validation vector ${vector.case_id} diverged: ${message}`)
  }
}
for (const vector of fixtures.lineage_vectors ?? []) {
  const records = vector.nodes.map((preimage) => ({
    schema_version: declarations.EVIDENCE_FINGERPRINT_SCHEMA_VERSION,
    hash_algorithm: declarations.FINGERPRINT_HASH_ALGORITHM,
    canonicalization: declarations.FINGERPRINT_CANONICALIZATION,
    preimage,
    digest: declarations.semanticFingerprintDigest(preimage),
    recorded_at: '2026-07-17T22:10:47Z',
  }))
  const graph = new declarations.EvidenceLineageGraph(records)
  const observed = {
    ancestors: graph.ancestorDigests(vector.target_digest),
    descendants: graph.descendantDigests(vector.root_digest),
    topological: graph.topologicalLineage(vector.target_digest),
  }
  for (const key of Object.keys(observed)) {
    if (JSON.stringify(observed[key]) !== JSON.stringify(vector[key])) {
      throw new Error(`lineage vector ${vector.case_id} ${key} diverged`)
    }
  }
}
for (const vector of fixtures.identity_conflict_vectors ?? []) {
  const shared = 'f'.repeat(64)
  let collision = false
  try {
    declarations.assertSameFingerprintIdentity(
      { digest: shared, preimage: vector.left },
      { digest: shared, preimage: vector.right },
    )
  } catch (error) {
    if (error instanceof declarations.FingerprintCollisionError) collision = true
    else throw error
  }
  if (collision !== vector.collision) {
    throw new Error(`identity conflict vector ${vector.case_id} diverged`)
  }
}

const validById = new Map()
const results = []
for (const fixture of fixtures.valid_documents) {
  const document = expandPlaceholders(fixture.document)
  validById.set(fixture.case_id, document)
  const errors = validateSchema(schemas, fixture.schema_id, document)
  results.push({ case_id: fixture.case_id, valid: errors.length === 0, errors })
}
for (const fixture of fixtures.invalid_cases) {
  const base = validById.get(fixture.base_case_id)
  if (base === undefined) throw new Error(`unknown base case ${fixture.base_case_id}`)
  const document = structuredClone(base)
  for (const change of fixture.changes) applyChange(document, change)
  const errors = validateSchema(schemas, fixture.schema_id, document)
  results.push({ case_id: fixture.case_id, valid: errors.length === 0, errors })
}

const constants = Object.fromEntries(
  Object.entries(declarations).filter(([name, value]) =>
    name.endsWith('_SCHEMA_VERSION') || Array.isArray(value),
  ),
)
process.stdout.write(`${JSON.stringify({ results, constants })}\n`)

function expandPlaceholders(value) {
  if (Array.isArray(value)) return value.map(expandPlaceholders)
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, expandPlaceholders(item)]))
  }
  if (value === '{{sha256}}') return 'a'.repeat(64)
  if (value === '{{sha256_b}}') return 'b'.repeat(64)
  if (value === '{{git_sha}}') return 'c'.repeat(40)
  if (value === '{{now}}') return '2026-07-17T14:43:29Z'
  if (value === '{{later}}') return '2026-07-17T14:48:29Z'
  return value
}

function applyChange(document, change) {
  const parts = change.path.split('/').slice(1).map((part) =>
    part.replaceAll('~1', '/').replaceAll('~0', '~'),
  )
  const key = parts.pop()
  let parent = document
  for (const part of parts) parent = parent[part]
  if (change.op === 'delete') delete parent[key]
  else parent[key] = expandPlaceholders(change.value)
}
