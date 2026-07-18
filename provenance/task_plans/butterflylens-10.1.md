# Task plan — ButterflyLens 10.1

Task ID: `butterflylens-10.1`

Objective: create a reusable public visual system that is photographic,
distinctly Australian, scientific-editorial, optimistic but
evidence-disciplined, responsive at 1280×720 and mobile, and accessible without
generic gradients or an admin-template appearance.

Competition criterion improved: a coherent public identity whose evidence
semantics and accessibility boundaries are reusable and machine-inspectable.

Starting and remote SHA: `11d8d3e232d2fa96eae6cc44c5a2f5cd615ce83b`.

BioMiner: visual-system work does not overlap the active GBIF fingerprinted
evidence database, so its record and data are not inspected or copied.

TaxaLens immutable source inspected:
`c5e87ead4fdb26d5c5624bbb8d8d67e46d8eddbc`. Literal/semantic token
separation, evidence markers, accessibility foundations, and primitive tests
were inspected; no name, value, source, style, component, or test was copied.

Relevant agent files read: root `AGENTS.md`; `docs/agents/TOOLS.md`,
`GIT_AND_PROVENANCE.md`, `ARCHITECTURE.md`, `SCIENCE_AND_DATA.md`,
`TESTING_AND_RELEASE.md`, and `TASK_TEMPLATE.md`.

Relevant skill: none. Image generation is intentionally not used because this
is a code-native system and the current rights-cleared photograph must remain
pixel-unaltered.

GitHits needed: yes. It remains unavailable and is not retried. Local and
immutable repository inspection plus current official primary websites are the
fallback.

Valyu needed: yes for current design/accessibility evidence. It remains
unavailable; official iNaturalist, ALA, ALA Lens, and W3C sources are used.

Expected files: visual-system foundations, primitives, JSON contract,
component and parity tests, current-surface adaptations, theme metadata, human
decision record, migration provenance, tool logs, and task report.

Contracts affected: a web-local `butterflylens-visual-system:v1.0.0` contract.
Scientific, database, API, and cross-language evidence contracts are unchanged.

Data/rights implications: the existing rights-cleared image remains the only
photographic asset and its pixels and fingerprint are unchanged; no new media or
provider payload is added.

Scientific risks: modifying evidence pixels; communicating availability by
colour alone; making unavailable evidence appear complete; or allowing visual
optimism to soften release blockers.

Security/privacy risks: remote fonts or assets, browser-bundled private data, or
new third-party runtime dependencies.

Tests: primitive semantics, visual contract, exact palette parity, WCAG contrast,
theme colour, focus, forced colours, reduced motion, target size, reflow and
breakpoints, no gradient/filter rule, full Python and web suites, production
build, rights/licensing, dependency audit, provenance, staged safety, and
whitespace.

Rollback/recovery: foundations and primitives are imported before page styles;
the visual-system files and small component adaptations can be reverted without
changing data, reviews, quality evidence, or database state.
