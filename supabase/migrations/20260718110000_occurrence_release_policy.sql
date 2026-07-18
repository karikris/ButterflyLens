-- ButterflyLens 14.1: immutable release-ready occurrence candidate receipts.
-- A release-ready candidate is not a published occurrence.

create table public.occurrence_release_receipts (
  id bigint generated always as identity primary key,
  occurrence_release_receipt_id text not null,
  release_candidate_pk bigint not null
    references public.release_candidates (id) on delete restrict,
  project_pk bigint not null references public.projects (id) on delete restrict,
  species_pk bigint not null references public.species (id) on delete restrict,
  media_object_pk bigint not null
    references public.media_objects (id) on delete restrict,
  candidate_fingerprint text not null,
  human_supported_consensus_pk bigint not null
    references public.consensus (id) on delete restrict,
  qualified_consensus_pk bigint not null
    references public.consensus (id) on delete restrict,
  expert_review_event_pk bigint
    references public.review_events (id) on delete restrict,
  location_publication_receipt_pk bigint not null
    references public.location_publication_receipts (id) on delete restrict,
  quality_snapshot_pk bigint not null
    references public.quality_snapshots (id) on delete restrict,
  coordinate_evidence_fingerprint text not null,
  date_evidence_fingerprint text not null,
  duplicate_independence_evidence_fingerprint text not null,
  rights_fingerprint text not null,
  quality_threshold_fingerprint text not null,
  conflict_audit_fingerprint text not null,
  evidence_packet_fingerprint text not null,
  gate_results jsonb not null,
  evidence_fingerprints text[] not null,
  policy_version text not null default 'butterflylens-occurrence-release:v1.0.0',
  release_state text not null default 'release_ready_occurrence_candidate',
  receipt_fingerprint text not null,
  published_occurrence boolean not null default false,
  scientific_claim_allowed boolean not null default false,
  created_at timestamptz not null default now(),
  constraint occurrence_release_receipts_id_check check (
    occurrence_release_receipt_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'
  ),
  constraint occurrence_release_receipts_candidate_fingerprint_check
    check (candidate_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint occurrence_release_receipts_coordinate_fingerprint_check
    check (coordinate_evidence_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint occurrence_release_receipts_date_fingerprint_check
    check (date_evidence_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint occurrence_release_receipts_duplicate_fingerprint_check
    check (duplicate_independence_evidence_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint occurrence_release_receipts_rights_fingerprint_check
    check (rights_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint occurrence_release_receipts_quality_threshold_check
    check (quality_threshold_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint occurrence_release_receipts_conflict_audit_check
    check (conflict_audit_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint occurrence_release_receipts_packet_fingerprint_check
    check (evidence_packet_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint occurrence_release_receipts_gate_results_check check (
    gate_results = '{
      "coordinate_date_validity": true,
      "duplicate_independence": true,
      "evidence_packet_complete": true,
      "expert_review_when_configured": true,
      "human_supported_identity": true,
      "no_unresolved_conflict": true,
      "qualified_consensus": true,
      "quality_threshold": true,
      "rights_provenance": true
    }'::jsonb
  ),
  constraint occurrence_release_receipts_evidence_check check (
    cardinality(evidence_fingerprints) >= 12
    and array_position(evidence_fingerprints, null) is null
  ),
  constraint occurrence_release_receipts_policy_check check (
    policy_version = 'butterflylens-occurrence-release:v1.0.0'
  ),
  constraint occurrence_release_receipts_state_check check (
    release_state = 'release_ready_occurrence_candidate'
  ),
  constraint occurrence_release_receipts_fingerprint_check
    check (receipt_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint occurrence_release_receipts_not_published_check
    check (not published_occurrence),
  constraint occurrence_release_receipts_non_scientific_check
    check (not scientific_claim_allowed),
  constraint occurrence_release_receipts_id_key
    unique (occurrence_release_receipt_id),
  constraint occurrence_release_receipts_candidate_key
    unique (release_candidate_pk),
  constraint occurrence_release_receipts_fingerprint_key
    unique (receipt_fingerprint)
);

create index occurrence_release_receipts_project_species_idx
on public.occurrence_release_receipts (project_pk, species_pk, created_at desc);
create index occurrence_release_receipts_media_object_idx
on public.occurrence_release_receipts (media_object_pk);
create index occurrence_release_receipts_human_consensus_idx
on public.occurrence_release_receipts (human_supported_consensus_pk);
create index occurrence_release_receipts_qualified_consensus_idx
on public.occurrence_release_receipts (qualified_consensus_pk);
create index occurrence_release_receipts_expert_event_idx
on public.occurrence_release_receipts (expert_review_event_pk)
where expert_review_event_pk is not null;
create index occurrence_release_receipts_location_idx
on public.occurrence_release_receipts (location_publication_receipt_pk);
create index occurrence_release_receipts_quality_idx
on public.occurrence_release_receipts (quality_snapshot_pk);

create function private.validate_occurrence_release_receipt()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  candidate_record record;
  release_consensus_record record;
  human_consensus_record record;
  qualified_consensus_record record;
  quality_record record;
  location_record record;
  expert_event_fingerprint text;
  expected_evidence_fingerprints text[];
begin
  select candidate.project_pk, candidate.species_pk, candidate.media_object_pk,
    candidate.consensus_pk, candidate.quality_snapshot_pk,
    candidate.candidate_fingerprint, candidate.candidate_state,
    candidate.human_supported_identity, candidate.qualified_consensus_passed,
    candidate.expert_review_required, candidate.expert_review_passed,
    candidate.coordinate_valid, candidate.date_valid,
    candidate.duplicate_independence_passed,
    candidate.rights_provenance_passed, candidate.quality_threshold_passed,
    candidate.no_unresolved_conflict, candidate.evidence_packet_complete,
    candidate.all_release_gates_passed, candidate.public_cell_id,
    candidate.occurrence_date, candidate.rights_fingerprint,
    candidate.evidence_packet_fingerprint,
    media.media_state, media.rights_status as media_rights_status,
    media.rights_fingerprint as media_rights_fingerprint, media.removed_at
  into candidate_record
  from public.release_candidates candidate
  join public.media_objects media on media.id = candidate.media_object_pk
  where candidate.id = new.release_candidate_pk;

  if candidate_record.project_pk is null
    or new.project_pk <> candidate_record.project_pk
    or new.species_pk <> candidate_record.species_pk
    or new.media_object_pk <> candidate_record.media_object_pk
    or new.candidate_fingerprint <> candidate_record.candidate_fingerprint then
    raise exception 'occurrence release target lineage does not match'
      using errcode = '23514';
  end if;
  if candidate_record.candidate_state not in ('eligible', 'approved', 'exported')
    or not candidate_record.all_release_gates_passed
    or not candidate_record.human_supported_identity
    or not candidate_record.qualified_consensus_passed
    or not (not candidate_record.expert_review_required
      or candidate_record.expert_review_passed)
    or not candidate_record.coordinate_valid
    or not candidate_record.date_valid
    or not candidate_record.duplicate_independence_passed
    or not candidate_record.rights_provenance_passed
    or not candidate_record.quality_threshold_passed
    or not candidate_record.no_unresolved_conflict
    or not candidate_record.evidence_packet_complete then
    raise exception 'occurrence release candidate has not passed every explicit gate'
      using errcode = '23514';
  end if;
  if candidate_record.public_cell_id is null
    or candidate_record.occurrence_date is null then
    raise exception 'occurrence release requires materialized coordinate and date evidence'
      using errcode = '23514';
  end if;

  select consensus.verification_campaign_pk, consensus.media_object_pk,
    consensus.species_pk, consensus.consensus_layer, consensus.status,
    consensus.decision, consensus.revision, consensus.consensus_fingerprint,
    consensus.layer_summary
  into release_consensus_record
  from public.consensus consensus
  where consensus.id = candidate_record.consensus_pk;
  if release_consensus_record.consensus_layer is distinct from 'release_consensus'
    or release_consensus_record.status is distinct from 'reached'
    or release_consensus_record.decision is distinct from 'yes'
    or release_consensus_record.layer_summary ->> 'outcome'
      is distinct from 'release_ready'
    or release_consensus_record.layer_summary ->> 'policy_version'
      is distinct from 'butterflylens-layered-consensus-policy:v1.0.0' then
    raise exception 'occurrence release requires exact release consensus'
      using errcode = '23514';
  end if;

  select consensus.verification_campaign_pk, consensus.media_object_pk,
    consensus.species_pk, consensus.status, consensus.decision,
    consensus.revision, consensus.consensus_fingerprint,
    consensus.layer_summary
  into human_consensus_record
  from public.consensus consensus
  where consensus.id = new.human_supported_consensus_pk
    and consensus.consensus_layer = 'community_evidence';
  if human_consensus_record.status is distinct from 'reached'
    or human_consensus_record.decision is distinct from 'yes'
    or human_consensus_record.layer_summary ->> 'outcome'
      is distinct from 'supported' then
    raise exception 'occurrence release requires human-supported identity'
      using errcode = '23514';
  end if;

  select consensus.verification_campaign_pk, consensus.media_object_pk,
    consensus.species_pk, consensus.status, consensus.decision,
    consensus.revision, consensus.consensus_fingerprint,
    consensus.layer_summary
  into qualified_consensus_record
  from public.consensus consensus
  where consensus.id = new.qualified_consensus_pk
    and consensus.consensus_layer = 'qualified_consensus';
  if qualified_consensus_record.status is distinct from 'reached'
    or qualified_consensus_record.decision is distinct from 'yes'
    or qualified_consensus_record.layer_summary ->> 'outcome'
      is distinct from 'supported' then
    raise exception 'occurrence release requires qualified consensus'
      using errcode = '23514';
  end if;
  if release_consensus_record.verification_campaign_pk
      is distinct from human_consensus_record.verification_campaign_pk
    or release_consensus_record.verification_campaign_pk
      is distinct from qualified_consensus_record.verification_campaign_pk
    or candidate_record.media_object_pk
      is distinct from human_consensus_record.media_object_pk
    or candidate_record.media_object_pk
      is distinct from qualified_consensus_record.media_object_pk
    or candidate_record.media_object_pk
      is distinct from release_consensus_record.media_object_pk
    or candidate_record.species_pk
      is distinct from human_consensus_record.species_pk
    or candidate_record.species_pk
      is distinct from qualified_consensus_record.species_pk
    or candidate_record.species_pk
      is distinct from release_consensus_record.species_pk then
    raise exception 'occurrence release consensus layers do not share exact lineage'
      using errcode = '23514';
  end if;
  if exists (
    select 1 from public.consensus later
    where later.verification_campaign_pk = human_consensus_record.verification_campaign_pk
      and later.media_object_pk = candidate_record.media_object_pk
      and later.consensus_layer = 'community_evidence'
      and later.revision > human_consensus_record.revision
  ) or exists (
    select 1 from public.consensus later
    where later.verification_campaign_pk = qualified_consensus_record.verification_campaign_pk
      and later.media_object_pk = candidate_record.media_object_pk
      and later.consensus_layer = 'qualified_consensus'
      and later.revision > qualified_consensus_record.revision
  ) or exists (
    select 1 from public.consensus later
    where later.verification_campaign_pk = release_consensus_record.verification_campaign_pk
      and later.media_object_pk = candidate_record.media_object_pk
      and later.consensus_layer = 'release_consensus'
      and later.revision > release_consensus_record.revision
  ) then
    raise exception 'occurrence release consensus is superseded'
      using errcode = '23514';
  end if;

  if not exists (
    select 1 from public.verification_campaigns campaign
    where campaign.id = release_consensus_record.verification_campaign_pk
      and campaign.project_pk = candidate_record.project_pk
      and campaign.species_pk = candidate_record.species_pk
      and campaign.expert_gate_required = candidate_record.expert_review_required
  ) then
    raise exception 'occurrence release campaign policy does not match candidate'
      using errcode = '23514';
  end if;

  if candidate_record.expert_review_required then
    select event.event_fingerprint into expert_event_fingerprint
    from public.review_events event
    join public.reviewer_profiles profile on profile.id = event.reviewer_profile_pk
    where event.id = new.expert_review_event_pk
      and event.verification_campaign_pk = release_consensus_record.verification_campaign_pk
      and event.media_object_pk = candidate_record.media_object_pk
      and event.decision = 'yes'
      and profile.status = 'active'
      and profile.qualification_state = 'verified'
      and profile.role in ('expert', 'curator', 'administrator')
      and not exists (
        select 1 from public.review_events superseding
        where superseding.supersedes_event_pk = event.id
      );
    if expert_event_fingerprint is null then
      raise exception 'configured expert release gate lacks current verified review'
        using errcode = '23514';
    end if;
  elsif new.expert_review_event_pk is not null then
    raise exception 'unconfigured expert gate cannot imply expert review'
      using errcode = '23514';
  end if;

  select quality.snapshot_kind, quality.scope_kind, quality.species_pk,
    quality.verification_campaign_pk, quality.representative, quality.blind,
    quality.population_estimate_allowed, quality.release_blockers,
    quality.snapshot_fingerprint, quality.estimate_payload
  into quality_record
  from public.quality_snapshots quality
  where quality.id = new.quality_snapshot_pk
    and quality.id = candidate_record.quality_snapshot_pk
    and quality.project_pk = candidate_record.project_pk;
  if quality_record.snapshot_kind is distinct from 'representative_audit'
    or not (
      (quality_record.scope_kind = 'species'
        and quality_record.species_pk = candidate_record.species_pk)
      or (quality_record.scope_kind = 'campaign'
        and quality_record.verification_campaign_pk
          = release_consensus_record.verification_campaign_pk)
    )
    or quality_record.representative is not true
    or quality_record.blind is not true
    or quality_record.population_estimate_allowed is not true
    or cardinality(quality_record.release_blockers) is distinct from 0
    or quality_record.estimate_payload ->> 'availability'
      is distinct from 'estimated' then
    raise exception 'occurrence release quality threshold lacks representative evidence'
      using errcode = '23514';
  end if;

  select receipt.receipt_fingerprint, receipt.publication_state
  into location_record
  from public.location_publication_receipts receipt
  where receipt.id = new.location_publication_receipt_pk
    and receipt.target_kind = 'release_candidate'
    and receipt.release_candidate_pk = new.release_candidate_pk
    and receipt.project_pk = candidate_record.project_pk
    and receipt.species_pk = candidate_record.species_pk;
  if location_record.publication_state is null
    or location_record.publication_state not in ('publish', 'generalised') then
    raise exception 'occurrence release lacks publishable sensitive-location receipt'
      using errcode = '23514';
  end if;

  if new.rights_fingerprint is distinct from candidate_record.rights_fingerprint
    or new.rights_fingerprint is distinct from candidate_record.media_rights_fingerprint
    or candidate_record.media_state is distinct from 'committed'
    or candidate_record.media_rights_status is distinct from 'allowed'
    or candidate_record.removed_at is not null
    or private.has_media_takedown_for_release(new.release_candidate_pk) then
    raise exception 'occurrence release rights or removal gate failed'
      using errcode = '23514';
  end if;
  if new.evidence_packet_fingerprint
      is distinct from candidate_record.evidence_packet_fingerprint then
    raise exception 'occurrence release evidence packet does not match candidate'
      using errcode = '23514';
  end if;
  if exists (
    select 1 from public.review_conflicts conflict
    where conflict.verification_campaign_pk = release_consensus_record.verification_campaign_pk
      and conflict.media_object_pk = candidate_record.media_object_pk
      and not exists (
        select 1 from public.adjudication_events adjudication
        where adjudication.review_conflict_pk = conflict.id
      )
  ) then
    raise exception 'occurrence release has unresolved human conflict'
      using errcode = '23514';
  end if;

  select array_agg(distinct fingerprint order by fingerprint)
  into expected_evidence_fingerprints
  from unnest(array[
    new.candidate_fingerprint,
    release_consensus_record.consensus_fingerprint,
    human_consensus_record.consensus_fingerprint,
    qualified_consensus_record.consensus_fingerprint,
    expert_event_fingerprint,
    location_record.receipt_fingerprint,
    quality_record.snapshot_fingerprint,
    new.coordinate_evidence_fingerprint,
    new.date_evidence_fingerprint,
    new.duplicate_independence_evidence_fingerprint,
    new.rights_fingerprint,
    new.quality_threshold_fingerprint,
    new.conflict_audit_fingerprint,
    new.evidence_packet_fingerprint
  ]) fingerprint
  where fingerprint is not null;
  if new.evidence_fingerprints <> expected_evidence_fingerprints then
    raise exception 'occurrence release evidence lineage must be exact, sorted, and unique'
      using errcode = '23514';
  end if;
  return new;
end;
$$;

create function private.reject_occurrence_release_receipt_mutation()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  raise exception 'occurrence release receipts are append only'
    using errcode = '55000';
end;
$$;

create trigger occurrence_release_receipts_validate
before insert on public.occurrence_release_receipts
for each row execute function private.validate_occurrence_release_receipt();
create trigger occurrence_release_receipts_reject_mutation
before update or delete on public.occurrence_release_receipts
for each row execute function private.reject_occurrence_release_receipt_mutation();

create function private.has_occurrence_release_receipt(
  target_release_candidate_pk bigint
)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.occurrence_release_receipts receipt
    where receipt.release_candidate_pk = target_release_candidate_pk
      and receipt.release_state = 'release_ready_occurrence_candidate'
      and not receipt.published_occurrence
  );
$$;

alter table public.occurrence_release_receipts enable row level security;

create policy occurrence_release_receipts_curator_read
on public.occurrence_release_receipts for select to authenticated
using (private.has_project_role(
  project_pk, array['curator', 'administrator']::text[]
));

drop policy release_candidates_public_read on public.release_candidates;
create policy release_candidates_public_read
on public.release_candidates for select to anon, authenticated
using (
  candidate_state in ('approved', 'exported') and all_release_gates_passed
  and private.has_publishable_location_receipt('release_candidate', id)
  and not private.has_media_takedown_for_release(id)
  and private.has_occurrence_release_receipt(id)
);

revoke all on table public.occurrence_release_receipts
from public, anon, authenticated;
revoke all on sequence public.occurrence_release_receipts_id_seq
from public, anon, authenticated;
grant select on table public.occurrence_release_receipts to authenticated;
grant select, insert on table public.occurrence_release_receipts to service_role;
grant usage, select on sequence public.occurrence_release_receipts_id_seq
to service_role;

revoke all on function private.validate_occurrence_release_receipt(),
  private.reject_occurrence_release_receipt_mutation(),
  private.has_occurrence_release_receipt(bigint)
from public, anon, authenticated;
grant execute on function private.has_occurrence_release_receipt(bigint)
to anon, authenticated;

comment on table public.occurrence_release_receipts is
  'Immutable exact-lineage proof that a candidate passed every release-readiness gate; never a publication claim.';
comment on function private.has_occurrence_release_receipt(bigint) is
  'Fixed-query final RLS gate for a validated release-ready occurrence candidate receipt.';
