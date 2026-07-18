import { execFileSync } from 'node:child_process'
import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const packageJson = JSON.parse(readFileSync(resolve(root, 'package.json'), 'utf8'))
const reportPath = resolve(root, 'dependency-licenses.json')
const allowedLicenses = new Set([
  'Apache-2.0',
  'BSD-2-Clause',
  'BSD-3-Clause',
  'BlueOak-1.0.0',
  'CC0-1.0',
  'ISC',
  'MIT',
  'MIT-0',
  'MPL-2.0',
])

function dependencyTree() {
  return JSON.parse(
    execFileSync('npm', ['ls', '--all', '--json', '--long'], {
      cwd: root,
      encoding: 'utf8',
      maxBuffer: 50_000_000,
    }),
  )
}

function collectPackages() {
  const tree = dependencyTree()
  const records = new Map()
  const productionDirect = new Set(Object.keys(packageJson.dependencies ?? {}))
  const developmentDirect = new Set(Object.keys(packageJson.devDependencies ?? {}))

  function visit(node, scope, direct = false) {
    if (node === null || typeof node !== 'object' || typeof node.name !== 'string') {
      return
    }
    const key = `${node.name}@${node.version}`
    const license = typeof node.license === 'string' ? node.license : null
    if (license === null || !allowedLicenses.has(license)) {
      throw new Error(`${key} has unapproved or missing licence: ${String(license)}`)
    }
    const current = records.get(key) ?? {
      name: node.name,
      version: node.version,
      license,
      direct,
      scopes: new Set(),
    }
    current.direct ||= direct
    current.scopes.add(scope)
    records.set(key, current)
    for (const child of Object.values(node.dependencies ?? {})) {
      visit(child, scope)
    }
  }

  for (const name of [...productionDirect].sort()) {
    visit(tree.dependencies?.[name], 'production', true)
  }
  for (const name of [...developmentDirect].sort()) {
    visit(tree.dependencies?.[name], 'development', true)
  }

  return [...records.values()]
    .map((record) => ({
      name: record.name,
      version: record.version,
      license: record.license,
      direct: record.direct,
      scopes: [...record.scopes].sort(),
    }))
    .sort((left, right) =>
      `${left.name}@${left.version}`.localeCompare(`${right.name}@${right.version}`),
    )
}

function comparable(report) {
  return JSON.stringify({
    schema_version: report.schema_version,
    lockfile: report.lockfile,
    allowed_licenses: report.allowed_licenses,
    packages: report.packages,
  })
}

const packages = collectPackages()
const report = {
  schema_version: 'butterflylens-npm-dependency-licenses/v1',
  generated_at: new Date().toISOString(),
  lockfile: 'package-lock.json',
  allowed_licenses: [...allowedLicenses].sort(),
  packages,
}

if (process.argv.includes('--generate')) {
  writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8')
  console.log(`dependency licence report generated (${packages.length} packages)`)
} else if (process.argv.includes('--check')) {
  const expected = JSON.parse(readFileSync(reportPath, 'utf8'))
  if (comparable(expected) !== comparable(report)) {
    throw new Error('dependency licence report is stale; run npm run licenses:generate')
  }
  console.log(`dependency licence report verified (${packages.length} packages)`)
} else {
  throw new Error('use --generate or --check')
}
