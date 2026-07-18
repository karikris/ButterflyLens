begin;

create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(40);

select has_table('public', 'reviewer_profiles', 'reviewer profiles table exists');
select has_table('public', 'verification_campaigns', 'campaigns table exists');
select has_table('public', 'assignments', 'assignments table exists');
select has_table('public', 'review_events', 'review events table exists');
select has_table('public', 'consensus', 'consensus table exists');
select has_table('public', 'reviewer_reliability', 'reliability table exists');
select has_table('public', 'quality_snapshots', 'quality snapshots table exists');

select ok((select relrowsecurity from pg_class where oid = 'public.reviewer_profiles'::regclass), 'profiles have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.verification_campaigns'::regclass), 'campaigns have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.assignments'::regclass), 'assignments have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.review_events'::regclass), 'events have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.consensus'::regclass), 'consensus has RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.reviewer_reliability'::regclass), 'reliability has RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.quality_snapshots'::regclass), 'quality has RLS');

select has_index('public', 'reviewer_profiles', 'reviewer_profiles_auth_user_key', 'profile auth FK is indexed');
select has_index('public', 'verification_campaigns', 'verification_campaigns_project_pk_idx', 'campaign project FK is indexed');
select has_index('public', 'assignments', 'assignments_reviewer_profile_pk_idx', 'assignment reviewer FK is indexed');
select has_index('public', 'review_events', 'review_events_assignment_pk_idx', 'event assignment FK is indexed');
select has_index('public', 'consensus', 'consensus_campaign_pk_idx', 'consensus campaign FK is indexed');
select has_index('public', 'reviewer_reliability', 'reviewer_reliability_reviewer_pk_idx', 'reliability reviewer FK is indexed');
select has_index('public', 'quality_snapshots', 'quality_snapshots_run_pk_idx', 'quality run FK is indexed');
select ok(not has_table_privilege('anon', 'public.review_events', 'select'), 'anon cannot read review evidence');
select ok(not has_table_privilege('authenticated', 'public.reviewer_reliability', 'select'), 'reviewer reliability remains private');
select ok(not has_table_privilege('service_role', 'public.review_events', 'update'), 'review events are append-only');

insert into auth.users (id) values ('00000000-0000-4000-8000-000000000001');
insert into public.projects (
  project_id, slug, name, boundary_id, boundary_version, boundary_sha256,
  sensitive_coordinate_policy_version, root_taxon_keys, taxonomy_fingerprint,
  search_plan_fingerprint, public_discovery_claim, data_policy_version,
  consent_policy_version
) values (
  'project:review-test', 'review-test', 'Review test', 'boundary:australia',
  'v1', repeat('a', 64), 'v1', array['bltx:v1:test'], repeat('b', 64),
  repeat('c', 64),
  'All butterfly candidate images discoverable through the published ButterflyLens Flickr search plan.',
  'v1', 'v1'
);
insert into public.runs (
  run_id, project_pk, run_kind, mode, status, requested_actor_type,
  engine_repository, engine_commit, engine_interface_version, engine_command
) select 'run:review-test', id, 'quality_snapshot', 'replay', 'queued', 'system',
  'karikris/ButterflyLens', repeat('d', 40), 'v1', 'synthetic test'
from public.projects where project_id = 'project:review-test';
insert into public.media_objects (
  media_object_id, project_pk, run_pk, source_kind, object_kind,
  storage_backend, storage_key, media_state, content_sha256, byte_count,
  media_type, decode_status, rights_fingerprint, rights_status,
  media_fingerprint, committed_at
) select 'media:review-test', p.id, r.id, 'reference', 'private_review_image',
  'b2', 'private/review/test.jpg', 'committed', repeat('e', 64), 100,
  'image/jpeg', 'valid', repeat('f', 64), 'allowed', repeat('1', 64), now()
