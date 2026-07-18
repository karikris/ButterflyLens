-- ButterflyLens 13.3: fail-closed sensitive-location publication receipts.
-- No table in this contract stores occurrence latitude or longitude.

create table public.location_source_constraints (
  id bigint generated always as identity primary key,
  location_source_constraint_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  species_pk bigint references public.species (id) on delete restrict,
  provider text not null,
  provider_snapshot_fingerprint text not null,
  disclosure_state text not null,
  location_used_for_target boolean not null,
  provider_precision text,
  flickr_accuracy smallint,
  maximum_public_h3_resolution smallint,
  resolution_mapping_version text,
  permission_evidence_fingerprint text not null,
  constraint_fingerprint text not null,
  scientific_claim_allowed boolean not null default false,
  created_at timestamptz not null default now(),
  constraint location_source_constraints_id_check check (
    location_source_constraint_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'
  ),
  constraint location_source_constraints_provider_check
    check (provider in ('ala', 'flickr')),
  constraint location_source_constraints_snapshot_fingerprint_check
    check (provider_snapshot_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint location_source_constraints_disclosure_check check (
    (provider = 'ala' and disclosure_state in (
      'public_processed', 'public_generalised', 'withheld', 'not_used'
    ))
    or (provider = 'flickr' and disclosure_state in (
      'public_geo', 'nonpublic_geo', 'no_geo', 'not_used'
    ))
  ),
  constraint location_source_constraints_flickr_accuracy_check check (
    (provider = 'ala' and flickr_accuracy is null)
    or (
      provider = 'flickr'
      and (
        (disclosure_state = 'public_geo' and flickr_accuracy between 1 and 16)
        or (disclosure_state <> 'public_geo' and flickr_accuracy is null)
      )
    )
  ),
  constraint location_source_constraints_use_shape_check check (
    (
      location_used_for_target
      and (
        (provider = 'ala' and disclosure_state in ('public_processed', 'public_generalised'))
        or (provider = 'flickr' and disclosure_state = 'public_geo')
      )
      and maximum_public_h3_resolution between 0 and 15
      and length(provider_precision) between 1 and 120
      and length(resolution_mapping_version) between 1 and 120
    )
    or (
      not location_used_for_target
      and maximum_public_h3_resolution is null
    )
  ),
  constraint location_source_constraints_not_used_check
    check (disclosure_state <> 'not_used' or not location_used_for_target),
  constraint location_source_constraints_permission_fingerprint_check
    check (permission_evidence_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint location_source_constraints_fingerprint_check
    check (constraint_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint location_source_constraints_non_scientific_check
    check (not scientific_claim_allowed),
  constraint location_source_constraints_id_key
    unique (location_source_constraint_id),
  constraint location_source_constraints_fingerprint_key
    unique (constraint_fingerprint)
);

create index location_source_constraints_project_species_idx
on public.location_source_constraints (project_pk, species_pk, provider, created_at desc);

create table public.location_publication_receipts (
  id bigint generated always as identity primary key,
  location_publication_receipt_id text not null,
  target_kind text not null,
  geographic_impact_pk bigint references public.geographic_impact (id) on delete restrict,
  release_candidate_pk bigint references public.release_candidates (id) on delete restrict,
  target_fingerprint text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  species_pk bigint references public.species (id) on delete restrict,
  policy_version text not null
    default 'butterflylens-sensitive-location-policy:v1.0.0',
  sensitivity_state text not null,
  policy_action text not null,
  maximum_public_h3_resolution smallint,
  allowed_scope_kinds text[] not null default '{}',
  minimum_public_record_count integer,
  policy_evidence_fingerprint text not null,
  source_constraint_fingerprints text[] not null default '{}',
  publication_state text not null,
  blocker_codes text[] not null default '{}',
  published_scope_kind text,
  published_scope_id text,
  published_h3_resolution smallint,
  published_h3_cell text,
  published_source_precision text,
  effective_maximum_h3_resolution smallint,
  public_record_count integer,
  receipt_fingerprint text not null,
  scientific_claim_allowed boolean not null default false,
  created_at timestamptz not null default now(),
  constraint location_publication_receipts_id_check check (
    location_publication_receipt_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'
  ),
  constraint location_publication_receipts_target_kind_check
    check (target_kind in ('geographic_impact', 'release_candidate')),
  constraint location_publication_receipts_target_shape_check check (
    (
      target_kind = 'geographic_impact'
      and geographic_impact_pk is not null and release_candidate_pk is null
    )
    or (
      target_kind = 'release_candidate'
      and release_candidate_pk is not null and geographic_impact_pk is null
    )
  ),
  constraint location_publication_receipts_target_fingerprint_check
    check (target_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint location_publication_receipts_policy_check
    check (policy_version = 'butterflylens-sensitive-location-policy:v1.0.0'),
  constraint location_publication_receipts_sensitivity_check
    check (sensitivity_state in ('not_sensitive', 'sensitive', 'unknown')),
  constraint location_publication_receipts_action_check
    check (policy_action in ('provider_resolution', 'generalise', 'withhold')),
  constraint location_publication_receipts_rule_shape_check check (
    (
      policy_action = 'withhold'
      and maximum_public_h3_resolution is null
      and cardinality(allowed_scope_kinds) = 0
      and minimum_public_record_count is null
    )
    or (
      policy_action in ('provider_resolution', 'generalise')
      and maximum_public_h3_resolution between 0 and 15
      and cardinality(allowed_scope_kinds) > 0
      and allowed_scope_kinds <@ array['australia', 'state_territory', 'ibra', 'lga', 'h3']::text[]
      and array_position(allowed_scope_kinds, null) is null
      and minimum_public_record_count >= 1
    )
  ),
  constraint location_publication_receipts_unknown_check
    check (sensitivity_state <> 'unknown' or policy_action = 'withhold'),
  constraint location_publication_receipts_sensitive_check
    check (sensitivity_state <> 'sensitive' or policy_action in ('generalise', 'withhold')),
  constraint location_publication_receipts_policy_evidence_check
    check (policy_evidence_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint location_publication_receipts_sources_check check (
    cardinality(source_constraint_fingerprints) > 0
    and array_position(source_constraint_fingerprints, null) is null
  ),
  constraint location_publication_receipts_state_check
    check (publication_state in ('publish', 'generalised', 'withheld')),
  constraint location_publication_receipts_public_shape_check check (
    (
      publication_state in ('publish', 'generalised')
      and cardinality(blocker_codes) = 0
      and published_scope_kind in ('australia', 'state_territory', 'ibra', 'lga', 'h3')
      and length(published_scope_id) between 1 and 240
      and published_source_precision in ('exact', 'generalised', 'coarse_rollup')
      and effective_maximum_h3_resolution between 0 and 15
      and public_record_count >= minimum_public_record_count
    )
    or (
      publication_state = 'withheld'
      and cardinality(blocker_codes) > 0
      and published_scope_kind is null and published_scope_id is null
      and published_h3_resolution is null and published_h3_cell is null
      and published_source_precision is null
      and effective_maximum_h3_resolution is null
      and public_record_count is null
    )
  ),
  constraint location_publication_receipts_h3_shape_check check (
    (
      publication_state in ('publish', 'generalised')
      and published_scope_kind = 'h3'
      and published_h3_resolution between 0 and effective_maximum_h3_resolution
      and published_h3_cell ~ '^[0-9a-f]{15}$'
    )
    or (
      publication_state in ('publish', 'generalised')
      and published_scope_kind <> 'h3'
      and published_h3_resolution is null and published_h3_cell is null
    )
    or publication_state = 'withheld'
  ),
  constraint location_publication_receipts_sensitive_public_check check (
    publication_state = 'withheld'
    or (publication_state = 'publish' and sensitivity_state = 'not_sensitive'
      and published_source_precision = 'exact')
    or (publication_state = 'generalised'
      and published_source_precision in ('generalised', 'coarse_rollup'))
  ),
  constraint location_publication_receipts_fingerprint_check
    check (receipt_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint location_publication_receipts_non_scientific_check
    check (not scientific_claim_allowed),
  constraint location_publication_receipts_id_key
    unique (location_publication_receipt_id),
  constraint location_publication_receipts_target_key
    unique nulls not distinct (target_kind, geographic_impact_pk, release_candidate_pk),
  constraint location_publication_receipts_fingerprint_key
    unique (receipt_fingerprint)
);

create index location_publication_receipts_project_species_idx
on public.location_publication_receipts (project_pk, species_pk, created_at desc);
create index location_publication_receipts_geographic_impact_idx
on public.location_publication_receipts (geographic_impact_pk)
where geographic_impact_pk is not null;
create index location_publication_receipts_release_candidate_idx
on public.location_publication_receipts (release_candidate_pk)
where release_candidate_pk is not null;

alter table public.release_candidates
add constraint release_candidates_public_cell_h3_check
check (public_cell_id is null or public_cell_id ~ '^h3:(?:[0-9]|1[0-5]):[0-9a-f]{15}$')
not valid;

create function private.validate_location_source_constraint()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.species_pk is not null and not exists (
    select 1 from public.species species
    where species.id = new.species_pk and species.project_pk = new.project_pk
  ) then
    raise exception 'location constraint species does not belong to project'
      using errcode = '23514';
  end if;
  return new;
end;
$$;

create function private.validate_location_publication_receipt()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  target_project_pk bigint;
  target_species_pk bigint;
  target_fingerprint_value text;
  target_scope_kind text;
  target_scope_id text;
  target_h3_resolution smallint;
  target_h3_cell text;
  target_source_precision text;
  target_ala_fingerprint text;
  target_flickr_fingerprint text;
  target_public_state boolean;
  target_available_count bigint;
  matching_constraint_count bigint;
  used_constraint_count bigint;
  used_provider_ceiling smallint;
  expected_effective_ceiling smallint;
  canonical_constraint_fingerprints text[];
  canonical_allowed_scope_kinds text[];
  canonical_blocker_codes text[];
  project_policy_version text;
begin
  if new.target_kind = 'geographic_impact' then
    select impact.project_pk, impact.species_pk, impact.impact_fingerprint,
      impact.scope_kind, impact.scope_id, impact.h3_resolution, impact.h3_cell,
      impact.source_precision, impact.ala_baseline_fingerprint,
      impact.flickr_snapshot_fingerprint, impact.visibility_state = 'public',
      coalesce(impact.ala_baseline_count, 0) + coalesce(impact.flickr_candidate_count, 0)
    into target_project_pk, target_species_pk, target_fingerprint_value,
      target_scope_kind, target_scope_id, target_h3_resolution, target_h3_cell,
      target_source_precision, target_ala_fingerprint, target_flickr_fingerprint,
      target_public_state, target_available_count
    from public.geographic_impact impact
    where impact.id = new.geographic_impact_pk;
  else
    select candidate.project_pk, candidate.species_pk, candidate.candidate_fingerprint,
      'h3'::text, candidate.public_cell_id,
      nullif(split_part(candidate.public_cell_id, ':', 2), '')::smallint,
      nullif(split_part(candidate.public_cell_id, ':', 3), ''), impact.source_precision,
      impact.ala_baseline_fingerprint, impact.flickr_snapshot_fingerprint,
      candidate.candidate_state in ('approved', 'exported')
        and candidate.all_release_gates_passed
        and candidate.coordinate_valid,
      1::bigint
    into target_project_pk, target_species_pk, target_fingerprint_value,
      target_scope_kind, target_scope_id, target_h3_resolution, target_h3_cell,
      target_source_precision, target_ala_fingerprint, target_flickr_fingerprint,
      target_public_state, target_available_count
    from public.release_candidates candidate
    join public.geographic_impact impact on impact.id = candidate.geographic_impact_pk
    where candidate.id = new.release_candidate_pk;
  end if;

  if target_project_pk is null then
    raise exception 'location receipt target is missing or lacks geographic lineage'
      using errcode = '23514';
  end if;
  if new.project_pk <> target_project_pk
    or new.species_pk is distinct from target_species_pk
    or new.target_fingerprint <> target_fingerprint_value then
    raise exception 'location receipt target lineage does not match'
      using errcode = '23514';
  end if;
  select project.sensitive_coordinate_policy_version
  into project_policy_version
  from public.projects project where project.id = new.project_pk;
  if project_policy_version <> new.policy_version then
    raise exception 'location receipt policy is not the project policy'
      using errcode = '23514';
  end if;

  select array_agg(scope_kind order by scope_kind)
  into canonical_allowed_scope_kinds
  from (select distinct unnest(new.allowed_scope_kinds) as scope_kind) scopes;
  if coalesce(canonical_allowed_scope_kinds, '{}'::text[]) <> new.allowed_scope_kinds then
    raise exception 'allowed location scopes must be sorted and unique'
      using errcode = '23514';
  end if;
  select array_agg(blocker_code order by blocker_code)
  into canonical_blocker_codes
  from (select distinct unnest(new.blocker_codes) as blocker_code) blockers;
  if coalesce(canonical_blocker_codes, '{}'::text[]) <> new.blocker_codes then
    raise exception 'location receipt blockers must be sorted and unique'
      using errcode = '23514';
  end if;

  select count(*),
    count(*) filter (where source.location_used_for_target),
    min(source.maximum_public_h3_resolution)
      filter (where source.location_used_for_target),
    array_agg(source.constraint_fingerprint order by source.constraint_fingerprint)
  into matching_constraint_count, used_constraint_count, used_provider_ceiling,
    canonical_constraint_fingerprints
  from public.location_source_constraints source
  where source.constraint_fingerprint = any(new.source_constraint_fingerprints)
    and source.project_pk = new.project_pk
    and source.species_pk is not distinct from new.species_pk;

  if matching_constraint_count <> cardinality(new.source_constraint_fingerprints)
    or canonical_constraint_fingerprints <> new.source_constraint_fingerprints then
    raise exception 'location receipt constraints must be sorted, unique, and match target lineage'
      using errcode = '23514';
  end if;
  if not exists (
    select 1 from public.location_source_constraints source
    where source.constraint_fingerprint = any(new.source_constraint_fingerprints)
      and source.provider = 'ala'
      and source.provider_snapshot_fingerprint = target_ala_fingerprint
  ) then
    raise exception 'location receipt lacks the exact ALA constraint'
      using errcode = '23514';
  end if;
  if target_flickr_fingerprint is not null and not exists (
    select 1 from public.location_source_constraints source
    where source.constraint_fingerprint = any(new.source_constraint_fingerprints)
      and source.provider = 'flickr'
      and source.provider_snapshot_fingerprint = target_flickr_fingerprint
  ) then
    raise exception 'location receipt lacks the exact Flickr constraint'
      using errcode = '23514';
  end if;
  if exists (
    select 1 from public.location_source_constraints source
    where source.constraint_fingerprint = any(new.source_constraint_fingerprints)
      and source.location_used_for_target
      and not (
        (source.provider = 'ala'
          and source.provider_snapshot_fingerprint = target_ala_fingerprint)
        or (source.provider = 'flickr'
          and target_flickr_fingerprint is not null
          and source.provider_snapshot_fingerprint = target_flickr_fingerprint)
      )
  ) then
    raise exception 'used provider location does not belong to the target snapshot'
      using errcode = '23514';
  end if;

  if new.publication_state in ('publish', 'generalised') then
    if not target_public_state then
      raise exception 'publishable receipt target is not otherwise public eligible'
        using errcode = '23514';
    end if;
    if used_constraint_count < 1 or used_provider_ceiling is null then
      raise exception 'publishable receipt requires a permitted provider location'
        using errcode = '23514';
    end if;
    expected_effective_ceiling := least(
      new.maximum_public_h3_resolution, used_provider_ceiling
    );
    if new.effective_maximum_h3_resolution <> expected_effective_ceiling then
      raise exception 'location receipt does not use the strictest resolution ceiling'
        using errcode = '23514';
    end if;
    if not new.published_scope_kind = any(new.allowed_scope_kinds) then
      raise exception 'published scope is not allowed by the sensitive policy'
        using errcode = '23514';
    end if;
    if new.published_scope_kind <> target_scope_kind
      or new.published_scope_id <> target_scope_id
      or new.published_h3_resolution is distinct from target_h3_resolution
      or new.published_h3_cell is distinct from target_h3_cell
      or new.published_source_precision <> target_source_precision then
      raise exception 'location receipt does not match the materialized target scope'
        using errcode = '23514';
    end if;
    if new.public_record_count > target_available_count then
      raise exception 'location receipt count exceeds available target evidence'
        using errcode = '23514';
    end if;
  end if;
  return new;
end;
$$;

create function private.reject_sensitive_location_ledger_mutation()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  raise exception 'sensitive location ledgers are append only' using errcode = '55000';
end;
$$;

create trigger location_source_constraints_validate
before insert on public.location_source_constraints
for each row execute function private.validate_location_source_constraint();
create trigger location_source_constraints_reject_mutation
before update or delete on public.location_source_constraints
for each row execute function private.reject_sensitive_location_ledger_mutation();
create trigger location_publication_receipts_validate
before insert on public.location_publication_receipts
for each row execute function private.validate_location_publication_receipt();
create trigger location_publication_receipts_reject_mutation
before update or delete on public.location_publication_receipts
for each row execute function private.reject_sensitive_location_ledger_mutation();

create function private.has_publishable_location_receipt(
  requested_target_kind text,
  requested_target_pk bigint
)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.location_publication_receipts receipt
    where receipt.target_kind = requested_target_kind
      and (
        (requested_target_kind = 'geographic_impact'
          and receipt.geographic_impact_pk = requested_target_pk)
        or (requested_target_kind = 'release_candidate'
          and receipt.release_candidate_pk = requested_target_pk)
      )
      and receipt.publication_state in ('publish', 'generalised')
  );
$$;

alter table public.location_source_constraints enable row level security;
alter table public.location_publication_receipts enable row level security;

revoke all on table public.location_source_constraints,
  public.location_publication_receipts from public, anon, authenticated;
revoke all on sequence public.location_source_constraints_id_seq,
  public.location_publication_receipts_id_seq from public, anon, authenticated;
grant select, insert on table public.location_source_constraints,
  public.location_publication_receipts to service_role;
grant usage, select on sequence public.location_source_constraints_id_seq,
  public.location_publication_receipts_id_seq to service_role;
grant select on table public.location_source_constraints,
  public.location_publication_receipts to authenticated;

create policy location_source_constraints_curator_read
on public.location_source_constraints for select to authenticated
using (private.has_project_role(project_pk, array['curator', 'administrator']::text[]));
create policy location_publication_receipts_curator_read
on public.location_publication_receipts for select to authenticated
using (private.has_project_role(project_pk, array['curator', 'administrator']::text[]));

drop policy geographic_impact_public_read on public.geographic_impact;
create policy geographic_impact_public_read
on public.geographic_impact for select to anon, authenticated
using (
  visibility_state = 'public'
  and private.has_publishable_location_receipt('geographic_impact', id)
);

drop policy release_candidates_public_read on public.release_candidates;
create policy release_candidates_public_read
on public.release_candidates for select to anon, authenticated
using (
  candidate_state in ('approved', 'exported') and all_release_gates_passed
  and private.has_publishable_location_receipt('release_candidate', id)
);

revoke all on function private.validate_location_source_constraint(),
  private.validate_location_publication_receipt(),
  private.reject_sensitive_location_ledger_mutation(),
  private.has_publishable_location_receipt(text, bigint)
from public, anon, authenticated;
grant execute on function private.has_publishable_location_receipt(text, bigint)
to anon, authenticated;

comment on table public.location_source_constraints is
  'Private append-only provider permission and public-resolution evidence; contains no occurrence coordinates.';
comment on table public.location_publication_receipts is
  'Private append-only fail-closed receipts required before public map or release location reads.';
comment on function private.has_publishable_location_receipt(text, bigint) is
  'Fixed-query RLS helper; only a validated publish/generalise receipt unlocks an otherwise public target.';
