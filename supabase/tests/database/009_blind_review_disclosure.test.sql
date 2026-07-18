begin;

create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(18);

select has_table('public', 'review_disclosures', 'review disclosure table exists');
select has_column('public', 'review_disclosures', 'revealed_after_event_pk');
select has_column('public', 'review_disclosures', 'model_label');
select has_column('public', 'review_disclosures', 'model_score_band');
select has_column('public', 'review_disclosures', 'flickr_query_term');
select has_column('public', 'review_disclosures', 'source_comment_excerpt');
select has_column('public', 'review_disclosures', 'peer_decisive_count');
select has_view('public', 'blind_review_assignments', 'blind assignment view exists');
select has_view(
  'public', 'post_decision_review_disclosures',
  'post-decision disclosure view exists'
);
select ok((
  select relrowsecurity from pg_class where oid = 'public.review_disclosures'::regclass
), 'review disclosures have RLS');
select ok(not has_table_privilege(
  'anon', 'public.review_disclosures', 'select'
), 'guests cannot read review disclosures');
select ok(not has_table_privilege(
  'authenticated', 'public.review_disclosures', 'insert'
), 'reviewers cannot create their own disclosures');
select ok(has_table_privilege(
  'authenticated', 'public.review_disclosures', 'select'
), 'authenticated reviewers may reach respondent-filtered disclosures');
select ok(has_table_privilege(
  'service_role', 'public.review_disclosures', 'insert'
), 'server can create allowlisted disclosures');
select ok(not has_column_privilege(
  'authenticated', 'public.media_objects', 'storage_key', 'select'
), 'reviewers cannot read private media storage keys');
select ok(has_column_privilege(
  'authenticated', 'public.media_objects', 'content_sha256', 'select'
), 'reviewers can verify assigned media content identity');
select ok(not has_table_privilege(
  'authenticated', 'public.model_evidence', 'select'
), 'model evidence remains hidden before decision');
select ok(not has_table_privilege(
  'authenticated', 'public.query_definitions', 'select'
), 'Flickr query terms remain hidden before decision');

select * from finish();
rollback;
