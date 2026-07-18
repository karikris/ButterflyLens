# Task plan — ButterflyLens 10.2

Task ID: `butterflylens-10.2`

Objective: build the responsive public application shell with this exact main
navigation: Explore, Verify, Species, Live, Quality, Contributors, Ask
ButterflyLens, and About.

Competition criterion improved: a coherent credential-free public journey with
clear implemented, submitted, and scheduled boundaries.

Starting and remote SHA:
`38f4d36369a46352373b2c29c1834fce996a4e2d`.

BioMiner: the application shell does not overlap the active GBIF fingerprinted
evidence-database build, so its record and data are not inspected or copied.

TaxaLens immutable source inspected:
`c5e87ead4fdb26d5c5624bbb8d8d67e46d8eddbc`. Single primary navigation,
focusable current-view target, honest static state, keyboard tests, and narrow
viewport precedent were inspected. No route, label, code, style, test, or data
was copied.

Relevant agent files read: root `AGENTS.md`; `docs/agents/TOOLS.md`,
`GIT_AND_PROVENANCE.md`, `ARCHITECTURE.md`, `SCIENCE_AND_DATA.md`,
`TESTING_AND_RELEASE.md`, and `TASK_TEMPLATE.md`.

Relevant skill: none. This is a code-native shell task.

GitHits needed: yes for shell precedent. It remains unavailable and is not
retried; local and immutable repository inspection is the fallback.

Valyu needed: no. The user supplied the exact navigation, and the current local
visual contract already contains verified W3C-derived accessibility boundaries.

Expected files: public shell component and stylesheet, application composition,
section landmarks, component/static tests, human decision record, migration
manifest, tool/model logs, prior-task commit receipt, and task report.

Contracts affected: the public in-document navigation and landmark contract;
scientific, database, API, and cross-language evidence contracts are unchanged.

Data/rights implications: no new provider data, media, remote asset, or public
record is introduced. The existing review image remains unchanged.

Scientific risks: dead links; presenting scheduled surfaces as complete;
softening candidate/release boundaries; or turning worker state into scientific
authority.

Security/privacy risks: remote navigation dependencies, external requests,
browser-bundled private data, or duplicated mobile landmarks.

Tests: exact navigation order and destinations, one semantic navigation,
landmarks and focusable skip target, one H1, scheduled-state count, 44-pixel
targets, mobile-contained reflow, forced-colour current state, full Python/web
suites, typecheck/build, contract parity, rights/licensing, dependency audit,
provenance, staged safety, and whitespace.

Rollback/recovery: the shell composes existing review and quality components;
its component, stylesheet, and small section-ID adaptations can be reverted
without modifying evidence, reviews, quality data, or database state.
