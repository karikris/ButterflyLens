# ButterflyLens Task 1.2.2 — remove analyst React components

Status: complete.

Starting SHA: `2f7d43b0d3fbe5bf7f991d0985e73dc1f08fcfbd`

Ending SHA: `TBD`

Remote SHA: `TBD`

Task ID: `butterflylens-1.2.2`

Primary model: `gpt-5.6-sol`

Reasoning effort: `xhigh`

Files changed:
- deleted `apps/web/src/analyst/AskButterflyLens.tsx`
- deleted `apps/web/src/analyst/analystModel.ts`
- deleted `apps/web/src/analyst/askButterflyLens.css`
- deleted `apps/web/src/analyst/AskButterflyLens.test.tsx`
- deleted `apps/web/src/analyst/analystModel.test.ts`
- removed empty `apps/web/src/analyst/` directory
- updated web/runtime tests and capture baseline config to remove now-missing
  `Ask ButterflyLens` route assertions:
  - `apps/web/src/communityJourney.e2e.test.tsx`
  - `apps/web/src/shell/PublicShell.test.tsx`
  - `apps/web/e2e/public-experience.browser.spec.ts`
  - `apps/web/scripts/capture-redesign-baseline.mjs`
- updated public-shell contract test assertions to remove deleted `analyst` file and
  navigation anchor in `tests/test_public_shell.py`
- `provenance/task_plans/butterflylens-1.2.2.md`

Task result:
- the submitted web runtime no longer contains analyst UI source modules
- no analyst component is now importable from the main bundle
- shared OpenAI artifacts remain untouched in `packages/openai` and `scripts`
