# Task 18.3 plan — rights-screened submitted ALA map

Task ID: `butterflylens-18.3`

Objective: turn the authoritative rebuilt ALA baseline into a deterministic,
offline public-map projection with exact accessible counts and drilldowns,
without exposing precise occurrence coordinates or implying that unavailable
Flickr, model, review, or release evidence is zero.

Starting and remote SHA:
`c7d6efda5a122502383ae66830e7b117259e5de2`.

Source goal SHA-256:
`898dbe5ec3520d1425bf5d0f891c49d6f7615318ed28b35b16f7513684a3fa40`.

BioMiner coordination SHA:
`ae6a18509b7be48da5c6ca69ab0caacf4632cc70`. BioMiner is still fetching only
Flickr metadata. Its mutable work remains untouched and no Flickr API call will
be made in ButterflyLens.

Authoritative data boundary: the rebuilt ButterflyLens ALA baseline remains the
authoritative baseline. The separately fingerprinted GBIF pack remains
complementary and is not merged into this projection.

Rights boundary: the complete ALA baseline remains preserved internally. The
public projection excludes every record from `dr1097`, `dr30019`, and `dr635`,
the three datasets already flagged by the frozen snapshot's conservative
citation-rights screen. This is a fail-closed publication choice, not a legal
conclusion or a resolution of those datasets' rights.

Explicit exclusions: YOLOE and BioCLIP remain `unfinished_not_run` by user
direction. Flickr metadata is an incomplete external work product. Flickr,
YOLOE, BioCLIP, community-review, human-supported, and release-ready values
therefore remain unavailable with reasons rather than fabricated zeroes.

GitHits is unavailable and disabled by direct user instruction. It will not be
called.

Skill used: Headroom, to retain the exact long-form goal and required map
contract while inspecting large local evidence records under receipt
`898dbe5ec3520d1425bf5d0f`.

## Subtask 18.3.1 — build the public map artifacts

- Add a deterministic no-network builder for rights-screened ALA H3 cells,
  national/state/IBRA/LGA/H3 summary scopes, and a compact browser snapshot.
- Emit `geographic_impact_cells.parquet`,
  `geographic_impact_summary.parquet`, and `map_manifest.json` with schemas,
  attribution, exclusions, counts, checksums, and evidence fingerprints.
- Validate each cell against the existing geographic-impact contract and add
  focused regression tests for exact totals, unavailable values, sensitive
  location controls, deterministic rebuilds, and rights exclusions.

Commit: `feat(map): build rights-screened ALA projection`.

## Subtask 18.3.2 — publish the offline Explore view

- Add an offline SVG national heatmap using derived H3 polygons only; make ALA
  blue and keep the unavailable Flickr layer visibly amber and text-labelled.
- Add state, IBRA, LGA statistical-approximation, and H3 drilldowns with an
  exact synchronized table and fingerprint-bound evidence details.
- Preserve keyboard, no-WebGL, forced-colour, reduced-motion, and no-network
  behavior with component and route tests.

Commit: `feat(web): add accessible submitted evidence map`.

## Subtask 18.3.3 — verify and publish the task

- Run focused and repository-level tests, web typecheck/build, rights,
  licensing, security, JSON, Python compilation, and whitespace gates.
- Record model usage, task provenance, commit receipts, and the exact remaining
  Flickr/model/live blockers.
- Commit the report and receipts, then push `main` once for Task 18.3 without
  force.

Commit: `docs(provenance): close submitted ALA map task`.
