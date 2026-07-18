# Task plan — ButterflyLens 10.6

Task ID: `butterflylens-10.6`

Objective: add an evidence-derived, consent-conscious contributor experience
that celebrates reviewed images, resolved conflicts, species and regions
helped, control coverage, and verified expert contribution without speed
rankings or scientific-authority claims.

Starting and remote SHA:
`2f83ce9b7df6cc1f8bc90946c1e6bb6fe55cb87d`.

BioMiner overlap: none. BioMiner remains dirty and active with no completed
Flickr or GBIF handoff. Its current-state ledger was inspected; no partial
output, log, configuration, credential, or runtime artifact is read or copied.
BioCLIP work visible there is explicitly skipped for this ButterflyLens goal.

GitHits: disabled for the remainder of the goal by explicit user instruction;
no call is made.

Expected files: deterministic Python contribution compiler, private-by-default
append-only Supabase snapshot and self-only projection, pgTAP/static database
tests, strict submitted web projection, contributor component and responsive
styles, component/model tests, visual-system coverage, provenance ledgers, and
task report.

Counting contract: count unique effective review media; unique append-only
adjudicated conflicts; distinct accepted species and public/generalised region
identifiers carried by governed event enrichment; distinct governed control
fingerprints; and effective review/adjudication events made under a verified
expert/curator role. Unavailable evidence remains null, not zero.

Privacy and dignity controls: self-only authenticated RLS, no anonymous/public
profile projection, no leaderboard, no comparison between people, no duration
or throughput field, no control identities or expected answers, no Auth IDs,
and no reviewer-reliability weight. Recognition never changes review,
consensus, expert-gate, quality, or release authority.

Database controls: explicit grants, RLS, active-profile/project-membership
validation, append-only snapshots, security-invoker latest-self view, indexed
foreign keys and latest-snapshot access, service-only writes, and no
security-definer function.

Tests: compiler counting/deduplication/expert-state/fingerprint/order/failure
contracts; strict browser parsing and unavailable-state handling; all six
celebration categories; absence of ranking/speed language and fields; SQL RLS,
grants, indexes, immutability and view boundaries; pgTAP plan parity; full
Python/web suites, build, rights/licensing, dependency audit, provenance,
staged safety, and whitespace.

Rollback: remove the contributor compiler, snapshot migration/view, web
surface, tests, and provenance for this task. No live database migration,
identity, contribution row, provider record, or media is introduced.
