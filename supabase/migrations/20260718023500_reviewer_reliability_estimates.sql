-- ButterflyLens 9.3: append-only private reviewer reliability estimates.
-- The calculation runs in deterministic application code; Postgres admits only
-- policy-consistent, lineage-bound snapshots and never calculates truth from a
-- model vote or majority agreement.

alter table public.reviewer_reliability
add column source_provider text,
add column estimator_version text,
add column snapshot_revision integer,
add column supersedes_reliability_pk bigint
  references public.reviewer_reliability (id) on delete restrict,
add column sample_count integer not null default 0,
add column decisive_count integer not null default 0,
add column positive_control_count integer not null default 0,
add column negative_control_count integer not null default 0,
add column control_accuracy double precision,
add column sensitivity double precision,
add column specificity double precision,
add column pairwise_agreement double precision,
add column krippendorff_alpha double precision,
add column adjudicated_overlap double precision,
add column interval_level double precision,
add column evidence_fingerprint text,
add column evidence_cutoff timestamptz,
add column blockers text[] not null default '{}';

with ranked as (
  select reliability.id,
    row_number() over (
      partition by reliability.reviewer_profile_pk, reliability.project_pk,
        reliability.family_taxon_key, reliability.life_stage,
        reliability.visual_domain
      order by reliability.measured_at, reliability.id
    ) as revision
  from public.reviewer_reliability reliability
)
update public.reviewer_reliability reliability
set snapshot_revision = ranked.revision,
  estimator_version = 'legacy-unversioned',
  evidence_fingerprint = reliability.reliability_fingerprint,
  evidence_cutoff = reliability.measured_at
from ranked where ranked.id = reliability.id;

alter table public.reviewer_reliability
alter column snapshot_revision set not null,
alter column evidence_fingerprint set not null,
alter column evidence_cutoff set not null,
add constraint reviewer_reliability_source_provider_check check (
  source_provider is null or source_provider in (
    'flickr', 'ala', 'gbif', 'inaturalist', 'wikimedia_commons',
    'community_upload', 'butterflylens_fixture'
  )
),
add constraint reviewer_reliability_estimator_version_check
  check (length(estimator_version) between 1 and 120),
add constraint reviewer_reliability_revision_check check (snapshot_revision >= 1),
add constraint reviewer_reliability_not_self_superseding_check
  check (supersedes_reliability_pk is null or supersedes_reliability_pk <> id),
add constraint reviewer_reliability_extended_counts_check check (
  sample_count >= 0 and decisive_count between 0 and sample_count
  and positive_control_count >= 0 and negative_control_count >= 0
  and positive_control_count + negative_control_count <= control_count
),
add constraint reviewer_reliability_control_accuracy_check
  check (control_accuracy is null or control_accuracy between 0 and 1),
add constraint reviewer_reliability_sensitivity_check
  check (sensitivity is null or sensitivity between 0 and 1),
add constraint reviewer_reliability_specificity_check
  check (specificity is null or specificity between 0 and 1),
add constraint reviewer_reliability_pairwise_check
  check (pairwise_agreement is null or pairwise_agreement between 0 and 1),
add constraint reviewer_reliability_alpha_check
  check (krippendorff_alpha is null or krippendorff_alpha between -1 and 1),
add constraint reviewer_reliability_adjudicated_overlap_check
  check (adjudicated_overlap is null or adjudicated_overlap between 0 and 1),
add constraint reviewer_reliability_interval_level_check
  check (interval_level is null or interval_level > 0 and interval_level < 1),
add constraint reviewer_reliability_evidence_fingerprint_check
  check (evidence_fingerprint ~ '^[0-9a-f]{64}$'),
add constraint reviewer_reliability_cutoff_check check (evidence_cutoff <= measured_at),
add constraint reviewer_reliability_blockers_check
  check (array_position(blockers, null) is null);

create index reviewer_reliability_supersedes_pk_idx
on public.reviewer_reliability (supersedes_reliability_pk)
where supersedes_reliability_pk is not null;
create unique index reviewer_reliability_domain_revision_key
on public.reviewer_reliability (
  reviewer_profile_pk, project_pk, family_taxon_key, source_provider,
  life_stage, visual_domain, snapshot_revision
)
where source_provider is not null;
create index reviewer_reliability_current_domain_idx
on public.reviewer_reliability (
  reviewer_profile_pk, project_pk, family_taxon_key, source_provider,
  life_stage, visual_domain, snapshot_revision desc
)
where source_provider is not null;

create function private.enforce_reviewer_reliability_snapshot()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  previous_snapshot record;
  expected_minimum boolean;
