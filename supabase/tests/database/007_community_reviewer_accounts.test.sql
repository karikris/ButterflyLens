begin;

create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(15);

select has_function(
  'public', 'register_reviewer', array['text', 'text'],
  'community reviewer registration RPC exists'
);
select ok((
  select function.prosecdef and function.proconfig @> array['search_path=""']
  from pg_proc function
  join pg_namespace namespace on namespace.oid = function.pronamespace
  where namespace.nspname = 'public' and function.proname = 'register_reviewer'
), 'registration RPC is fixed-search-path security definer');
select ok(not has_function_privilege(
  'anon', 'public.register_reviewer(text,text)', 'execute'
), 'guest role cannot register a reviewer');
select ok(has_function_privilege(
  'authenticated', 'public.register_reviewer(text,text)', 'execute'
), 'authenticated role can call reviewer registration');
select col_type_is(
  'public', 'project_memberships', 'enrollment_kind', 'text',
  'membership records its enrollment kind'
);

insert into public.projects (
  project_id, slug, name, status, boundary_id, boundary_version, boundary_sha256,
  sensitive_coordinate_policy_version, root_taxon_keys, taxonomy_fingerprint,
  search_plan_fingerprint, public_discovery_claim, data_policy_version,
  consent_policy_version
) values (
  'project:community-auth', 'community-auth', 'Community auth', 'active',
  'boundary:australia', 'v1', repeat('a', 64), 'v1',
  array['bltx:v1:test'], repeat('b', 64), repeat('c', 64),
  'All butterfly candidate images discoverable through the published ButterflyLens Flickr search plan.',
  'v1', 'v1'
);

insert into auth.users (id, is_anonymous) values
  ('00000000-0000-4000-8000-000000000021', false),
  ('00000000-0000-4000-8000-000000000022', true);

select set_config('request.jwt.claim.sub', '00000000-0000-4000-8000-000000000021', true);
set local role authenticated;
select lives_ok(
  $$select * from public.register_reviewer('project:community-auth', 'Golden Sun')$$,
  'permanent account can register with a pseudonym'
);
select lives_ok(
  $$select * from public.register_reviewer('project:community-auth', 'Ignored Rename')$$,
  'registration is idempotent'
);
reset role;

select is((
  select count(*) from public.reviewer_profiles
  where auth_user_id = '00000000-0000-4000-8000-000000000021'
), 1::bigint, 'one profile is created for the Auth user');
select is((
  select public_name from public.reviewer_profiles
  where auth_user_id = '00000000-0000-4000-8000-000000000021'
), 'Golden Sun', 'idempotent registration preserves the original pseudonym');
select is((
  select role from public.reviewer_profiles
  where auth_user_id = '00000000-0000-4000-8000-000000000021'
), 'reviewer', 'self-service profile has only the base reviewer role');
select is((
  select membership.role from public.project_memberships membership
  where membership.auth_user_id = '00000000-0000-4000-8000-000000000021'
), 'reviewer', 'self-service project authority has only reviewer role');
select is((
  select membership.enrollment_kind from public.project_memberships membership
  where membership.auth_user_id = '00000000-0000-4000-8000-000000000021'
), 'self_service', 'membership records self-service enrollment');
select ok((
  select membership.status = 'active' and membership.approved_by_reviewer_pk is null
  from public.project_memberships membership
  where membership.auth_user_id = '00000000-0000-4000-8000-000000000021'
), 'base reviewer is active without fabricated privileged approval');

select set_config('request.jwt.claim.sub', '00000000-0000-4000-8000-000000000022', true);
set local role authenticated;
select throws_ok(
  $$select * from public.register_reviewer('project:community-auth', 'Temporary Blue')$$,
  '42501', 'reviewer registration requires a permanent account',
  'anonymous Auth user cannot become a registered reviewer'
);
reset role;

select throws_ok(
  $$insert into public.project_memberships (
      project_membership_id, project_pk, reviewer_profile_pk, auth_user_id,
      role, status, enrollment_kind
    ) select 'membership:invalid-expert', project.id, profile.id,
      profile.auth_user_id, 'expert', 'active', 'self_service'
    from public.projects project
    join public.reviewer_profiles profile
      on profile.auth_user_id = '00000000-0000-4000-8000-000000000021'
    where project.project_id = 'project:community-auth'$$,
  '23514', 'expert membership requires verified expert profile',
  'self-service enrollment cannot create a privileged role'
);

select * from finish();
rollback;
