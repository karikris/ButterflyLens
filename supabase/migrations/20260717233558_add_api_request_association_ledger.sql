alter table public.query_associations
drop constraint query_associations_relationship_check;

alter table public.query_associations
add constraint query_associations_relationship_check
check (
  relationship in (
    'accepted_name', 'synonym', 'english_vernacular', 'trusted_vernacular',
    'authorized_first_nations_name', 'genus', 'family', 'order',
    'broad_butterfly', 'global_out_of_range'
  )
);

create table public.api_request_associations (
  id bigint generated always as identity primary key,
  api_request_association_id text not null,
  api_request_pk bigint not null references public.api_requests (id) on delete restrict,
  query_association_pk bigint not null references public.query_associations (id) on delete restrict,
  query_request_link_id text not null,
  link_fingerprint text not null,
  created_at timestamptz not null default now(),
  constraint api_request_associations_id_check
    check (api_request_association_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint api_request_associations_query_link_id_check
    check (query_request_link_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint api_request_associations_fingerprint_check
    check (link_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint api_request_associations_id_key unique (api_request_association_id),
  constraint api_request_associations_link_fingerprint_key unique (link_fingerprint),
  constraint api_request_associations_logical_key
    unique (api_request_pk, query_association_pk)
);

create index api_request_associations_query_association_pk_idx
on public.api_request_associations (query_association_pk);

alter table public.api_request_associations enable row level security;

revoke all on table public.api_request_associations
from public, anon, authenticated;
revoke all on sequence public.api_request_associations_id_seq
from public, anon, authenticated;

grant select, insert on table public.api_request_associations to service_role;
grant usage, select on sequence public.api_request_associations_id_seq to service_role;

comment on table public.api_request_associations is
  'Append-only links retaining every logical query association behind each deduplicated physical Flickr request; query terms are discovery evidence, never taxon labels.';
