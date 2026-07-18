begin;

create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(33);

select has_table('public', 'operational_monitoring_snapshots');
select ok(
  (select relrowsecurity from pg_class where oid = 'public.operational_monitoring_snapshots'::regclass),
  'operational monitoring has RLS'
);
select has_index('public', 'operational_monitoring_snapshots', 'operational_monitoring_snapshots_project_observed_idx');
select has_index('public', 'operational_monitoring_snapshots', 'operational_monitoring_snapshots_run_pk_idx');
select has_index('public', 'operational_monitoring_snapshots', 'operational_monitoring_snapshots_worker_heartbeat_pk_idx');
select has_trigger('public', 'operational_monitoring_snapshots', 'operational_monitoring_snapshots_validate_lineage');
select has_trigger('public', 'operational_monitoring_snapshots', 'operational_monitoring_snapshots_reject_mutation');
select ok(not has_table_privilege('anon', 'public.operational_monitoring_snapshots', 'select'), 'guest cannot query monitoring storage');
select ok(not has_table_privilege('authenticated', 'public.operational_monitoring_snapshots', 'select'), 'browser user cannot query monitoring storage');
select ok(has_table_privilege('service_role', 'public.operational_monitoring_snapshots', 'select'), 'service boundary reads monitoring');
select ok(has_table_privilege('service_role', 'public.operational_monitoring_snapshots', 'insert'), 'worker service appends monitoring');
select ok(not has_table_privilege('service_role', 'public.operational_monitoring_snapshots', 'update'), 'monitoring cannot be updated');
select ok(not has_table_privilege('service_role', 'public.operational_monitoring_snapshots', 'delete'), 'monitoring cannot be deleted');
select ok(not has_sequence_privilege('anon', 'public.operational_monitoring_snapshots_id_seq', 'usage'), 'guest cannot allocate monitoring IDs');
select has_function('private', 'validate_operational_monitoring_lineage', array[]::text[]);
select ok((
  select function.prosecdef and function.proconfig @> array['search_path=""']
  from pg_proc function join pg_namespace namespace on namespace.oid = function.pronamespace
  where namespace.nspname = 'private' and function.proname = 'validate_operational_monitoring_lineage'
), 'lineage trigger is fixed-search-path security definer');
select has_function('private', 'reject_operational_monitoring_mutation', array[]::text[]);
select ok((
  select function.prosecdef and function.proconfig @> array['search_path=""']
  from pg_proc function join pg_namespace namespace on namespace.oid = function.pronamespace
  where namespace.nspname = 'private' and function.proname = 'reject_operational_monitoring_mutation'
), 'mutation trigger is fixed-search-path security definer');
select ok(not has_function_privilege('anon', 'private.validate_operational_monitoring_lineage()', 'execute'), 'guest cannot execute lineage trigger');
select ok(not has_function_privilege('anon', 'private.reject_operational_monitoring_mutation()', 'execute'), 'guest cannot execute mutation trigger');

insert into public.projects (
  project_id, slug, name, status, boundary_id, boundary_version, boundary_sha256,
  sensitive_coordinate_policy_version, root_taxon_keys, taxonomy_fingerprint,
  search_plan_fingerprint, public_discovery_claim, data_policy_version,
  consent_policy_version
) values
  (
    'project:monitoring-one', 'monitoring-one', 'Monitoring one', 'active',
    'boundary:australia', 'v1', repeat('a',64), 'v1', array['bltx:v1:test'],
    repeat('b',64), repeat('c',64),
    'All butterfly candidate images discoverable through the published ButterflyLens Flickr search plan.',
    'v1', 'v1'
  ),
  (
    'project:monitoring-two', 'monitoring-two', 'Monitoring two', 'active',
    'boundary:australia', 'v1', repeat('d',64), 'v1', array['bltx:v1:test'],
    repeat('e',64), repeat('f',64),
    'All butterfly candidate images discoverable through the published ButterflyLens Flickr search plan.',
    'v1', 'v1'
  );

insert into public.runs (
  run_id, project_pk, run_kind, mode, status, requested_actor_type,
  requested_at, started_at, updated_at, engine_repository, engine_commit,
  engine_interface_version, engine_command, input_fingerprints
) select
  'run:monitoring-one', project.id, 'full_pipeline', 'live', 'running', 'system',
  now() - interval '2 minutes', now() - interval '2 minutes', now(),
  'karikris/BioMiner', repeat('1',40), 'v1', 'biominer run bounded', array[repeat('2',64)]
