# Task plan — ButterflyLens 1.2.1

Task ID: `butterflylens-1.2.1`

Objective: remove the public Ask ButterflyLens navigation entry and runtime mount
point without touching shared provenance/evaluation assets.

Starting SHA: `3163e777686fbeba3a63e7c96da8a117aef50400`

Remote main SHA: `3163e777686fbeba3a63e7c96da8a117aef50400`

BioMiner SHA: `bfdb4b38646f16062d7fb4a6d0f4b0674c8f01dd`

TaxaLens SHA: `e845dd98493979f37b04dbb6538e0d7b8758ca11`

Relevant agent files read: root `AGENTS.md`; `docs/agents/TOOLS.md`;
`docs/agents/GIT_AND_PROVENANCE.md`; `docs/agents/SCIENCE_AND_DATA.md`.

Relevant skill: none required.

GitHits needed: unavailable (user-directed); no query executed.

Valyu needed: none for this task.

Files expected:
- `apps/web/src/main.tsx`
- `apps/web/src/App.tsx`
- `apps/web/src/shell/PublicShell.tsx`

Contracts affected:
- Public shell navigation ordering
- Primary rendered runtime route flow

Scientific risks:
- Preserving the analyst fragment in a hidden route could imply a hidden runtime
  general-purpose interface despite no nav link.

Security/privacy risks:
- Any remaining runtime ask analyst UI would keep accidental access points for model calls.
