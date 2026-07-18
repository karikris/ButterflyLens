begin;

create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(25);

select has_table('public', 'geographic_impact', 'geographic impact table exists');
select has_table('public', 'release_candidates', 'release candidates table exists');
select ok((select relrowsecurity from pg_class where oid = 'public.geographic_impact'::regclass), 'impact has RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.release_candidates'::regclass), 'release candidates have RLS');
select has_index('public', 'geographic_impact', 'geographic_impact_project_pk_idx', 'impact project FK is indexed');
select has_index('public', 'geographic_impact', 'geographic_impact_worker_heartbeat_pk_idx', 'impact heartbeat FK is indexed');
select has_index('public', 'release_candidates', 'release_candidates_species_pk_idx', 'release species FK is indexed');
select has_index('public', 'release_candidates', 'release_candidates_consensus_pk_idx', 'release consensus FK is indexed');
select has_index('public', 'release_candidates', 'release_candidates_quality_snapshot_pk_idx', 'release quality FK is indexed');
select has_index('public', 'release_candidates', 'release_candidates_authorizer_pk_idx', 'release authorizer FK is indexed');
select ok(not has_table_privilege('anon', 'public.geographic_impact', 'select'), 'anon has no map access before explicit policy');
select ok(not has_table_privilege('authenticated', 'public.release_candidates', 'insert'), 'authenticated cannot release records');
select ok(not has_table_privilege('service_role', 'public.geographic_impact', 'update'), 'impact cells are append-only');

insert into public.projects (
  project_id, slug, name, boundary_id, boundary_version, boundary_sha256,
  sensitive_coordinate_policy_version, root_taxon_keys, taxonomy_fingerprint,
  search_plan_fingerprint, public_discovery_claim, data_policy_version,
  consent_policy_version
) values (
  'project:map-test', 'map-test', 'Map test', 'boundary:australia', 'v1',
  repeat('a',64), 'v1', array['bltx:v1:test'], repeat('b',64), repeat('c',64),
  'All butterfly candidate images discoverable through the published ButterflyLens Flickr search plan.',
  'v1', 'v1'
);
insert into public.runs (
  run_id, project_pk, run_kind, mode, status, requested_actor_type,
  engine_repository, engine_commit, engine_interface_version, engine_command
) select 'run:map-test', id, 'geographic_impact', 'replay', 'queued', 'system',
  'karikris/ButterflyLens', repeat('d',40), 'v1', 'synthetic test'
from public.projects where project_id = 'project:map-test';
insert into public.species (
  species_id, project_pk, butterflylens_taxon_key, accepted_scientific_name,
  taxonomy_fingerprint, taxon_source, taxon_source_id
) select 'species:map-test', id, 'bltx:v1:test', 'Papilio testus', repeat('b',64),
  'Australian Faunal Directory', 'afd:test'
from public.projects where project_id = 'project:map-test';
insert into public.media_objects (
  media_object_id, project_pk, run_pk, source_kind, object_kind,
  storage_backend, storage_key, media_state, content_sha256, byte_count,
  media_type, decode_status, rights_fingerprint, rights_status,
  media_fingerprint, committed_at
) select 'media:map-test', p.id, r.id, 'reference', 'private_review_image',
  'b2', 'private/map/test.jpg', 'committed', repeat('e',64), 100,
  'image/jpeg', 'valid', repeat('f',64), 'allowed', repeat('1',64), now()
from public.projects p join public.runs r on r.project_pk = p.id
where p.project_id = 'project:map-test';
insert into public.verification_campaigns (
  verification_campaign_id, project_pk, campaign_kind, name, question,
  target_review_count, campaign_fingerprint
) select 'campaign:map-test', id, 'ordinary_image', 'Map test campaign',
  'Is this a butterfly?', 2, repeat('2',64)
from public.projects where project_id = 'project:map-test';
insert into public.consensus (
  consensus_id, verification_campaign_pk, media_object_pk, species_pk,
  consensus_layer, status, method, method_version, eligible_review_count,
  decisive_review_count, review_event_fingerprints, layer_summary,
  consensus_fingerprint
) select 'consensus:map-test', c.id, m.id, s.id, 'community_evidence',
  'insufficient', 'unweighted_human_counts_v1',
  'butterflylens-layered-consensus:v1.0.0', 0, 0, '{}',
  jsonb_build_object(
    'method', 'unweighted_human_counts_v1',
    'policy_version', 'butterflylens-layered-consensus-policy:v1.0.0',
    'status', 'pending',
    'outcome', null, 'eligible_review_count', 0,
    'decisive_review_count', 0, 'support_count', 0, 'oppose_count', 0,
    'support_total', 0, 'oppose_total', 0,
    'uncertain_count', 0, 'media_failure_count', 0, 'deferred_count', 0,
    'dissent_count', 0, 'event_fingerprints', '[]'::jsonb,
    'blockers', jsonb_build_array('decisive_reviews_below_required'),
    'model_vote_included', false, 'scientific_claim_allowed', false,
    'outer_consensus_fingerprint', repeat('3',64),
    'adjudication_event_fingerprint', null,
    'release_gates', jsonb_build_object(
      'rights_passed', false, 'provenance_passed', false,
      'conflict_resolved', false, 'quality_passed', false,
      'expert_gate_satisfied', false, 'authorization_passed', false
    )
  ), repeat('3',64)
