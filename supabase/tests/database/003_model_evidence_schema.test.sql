begin;

create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(38);

select has_table('public', 'media_objects', 'media objects table exists');
select has_table('public', 'duplicate_groups', 'duplicate groups table exists');
select has_table('public', 'duplicate_group_members', 'duplicate memberships table exists');
select has_table('public', 'pipeline_stages', 'pipeline stages table exists');
select has_table('public', 'worker_leases', 'worker leases table exists');
select has_table('public', 'worker_heartbeats', 'worker heartbeats table exists');
select has_table('public', 'model_evidence', 'model evidence table exists');

select ok((select relrowsecurity from pg_class where oid = 'public.media_objects'::regclass), 'media has RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.duplicate_groups'::regclass), 'groups have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.duplicate_group_members'::regclass), 'members have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.pipeline_stages'::regclass), 'stages have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.worker_leases'::regclass), 'leases have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.worker_heartbeats'::regclass), 'heartbeats have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.model_evidence'::regclass), 'evidence has RLS');

select has_index('public', 'media_objects', 'media_objects_run_pk_idx', 'media run FK is indexed');
select has_index('public', 'duplicate_groups', 'duplicate_groups_representative_media_pk_idx', 'representative FK is indexed');
select has_index('public', 'duplicate_group_members', 'duplicate_group_members_media_pk_idx', 'member media FK is indexed');
select has_index('public', 'pipeline_stages', 'pipeline_stages_run_pk_idx', 'stage run FK is indexed');
select has_index('public', 'worker_leases', 'worker_leases_pipeline_stage_pk_idx', 'lease stage FK is indexed');
select has_index('public', 'worker_heartbeats', 'worker_heartbeats_worker_lease_pk_idx', 'heartbeat lease FK is indexed');
select has_index('public', 'model_evidence', 'model_evidence_pipeline_stage_pk_idx', 'evidence stage FK is indexed');
select ok(not has_table_privilege('anon', 'public.model_evidence', 'select'), 'anon cannot read raw model evidence');
select ok(not has_table_privilege('authenticated', 'public.worker_leases', 'insert'), 'authenticated cannot acquire worker leases');
select ok(not has_table_privilege('service_role', 'public.worker_heartbeats', 'update'), 'heartbeats are append-only for the worker service');

insert into public.projects (
  project_id, slug, name, boundary_id, boundary_version, boundary_sha256,
  sensitive_coordinate_policy_version, root_taxon_keys, taxonomy_fingerprint,
  search_plan_fingerprint, public_discovery_claim, data_policy_version,
  consent_policy_version
) values (
  'project:model-test', 'model-test', 'Model evidence test',
  'boundary:australia', 'v1', repeat('a', 64), 'v1',
  array['bltx:v1:846e98d50678dffa38d43103'], repeat('b', 64), repeat('c', 64),
  'All butterfly candidate images discoverable through the published ButterflyLens Flickr search plan.',
  'v1', 'v1'
);
insert into public.runs (
  run_id, project_pk, run_kind, mode, status, requested_actor_type,
  engine_repository, engine_commit, engine_interface_version, engine_command
) select 'run:model-test', id, 'vision_pipeline', 'replay', 'queued',
  'system', 'karikris/ButterflyLens', repeat('d', 40), 'v1', 'synthetic test'
from public.projects where project_id = 'project:model-test';
insert into public.media_objects (
  media_object_id, project_pk, run_pk, source_kind, object_kind,
  storage_backend, storage_key, media_state, content_sha256, byte_count,
  media_type, width_pixels, height_pixels, decode_status, rights_fingerprint,
  rights_status, media_fingerprint, committed_at
) select 'media:test', p.id, r.id, 'reference', 'source_image',
  'b2', 'references/sha256/test.jpg', 'committed', repeat('e', 64), 1024,
  'image/jpeg', 64, 64, 'valid', repeat('f', 64), 'allowed', repeat('1', 64), now()
from public.projects p join public.runs r on r.project_pk = p.id
where p.project_id = 'project:model-test';
insert into public.duplicate_groups (
  duplicate_group_id, project_pk, run_pk, representative_media_pk,
  grouping_kind, algorithm, algorithm_version, threshold, group_fingerprint
) select 'duplicate-group:test', p.id, r.id, m.id, 'exact_content',
  'sha256', 'v1', 0, repeat('2', 64)