begin
  perform pg_advisory_xact_lock(hashtextextended(
    new.reviewer_profile_pk::text || ':' || new.project_pk::text || ':'
    || new.family_taxon_key || ':' || coalesce(new.source_provider, '') || ':'
    || new.life_stage || ':' || new.visual_domain,
    0
  ));

  if new.source_provider is null
     or new.estimator_version <> 'butterflylens-reliability-estimator:v1.0.0'
     or new.policy_version <> 'butterflylens-reviewer-reliability-policy:v1.0.0' then
    raise exception 'new reliability snapshots require exact domain, estimator, and policy versions'
      using errcode = '23514';
  end if;
  if new.metrics ->> 'visibility' is distinct from 'private'
     or (new.metrics -> 'public_ranking_allowed') is distinct from 'false'::jsonb
     or (new.metrics -> 'model_agreement_used') is distinct from 'false'::jsonb
     or (new.metrics -> 'majority_agreement_alone_used') is distinct from 'false'::jsonb
     or (new.metrics -> 'scientific_claim_allowed') is distinct from 'false'::jsonb
     or new.metrics ->> 'method' is distinct from 'control_calibrated_beta_binomial_v1' then
    raise exception 'reliability snapshot violates privacy or non-circularity policy'
      using errcode = '23514';
  end if;
  if (new.metrics ->> 'evidence_fingerprint')
       is distinct from new.evidence_fingerprint
     or (new.metrics ->> 'control_accuracy')::double precision
       is distinct from new.control_accuracy
     or (new.metrics ->> 'sensitivity')::double precision
       is distinct from new.sensitivity
     or (new.metrics ->> 'specificity')::double precision
       is distinct from new.specificity
     or (new.metrics ->> 'pairwise_agreement')::double precision
       is distinct from new.pairwise_agreement
     or (new.metrics ->> 'krippendorff_alpha')::double precision
       is distinct from new.krippendorff_alpha
     or (new.metrics ->> 'adjudicated_overlap')::double precision
       is distinct from new.adjudicated_overlap then
    raise exception 'reliability metric columns diverge from the private snapshot payload'
      using errcode = '23514';
  end if;

  expected_minimum := new.control_count >= 20
    and new.positive_control_count >= 5
    and new.negative_control_count >= 5
    and new.overlap_count >= 10
    and new.adjudicated_count >= 5;
  if new.minimum_evidence_met <> expected_minimum then
    raise exception 'minimum evidence flag disagrees with policy thresholds'
      using errcode = '23514';
  end if;
  if new.sample_count <> new.control_count + new.overlap_count then
    raise exception 'reliability sample count must equal controls plus overlap items'
      using errcode = '23514';
  end if;
  if (new.positive_control_count >= 10) <> (new.sensitivity is not null)
     or (new.negative_control_count >= 10) <> (new.specificity is not null) then
    raise exception 'sensitivity or specificity violates class minimum'
      using errcode = '23514';
  end if;
  if expected_minimum and (
    new.weighting_state <> 'shrunk_capped'
    or new.control_accuracy is null or new.pairwise_agreement is null
    or new.adjudicated_overlap is null
    or new.weight_lower is null or new.weight_upper is null
    or new.interval_level is distinct from 0.95::double precision
    or cardinality(new.blockers) <> 0
  ) then
    raise exception 'eligible reliability snapshot is missing required estimates'
      using errcode = '23514';
  end if;
  if not expected_minimum and (
    new.weighting_state = 'shrunk_capped' or new.shrunk_weight <> 1
    or new.weight_lower is not null or new.weight_upper is not null
    or new.interval_level is not null or cardinality(new.blockers) = 0
  ) then
    raise exception 'insufficient evidence must preserve equal weight and blockers'
      using errcode = '23514';
  end if;

  select reliability.id, reliability.snapshot_revision,
    reliability.measured_at
  into previous_snapshot
  from public.reviewer_reliability reliability
  where reliability.reviewer_profile_pk = new.reviewer_profile_pk
    and reliability.project_pk = new.project_pk
    and reliability.family_taxon_key = new.family_taxon_key
    and reliability.source_provider = new.source_provider
    and reliability.life_stage = new.life_stage
    and reliability.visual_domain = new.visual_domain
  order by reliability.snapshot_revision desc
  limit 1;

  if not found then
    new.snapshot_revision := 1;
    new.supersedes_reliability_pk := null;
  else
    if new.measured_at < previous_snapshot.measured_at then
      raise exception 'reliability snapshot time regresses its domain lineage'
        using errcode = '23514';
    end if;
    new.snapshot_revision := previous_snapshot.snapshot_revision + 1;
    new.supersedes_reliability_pk := previous_snapshot.id;
  end if;
  return new;
end;
$$;

create trigger reviewer_reliability_enforce_snapshot
before insert on public.reviewer_reliability
for each row execute function private.enforce_reviewer_reliability_snapshot();

create function private.reject_reviewer_reliability_mutation()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  raise exception 'reviewer reliability snapshots are append only'
    using errcode = '55000';
end;
$$;

create trigger reviewer_reliability_reject_mutation
before update or delete on public.reviewer_reliability
for each row execute function private.reject_reviewer_reliability_mutation();

revoke all on function private.enforce_reviewer_reliability_snapshot(),
  private.reject_reviewer_reliability_mutation()
from public, anon, authenticated;

comment on table public.reviewer_reliability is
  'Private append-only domain snapshots with exact evidence lineage, uncertainty, equal-weight fallback, and no model or majority truth shortcut.';