from public.projects project where project.project_id = 'project:monitoring-one';

insert into public.operational_monitoring_snapshots (
  monitoring_snapshot_id, project_pk, run_pk, observed_at,
  heartbeat_state, heartbeat_reason,
  api_budget_state, api_budget_reason,
  stage_health_state, stage_health_reason,
  queue_state, queue_reason,
  failure_state, failure_reason,
  artifact_state, artifact_fingerprint, artifact_committed_at, artifact_reason,
  map_state, map_fingerprint, map_refreshed_at, map_reason,
  model_state, yoloe_state, bioclip_state, model_reason,
  resource_state, resource_reason, scientific_claim_allowed, snapshot_fingerprint
) select
  'blmon:v1:000000000000000000000001', project.id, run.id, now() - interval '1 minute',
  'unavailable', 'No governed heartbeat is published.',
  'unavailable', 'No governed API budget is published.',
  'unavailable', 'No governed stage aggregate is published.',
  'unavailable', 'No governed queue aggregate is published.',
  'unavailable', 'No governed failure aggregate is published.',
  'submitted', repeat('3',64), now() - interval '3 minutes', 'Submitted artifact remains available.',
  'submitted', repeat('4',64), now() - interval '3 minutes', 'Submitted map remains available.',
  'unfinished', 'unfinished', 'unfinished', 'YOLOE and BioCLIP remain unfinished.',
  'unavailable', 'No governed resource aggregate is published.', false, repeat('5',64)
from public.projects project join public.runs run on run.project_pk = project.id
where project.project_id = 'project:monitoring-one';

select is((select count(*) from public.operational_monitoring_snapshots), 1::bigint, 'valid monitoring snapshot is appended');
select is((select scientific_claim_allowed from public.operational_monitoring_snapshots), false, 'monitoring cannot grant scientific authority');
select throws_ok(
  $$update public.operational_monitoring_snapshots set failure_count = 0$$,
  '55000', 'operational monitoring snapshots are append only', 'monitoring cannot be changed'
);
select throws_ok(
  $$delete from public.operational_monitoring_snapshots$$,
  '55000', 'operational monitoring snapshots are append only', 'monitoring cannot be deleted'
);

create function pg_temp.clone_monitoring(
  candidate_id text,
  candidate_fingerprint text,
  candidate_project_pk bigint default null,
  candidate_run_pk bigint default null,
  candidate_api_state text default null,
  candidate_api_limit bigint default null,
  candidate_api_used bigint default null,
  candidate_api_remaining bigint default null,
  candidate_failure_state text default null,
  candidate_failure_count bigint default null,
  candidate_queue_state text default null,
  candidate_queue_depth bigint default null,
  candidate_queue_capacity bigint default null,
  candidate_claim boolean default null,
  candidate_model_state text default null,
  candidate_yoloe_state text default null
) returns void
language sql
as $$
  insert into public.operational_monitoring_snapshots (
    monitoring_snapshot_id, project_pk, run_pk, worker_heartbeat_pk, observed_at,
    heartbeat_state, heartbeat_observed_at, worker_state, heartbeat_reason,
    api_budget_state, api_budget_limit, api_budget_used, api_budget_remaining,
    api_budget_resets_at, api_budget_reason,
    stage_health_state, current_stage, stage_state, healthy_stage_count,
    failed_stage_count, stage_health_reason,
    queue_state, queue_depth, queue_capacity, queue_reason,
    failure_state, failure_count, failure_reason,
    artifact_state, artifact_fingerprint, artifact_committed_at, artifact_reason,
    map_state, map_fingerprint, map_refreshed_at, map_reason,
    model_state, yoloe_state, bioclip_state, model_reason,
    resource_state, free_disk_bytes, process_rss_bytes, memory_capacity_bytes,
    mps_allocated_bytes, mps_reserved_bytes, resource_reason,
    scientific_claim_allowed, snapshot_fingerprint, recorded_at
  )
  select
    candidate_id, coalesce(candidate_project_pk, source.project_pk),
    coalesce(candidate_run_pk, source.run_pk), source.worker_heartbeat_pk, source.observed_at,
    source.heartbeat_state, source.heartbeat_observed_at, source.worker_state, source.heartbeat_reason,
    coalesce(candidate_api_state, source.api_budget_state),
    coalesce(candidate_api_limit, source.api_budget_limit),
    coalesce(candidate_api_used, source.api_budget_used),
    coalesce(candidate_api_remaining, source.api_budget_remaining),
    source.api_budget_resets_at, source.api_budget_reason,
    source.stage_health_state, source.current_stage, source.stage_state,
    source.healthy_stage_count, source.failed_stage_count, source.stage_health_reason,
    coalesce(candidate_queue_state, source.queue_state),
    coalesce(candidate_queue_depth, source.queue_depth),
    coalesce(candidate_queue_capacity, source.queue_capacity), source.queue_reason,
    coalesce(candidate_failure_state, source.failure_state),
    coalesce(candidate_failure_count, source.failure_count), source.failure_reason,
    source.artifact_state, source.artifact_fingerprint, source.artifact_committed_at, source.artifact_reason,
    source.map_state, source.map_fingerprint, source.map_refreshed_at, source.map_reason,
    coalesce(candidate_model_state, source.model_state),
    coalesce(candidate_yoloe_state, source.yoloe_state), source.bioclip_state, source.model_reason,
    source.resource_state, source.free_disk_bytes, source.process_rss_bytes,
    source.memory_capacity_bytes, source.mps_allocated_bytes, source.mps_reserved_bytes,
    source.resource_reason, coalesce(candidate_claim, source.scientific_claim_allowed),
    candidate_fingerprint, source.recorded_at
  from public.operational_monitoring_snapshots source
  where source.monitoring_snapshot_id = 'blmon:v1:000000000000000000000001'
