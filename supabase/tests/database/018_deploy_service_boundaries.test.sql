begin;

create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(38);

select has_table('public', 'server_action_receipts');
select has_table('public', 'b2_signing_receipts');
select ok((select relrowsecurity from pg_class where oid = 'public.server_action_receipts'::regclass), 'server actions have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.b2_signing_receipts'::regclass), 'B2 receipts have RLS');
select has_index('public', 'server_action_receipts', 'server_action_receipts_project_pk_idx');
select has_index('public', 'server_action_receipts', 'server_action_receipts_run_pk_idx');
select has_index('public', 'server_action_receipts', 'server_action_receipts_requested_by_idx');
select has_index('public', 'b2_signing_receipts', 'b2_signing_receipts_project_pk_idx');
select has_index('public', 'b2_signing_receipts', 'b2_signing_receipts_media_object_pk_idx');
select has_index('public', 'b2_signing_receipts', 'b2_signing_receipts_auth_user_id_idx');
select has_trigger('public', 'server_action_receipts', 'server_action_receipts_apply');
select has_trigger('public', 'server_action_receipts', 'server_action_receipts_reject_mutation');
select has_trigger('public', 'b2_signing_receipts', 'b2_signing_receipts_reject_mutation');
select ok(has_table_privilege('authenticated', 'public.server_action_receipts', 'select'), 'users may read policy-scoped action receipts');
select ok(not has_table_privilege('authenticated', 'public.server_action_receipts', 'insert'), 'users cannot insert actions directly');
select ok(not has_table_privilege('anon', 'public.server_action_receipts', 'select'), 'guests cannot read actions');
select ok(has_table_privilege('service_role', 'public.server_action_receipts', 'insert'), 'service boundary inserts actions');
select ok(has_table_privilege('authenticated', 'public.b2_signing_receipts', 'select'), 'users may read their own signing receipts');
select ok(not has_table_privilege('authenticated', 'public.b2_signing_receipts', 'insert'), 'users cannot forge signing receipts');
select ok(has_table_privilege('service_role', 'public.b2_signing_receipts', 'insert'), 'service boundary inserts signing receipts');
select has_function('private', 'apply_controlled_server_action', array[]::text[]);
select ok((
  select function.prosecdef and function.proconfig @> array['search_path=""']
  from pg_proc function join pg_namespace namespace on namespace.oid = function.pronamespace
  where namespace.nspname = 'private' and function.proname = 'apply_controlled_server_action'
), 'action trigger is fixed-search-path security definer');
select ok(not has_function_privilege('anon', 'private.apply_controlled_server_action()', 'execute'), 'guest cannot execute action trigger');
select ok(not has_function_privilege('authenticated', 'private.apply_controlled_server_action()', 'execute'), 'user cannot execute action trigger');

insert into auth.users (id) values
  ('00000000-0000-4000-8000-000000000101'),
  ('00000000-0000-4000-8000-000000000102');

insert into public.reviewer_profiles (
  reviewer_profile_id, auth_user_id, public_name, role, qualification_state
) values
  ('reviewer:service-admin', '00000000-0000-4000-8000-000000000101', 'Service Admin', 'administrator', 'unverified'),
  ('reviewer:service-member', '00000000-0000-4000-8000-000000000102', 'Service Member', 'reviewer', 'unverified');

insert into public.projects (
  project_id, slug, name, status, boundary_id, boundary_version, boundary_sha256,
  sensitive_coordinate_policy_version, root_taxon_keys, taxonomy_fingerprint,
  search_plan_fingerprint, public_discovery_claim, data_policy_version,
  consent_policy_version
) values (
  'project:service-boundary', 'service-boundary', 'Service boundary', 'active',
  'boundary:australia', 'v1', repeat('a',64), 'v1', array['bltx:v1:test'],
  repeat('b',64), repeat('c',64),
  'All butterfly candidate images discoverable through the published ButterflyLens Flickr search plan.',
  'v1', 'v1'
);

