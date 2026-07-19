# Task plan — ButterflyLens 1.2.2

Task ID: `butterflylens-1.2.2`

Objective: remove React analyst components and frontend analyst runtime tests from
the submitted experience.

Starting SHA: `2f7d43b0d3fbe5bf7f991d0985e73dc1f08fcfbd`

Remote main SHA: `2f7d43b0d3fbe5bf7f991d0985e73dc1f08fcfbd`

BioMiner SHA: `bfdb4b38646f16062d7fb4a6d0f4b0674c8f01dd`

TaxaLens SHA: `e845dd98493979f37b04dbb6538e0d7b8758ca11`

Relevant agent files read: root `AGENTS.md`; `docs/agents/GIT_AND_PROVENANCE.md`;
`docs/agents/TOOLS.md`; `docs/agents/SCIENCE_AND_DATA.md` not needed for this
frontend removal step.

Relevant skill: none required.

GitHits needed: unavailable (user-directed).

Valyu needed: none for this subtask.

Files expected:
- delete `apps/web/src/analyst/AskButterflyLens.tsx`
- delete `apps/web/src/analyst/analystModel.ts`
- delete `apps/web/src/analyst/askButterflyLens.css`
- delete `apps/web/src/analyst/AskButterflyLens.test.tsx`
- delete `apps/web/src/analyst/analystModel.test.ts`
- delete `apps/web/src/analyst/` if empty
- remove runtime analyst assertions from web tests and captures that referenced
  the removed section

Contracts affected:
- public runtime bundle no longer includes analyst browser component/module surface

Roll-forward notes:
- keep shared OpenAI artifacts in `packages/openai/*` and evaluator scripts.
