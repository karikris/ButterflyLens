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
