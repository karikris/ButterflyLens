begin;

create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(30);

select has_table('public', 'projects', 'projects table exists');
select has_table('public', 'runs', 'runs table exists');
select has_pk('public', 'projects', 'projects has a primary key');
select has_pk('public', 'runs', 'runs has a primary key');
select col_type_is('public', 'projects', 'id', 'bigint', 'project PK is bigint');
select col_type_is('public', 'runs', 'id', 'bigint', 'run PK is bigint');
select col_type_is('public', 'projects', 'created_at', 'timestamp with time zone', 'project time is timezone-aware');
select col_type_is('public', 'runs', 'requested_at', 'timestamp with time zone', 'run time is timezone-aware');
select has_unique('public', 'projects', 'projects_project_id_key', 'stable project ID is unique');
select has_unique('public', 'projects', 'projects_slug_key', 'project slug is unique');
select has_unique('public', 'runs', 'runs_run_id_key', 'stable run ID is unique');
select has_fk('public', 'runs', 'runs_project_pk_fkey', 'run references its project');
select has_index('public', 'projects', 'projects_created_by_idx', 'project creator FK is indexed');
select has_index('public', 'runs', 'runs_project_pk_requested_at_idx', 'run project FK is indexed');
select has_index('public', 'runs', 'runs_active_status_idx', 'active-run lookup is indexed');
select ok(
  (select relrowsecurity from pg_class where oid = 'public.projects'::regclass),
  'projects has RLS enabled'
);
select ok(
  (select relrowsecurity from pg_class where oid = 'public.runs'::regclass),
  'runs has RLS enabled'
);
select ok(not has_table_privilege('anon', 'public.projects', 'select'), 'anon cannot select projects');
select ok(not has_table_privilege('authenticated', 'public.runs', 'insert'), 'authenticated cannot insert runs yet');
select ok(has_table_privilege('service_role', 'public.projects', 'select'), 'service role can select projects');
select ok(has_table_privilege('service_role', 'public.runs', 'insert'), 'service role can insert runs');

insert into public.projects (
  project_id, slug, name, description, status, boundary_id, boundary_version,
  boundary_sha256, sensitive_coordinate_policy_version, root_taxon_keys,
  taxonomy_fingerprint, search_plan_fingerprint, public_discovery_claim,
  data_policy_version, consent_policy_version
) values (
  'project:australian-butterflies', 'australian-butterflies',
  'Australian butterflies', 'Test project', 'active', 'boundary:australia',
  'test-v1', repeat('a', 64), 'sensitive-v1',
  array['bltx:v1:846e98d50678dffa38d43103'], repeat('b', 64), repeat('c', 64),
  'All butterfly candidate images discoverable through the published ButterflyLens Flickr search plan.',
  'data-v1', 'consent-v1'
);

select is((select count(*) from public.projects), 1::bigint, 'valid project inserts');

insert into public.runs (
  run_id, project_pk, run_kind, mode, status, requested_actor_type,
  engine_repository, engine_commit, engine_interface_version, engine_command,
  input_fingerprints
) values (
  'run:reference-bank:test', (select id from public.projects), 'reference_bank',
  'replay', 'queued', 'system', 'karikris/ButterflyLens', repeat('d', 40),
  'butterflylens-run:v1.0.0', 'reference-bank replay', array[repeat('e', 64)]
);

select is((select count(*) from public.runs), 1::bigint, 'valid queued run inserts');
select throws_ok(
  $$insert into public.projects (
      project_id, slug, name, boundary_id, boundary_version, boundary_sha256,
      sensitive_coordinate_policy_version, root_taxon_keys, taxonomy_fingerprint,
      search_plan_fingerprint, public_discovery_claim, data_policy_version,
      consent_policy_version
    ) values (
      'PROJECT:INVALID', 'invalid-project', 'Invalid', 'boundary:australia', 'v1',
      repeat('a', 64), 'v1', array['bltx:v1:test'], repeat('b', 64),
      repeat('c', 64),
      'All butterfly candidate images discoverable through the published ButterflyLens Flickr search plan.',
      'v1', 'v1'
    )$$,
  '23514',
  'invalid stable project IDs are rejected'
);
select throws_ok(
  $$insert into public.runs (
      run_id, project_pk, run_kind, mode, status, requested_actor_type,
      engine_repository, engine_commit, engine_interface_version, engine_command
    ) values (
      'run:invalid-kind', (select id from public.projects), 'invented', 'live',
      'queued', 'system', 'repo', repeat('d', 40), 'v1', 'command'
    )$$,
  '23514',
  'unknown run kinds are rejected'
);
select throws_ok(
  $$insert into public.runs (
      run_id, project_pk, run_kind, mode, status, requested_actor_type,
      requested_actor_id, engine_repository, engine_commit,
      engine_interface_version, engine_command
    ) values (
      'run:invalid-system-actor', (select id from public.projects), 'full_pipeline',
      'live', 'queued', 'system', 'account:one', 'repo', repeat('d', 40), 'v1',
      'command'
    )$$,
  '23514',
  'system actors cannot carry account IDs'
);
select throws_ok(
  $$insert into public.runs (
      run_id, project_pk, run_kind, mode, status, requested_actor_type,
      requested_at, started_at, engine_repository, engine_commit,
      engine_interface_version, engine_command
    ) values (
      'run:invalid-queued-state', (select id from public.projects), 'full_pipeline',
      'live', 'queued', 'system', now(), now(), 'repo', repeat('d', 40), 'v1',
      'command'
    )$$,
  '23514',
  'queued runs cannot claim a start time'
);
select throws_ok(
  $$insert into public.runs (
      run_id, project_pk, run_kind, mode, status, requested_actor_type,
      finished_at, engine_repository, engine_commit, engine_interface_version,
      engine_command
    ) values (
      'run:failed-without-error', (select id from public.projects), 'full_pipeline',
      'live', 'failed', 'system', now(), 'repo', repeat('d', 40), 'v1', 'command'
    )$$,
  '23514',
  'failed runs require structured error evidence'
);
select throws_ok(
  $$delete from public.projects where project_id = 'project:australian-butterflies'$$,
  '23503',
  'projects with runs cannot be deleted'
);
select is(
  (select status from public.runs where run_id = 'run:reference-bank:test'),
  'queued',
  'failed fixture inserts do not mutate the valid run'
);

select * from finish();
rollback;
