# Task plan — ButterflyLens 10.4

Task ID: `butterflylens-10.4`

Objective: add a live M5 pipeline page showing API budget, calls, queries,
metadata, unique images, model progress, review backlog, worker heartbeat, and
last committed artifact.

Starting and remote SHA:
`f053c27d877fba07df841e2825618d9f705b2333`.

Overlap decision: **deferred before implementation**. The user reports an active
parallel Flickr fetch with 50,000 unique images and an estimated 20 hours
remaining. BioMiner's current record and dirty worktree confirm active local
work and prohibit duplicate jobs or overlapping file access.

No Flickr API call, BioMiner output read/copy, UI implementation, provenance
claim, commit, or push is permitted for this task until the running work
publishes a completed fingerprinted handoff. The existing Live surface remains
explicitly scheduled.

Next safe task: Task 10.5, enforce Flickr public-display terms without provider
traffic or partial-run data.
