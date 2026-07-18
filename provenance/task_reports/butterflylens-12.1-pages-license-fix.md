# ButterflyLens 12.1 — Pages licence portability fix

Status: **implemented and locally verified; remote rerun pending this commit**.

Starting SHA:
`e89c21f31e5a514dd199892c13aed99c9fb2cb9d`.

## Outcome

GitHub Actions run `29637404587` failed in the build job before Pages setup.
The exact error was an absent npm-tree licence field for locked
`react@19.2.7`; no deployment step ran.

The dependency audit now falls back to the exact installed package manifest
only when npm omits the field. It resolves both roots through the filesystem,
rejects paths outside the trusted `node_modules` tree, requires the manifest
name and version to match npm's dependency identity, and applies the same
closed licence allowlist. It does not infer a licence from a package name,
registry page, lockfile URL, or dependency neighbour.

The standalone Node test filename no longer matches Vitest discovery. The
normal `npm test` command consequently runs 14 Vitest files with 67 tests, then
three Node tests covering the successful manifest fallback and both fail-closed
guards.

## Verification

- 14 Vitest files and 67 tests passed.
- All three standalone Node licence tests passed.
- The normal build and `/ButterflyLens/` production build passed with 116
  dependency records and the unchanged bundle-size warning.
- The licence check passed through local npm 9.2.0, npm 10.9.4 dependency-tree
  inspection, and current npm 12.0.1. npm 12 correctly warned that Node
  22.22.1 is just below its supported patch floor, but the check itself passed.

No dependency, lockfile, allowlisted licence, application behavior, provider
data, Supabase state, B2 state, or Flickr state changed.