from public.projects p
join public.runs r on r.project_pk = p.id
join public.media_objects m on m.project_pk = p.id
where p.project_id = 'project:model-test';
insert into public.duplicate_group_members (
  duplicate_group_pk, media_object_pk, member_role, distance, membership_fingerprint
) select d.id, d.representative_media_pk, 'representative', 0, repeat('3', 64)
from public.duplicate_groups d where d.duplicate_group_id = 'duplicate-group:test';
insert into public.pipeline_stages (
  pipeline_stage_id, run_pk, stage_kind, status, status_reason,
  work_fingerprint, finished_at
) select 'stage:yoloe-skipped', id, 'yoloe_route', 'skipped_unfinished',
  'User directed YOLOE work to remain unfinished.', repeat('4', 64), now()
from public.runs where run_id = 'run:model-test';
insert into public.pipeline_stages (
  pipeline_stage_id, run_pk, stage_kind, status, work_fingerprint
) select 'stage:download-test', id, 'download', 'leased', repeat('5', 64)
from public.runs where run_id = 'run:model-test';
insert into public.worker_leases (
  worker_lease_id, pipeline_stage_pk, worker_id, lease_revision,
  fencing_token_sha256, expires_at
) select 'lease:test', id, 'worker:test', 1, repeat('6', 64), now() + interval '5 minutes'
from public.pipeline_stages where pipeline_stage_id = 'stage:download-test';
insert into public.worker_heartbeats (
  worker_heartbeat_id, worker_id, worker_lease_pk, pipeline_stage_pk,
  observed_at, health_state, machine_fingerprint, current_stage,
  metrics, model_status, heartbeat_fingerprint
) select 'heartbeat:test', l.worker_id, l.id, l.pipeline_stage_pk, now(),
  'healthy', repeat('7', 64), 'download', '{"queue_depth":0}'::jsonb,
  '{"yoloe":"unfinished","bioclip":"unfinished"}'::jsonb, repeat('8', 64)
from public.worker_leases l where l.worker_lease_id = 'lease:test';
insert into public.model_evidence (
  model_evidence_id, pipeline_stage_pk, media_object_pk, evidence_kind,
  evidence_status, status_reason, evidence_fingerprint
) select 'model-evidence:yoloe-skipped', s.id, m.id, 'yoloe_route',
  'skipped_unfinished', 'User directed YOLOE work to remain unfinished.', repeat('9', 64)
from public.pipeline_stages s cross join public.media_objects m
where s.pipeline_stage_id = 'stage:yoloe-skipped' and m.media_object_id = 'media:test';

select is((select count(*) from public.media_objects), 1::bigint, 'valid media inserts');
select is((select count(*) from public.duplicate_groups), 1::bigint, 'valid group inserts');
select is((select count(*) from public.duplicate_group_members), 1::bigint, 'valid membership inserts');
select is((select count(*) from public.pipeline_stages), 2::bigint, 'typed stages insert');
select is((select count(*) from public.worker_leases), 1::bigint, 'fenced lease inserts');
select is((select count(*) from public.worker_heartbeats), 1::bigint, 'append-only heartbeat inserts');
select is((select count(*) from public.model_evidence), 1::bigint, 'unfinished model state inserts without output');

select throws_ok(
  $$update public.media_objects set rights_status = 'unknown', download_allowed = true$$,
  '23514', 'unknown media rights block download'
);
select throws_ok(
  $$update public.media_objects set storage_key = 'https://signed.example.test/private'$$,
  '23514', 'media storage rejects URLs and signed links'
);
select throws_ok(
  $$update public.pipeline_stages set status = 'succeeded', finished_at = now() where pipeline_stage_id = 'stage:download-test'$$,
  '23514', 'successful stages require output fingerprint'
);
select throws_ok(
  $$insert into public.worker_leases (
      worker_lease_id, pipeline_stage_pk, worker_id, lease_revision,
      fencing_token_sha256, expires_at
    ) select 'lease:stale-race', pipeline_stage_pk, 'worker:other', 2,
      repeat('a', 64), now() + interval '5 minutes'
    from public.worker_leases where worker_lease_id = 'lease:test'$$,
  '23505', 'one current fenced lease is allowed per stage'
);
select throws_ok(
  $$insert into public.model_evidence (
      model_evidence_id, pipeline_stage_pk, media_object_pk, evidence_kind,
      evidence_status, evidence_fingerprint
    ) select 'model-evidence:false-complete', pipeline_stage_pk, media_object_pk,
      'yoloe_route', 'completed', repeat('b', 64)
    from public.model_evidence where model_evidence_id = 'model-evidence:yoloe-skipped'$$,
  '23514', 'completed model evidence requires pinned inputs and output'
);
select throws_ok(
  $$update public.model_evidence set calibrated_probability = 0.9$$,
  '23514', 'calibrated probability requires an independent calibrator fingerprint'
);
select throws_ok(
  $$update public.worker_heartbeats set metrics = '{"auth_token":"forbidden"}'::jsonb$$,
  '23514', 'heartbeat payload rejects credentials'
);

select * from finish();
rollback;
