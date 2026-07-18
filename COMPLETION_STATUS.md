# ButterflyLens completion status

ButterflyLens is **not complete or release-ready** at the fixed repository
boundary `7a2c2eba61cd10034096e006cdb04fd5018a2b10`.

The exact audit in
[`provenance/completion_audit.v1.json`](provenance/completion_audit.v1.json)
finds:

- 70 of 100 final criteria satisfied;
- 9 partial;
- 7 blocked by the explicit instruction to leave YOLOE and BioCLIP unfinished;
- 14 blocked on an immutable upstream handoff, public-release rights, live
  infrastructure evidence, or human recording;
- 11 of 46 minimum artifacts present under the requested name;
- 7 present as named equivalents;
- 5 model artifacts explicitly deferred; and
- 23 live or downstream artifacts not yet available.

`satisfied` means the fixed Git tree contains direct implementation or artifact
evidence for the criterion. It does not turn a provider assertion into a human
identification, an image candidate into an occurrence, or a tested service
contract into observed live operation.

## Binding unfinished work

1. BioMiner is still fetching Flickr metadata. ButterflyLens has not copied its
   partial outputs and has not made a Flickr API call. A complete immutable,
   fingerprinted, rights-reviewed handoff is required before Flickr artifacts,
   impact cells, live metrics, or downstream evidence can be admitted.
2. YOLOE and BioCLIP execution remains `unfinished_not_run` by user direction.
   Their routes, full-frame inputs, embeddings, prototypes, scores, persistent
   model workers, and unchanged-embedding proof remain incomplete.
3. The public geographic-impact map remains blocked by missing Flickr/model/
   review impact cells and unresolved ALA public-product rights. Contracts are
   present; the real map and drilldowns are not.
4. GPT-5.6 has a bounded live implementation and deterministic evidence tools,
   but no credentialed live model evaluation is claimed. The public replay is
   deliberately credential-free and labelled `Model not invoked`.
5. Worker heartbeat, restart, append-only live updates, and public inspection
   have tested local contracts, but no live M5 receipt is attached.
6. The 2:48 video packet is ready, but the real-product recording, human
   voiceover, approval, upload, and public URL remain unfinished.

The rebuilt ButterflyLens ALA baseline is authoritative. The GBIF Parquet pack
is a separate complementary evidence lane. Neither GBIF inclusion nor Flickr
search output is treated as human verification or release-ready occurrence
evidence.
