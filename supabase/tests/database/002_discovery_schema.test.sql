begin;

create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(44);

select has_table('public', 'species', 'species table exists');
select has_table('public', 'name_assertions', 'name assertions table exists');
select has_table('public', 'query_definitions', 'query definitions table exists');
select has_table('public', 'query_associations', 'query associations table exists');
select has_table('public', 'api_requests', 'API requests table exists');
select has_table('public', 'api_request_associations', 'request association ledger exists');
select has_table('public', 'flickr_photos', 'Flickr source records table exists');

select ok((select relrowsecurity from pg_class where oid = 'public.species'::regclass), 'species has RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.name_assertions'::regclass), 'names have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.query_definitions'::regclass), 'definitions have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.query_associations'::regclass), 'associations have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.api_requests'::regclass), 'requests have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.api_request_associations'::regclass), 'request association ledger has RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.flickr_photos'::regclass), 'photos have RLS');

select has_index('public', 'species', 'species_project_pk_idx', 'species project FK is indexed');
select has_index('public', 'name_assertions', 'name_assertions_species_pk_idx', 'name species FK is indexed');
select has_index('public', 'query_definitions', 'query_definitions_project_pk_idx', 'definition project FK is indexed');
select has_index('public', 'query_associations', 'query_associations_species_pk_idx', 'association species FK is indexed');
select has_index('public', 'api_requests', 'api_requests_run_pk_requested_at_idx', 'request run FK is indexed');
select has_index('public', 'api_request_associations', 'api_request_associations_query_association_pk_idx', 'request association logical FK is indexed');
select has_index('public', 'flickr_photos', 'flickr_photos_api_request_pk_idx', 'photo request FK is indexed');
select ok(not has_table_privilege('anon', 'public.flickr_photos', 'select'), 'anon cannot read source records');
select ok(not has_table_privilege('authenticated', 'public.api_requests', 'insert'), 'authenticated cannot spend budget');
select ok(not has_table_privilege('authenticated', 'public.api_request_associations', 'insert'), 'authenticated cannot add request associations');
select ok(has_table_privilege('service_role', 'public.api_request_associations', 'insert'), 'service role can append request associations');
select ok(
  (select pg_get_constraintdef(oid) like '%trusted_vernacular%' and pg_get_constraintdef(oid) like '%broad_butterfly%'
   from pg_constraint
   where conrelid = 'public.query_associations'::regclass
     and conname = 'query_associations_relationship_check'),
  'database relationship vocabulary covers every planner relationship'
);

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
insert into public.api_request_associations (
  api_request_association_id, api_request_pk, query_association_pk,
  query_request_link_id, link_fingerprint
) select 'request-association:test', r.id, a.id, 'blql:v1:test', repeat('9', 64)
from public.api_requests r cross join public.query_associations a
where r.api_request_id = 'request:test' and a.query_association_id = 'association:test';
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
select is((select count(*) from public.api_request_associations), 1::bigint, 'valid request association inserts');
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
select throws_ok(
  $$insert into public.api_request_associations (
      api_request_association_id, api_request_pk, query_association_pk,
      query_request_link_id, link_fingerprint
    ) select 'request-association:duplicate', r.id, a.id, 'blql:v1:duplicate',
      repeat('a', 64)
    from public.api_requests r cross join public.query_associations a
    where r.api_request_id = 'request:test' and a.query_association_id = 'association:test'$$,
  '23505', 'one stored link is allowed per request and logical association'
);
select is(
  (select query_term_is_species_label from public.query_associations where query_association_id = 'association:test'),
  false,
  'stored request association remains linked to non-label logical meaning'
);
insert into public.api_requests (
  api_request_id, run_pk, query_definition_pk, retry_of_request_pk, method,
  endpoint, normalized_parameters, request_fingerprint, status, started_at,
  completed_at, http_status, response_sha256, response_fingerprint, retry_count
) select 'request:retry-1', r.run_pk, r.query_definition_pk, r.id,
  'flickr.photos.search', r.endpoint, r.normalized_parameters,
  r.request_fingerprint, 'succeeded', now(), now(), 200,
  repeat('b', 64), repeat('c', 64), 1
from public.api_requests r where r.api_request_id = 'request:test';
select is((select count(*) from public.api_requests), 2::bigint, 'one retry attempt inserts beside its root request');
select is(
  (select retry_count from public.api_requests where api_request_id = 'request:retry-1'),
  1::smallint,
  'retry attempt number is persisted'
);
select throws_ok(
  $$insert into public.api_requests (
      api_request_id, run_pk, query_definition_pk, method, endpoint,
      normalized_parameters, request_fingerprint, status, completed_at,
      http_status, response_sha256, response_fingerprint, retry_count
    ) select 'request:retry-without-parent', run_pk, query_definition_pk,
      method, endpoint, normalized_parameters, request_fingerprint,
      'succeeded', now(), 200, repeat('d', 64), repeat('e', 64), 2
    from public.api_requests where api_request_id = 'request:test'$$,
  '23514', 'retry attempts require parent request lineage'
);
select throws_ok(
  $$insert into public.api_requests (
      api_request_id, run_pk, query_definition_pk, retry_of_request_pk, method,
      endpoint, normalized_parameters, request_fingerprint, status,
      completed_at, http_status, response_sha256, response_fingerprint,
      retry_count
    ) select 'request:duplicate-retry-1', run_pk, query_definition_pk, id,
      method, endpoint, normalized_parameters, request_fingerprint,
      'succeeded', now(), 200, repeat('f', 64), repeat('0', 64), 1
    from public.api_requests where api_request_id = 'request:test'$$,
  '23505', 'one attempt number is allowed per run and physical request'
);

select * from finish();
rollback;
