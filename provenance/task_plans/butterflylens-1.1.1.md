# Task plan — ButterflyLens 1.1.1

Task ID: `butterflylens-1.1.1`

Objective: inventory all runtime GPT-5.6 analyst dependencies, mark shared
contracts, and record the exact removal boundary before changing runtime behavior.

Starting SHA: `5209ff7f5da564965419870c7a4703b86bafd6a8`

Remote main SHA: `5209ff7f5da564965419870c7a4703b86bafd6a8`

BioMiner SHA: `bfdb4b38646f16062d7fb4a6d0f4b0674c8f01dd`

TaxaLens SHA: `e845dd98493979f37b04dbb6538e0d7b8758ca11`

Relevant agent files read: root `AGENTS.md`; `docs/agents/TOOLS.md`; `docs/agents/GIT_AND_PROVENANCE.md`;
`docs/agents/SCIENCE_AND_DATA.md`; `docs/agents/ARCHITECTURE.md`.

Relevant skill: none required.

GitHits needed: unavailable (user direction); one bounded attempt was recorded.

Valyu needed: none for this task.

Files expected:
- `docs/reports/butterflylens_redesign_1_1_1_openai_runtime_audit.md`
- `provenance/task_reports/butterflylens-1.1.1.md`

Contracts affected:
- Public shell route graph and analyst components
- Supabase Edge Function request boundaries
- OpenAI runtime import/secret surface

Data/rights implications:
- Ensure no runtime model-call path remains in public product.
- Preserve submitted replay assets and Codex development provenance.

Scientific risks:
- Premature removal of shared non-runtime evidence contracts used by offline replay/evaluation.

Security/privacy risks:
- `OPENAI_API_KEY` references in functions and local runtime configuration.

Tests:
- None executed for this subtask (audit-and-report only).

Rollback/recovery:
- This task is documentation-only; no runtime rollback path is needed.