from public.projects p join public.runs r on r.project_pk = p.id
where p.project_id = 'project:review-test';
insert into public.reviewer_profiles (
  reviewer_profile_id, auth_user_id, public_name
) values ('reviewer:test', '00000000-0000-4000-8000-000000000001', 'Butterfly Friend');
insert into public.project_memberships (
  project_membership_id, project_pk, reviewer_profile_pk, auth_user_id,
  role, status, enrollment_kind
) select 'membership:review-test', project.id, profile.id, profile.auth_user_id,
  'reviewer', 'active', 'self_service'
from public.projects project cross join public.reviewer_profiles profile
where project.project_id = 'project:review-test'
  and profile.reviewer_profile_id = 'reviewer:test';
insert into public.verification_campaigns (
  verification_campaign_id, project_pk, campaign_kind, name, question,
  status, target_review_count, campaign_fingerprint, opens_at
) select 'campaign:test', id, 'ordinary_image', 'Synthetic campaign',
  'Is this a butterfly?', 'open', 2, repeat('2', 64), now()
from public.projects where project_id = 'project:review-test';
insert into public.assignments (
  assignment_id, verification_campaign_pk, media_object_pk,
  reviewer_profile_pk, assignment_sequence, status,
  blind_payload_fingerprint, assignment_fingerprint, responded_at
) select 'assignment:test', c.id, m.id, r.id, 1, 'responded',
  repeat('3', 64), repeat('4', 64), now()
from public.verification_campaigns c
cross join public.media_objects m cross join public.reviewer_profiles r
where c.verification_campaign_id = 'campaign:test'
  and m.media_object_id = 'media:review-test' and r.reviewer_profile_id = 'reviewer:test';
insert into public.review_events (
  review_event_id, assignment_pk, verification_campaign_pk, media_object_pk,
  reviewer_profile_pk, question, image_sha256, decision, confidence,
  decided_at, duration_ms, source_version, model_version, review_context,
  event_fingerprint
) select 'review-event:test', a.id, a.verification_campaign_pk, a.media_object_pk,
  a.reviewer_profile_pk, 'Is this a butterfly?', repeat('e', 64), 'yes', 4,
  now(), 1500, 'review-source:v1', 'unavailable:test', jsonb_build_object(
    'blind_payload_fingerprint', repeat('3', 64),
    'assignment_policy_version', 'repeated-independent-v1',
    'blind_state', 'blind', 'scientific_claim_allowed', false
  ), repeat('5', 64)
from public.assignments a where a.assignment_id = 'assignment:test';
insert into public.consensus (
  consensus_id, verification_campaign_pk, media_object_pk, consensus_layer,
  status, decision, method, method_version, eligible_review_count,
  decisive_review_count, review_event_fingerprints, layer_summary,
  consensus_fingerprint
) select 'consensus:test', verification_campaign_pk, media_object_pk,
  'community_evidence', 'reached', 'yes', 'unweighted_human_counts_v1',
  'butterflylens-layered-consensus:v1.0.0', 1, 1,
  array[event_fingerprint], jsonb_build_object(
    'method', 'unweighted_human_counts_v1',
    'policy_version', 'butterflylens-layered-consensus-policy:v1.0.0',
    'status', 'available',
    'outcome', 'supported', 'eligible_review_count', 1,
    'decisive_review_count', 1, 'support_count', 1, 'oppose_count', 0,
    'support_total', 1, 'oppose_total', 0,
    'uncertain_count', 0, 'media_failure_count', 0, 'deferred_count', 0,
    'dissent_count', 0, 'event_fingerprints', to_jsonb(array[event_fingerprint]),
    'blockers', '[]'::jsonb, 'model_vote_included', false,
    'scientific_claim_allowed', false,
    'outer_consensus_fingerprint', repeat('6', 64),
    'adjudication_event_fingerprint', null,
    'release_gates', jsonb_build_object(
      'rights_passed', false, 'provenance_passed', false,
      'conflict_resolved', false, 'quality_passed', false,
      'expert_gate_satisfied', false, 'authorization_passed', false
    )
  ), repeat('6', 64)
