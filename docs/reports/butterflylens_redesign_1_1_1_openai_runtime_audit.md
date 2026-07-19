# ButterflyLens redesign Task 1.1.1 — runtime analyst dependency audit

Status: complete.

Date: 2026-07-19

Starting and ending ButterflyLens SHA:
`5209ff7f5da564965419870c7a4703b86bafd6a8`.

Objective: audit runtime Bounded model analyst surface and identify shared contracts so
only runtime analyst behavior can be removed in later subtasks.

## Current evidence from local implementation

### 1) Web application runtime surface

The following files are active in the submitted runtime bundle:

- `apps/web/src/App.tsx`
  - Imports and renders `AskButterflyLens`.
  - Keeps the analyst section in the primary shell flow.
- `apps/web/src/main.tsx`
  - Imports `./analyst/askButterflyLens.css`.
- `apps/web/src/shell/PublicShell.tsx`
  - Includes `Ask ButterflyLens` in `primaryNavigation`.
- `apps/web/src/analyst/AskButterflyLens.tsx`
  - Composer + stored/live analyst UI, including replay and trace reveal.
- `apps/web/src/analyst/analystModel.ts`
  - Client request shape, endpoint binding to `/functions/v1/ask-butterflylens`,
    and replay/model schema validation.
- `apps/web/src/analyst/askButterflyLens.css`
  - Styles dedicated to analyst experience.
- `apps/web/src/analyst/AskButterflyLens.test.tsx`
  - UI coverage for the runtime analyst section.
- `apps/web/src/analyst/analystModel.test.ts`
  - Browser contract tests for analyst client models.
- `apps/web/src/communityJourney.e2e.test.tsx`
  - Journey step invoking and asserting analyst replay.

### 2) Supabase runtime surface

- `supabase/functions/ask-butterflylens/index.ts`
  - Authenticated Edge Function wrapper using `@supabase/server` and `openai`.
- `supabase/functions/_shared/analyst.ts`
  - Analyst request parser, bounded prompt instructions, execution loop, and
    OpenAI Responses request contract.
- `supabase/functions/_shared/edgeBoundary.ts`
  - Analyst-specific request boundary and failure response mapping.
- `supabase/functions/_shared/submittedTools.ts`
  - Tool contracts used by analyst execution path and evaluator scripts.
- `supabase/functions/deno.json`
  - Import map includes `openai` and `openai/responses`.
- `supabase/config.toml`
  - `[functions.ask-butterflylens] verify_jwt = true`.
  - `studio.openai_api_key` is set for local studio tooling.
- `supabase/functions/tests/ask ...` analyst tests (runtime boundary + unit behavior):
  - `supabase/functions/tests/analyst_test.ts`
  - `supabase/functions/tests/edge_boundary_test.ts`
  - `supabase/functions/tests/live_evaluation_runner_test.ts`
- `supabase/functions/tests/submitted_tools_test.ts`
  - Tool result schema assertions that are specific to analyst contracts.

### 3) Runtime dependency files

- `supabase/functions/deno.lock` and `supabase/functions/dependency-licenses.json`
  include `openai` dependency state and license capture.
- `supabase/functions/deno.json` imports `openai/responses`.

## Runtime dependencies retained for non-runtime reasons (shared contracts)

The following are still in use for provenance, tests, and evidence replay, but
must remain available when runtime analyst UI is removed:

- `packages/openai/*.schema.json`
- `packages/openai/*.v1.json`
- `packages/openai/python/*`
- `scripts/build_openai_replay.py`
- `scripts/grade_openai_evaluation.py`
- `scripts/build_openai_evaluations.py`
- `scripts/run_openai_live_evaluation.ts`
- `test_openai_*.py`, `tests/test_openai_replay.py`, `tests/test_openai_evaluations.py`,
  `tests/test_public_shell.py` (contract assertions include analyst references)

These assets are historical/verification-oriented and should not be interpreted as
live product runtime after the removal step.

## Direct conflicts with the redesign objective

- Public analyst navigation remains reachable via fragment.
- Ask ButterflyLens runtime section is still mounted in the page.
- Live Edge Function boundary (`ask-butterflylens`) remains reachable when auth
  is present.
- OpenAI runtime dependency stack still exists in Deno configuration.

## Shared dependency decision for upcoming 1.2/1.3 work

- Preserve as shared provenance/evaluation only:
  - `packages/openai/*`
  - offline OpenAI evaluator scripts and tests that do not require runtime service exposure.
- Remove for runtime product surface:
  - web analyst modules,
  - public navigation entries,
  - `ask-butterflylens` Edge Function endpoint and handler imports,
  - OpenAI client dependency on Deno path,
  - analyst-specific client/e2e tests and local shell assertions.

## Next step

Proceed to 1.2 subtask removals only after this boundary is accepted, starting
with route/navigation and component deletion while keeping historical evidence
artifacts untouched.