insert into public.project_memberships (
  project_membership_id, project_pk, reviewer_profile_pk, auth_user_id,
  role, status, approved_by_reviewer_pk
) select 'membership:service-admin', project.id, profile.id, profile.auth_user_id,
  'administrator', 'active', profile.id
from public.projects project cross join public.reviewer_profiles profile
where project.project_id = 'project:service-boundary'
  and profile.reviewer_profile_id = 'reviewer:service-admin';

insert into public.runs (
  run_id, project_pk, run_kind, mode, status, requested_actor_type,
  requested_actor_id, requested_at, started_at, updated_at, engine_repository,
  engine_commit, engine_interface_version, engine_command, input_fingerprints,
  revision
) select 'run:service-boundary', project.id, 'full_pipeline', 'live', 'running',
  'operator', 'operator:test', now(), now(), now(), 'karikris/BioMiner',
  repeat('d',40), 'v1', 'biominer run bounded', array[repeat('e',64)], 1
from public.projects project where project.project_id = 'project:service-boundary';

insert into public.media_objects (
  media_object_id, project_pk, run_pk, source_kind, object_kind,
  storage_backend, storage_key, media_state, content_sha256, byte_count,
  media_type, width_pixels, height_pixels, decode_status, rights_fingerprint,
  rights_status, download_allowed, display_allowed, media_fingerprint,
  committed_at
) select 'media:service-boundary', project.id, run.id, 'reference',
  'private_review_image', 'b2',
  'butterflylens/v1/projects/test/runs/test/review-media/test/aa/' || repeat('f',64) || '.jpg',
  'committed', repeat('f',64), 1200, 'image/jpeg', 40, 30, 'valid',
  repeat('1',64), 'allowed', true, true, repeat('2',64), now()
from public.projects project join public.runs run on run.project_pk = project.id
where project.project_id = 'project:service-boundary';

insert into public.server_action_receipts (
  server_action_id, project_pk, run_pk, requested_by, action,
  expected_revision, request_fingerprint
) select 'action:pause-service-run', project.id, run.id,
  '00000000-0000-4000-8000-000000000101', 'pause_run', 1, repeat('3',64)
from public.projects project join public.runs run on run.project_pk = project.id
where run.run_id = 'run:service-boundary';

select is((select status from public.runs where run_id = 'run:service-boundary'), 'paused', 'pause action changes only the run state');
select is((select revision from public.runs where run_id = 'run:service-boundary'), 2::bigint, 'pause action increments revision once');
select is((select prior_status from public.server_action_receipts where server_action_id = 'action:pause-service-run'), 'running', 'receipt retains prior state');
select is((select result_status from public.server_action_receipts where server_action_id = 'action:pause-service-run'), 'paused', 'receipt retains result state');

select throws_ok($sql$
  insert into public.server_action_receipts (
    server_action_id, project_pk, run_pk, requested_by, action,
    expected_revision, request_fingerprint
  ) select 'action:pause-service-run', project.id, run.id,
    '00000000-0000-4000-8000-000000000101', 'pause_run', 1, repeat('3',64)
  from public.projects project join public.runs run on run.project_pk = project.id
  where run.run_id = 'run:service-boundary'
$sql$, '23505', 'duplicate action ID reaches the idempotent lookup path');

select throws_ok($sql$
  insert into public.server_action_receipts (
    server_action_id, project_pk, run_pk, requested_by, action,
    expected_revision, request_fingerprint
  ) select 'action:stale-service-run', project.id, run.id,
    '00000000-0000-4000-8000-000000000101', 'resume_run', 1, repeat('4',64)
  from public.projects project join public.runs run on run.project_pk = project.id
  where run.run_id = 'run:service-boundary'
$sql$, '40001', 'controlled run revision is stale', 'stale run control is rejected');

