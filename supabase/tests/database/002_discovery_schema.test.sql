begin;

create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(31);

select has_table('public', 'species', 'species table exists');
select has_table('public', 'name_assertions', 'name assertions table exists');
select has_table('public', 'query_definitions', 'query definitions table exists');
select has_table('public', 'query_associations', 'query associations table exists');
select has_table('public', 'api_requests', 'API requests table exists');
select has_table('public', 'flickr_photos', 'Flickr source records table exists');

select ok((select relrowsecurity from pg_class where oid = 'public.species'::regclass), 'species has RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.name_assertions'::regclass), 'names have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.query_definitions'::regclass), 'definitions have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.query_associations'::regclass), 'associations have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.api_requests'::regclass), 'requests have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.flickr_photos'::regclass), 'photos have RLS');

select has_index('public', 'species', 'species_project_pk_idx', 'species project FK is indexed');
select has_index('public', 'name_assertions', 'name_assertions_species_pk_idx', 'name species FK is indexed');
select has_index('public', 'query_definitions', 'query_definitions_project_pk_idx', 'definition project FK is indexed');
select has_index('public', 'query_associations', 'query_associations_species_pk_idx', 'association species FK is indexed');
select has_index('public', 'api_requests', 'api_requests_run_pk_requested_at_idx', 'request run FK is indexed');
select has_index('public', 'flickr_photos', 'flickr_photos_api_request_pk_idx', 'photo request FK is indexed');
select ok(not has_table_privilege('anon', 'public.flickr_photos', 'select'), 'anon cannot read source records');
select ok(not has_table_privilege('authenticated', 'public.api_requests', 'insert'), 'authenticated cannot spend budget');

insert into public.projects (
  project_id, slug, name, boundary_id, boundary_version, boundary_sha256,
  sensitive_coordinate_policy_version, root_taxon_keys, taxonomy_fingerprint,
  search_plan_fingerprint, public_discovery_claim, data_policy_version,
  consent_policy_version
) values (
  'project:discovery-test', 'discovery-test', 'Discovery test',
  'boundary:australia', 'v1', repeat('a', 64), 'v1',
  array['bltx:v1:846e98d50678dffa38d43103'], repeat('b', 64), repeat('c', 64),
  'All butterfly candidate images discoverable through the published ButterflyLens Flickr search plan.',
  'v1', 'v1'
);
insert into public.runs (
  run_id, project_pk, run_kind, mode, status, requested_actor_type,
  engine_repository, engine_commit, engine_interface_version, engine_command
) select 'run:discovery-test', id, 'flickr_discovery', 'replay', 'queued',
  'system', 'karikris/ButterflyLens', repeat('d', 40), 'v1', 'synthetic test'
from public.projects where project_id = 'project:discovery-test';
insert into public.species (
  species_id, project_pk, butterflylens_taxon_key, accepted_scientific_name,
  taxonomy_fingerprint, taxon_source, taxon_source_id
) select 'species:test', id, 'bltx:v1:test', 'Papilio testus', repeat('b', 64),
  'Australian Faunal Directory', 'afd:test'
from public.projects where project_id = 'project:discovery-test';
insert into public.name_assertions (
  assertion_id, project_pk, species_pk, taxon_key, name_text, normalized_name,
  name_type, language_code, region_code, trust_tier, review_state,
  query_eligible, query_eligibility_reason, homonym_risk, source_provider,
  source_dataset, source_url, source_version, retrieved_at, assertion_fingerprint
) select 'assertion:test', p.id, s.id, s.butterflylens_taxon_key,
  s.accepted_scientific_name, 'papilio testus', 'accepted_scientific', 'zxx',
  'AU', 'accepted_authority', 'source_assertion_unreviewed', true,
  'trusted_scientific_name_unique_in_pack', 'none_detected_in_pack',
  'Australian Faunal Directory', 'AFD', 'https://example.test/afd', 'v1',
  now(), repeat('e', 64)