from public.review_events where review_event_id = 'review-event:test';
insert into public.reviewer_reliability (
  reviewer_reliability_id, reviewer_profile_pk, project_pk, family_taxon_key,
  source_provider, life_stage, visual_domain, weighting_state,
  sample_count, decisive_count, positive_control_count,
  negative_control_count, control_accuracy, overlap_count,
  adjudicated_count, evidence_fingerprint, evidence_cutoff, blockers,
  metrics, estimator_version, policy_version, reliability_fingerprint,
  measured_at
) select 'reliability:test', rp.id, p.id, 'family:all',
  'butterflylens_fixture', 'unknown', 'ambiguous', 'insufficient_evidence',
  0, 0, 0, 0, null, 0, 0, repeat('6', 64), now(),
  array['control_attempts_below_minimum'], jsonb_build_object(
    'visibility', 'private', 'public_ranking_allowed', false,
    'model_agreement_used', false, 'majority_agreement_alone_used', false,
    'scientific_claim_allowed', false,
    'method', 'control_calibrated_beta_binomial_v1',
    'evidence_fingerprint', repeat('6', 64),
    'control_accuracy', null, 'sensitivity', null, 'specificity', null,
    'pairwise_agreement', null, 'krippendorff_alpha', null,
    'adjudicated_overlap', null
  ), 'butterflylens-reliability-estimator:v1.0.0',
  'butterflylens-reviewer-reliability-policy:v1.0.0', repeat('7', 64), now()
from public.reviewer_profiles rp cross join public.projects p
where rp.reviewer_profile_id = 'reviewer:test' and p.project_id = 'project:review-test';
insert into public.quality_snapshots (
  quality_snapshot_id, project_pk, run_pk, snapshot_kind, scope_kind,
  sampling_frame_fingerprint, reviewed_sample, decisive_reviews,
  release_blockers, snapshot_fingerprint, estimator_version, policy_version,
  sampling_plan_id, audit_evidence_fingerprint, sampling_design,
  representative, blind,
  interval_method, bootstrap_replicates, bootstrap_seed_fingerprint,
  resampling_group_count, population_estimate_allowed, estimate_payload
) select 'quality:test', p.id, r.id, 'targeted_failure_discovery', 'national',
  repeat('8', 64), 1, 1, array['not_population_representative'], repeat('9', 64),
  'butterflylens-dataset-quality-estimator:v1.0.0',
  'butterflylens-representative-audit-policy:v1.0.0',
  'plan:review-targeted', repeat('b', 64), 'targeted_priority', false, true,
  'stratified_owner_observation_group_bootstrap_v1', 200, repeat('a', 64),
  0, false, jsonb_build_object(
    'schema_version', 'butterflylens-quality-snapshot:v1.0.0',
    'estimator_version', 'butterflylens-dataset-quality-estimator:v1.0.0',
    'policy_version', 'butterflylens-representative-audit-policy:v1.0.0',
    'quality_snapshot_id', 'quality:test',
    'project_id', 'project:review-test', 'run_id', 'run:review-test',
    'audit_kind', 'targeted_failure_discovery', 'availability', 'unavailable',
    'sampling_plan_id', 'plan:review-targeted',
    'audit_evidence_fingerprint', repeat('b', 64),
    'audit_records', jsonb_build_array(jsonb_build_object(
      'record_id', 'record:test', 'stratum_id', 'stratum:targeted',
      'inclusion_probability', null, 'owner_group_fingerprint', null,
      'observation_group_fingerprint', null, 'outcome', 'not_supported',
      'consensus_status', 'complete_agreement',
      'review_fingerprint', repeat('c', 64),
      'consensus_fingerprint', repeat('d', 64)
    )),
    'sampling_strata', jsonb_build_array(jsonb_build_object(
      'stratum_id', 'stratum:targeted', 'population_count', null,
      'population_weight', null, 'sample_count', 1, 'decisive_count', 1,
      'supported_count', 0, 'failure_count', 1, 'analysis_weight', null,
      'precision_estimate', null, 'resampling_group_count', 0
    )),
    'grouping_keys', jsonb_build_array('owner_id', 'observation_id'),
    'sampling_design', 'targeted_priority',
    'sampling_frame_fingerprint', repeat('8', 64),
    'snapshot_fingerprint', repeat('9', 64),
    'reviewed_sample', 1, 'decisive_reviews', 1,
    'supported_count', 0, 'failure_count', 1, 'unresolved_count', 0,
    'precision_estimate', null, 'effective_sample_size', null, 'interval', null,
    'inclusion_probability_method', null,
    'interval_method', 'stratified_owner_observation_group_bootstrap_v1',
    'representative', false, 'blind', true,
    'bootstrap_replicates', 200,
    'bootstrap_seed_fingerprint', repeat('a', 64),
    'resampling_group_count', 0,
    'blockers', jsonb_build_array('not_population_representative'),
    'population_estimate_allowed', false,
    'targeted_queue_separate', true, 'model_vote_included', false,
    'scientific_claim_allowed', false, 'generated_at', now()
  )
