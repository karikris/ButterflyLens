# Task plan — ButterflyLens 12.1 Pages licence fix

Task ID: `butterflylens-12.1-pages-license-fix`

Objective: repair the fresh-runner dependency-licence failure in GitHub Actions
run `29637404587` without weakening the allowlist or trusting registry metadata.

Starting and remote SHA:
`e89c21f31e5a514dd199892c13aed99c9fb2cb9d`.

Observed failure: npm's long dependency tree returned `license: null` for the
locked `react@19.2.7` package even though its exact installed package manifest
declares MIT. The build stopped before Pages configuration or upload.

Approach: retain npm's reported licence when present. When it is absent, resolve
the real installed directory, prove that directory remains below the trusted
`node_modules` root, load its package manifest, require the exact npm-reported
name and version, and only then apply the unchanged licence allowlist. Add Node
regressions for the valid fallback, an identity mismatch, and an out-of-root
path. Keep Vitest and the Node filesystem tests as distinct test runners.

Tests: 14-file Vitest suite, standalone Node tests, dependency licence check
under the repository npm and the current npm CLI, Pages-base production build,
Python licence verifier, JSON/JSONL, whitespace, and staged secret/scope checks.

Rollback: revert this isolated fix commit. The previous behavior fails closed,
so rollback cannot accidentally approve a dependency; it only restores the
fresh-runner false negative.
