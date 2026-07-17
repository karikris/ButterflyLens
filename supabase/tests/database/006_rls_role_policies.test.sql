begin;

create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(44);

select has_table('public', 'project_memberships', 'project memberships table exists');
select ok((select relrowsecurity from pg_class where oid = 'public.project_memberships'::regclass), 'memberships have RLS');
select has_index('public', 'project_memberships', 'project_memberships_project_pk_idx', 'membership project FK is indexed');
select has_index('public', 'project_memberships', 'project_memberships_reviewer_profile_pk_idx', 'membership profile FK is indexed');
select has_index('public', 'project_memberships', 'project_memberships_auth_project_role_idx', 'membership role lookup is indexed');
select has_index('public', 'project_memberships', 'project_memberships_approver_pk_idx', 'membership approver FK is indexed');

select ok(exists(select 1 from pg_policies where schemaname='public' and policyname='projects_public_read'), 'active projects have public read policy');
select ok(exists(select 1 from pg_policies where schemaname='public' and policyname='species_public_read'), 'accepted species have public read policy');
select ok(exists(select 1 from pg_policies where schemaname='public' and policyname='geographic_impact_public_read'), 'public impact has read policy');
select ok(exists(select 1 from pg_policies where schemaname='public' and policyname='release_candidates_public_read'), 'approved release candidates have public policy');
select ok(exists(select 1 from pg_policies where schemaname='public' and policyname='reviewer_profiles_self_update'), 'profile has narrow self-update policy');
select ok(exists(select 1 from pg_policies where schemaname='public' and policyname='project_memberships_self_read'), 'membership has self-read policy');
select ok(exists(select 1 from pg_policies where schemaname='public' and policyname='project_memberships_curator_read'), 'membership has curator policy');
select ok(exists(select 1 from pg_policies where schemaname='public' and policyname='api_requests_curator_read'), 'physical requests are curator-only');
select ok(exists(select 1 from pg_policies where schemaname='public' and policyname='model_evidence_curator_read'), 'raw model evidence is curator-only');
select ok(exists(select 1 from pg_policies where schemaname='public' and policyname='verification_campaigns_member_read'), 'members can read non-draft campaigns');
select ok(exists(select 1 from pg_policies where schemaname='public' and policyname='verification_campaigns_curator_all'), 'curators manage campaigns');
select ok(exists(select 1 from pg_policies where schemaname='public' and policyname='assignments_self_read'), 'reviewers read own assignments');
select ok(exists(select 1 from pg_policies where schemaname='public' and policyname='review_events_self_insert'), 'reviewers insert own review events');
select ok(exists(select 1 from pg_policies where schemaname='public' and policyname='review_events_curator_read'), 'curators inspect review events');
select ok(exists(select 1 from pg_policies where schemaname='public' and policyname='consensus_respondent_read'), 'consensus remains blind until response');
select ok(exists(select 1 from pg_policies where schemaname='public' and policyname='reviewer_reliability_self_read'), 'reliability is private to self');
select ok(exists(select 1 from pg_policies where schemaname='public' and policyname='quality_snapshots_member_read'), 'members read quality snapshots');
select ok(exists(select 1 from pg_policies where schemaname='public' and policyname='release_candidates_curator_read'), 'curators inspect blocked candidates');

select ok(has_column_privilege('anon', 'public.projects', 'slug', 'select'), 'anon can query safe public project columns');
select ok(not has_column_privilege('anon', 'public.projects', 'created_by', 'select'), 'anon cannot read project auth identity');
select ok(not has_table_privilege('anon', 'public.api_requests', 'select'), 'anon cannot query provider requests');
select ok(has_table_privilege('authenticated', 'public.project_memberships', 'select'), 'authenticated can query membership through RLS');
select ok(not has_table_privilege('authenticated', 'public.project_memberships', 'insert'), 'authenticated cannot self-assign project role');
select ok(has_table_privilege('authenticated', 'public.review_events', 'insert'), 'authenticated reviewer can submit through RLS');
select ok(not has_table_privilege('authenticated', 'public.review_events', 'update'), 'review events remain append-only');
select ok(not has_table_privilege('authenticated', 'public.release_candidates', 'insert'), 'browser roles cannot create releases');
select ok(has_table_privilege('authenticated', 'public.verification_campaigns', 'insert'), 'curator campaign insert is policy-gated');

select ok((
  select function.prosecdef and function.proconfig @> array['search_path=""']
  from pg_proc function join pg_namespace namespace on namespace.oid=function.pronamespace
  where namespace.nspname='private' and function.proname='has_project_role'
), 'role helper is fixed-search-path security definer in private schema');
select ok((
  select not has_function_privilege('anon', function.oid, 'execute')
    and has_function_privilege('authenticated', function.oid, 'execute')
  from pg_proc function join pg_namespace namespace on namespace.oid=function.pronamespace
  where namespace.nspname='private' and function.proname='has_project_role'
), 'role helper execution is restricted to authenticated');