from public.verification_campaigns c cross join public.media_objects m
cross join public.species s
where c.verification_campaign_id = 'campaign:map-test'
  and m.media_object_id = 'media:map-test' and s.species_id = 'species:map-test';
insert into public.quality_snapshots (
  quality_snapshot_id, project_pk, run_pk, snapshot_kind, scope_kind,
  sampling_frame_fingerprint, reviewed_sample, decisive_reviews,
  release_blockers, snapshot_fingerprint, estimator_version, policy_version,
  sampling_plan_id, audit_evidence_fingerprint, sampling_design,
  representative, blind,
  interval_method, bootstrap_replicates, bootstrap_seed_fingerprint,
  resampling_group_count, population_estimate_allowed, estimate_payload
) select 'quality:map-test', p.id, r.id, 'targeted_failure_discovery', 'national',
  repeat('4',64), 0, 0, array['no_human_review'], repeat('5',64),
  'butterflylens-dataset-quality-estimator:v1.0.0',
  'butterflylens-representative-audit-policy:v1.0.0',
  'plan:map-targeted', repeat('7',64), 'targeted_priority', false, true,
  'stratified_owner_observation_group_bootstrap_v1', 200, repeat('6',64),
  0, false, jsonb_build_object(
    'schema_version', 'butterflylens-quality-snapshot:v1.0.0',
    'estimator_version', 'butterflylens-dataset-quality-estimator:v1.0.0',
    'policy_version', 'butterflylens-representative-audit-policy:v1.0.0',
    'quality_snapshot_id', 'quality:map-test',
    'project_id', 'project:map-test', 'run_id', 'run:map-test',
    'audit_kind', 'targeted_failure_discovery', 'availability', 'unavailable',
    'sampling_plan_id', 'plan:map-targeted', 'sampling_design', 'targeted_priority',
    'audit_evidence_fingerprint', repeat('7',64),
    'audit_records', jsonb_build_array(),
    'sampling_strata', jsonb_build_array(jsonb_build_object(
      'stratum_id', 'stratum:targeted', 'population_count', null,
      'population_weight', null, 'sample_count', 0, 'decisive_count', 0,
      'supported_count', 0, 'failure_count', 0, 'analysis_weight', null,
      'precision_estimate', null, 'resampling_group_count', 0
    )),
    'grouping_keys', jsonb_build_array('owner_id', 'observation_id'),
    'sampling_frame_fingerprint', repeat('4',64),
    'snapshot_fingerprint', repeat('5',64),
    'reviewed_sample', 0, 'decisive_reviews', 0,
    'supported_count', 0, 'failure_count', 0, 'unresolved_count', 0,
    'precision_estimate', null, 'effective_sample_size', null, 'interval', null,
    'inclusion_probability_method', null,
    'interval_method', 'stratified_owner_observation_group_bootstrap_v1',
    'representative', false, 'blind', true,
    'bootstrap_replicates', 200,
    'bootstrap_seed_fingerprint', repeat('6',64),
    'resampling_group_count', 0,
    'blockers', jsonb_build_array('no_human_review'),
    'population_estimate_allowed', false,
    'targeted_queue_separate', true, 'model_vote_included', false,
    'scientific_claim_allowed', false, 'generated_at', now()
  )
