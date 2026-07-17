# Flickr query planner

The query compiler transforms versioned local name assertions into discovery
terms. It does not call Flickr. Every output retains the exact assertion,
accepted taxon key, trust tier, source, language, region, eligibility reason,
and query tier. `term_semantics` always states that the term is for discovery
only and is not a taxonomic or image label.

Tier assignment is closed: species names are tier 1, genera tier 2, families
tier 3, and order/superfamily terms tier 4. The global out-of-range lane owns
tier 5 in a later subtask. Unsupported intermediate ranks do not silently fall
into a broader tier.

The compiler rejects ineligible, weak, homonymous, malformed, or untrusted
assertions. First Nations language terms require a separate authorized,
community-scoped, query-permitted decision adapter. The current authoritative
pack contains zero such approvals, so none compile.

Logical query definitions remain one-per-source assertion at this layer.
Physical request deduplication is a separate step and may never discard those
logical associations.

The logical/physical planner makes that boundary explicit. A logical
association binds a query definition to one taxon, relationship, lane, and
reason while fixing `query_term_is_taxon_label` to false. A separate physical
request identity hashes only the provider, method, endpoint, and normalized
non-secret parameters. Identical request semantics therefore produce one
planned request, while a link artifact retains every logical association that
led to it. Neither a physical request nor a link is evidence that the request
was sent or that a returned photo depicts the associated taxon.

The planner rejects credentials, authentication material, ambiguous parameter
names, tampered logical associations, and missing definitions. It emits
`planned_not_sent` requests only; budget reservation and provider execution
remain later, separately audited steps.

## Australia-known lane

The `australia_known` lane is derived only from the rebuilt authoritative
Australian taxonomy/name pack. Tier 1 species terms link to their accepted
species. Tier 2 genus, tier 3 family, and tier 4 superfamily terms expand
through the frozen authoritative parent paths to one explicit logical
association per descendant accepted species. Physical requests then deduplicate
those associations losslessly.

"Australia-known" describes taxon scope, not photo geography. The lane does
not add an Australian location filter, does not establish that a discovered
photo was taken in Australia, and does not permit absence inference. Every
request remains `planned_not_sent` until a later budgeted execution task.

## Global out-of-range lane

Tier 5 accepts only species-rank accepted scientific names from an admitted,
fingerprinted global authority snapshot. Every source assertion must state
authoritative trust, no detected homonym risk, query eligibility, and a
checksum-bound comparison showing that the species is not in the current
authoritative Australian checklist. A collision with any accepted Australian
species name or synonym fails the lane rather than treating an incomplete
crosswalk as range evidence.

"Not currently known from Australia" is a checklist-comparison state, not a
claim of biological absence, endemism elsewhere, or photo location. Weak,
homonymous, ambiguous, stale-comparison, and non-species rows do not enter the
lane. The current real-data lane is blocked pending BioMiner's live
current-policy GBIF fingerprint database and quality evidence; fixtures only
exercise the admission contract, and no Flickr request is made.

## Eligibility and homonym boundary

An assertion cannot become query-eligible merely by setting a boolean. The
compiler independently requires canonical NFKC/casefold/whitespace
normalization, a non-pending eligibility reason, no detected homonym risk, a
name-type-appropriate trust tier and language, and an identified source
provider. Batch compilation rejects a normalized term assigned to multiple
taxa even if every individual row claims eligibility. The global lane applies
the same cross-row homonym gate after its tier-5 checks.

Single-token vernaculars, cross-taxon collisions, weak or mismatched trust,
contradictory eligibility reasons, unsupported ranks, unauthorized First
Nations terms, and stale range comparisons all fail closed. These are query
eligibility decisions only; passing them does not label a photo or verify a
taxon occurrence.

## Australian geo/time partitioning

Australian discovery seeds one bounding-box envelope for each of the nine ABS
ASGS Edition 3 state/territory codes inside the official national extent. The
envelopes are derived from the 2021 GDA2020 boundary geometry and are not
polygons: they may overlap, include water, and do not prove state membership.
Result records must therefore still be deduplicated and geographically
validated downstream.

Each geo partition fixes `has_geo=1`, the non-deprecated `content_types=0`
photo filter, and exactly 250 results per page. A count checkpoint at 4,000 or
more is never paged as complete. It bisects its inclusive upload-time interval
without gaps; if a one-second interval still saturates, it bisects the longest
bbox axis. Physical parameter fingerprints reject duplicate partitions.

Below 4,000 results, the planner creates an exact page inventory with explicit
page numbers and null cursors. Completion requires every expected page once,
stable observed totals, response fingerprints, no page over 250 rows, and
returned row counts reconciling to the count checkpoint. Planning and
checkpoint functions make no Flickr request.