insert into auth.users (id) values
  ('00000000-0000-4000-8000-000000000010'),
  ('00000000-0000-4000-8000-000000000011'),
  ('00000000-0000-4000-8000-000000000012');
insert into public.reviewer_profiles (
  reviewer_profile_id, auth_user_id, public_name, role, qualification_state
) values
  ('reviewer:admin', '00000000-0000-4000-8000-000000000010', 'Admin Butterfly', 'administrator', 'unverified'),
  ('reviewer:member', '00000000-0000-4000-8000-000000000011', 'Member Butterfly', 'reviewer', 'unverified');
insert into public.projects (
  project_id, slug, name, status, boundary_id, boundary_version, boundary_sha256,
  sensitive_coordinate_policy_version, root_taxon_keys, taxonomy_fingerprint,
  search_plan_fingerprint, public_discovery_claim, data_policy_version,
  consent_policy_version
) values
  ('project:rls-active', 'rls-active', 'RLS active', 'active', 'boundary:australia',
   'v1', repeat('a',64), 'v1', array['bltx:v1:test'], repeat('b',64), repeat('c',64),
   'All butterfly candidate images discoverable through the published ButterflyLens Flickr search plan.', 'v1', 'v1'),
  ('project:rls-draft', 'rls-draft', 'RLS draft', 'draft', 'boundary:australia',
   'v1', repeat('d',64), 'v1', array['bltx:v1:test'], repeat('e',64), repeat('f',64),
   'All butterfly candidate images discoverable through the published ButterflyLens Flickr search plan.', 'v1', 'v1');
insert into public.project_memberships (
  project_membership_id, project_pk, reviewer_profile_pk, auth_user_id,
  role, status, approved_by_reviewer_pk
) select 'membership:admin-active', p.id, r.id, r.auth_user_id,
  'administrator', 'active', r.id
from public.projects p cross join public.reviewer_profiles r
where p.project_id='project:rls-active' and r.reviewer_profile_id='reviewer:admin';
insert into public.project_memberships (
  project_membership_id, project_pk, reviewer_profile_pk, auth_user_id,
  role, status, approved_by_reviewer_pk
) select 'membership:member-active', p.id, member.id, member.auth_user_id,
  'reviewer', 'active', admin.id
from public.projects p cross join public.reviewer_profiles member
cross join public.reviewer_profiles admin
where p.project_id='project:rls-active'
  and member.reviewer_profile_id='reviewer:member'
  and admin.reviewer_profile_id='reviewer:admin';
insert into public.project_memberships (
  project_membership_id, project_pk, reviewer_profile_pk, auth_user_id,
  role, status, approved_by_reviewer_pk
) select 'membership:member-draft', p.id, member.id, member.auth_user_id,
  'reviewer', 'active', admin.id
from public.projects p cross join public.reviewer_profiles member
cross join public.reviewer_profiles admin
where p.project_id='project:rls-draft'
  and member.reviewer_profile_id='reviewer:member'
  and admin.reviewer_profile_id='reviewer:admin';

set local role anon;
select is((select count(*) from public.projects), 1::bigint, 'anon sees active project only');
reset role;

select set_config('request.jwt.claim.sub', '00000000-0000-4000-8000-000000000011', true);
set local role authenticated;
select is((select count(*) from public.projects), 2::bigint, 'member sees active and own draft project');
select is((select count(*) from public.project_memberships), 2::bigint, 'member sees only own memberships');
select is((select count(*) from public.reviewer_profiles), 1::bigint, 'member sees own profile only');
select throws_ok(
  $$update public.reviewer_profiles set role='administrator' where reviewer_profile_id='reviewer:member'$$,
  '42501', 'reviewer cannot elevate role through profile update'
);
reset role;

select set_config('request.jwt.claim.sub', '00000000-0000-4000-8000-000000000010', true);
set local role authenticated;
select is((select count(*) from public.project_memberships), 2::bigint, 'administrator sees memberships only in administered project');
select is((select count(*) from public.reviewer_profiles), 2::bigint, 'administrator sees project reviewer profiles');
reset role;

select set_config('request.jwt.claim.sub', '00000000-0000-4000-8000-000000000012', true);
set local role authenticated;
select is((select count(*) from public.projects), 1::bigint, 'authenticated non-member receives public project projection only');
select is((select count(*) from public.project_memberships), 0::bigint, 'authenticated non-member has no project authority');
reset role;

select * from finish();
rollback;
