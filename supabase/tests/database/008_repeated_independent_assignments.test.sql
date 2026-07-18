begin;

create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(21);

select has_table(
  'private', 'review_assignment_policies',
  'server-only repeated assignment policy table exists'
);
select has_column('public', 'assignments', 'assignment_reason');
select has_column('public', 'assignments', 'required_reviewer_role');
select has_column('public', 'assignments', 'assignment_policy_version');
select has_function(
  'private', 'review_assignment_progress', array['bigint', 'bigint'],
  'server-only assignment progress function exists'
);
select ok(not has_table_privilege(
  'anon', 'private.review_assignment_policies', 'select'
), 'guests cannot inspect assignment policy state');
select ok(not has_table_privilege(
  'authenticated', 'private.review_assignment_policies', 'select'
), 'reviewers cannot inspect server assignment policy state');
select ok(not has_function_privilege(
  'anon', 'private.review_assignment_progress(bigint,bigint)', 'execute'
), 'guests cannot inspect assignment progress');
select ok(not has_function_privilege(
  'authenticated', 'private.review_assignment_progress(bigint,bigint)', 'execute'
), 'reviewers cannot inspect aggregate progress before decision');
select ok(has_function_privilege(
  'service_role', 'private.review_assignment_progress(bigint,bigint)', 'execute'
), 'server may inspect assignment progress');
select ok(has_schema_privilege(
  'service_role', 'private', 'usage'
), 'server has explicit access to the private assignment schema');

select is((
  select default_review_count from private.review_assignment_policies
  where campaign_kind = 'ordinary_image'
), 2::smallint, 'ordinary images default to two reviewers');
select is((
  select default_review_count from private.review_assignment_policies
  where campaign_kind = 'disagreement'
), 3::smallint, 'disagreement requires a third reviewer');
select is((
  select minimum_review_count from private.review_assignment_policies
  where campaign_kind = 'potential_gap'
), 3::smallint, 'potential gaps start at three reviewers');
select is((
  select maximum_review_count from private.review_assignment_policies
  where campaign_kind = 'potential_gap'
), 5::smallint, 'potential gaps allow up to five reviewers');
select is((
  select default_review_count from private.review_assignment_policies
  where campaign_kind = 'reference_image'
), 2::smallint, 'reference images default to two reviewers');
select is((
  select minimum_qualified_review_count from private.review_assignment_policies
  where campaign_kind = 'high_impact_release'
), 2::smallint, 'high-impact releases require qualified reviews');
select is((
  select expert_gate_required from private.review_assignment_policies
  where campaign_kind = 'high_impact_release'
), true, 'high-impact releases require an expert gate');
select is((
  select count(*) from private.review_assignment_policies
), 5::bigint, 'the required assignment policy set is closed');
select ok((
  select bool_and(policy_version = 'repeated-independent-v1')
  from private.review_assignment_policies
), 'every assignment policy has the pinned version');
select ok((
  select bool_and(default_review_count between minimum_review_count and maximum_review_count)
  from private.review_assignment_policies
), 'every default lies within its permitted review range');

select * from finish();
rollback;