from public.projects p join public.runs r on r.project_pk = p.id
where p.project_id = 'project:map-test';
insert into public.geographic_impact (
  geographic_impact_id, project_pk, run_pk, species_pk, quality_snapshot_pk,
  snapshot_mode, snapshot_state, source_commit, source_snapshot_fingerprint,
  ala_baseline_fingerprint, provider_union_fingerprint,
  review_projection_fingerprint, scope_kind, scope_id, source_precision,
  ala_baseline_count, ala_baseline_count_state,
  flickr_candidate_count_state, flickr_candidate_count_reason,
  yoloe_butterfly_count_state, yoloe_butterfly_count_reason,
  bioclip_species_candidate_count_state, bioclip_species_candidate_count_reason,
  community_reviewed_count, community_reviewed_count_state,
  human_supported_count, human_supported_count_state,
  release_ready_count, release_ready_count_state,
  potential_coverage_gap_state, potential_coverage_gap_reason,
  human_supported_additional_state, human_supported_additional_reason,
  release_ready_additional_state, release_ready_additional_reason,
  nearest_ala_distance_state, nearest_ala_distance_reason,
  latest_ala_date, latest_ala_date_state,
  latest_flickr_date_state, latest_flickr_date_reason,
  data_deficiency_state, data_deficiency_reason, evidence_fingerprints,
  impact_fingerprint
) select 'impact:map-test', p.id, r.id, s.id, q.id, 'submitted', 'available',
  repeat('d',40), repeat('6',64), repeat('7',64), repeat('8',64), repeat('9',64),
  'australia', 'AU', 'coarse_rollup', 5, 'available',
  'unavailable', 'Flickr API calls prohibited in this goal',
  'unavailable', 'YOLOE skipped unfinished by user direction',
  'unavailable', 'BioCLIP skipped unfinished by user direction',
  0, 'available', 0, 'available', 0, 'available',
  'unavailable', 'Flickr discovery unavailable',
  'unavailable', 'Flickr discovery unavailable',
  'unavailable', 'Flickr discovery unavailable',
  'unavailable', 'No comparable candidate location', date '2020-01-01', 'available',
  'unavailable', 'Flickr discovery unavailable', 'data_deficient',
  'Model and Flickr evidence are unavailable', array[repeat('7',64), repeat('9',64)],
  repeat('a',64)
from public.projects p join public.runs r on r.project_pk = p.id
join public.species s on s.project_pk = p.id
join public.quality_snapshots q on q.project_pk = p.id
where p.project_id = 'project:map-test';
insert into public.release_candidates (
  release_candidate_id, project_pk, run_pk, species_pk, media_object_pk,
  consensus_pk, quality_snapshot_pk, geographic_impact_pk, candidate_state,
  release_blockers, rights_fingerprint, candidate_fingerprint
) select 'release:map-test', p.id, r.id, s.id, m.id, c.id, q.id, g.id,
  'blocked', array['human_review_absent','models_unfinished','flickr_unavailable'],
  repeat('f',64), repeat('b',64)
from public.projects p join public.runs r on r.project_pk = p.id
join public.species s on s.project_pk = p.id
cross join public.media_objects m cross join public.consensus c
cross join public.quality_snapshots q cross join public.geographic_impact g
where p.project_id = 'project:map-test' and m.media_object_id = 'media:map-test'
  and c.consensus_id = 'consensus:map-test' and q.quality_snapshot_id = 'quality:map-test'
  and g.geographic_impact_id = 'impact:map-test';

select is((select count(*) from public.geographic_impact), 1::bigint, 'truthful submitted impact inserts');
select is((select count(*) from public.release_candidates), 1::bigint, 'blocked release candidate inserts');

select throws_ok(
  $$update public.geographic_impact set ala_baseline_authority = 'legacy_repository'$$,
  '23514', 'rebuilt ButterflyLens baseline remains authoritative'
);
select throws_ok(
  $$update public.geographic_impact set flickr_candidate_count = 0$$,
  '23514', 'unavailable Flickr evidence cannot be encoded as zero'
);
select throws_ok(
  $$update public.geographic_impact set snapshot_mode = 'live'$$,
  '23514', 'available live snapshot requires observed heartbeat'
);
select throws_ok(
  $$update public.geographic_impact set scope_kind = 'h3', scope_id = 'h3:test'$$,
  '23514', 'H3 impact requires complete grid identity'
);
select throws_ok(
  $$update public.release_candidates set candidate_state = 'eligible'$$,
  '23514', 'eligible release candidate requires every gate'
);
select throws_ok(
  $$update public.release_candidates set all_release_gates_passed = true$$,
  '23514', 'all-gates flag must equal the individual gates'
);
select throws_ok(
  $$update public.release_candidates set release_blockers = '{}'$$,
  '23514', 'blocked release candidate requires blockers'
);
select throws_ok(
  $$update public.release_candidates set evidence_packet_complete = true$$,
  '23514', 'complete evidence packet requires its fingerprint'
);
select throws_ok(
  $$update public.release_candidates set candidate_state = 'approved'$$,
  '23514', 'approval cannot bypass gates or qualified authority'
);
select throws_ok(
  $$update public.geographic_impact set yoloe_butterfly_count_state = 'available', yoloe_butterfly_count_reason = null$$,
  '23514', 'available model count requires a measured value'
);

select * from finish();
rollback;
