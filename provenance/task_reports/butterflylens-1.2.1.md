# ButterflyLens Task 1.2.1 — remove navigation and route

Status: complete.

Starting SHA: `3163e777686fbeba3a63e7c96da8a117aef50400`

Ending SHA: `2e24db4c86a0951684af82b97b5de6b56a224758`

Remote SHA: `2e24db4c86a0951684af82b97b5de6b56a224758`

Task ID: `butterflylens-1.2.1`

Primary model: `bounded-model`

Reasoning effort: `xhigh`

Codex session: not started in this environment session

Files changed:
- `apps/web/src/main.tsx`
- `apps/web/src/App.tsx`
- `apps/web/src/shell/PublicShell.tsx`
- `provenance/task_plans/butterflylens-1.2.1.md`

Tests run:
- not run by request for this subtask

Task result:
- removed Ask ButterflyLens from `primaryNavigation`
- removed `AskButterflyLens` import and render from `App`
- removed analyst CSS import from web entrypoint

Known follow-up:
- remove analyst component/tests and Supabase runtime in upcoming subtasks 1.2.2 and 1.3.x