from public.projects p join public.species s on s.project_pk = p.id
where p.project_id = 'project:discovery-test';
insert into public.query_definitions (
  query_definition_id, project_pk, source_name_assertion_pk, query_term,
  normalized_query_term, tier, trust_tier, parameters, status,
  authorization_state, definition_fingerprint
) select 'query:test', p.id, n.id, 'Papilio testus', 'papilio testus', 1,
  'accepted_authority', '{"text":"Papilio testus"}'::jsonb, 'active',
  'authorized', repeat('f', 64)
from public.projects p join public.name_assertions n on n.project_pk = p.id
where p.project_id = 'project:discovery-test';
insert into public.query_associations (
  query_association_id, query_definition_pk, species_pk, name_assertion_pk,
  relationship, association_reason, association_fingerprint
) select 'association:test', q.id, s.id, n.id, 'accepted_name',
  'logical association retained independently', repeat('1', 64)
from public.query_definitions q
join public.name_assertions n on n.id = q.source_name_assertion_pk
join public.species s on s.id = n.species_pk;
insert into public.api_requests (
  api_request_id, run_pk, query_definition_pk, method, endpoint,
  normalized_parameters, request_fingerprint, status, started_at, completed_at,
  http_status, response_sha256, response_fingerprint
) select 'request:test', r.id, q.id, 'flickr.photos.search',
  'https://www.flickr.com/services/rest', '{"text":"Papilio testus"}'::jsonb,
  repeat('2', 64), 'succeeded', now(), now(), 200, repeat('3', 64), repeat('4', 64)
from public.runs r cross join public.query_definitions q
where r.run_id = 'run:discovery-test' and q.query_definition_id = 'query:test';
insert into public.flickr_photos (
  flickr_record_id, api_request_pk, flickr_photo_id, owner_nsid, title,
  source_url, observed_at, visibility_state, rights_status, source_record,
  source_record_sha256, source_record_fingerprint
) select 'flickr-record:test', id, '123456789', 'owner@test', 'Synthetic',
  'https://www.flickr.com/photos/owner/123456789', now(), 'public', 'unknown',
  '{"id":"123456789"}'::jsonb, repeat('5', 64), repeat('6', 64)
from public.api_requests where api_request_id = 'request:test';

select is((select count(*) from public.species), 1::bigint, 'valid species inserts');
select is((select count(*) from public.name_assertions), 1::bigint, 'valid name inserts');
select is((select count(*) from public.query_definitions), 1::bigint, 'valid definition inserts');
select is((select count(*) from public.query_associations), 1::bigint, 'valid association inserts');
select is((select count(*) from public.api_requests), 1::bigint, 'valid request inserts');
select is((select count(*) from public.flickr_photos), 1::bigint, 'valid source record inserts');

select throws_ok(
  $$update public.query_definitions set parameters = '{"api_key":"forbidden"}'::jsonb$$,
  '23514', 'query definitions reject secrets'
);
select throws_ok(
  $$update public.query_associations set query_term_is_species_label = true$$,
  '23514', 'query terms cannot become species labels'
);
select throws_ok(
  $$update public.flickr_photos set display_allowed = true where rights_status = 'unknown'$$,
  '23514', 'unknown rights block media use'
);
select throws_ok(
  $$insert into public.flickr_photos (
      flickr_record_id, api_request_pk, flickr_photo_id, owner_nsid, source_url,
      observed_at, visibility_state, rights_status, source_record,
      source_record_sha256, source_record_fingerprint
    ) select 'flickr-record:duplicate-current', id, '123456789', 'owner@test',
      'https://www.flickr.com/photos/owner/123456789', now(), 'public', 'unknown',
      '{"id":"123456789","version":2}'::jsonb, repeat('7',64), repeat('8',64)
    from public.api_requests where api_request_id = 'request:test'$$,
  '23505', 'one current projection is allowed per Flickr photo'
);
select throws_ok(
  $$update public.api_requests set normalized_parameters = '{"oauth_token":"forbidden"}'::jsonb$$,
  '23514', 'physical request records reject credentials'
);

select * from finish();
rollback;
