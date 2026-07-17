-- ButterflyLens 3.1.2: discovery plans, physical requests, and source records.
-- This migration creates storage contracts only and performs no Flickr call.

create table public.species (
  id bigint generated always as identity primary key,
  species_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  butterflylens_taxon_key text not null,
  accepted_scientific_name text not null,
  taxonomy_fingerprint text not null,
  taxon_source text not null,
  taxon_source_id text not null,
  status text not null default 'accepted',
  created_at timestamptz not null default now(),
  constraint species_species_id_check
    check (species_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint species_taxon_key_check
    check (butterflylens_taxon_key ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint species_name_check check (length(accepted_scientific_name) between 1 and 240),
  constraint species_taxonomy_fingerprint_check
    check (taxonomy_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint species_source_check
    check (length(taxon_source) between 1 and 160 and length(taxon_source_id) between 1 and 500),
  constraint species_status_check check (status in ('accepted', 'excluded', 'retired')),
  constraint species_species_id_key unique (species_id),
  constraint species_project_taxon_key unique (project_pk, butterflylens_taxon_key)
);

create index species_project_pk_idx on public.species (project_pk);

create table public.name_assertions (
  id bigint generated always as identity primary key,
  assertion_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  species_pk bigint references public.species (id) on delete restrict,
  taxon_key text not null,
  name_text text not null,
  normalized_name text not null,
  name_type text not null,
  language_code text not null,
  region_code text not null,
  trust_tier text not null,
  review_state text not null,
  query_eligible boolean not null default false,
  query_eligibility_reason text not null,
  homonym_risk text not null,
  source_provider text not null,
  source_dataset text not null,
  source_url text not null,
  source_version text not null,
  source_response_sha256 text,
  retrieved_at timestamptz not null,
  assertion_fingerprint text not null,
  constraint name_assertions_assertion_id_check
    check (assertion_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint name_assertions_taxon_key_check
    check (taxon_key ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint name_assertions_text_check
    check (length(name_text) between 1 and 500 and length(normalized_name) between 1 and 500),
  constraint name_assertions_type_check
    check (name_type in ('accepted_scientific', 'scientific_synonym', 'english_vernacular', 'first_nations_language')),
  constraint name_assertions_language_check check (language_code ~ '^[a-z0-9-]{2,35}$'),
  constraint name_assertions_region_check check (length(region_code) between 2 and 40),
  constraint name_assertions_trust_check
    check (length(trust_tier) between 1 and 120 and length(review_state) between 1 and 120),
  constraint name_assertions_query_reason_check
    check (length(query_eligibility_reason) between 1 and 240),
  constraint name_assertions_source_check
    check (
      length(source_provider) between 1 and 160
      and length(source_dataset) between 1 and 240
      and source_url ~ '^https://'
      and length(source_version) between 1 and 160
    ),
  constraint name_assertions_source_response_sha256_check
    check (source_response_sha256 is null or source_response_sha256 ~ '^[0-9a-f]{64}$'),
  constraint name_assertions_fingerprint_check
    check (assertion_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint name_assertions_assertion_id_key unique (assertion_id),
  constraint name_assertions_fingerprint_key unique (assertion_fingerprint)
);

create index name_assertions_project_pk_idx on public.name_assertions (project_pk);
create index name_assertions_species_pk_idx on public.name_assertions (species_pk)
where species_pk is not null;
create index name_assertions_query_eligible_idx
on public.name_assertions (project_pk, name_type, normalized_name)
where query_eligible;

create table public.query_definitions (
  id bigint generated always as identity primary key,
  query_definition_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  source_name_assertion_pk bigint references public.name_assertions (id) on delete restrict,
  provider text not null default 'flickr',
  method text not null default 'flickr.photos.search',
  query_term text not null,
  normalized_query_term text not null,
  tier smallint not null,
  trust_tier text not null,
  parameters jsonb not null,
  status text not null default 'planned',
  authorization_state text not null default 'blocked',
  definition_fingerprint text not null,
  created_at timestamptz not null default now(),
  constraint query_definitions_id_check
    check (query_definition_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint query_definitions_provider_check check (provider = 'flickr'),
  constraint query_definitions_method_check check (method = 'flickr.photos.search'),
  constraint query_definitions_term_check
    check (length(query_term) between 1 and 500 and length(normalized_query_term) between 1 and 500),
  constraint query_definitions_tier_check check (tier between 1 and 5),
  constraint query_definitions_trust_check check (length(trust_tier) between 1 and 120),
  constraint query_definitions_parameters_check check (jsonb_typeof(parameters) = 'object'),
  constraint query_definitions_no_secrets_check
    check (
      not (parameters ?| array['api_key', 'api_sig', 'auth_token', 'oauth_token', 'secret'])
    ),
  constraint query_definitions_status_check check (status in ('planned', 'active', 'blocked', 'retired')),
  constraint query_definitions_authorization_check
    check (authorization_state in ('blocked', 'authorized', 'revoked')),
  constraint query_definitions_fingerprint_check
    check (definition_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint query_definitions_id_key unique (query_definition_id),
  constraint query_definitions_project_fingerprint_key unique (project_pk, definition_fingerprint)
);

create index query_definitions_project_pk_idx on public.query_definitions (project_pk);
create index query_definitions_source_name_assertion_pk_idx
on public.query_definitions (source_name_assertion_pk)
where source_name_assertion_pk is not null;
create index query_definitions_active_tier_idx
on public.query_definitions (project_pk, tier, id)
where status = 'active' and authorization_state = 'authorized';

create table public.query_associations (
  id bigint generated always as identity primary key,
  query_association_id text not null,
  query_definition_pk bigint not null references public.query_definitions (id) on delete restrict,
  species_pk bigint not null references public.species (id) on delete restrict,
  name_assertion_pk bigint references public.name_assertions (id) on delete restrict,
  relationship text not null,
  association_reason text not null,
  query_term_is_species_label boolean not null default false,
  association_fingerprint text not null,
  created_at timestamptz not null default now(),
  constraint query_associations_id_check
    check (query_association_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint query_associations_relationship_check
    check (relationship in ('accepted_name', 'synonym', 'english_vernacular', 'authorized_first_nations_name', 'genus', 'family', 'order', 'global_out_of_range')),
  constraint query_associations_reason_check check (length(association_reason) between 1 and 500),
  constraint query_associations_not_label_check check (not query_term_is_species_label),
  constraint query_associations_fingerprint_check
    check (association_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint query_associations_id_key unique (query_association_id),
  constraint query_associations_fingerprint_key unique (association_fingerprint),
  constraint query_associations_logical_key
    unique (query_definition_pk, species_pk, relationship)
);

create index query_associations_query_definition_pk_idx
on public.query_associations (query_definition_pk);
create index query_associations_species_pk_idx on public.query_associations (species_pk);
create index query_associations_name_assertion_pk_idx
on public.query_associations (name_assertion_pk)
where name_assertion_pk is not null;

create table public.api_requests (
  id bigint generated always as identity primary key,
  api_request_id text not null,
  run_pk bigint not null references public.runs (id) on delete restrict,
  query_definition_pk bigint not null references public.query_definitions (id) on delete restrict,
  retry_of_request_pk bigint references public.api_requests (id) on delete restrict,
  provider text not null default 'flickr',
  method text not null,
  endpoint text not null,
  normalized_parameters jsonb not null,
  request_fingerprint text not null,
  status text not null default 'planned',
  requested_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz,
  http_status smallint,
  response_sha256 text,
  response_fingerprint text,
  retry_count smallint not null default 0,
  budget_units smallint not null default 1,
  error_code text,
  constraint api_requests_id_check
    check (api_request_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint api_requests_provider_check check (provider = 'flickr'),
  constraint api_requests_method_check check (length(method) between 1 and 120),
  constraint api_requests_endpoint_check check (endpoint ~ '^https://'),
  constraint api_requests_parameters_check check (jsonb_typeof(normalized_parameters) = 'object'),
  constraint api_requests_no_secrets_check
    check (not (normalized_parameters ?| array['api_key', 'api_sig', 'auth_token', 'oauth_token', 'secret'])),
  constraint api_requests_fingerprint_check check (request_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint api_requests_status_check
    check (status in ('planned', 'started', 'succeeded', 'failed', 'quarantined', 'skipped')),
  constraint api_requests_http_status_check
    check (http_status is null or http_status between 100 and 599),
  constraint api_requests_response_sha256_check
    check (response_sha256 is null or response_sha256 ~ '^[0-9a-f]{64}$'),
  constraint api_requests_response_fingerprint_check
    check (response_fingerprint is null or response_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint api_requests_retry_check check (retry_count >= 0 and budget_units = 1),
  constraint api_requests_timestamps_check
    check (
      (started_at is null or started_at >= requested_at)
      and (completed_at is null or completed_at >= coalesce(started_at, requested_at))
    ),
  constraint api_requests_completion_check
    check (
      status not in ('succeeded', 'failed', 'quarantined', 'skipped')
      or completed_at is not null
    ),
  constraint api_requests_success_check
    check (
      status <> 'succeeded'
      or (http_status between 200 and 299 and response_sha256 is not null and response_fingerprint is not null)
    ),
  constraint api_requests_id_key unique (api_request_id),
  constraint api_requests_run_fingerprint_key unique (run_pk, request_fingerprint)
);

create index api_requests_run_pk_requested_at_idx on public.api_requests (run_pk, requested_at);
create index api_requests_query_definition_pk_idx on public.api_requests (query_definition_pk);
create index api_requests_retry_of_request_pk_idx on public.api_requests (retry_of_request_pk)
where retry_of_request_pk is not null;
create index api_requests_active_idx on public.api_requests (status, requested_at)
where status in ('planned', 'started');

create table public.flickr_photos (
  id bigint generated always as identity primary key,
  flickr_record_id text not null,
  api_request_pk bigint not null references public.api_requests (id) on delete restrict,
  flickr_photo_id text not null,
  owner_nsid text not null,
  owner_display_name text,
  title text not null default '',
  description text not null default '',
  source_url text not null,
  licence_id text,
  licence_url text,
  date_posted timestamptz,
  date_taken timestamptz,
  observed_at timestamptz not null,
  visibility_state text not null,
  safety_level smallint,
  media_kind text not null default 'photo',
  rights_status text not null default 'unknown',
  download_allowed boolean not null default false,
  model_inference_allowed boolean not null default false,
  display_allowed boolean not null default false,
  redistribution_allowed boolean not null default false,
  source_record jsonb not null,
  source_record_sha256 text not null,
  source_record_fingerprint text not null,
  is_current boolean not null default true,
  removed_at timestamptz,
  constraint flickr_photos_record_id_check
    check (flickr_record_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint flickr_photos_photo_id_check check (flickr_photo_id ~ '^[0-9]+$'),
  constraint flickr_photos_owner_check check (length(owner_nsid) between 1 and 120),
  constraint flickr_photos_text_check
    check (length(title) <= 1000 and length(description) <= 10000),
  constraint flickr_photos_source_url_check check (source_url ~ '^https://www\.flickr\.com/'),
  constraint flickr_photos_licence_url_check check (licence_url is null or licence_url ~ '^https://'),
  constraint flickr_photos_visibility_check
    check (visibility_state in ('public', 'private', 'deleted', 'unavailable')),
  constraint flickr_photos_safety_check check (safety_level is null or safety_level between 1 and 3),
  constraint flickr_photos_media_kind_check check (media_kind = 'photo'),
  constraint flickr_photos_rights_check
    check (rights_status in ('unknown', 'allowed', 'blocked', 'quarantined', 'removed')),
  constraint flickr_photos_unknown_blocks_use_check
    check (
      rights_status = 'allowed'
      or not (download_allowed or model_inference_allowed or display_allowed or redistribution_allowed)
    ),
  constraint flickr_photos_source_record_check check (jsonb_typeof(source_record) = 'object'),
  constraint flickr_photos_no_secrets_check
    check (not (source_record ?| array['api_key', 'api_sig', 'auth_token', 'oauth_token', 'secret'])),
  constraint flickr_photos_sha256_check check (source_record_sha256 ~ '^[0-9a-f]{64}$'),
  constraint flickr_photos_fingerprint_check check (source_record_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint flickr_photos_removal_check
    check (
      (visibility_state in ('deleted', 'unavailable') or rights_status = 'removed')
      = (removed_at is not null)
    ),
  constraint flickr_photos_record_id_key unique (flickr_record_id),
  constraint flickr_photos_source_fingerprint_key unique (source_record_fingerprint),
  constraint flickr_photos_version_key unique (flickr_photo_id, source_record_fingerprint)
);

create index flickr_photos_api_request_pk_idx on public.flickr_photos (api_request_pk);
create index flickr_photos_photo_id_observed_at_idx
on public.flickr_photos (flickr_photo_id, observed_at desc);
create unique index flickr_photos_one_current_idx
on public.flickr_photos (flickr_photo_id)
where is_current;
create index flickr_photos_removal_due_idx on public.flickr_photos (removed_at)
where removed_at is not null;

alter table public.species enable row level security;
alter table public.name_assertions enable row level security;
alter table public.query_definitions enable row level security;
alter table public.query_associations enable row level security;
alter table public.api_requests enable row level security;
alter table public.flickr_photos enable row level security;

revoke all on table public.species, public.name_assertions, public.query_definitions,
  public.query_associations, public.api_requests, public.flickr_photos
from public, anon, authenticated;
revoke all on sequence public.species_id_seq, public.name_assertions_id_seq,
  public.query_definitions_id_seq, public.query_associations_id_seq,
  public.api_requests_id_seq, public.flickr_photos_id_seq
from public, anon, authenticated;

grant select, insert, update, delete on table public.species,
  public.name_assertions, public.query_definitions, public.query_associations,
  public.api_requests, public.flickr_photos to service_role;
grant usage, select on sequence public.species_id_seq,
  public.name_assertions_id_seq, public.query_definitions_id_seq,
  public.query_associations_id_seq, public.api_requests_id_seq,
  public.flickr_photos_id_seq to service_role;

comment on table public.query_associations is
  'Logical species/name associations retained independently from deduplicated physical requests; query terms are never labels.';
comment on table public.api_requests is
  'One physical Flickr request per run fingerprint; secrets and provider credentials are forbidden.';
comment on table public.flickr_photos is
  'Versioned immutable-identity Flickr source records; API access does not imply media-use permission.';