select throws_ok($sql$
  insert into public.server_action_receipts (
    server_action_id, project_pk, run_pk, requested_by, action,
    expected_revision, request_fingerprint
  ) select 'action:unauthorized-service-run', project.id, run.id,
    '00000000-0000-4000-8000-000000000102', 'resume_run', 2, repeat('5',64)
  from public.projects project join public.runs run on run.project_pk = project.id
  where run.run_id = 'run:service-boundary'
$sql$, '42501', 'verified actor lacks run-control authority', 'non-curator control is rejected');

insert into public.server_action_receipts (
  server_action_id, project_pk, run_pk, requested_by, action,
  expected_revision, request_fingerprint
) select 'action:resume-service-run', project.id, run.id,
  '00000000-0000-4000-8000-000000000101', 'resume_run', 2, repeat('6',64)
from public.projects project join public.runs run on run.project_pk = project.id
where run.run_id = 'run:service-boundary';

select is((select status from public.runs where run_id = 'run:service-boundary'), 'running', 'resume action restores running state');

insert into public.server_action_receipts (
  server_action_id, project_pk, run_pk, requested_by, action,
  expected_revision, request_fingerprint
) select 'action:cancel-service-run', project.id, run.id,
  '00000000-0000-4000-8000-000000000101', 'cancel_run', 3, repeat('7',64)
from public.projects project join public.runs run on run.project_pk = project.id
where run.run_id = 'run:service-boundary';

select is((select status from public.runs where run_id = 'run:service-boundary'), 'cancelled', 'cancel action reaches terminal state');
select throws_ok(
  $$update public.server_action_receipts set result_status = 'running' where server_action_id = 'action:cancel-service-run'$$,
  '55000', 'service receipts are append only', 'action receipts cannot be changed'
);

insert into public.b2_signing_receipts (
  signing_receipt_id, project_pk, media_object_pk, auth_user_id, method,
  ttl_seconds, issued_at, expires_at, request_fingerprint
) select 'b2sign:00000000-0000-4000-8000-000000000103', project.id, media.id,
  '00000000-0000-4000-8000-000000000101', 'GET', 300,
  '2026-07-18T08:00:00Z'::timestamptz, '2026-07-18T08:05:00Z'::timestamptz,
  repeat('8',64)
from public.projects project join public.media_objects media on media.project_pk = project.id
where media.media_object_id = 'media:service-boundary';

select set_config('request.jwt.claim.sub', '00000000-0000-4000-8000-000000000101', true);
set local role authenticated;
select is((select count(*) from public.b2_signing_receipts), 1::bigint, 'requester reads own signing receipt');
reset role;

select set_config('request.jwt.claim.sub', '00000000-0000-4000-8000-000000000102', true);
set local role authenticated;
select is((select count(*) from public.b2_signing_receipts), 0::bigint, 'unrelated reviewer cannot read signing receipt');
reset role;

select throws_ok(
  $$delete from public.b2_signing_receipts where signing_receipt_id = 'b2sign:00000000-0000-4000-8000-000000000103'$$,
  '55000', 'service receipts are append only', 'signing receipts cannot be deleted'
);

select throws_ok($sql$
  insert into public.b2_signing_receipts (
    signing_receipt_id, project_pk, media_object_pk, auth_user_id, method,
    ttl_seconds, issued_at, expires_at, request_fingerprint
  ) select 'b2sign:00000000-0000-4000-8000-000000000104', project.id, media.id,
    '00000000-0000-4000-8000-000000000101', 'GET', 901,
    '2026-07-18T08:00:00Z'::timestamptz, '2026-07-18T08:15:01Z'::timestamptz,
    repeat('9',64)
  from public.projects project join public.media_objects media on media.project_pk = project.id
  where media.media_object_id = 'media:service-boundary'
$sql$, '23514', 'signing TTL above 900 seconds is rejected');

select * from finish();
rollback;
