# ButterflyLens shared contracts

This package is the cross-service contract boundary for ButterflyLens. JSON
Schema Draft 2020-12 is the wire authority. TypeScript and Python declarations
mirror the same field names and version constants; parity fixtures and runtime
checks are added in Task 1.3.6.

## Rules

- Contract records are JSON objects with an exact `schema_version`.
- Unknown properties and unknown schema versions fail closed.
- IDs are opaque stable identifiers. A display label is never an identifier.
- SHA-256 values are lowercase hexadecimal and are not interchangeable with
  semantic evidence fingerprints unless the field says so.
- Timestamps are RFC 3339 date-times in UTC at production boundaries.
- `null`, zero, unavailable, withheld, and not applicable are different states.
- A run describes work and artifacts; it never upgrades candidate, review, or
  release maturity by itself.
- Browser code consumes admitted API projections. It does not execute BioMiner
  commands or accept provider and worker secrets.

## Layout

| Path | Role |
| --- | --- |
| `schemas/` | JSON Schema Draft 2020-12 wire contracts |
| `src/` | TypeScript declarations and version constants |
| `python/butterflylens/contracts/` | Python `butterflylens.contracts` declarations |

Schema identifiers are versioned URNs. A later version is a new contract, not
an in-place reinterpretation of stored evidence.