$$;

select throws_ok(
  $$select pg_temp.clone_monitoring('blmon:v1:000000000000000000000002', repeat('6',64), candidate_api_state => 'available', candidate_api_limit => 10, candidate_api_used => 4, candidate_api_remaining => 7)$$,
  '23514', null, 'API budget arithmetic is enforced'
);
select throws_ok(
  $$select pg_temp.clone_monitoring('blmon:v1:000000000000000000000003', repeat('7',64), candidate_failure_count => 0)$$,
  '23514', null, 'unavailable failure count cannot masquerade as zero'
);
select throws_ok(
  $$select pg_temp.clone_monitoring('blmon:v1:000000000000000000000004', repeat('8',64), candidate_queue_state => 'available', candidate_queue_depth => 11, candidate_queue_capacity => 10)$$,
  '23514', null, 'queue depth cannot exceed capacity'
);
select throws_ok(
  $$select pg_temp.clone_monitoring('blmon:v1:000000000000000000000005', repeat('9',64), candidate_claim => true)$$,
  '23514', null, 'monitoring cannot grant scientific authority'
);
select throws_ok(
  $$select pg_temp.clone_monitoring(
    'blmon:v1:000000000000000000000006', repeat('a',64),
    candidate_project_pk => (select id from public.projects where project_id = 'project:monitoring-two')
  )$$,
  '23514', 'monitoring run lineage does not match project', 'run lineage cannot cross projects'
);
select throws_ok(
  $$select pg_temp.clone_monitoring('monitoring:invalid', repeat('b',64))$$,
  '23514', null, 'monitoring snapshot ID shape is enforced'
);
select throws_ok(
  $$select pg_temp.clone_monitoring('blmon:v1:000000000000000000000007', repeat('5',64))$$,
  '23505', null, 'monitoring fingerprints are unique'
);
select throws_ok(
  $$select pg_temp.clone_monitoring('blmon:v1:000000000000000000000008', repeat('c',64), candidate_model_state => 'unfinished', candidate_yoloe_state => 'ready')$$,
  '23514', null, 'unfinished model state remains explicit for both skipped models'
);
select throws_ok(
  $$select pg_temp.clone_monitoring('blmon:v1:000000000000000000000009', repeat('d',64), candidate_api_state => 'available', candidate_api_limit => 9007199254740992, candidate_api_used => 9007199254740992, candidate_api_remaining => 0)$$,
  '23514', null, 'public counters cannot exceed JavaScript safe integers'
);

select * from finish();
rollback;
