import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import test from 'node:test'

import { resolveDependencyLicense } from './dependency-licenses.mjs'

function fixture(name = 'fixture', version = '1.2.3', license = 'MIT') {
  const root = mkdtempSync(join(tmpdir(), 'butterflylens-license-'))
  const modules = join(root, 'node_modules')
  const installed = join(modules, name)
  mkdirSync(installed, { recursive: true })
  writeFileSync(
    join(installed, 'package.json'),
    JSON.stringify({ name, version, license }),
    'utf8',
  )
  return { root, modules, installed }
}

test('uses the exact installed manifest when npm omits licence metadata', () => {
  const installed = fixture()
  try {
    assert.equal(
      resolveDependencyLicense(
        { name: 'fixture', version: '1.2.3', path: installed.installed },
        installed.modules,
      ),
      'MIT',
    )
  } finally {
    rmSync(installed.root, { recursive: true, force: true })
  }
})

test('rejects an installed manifest whose identity does not match npm output', () => {
  const installed = fixture()
  try {
    assert.throws(
      () =>
        resolveDependencyLicense(
          { name: 'fixture', version: '9.9.9', path: installed.installed },
          installed.modules,
        ),
      /does not match its installed package manifest/,
    )
  } finally {
    rmSync(installed.root, { recursive: true, force: true })
  }
})

test('rejects fallback package paths outside the trusted node_modules tree', () => {
  const installed = fixture()
  const outside = fixture('outside')
  try {
    assert.throws(
      () =>
        resolveDependencyLicense(
          { name: 'outside', version: '1.2.3', path: outside.installed },
          installed.modules,
        ),
      /resolved outside node_modules/,
    )
  } finally {
    rmSync(installed.root, { recursive: true, force: true })
    rmSync(outside.root, { recursive: true, force: true })
  }
})