from public.projects p join public.runs r on r.project_pk = p.id
where p.project_id = 'project:review-test';

select is((select count(*) from public.reviewer_profiles), 1::bigint, 'valid profile inserts');
select is((select count(*) from public.verification_campaigns), 1::bigint, 'valid campaign inserts');
select is((select count(*) from public.assignments), 1::bigint, 'valid independent assignment inserts');
select is((select count(*) from public.review_events), 1::bigint, 'valid append-only event inserts');
select is((select count(*) from public.consensus), 1::bigint, 'valid layered consensus inserts');
select is((select count(*) from public.reviewer_reliability), 1::bigint, 'valid private reliability inserts');
select is((select count(*) from public.quality_snapshots), 1::bigint, 'valid quality snapshot inserts');

select throws_ok(
  $$update public.reviewer_profiles set role = 'expert'$$,
  '23514', 'expert role requires verified qualification'
);
select throws_ok(
  $$insert into public.assignments (
      assignment_id, verification_campaign_pk, media_object_pk,
      reviewer_profile_pk, assignment_sequence, blind_payload_fingerprint,
      assignment_fingerprint
    ) select 'assignment:duplicate-reviewer', verification_campaign_pk,
      media_object_pk, reviewer_profile_pk, 2, repeat('a',64), repeat('b',64)
    from public.assignments where assignment_id = 'assignment:test'$$,
  '23505', 'same reviewer cannot receive the same item twice'
);
select throws_ok(
  $$update public.review_events set decision = 'alternative_taxon'$$,
  '55000', 'append-only review decisions cannot be mutated'
);
select throws_ok(
  $$update public.review_events set reviewer_profile_pk = 999999$$,
  '55000', 'append-only review identity cannot be mutated'
);
select throws_ok(
  $$insert into public.consensus (
      consensus_id, verification_campaign_pk, media_object_pk,
      consensus_layer, status, decision, method, method_version,
      eligible_review_count, decisive_review_count,
      review_event_fingerprints, consensus_fingerprint
    ) select 'consensus:false-release', verification_campaign_pk,
      media_object_pk, 'release_consensus', 'reached', 'yes', 'synthetic', 'v1',
      1, 1, array[repeat('5',64)], repeat('c',64)
    from public.consensus where consensus_id = 'consensus:test'$$,
  '23514', 'release consensus requires expert gate'
);
select throws_ok(
  $$update public.reviewer_reliability set weighting_state = 'shrunk_capped', shrunk_weight = 1.2$$,
  '55000', 'append-only reliability weights cannot be mutated'
);
select throws_ok(
  $$update public.reviewer_reliability set metrics = '{"bioclip_agreement":1}'::jsonb$$,
  '55000', 'append-only reliability metrics cannot be mutated'
);
select throws_ok(
  $$update public.quality_snapshots set snapshot_kind = 'representative_audit'$$,
  '55000', 'append-only quality audit lane cannot be mutated'
);
select throws_ok(
  $$update public.quality_snapshots set precision_estimate = 0.8, interval_lower = 0.9, interval_upper = 1$$,
  '55000', 'append-only quality estimates cannot be mutated'
);

select * from finish();
rollback;
