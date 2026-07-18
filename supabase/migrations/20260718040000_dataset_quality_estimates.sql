-- ButterflyLens 9.5: representative dataset-quality estimates.
-- Probability audits and targeted failure discovery are separate lanes. Only
-- the former can carry a population estimate; both remain append-only evidence.

alter table public.quality_snapshots
add column estimator_version text,
add column policy_version text,
add column snapshot_revision integer,
add column supersedes_quality_snapshot_pk bigint
  references public.quality_snapshots (id) on delete restrict,
add column sampling_plan_id text,
add column audit_evidence_fingerprint text,
add column sampling_design text,
add column representative boolean not null default false,
add column blind boolean not null default false,
add column confidence_level double precision,
add column interval_method text,
add column bootstrap_replicates integer,
add column bootstrap_seed_fingerprint text,
add column resampling_group_count integer not null default 0,
add column population_estimate_allowed boolean not null default false,
add column estimate_payload jsonb not null default '{}'::jsonb;

with ranked as (
  select quality.id,
    row_number() over (
      partition by quality.project_pk, quality.run_pk, quality.scope_kind,
        quality.species_pk, quality.verification_campaign_pk,
        quality.snapshot_kind
      order by quality.created_at, quality.id
    ) as revision
  from public.quality_snapshots quality
)
update public.quality_snapshots quality
set estimator_version = 'legacy-unversioned',
  policy_version = 'legacy-unversioned',
  snapshot_revision = ranked.revision,
  sampling_plan_id = 'legacy:' || quality.id::text,
  audit_evidence_fingerprint = quality.snapshot_fingerprint,
  sampling_design = 'legacy_operational',
  bootstrap_replicates = 200,
  bootstrap_seed_fingerprint = quality.snapshot_fingerprint,
  population_estimate_allowed = quality.precision_estimate is not null,
  estimate_payload = jsonb_build_object(
    'schema_version', 'legacy-unversioned',
    'availability', case when quality.precision_estimate is null
      then 'unavailable' else 'estimated' end,
    'audit_kind', quality.snapshot_kind,
    'sampling_plan_id', 'legacy:' || quality.id::text,
    'sampling_design', 'legacy_operational',
    'sampling_frame_fingerprint', quality.sampling_frame_fingerprint,
    'reviewed_sample', quality.reviewed_sample,
    'decisive_reviews', quality.decisive_reviews,
    'precision_estimate', quality.precision_estimate,
    'effective_sample_size', quality.effective_sample_size,
    'blockers', to_jsonb(quality.release_blockers),
    'targeted_queue_separate', true,
    'model_vote_included', false,
    'scientific_claim_allowed', false,
    'snapshot_fingerprint', quality.snapshot_fingerprint
  )
from ranked where ranked.id = quality.id;

alter table public.quality_snapshots
alter column estimator_version set not null,
alter column policy_version set not null,
alter column snapshot_revision set not null,
alter column sampling_plan_id set not null,
alter column audit_evidence_fingerprint set not null,
alter column sampling_design set not null,
alter column bootstrap_replicates set not null,
alter column bootstrap_seed_fingerprint set not null,
drop constraint quality_snapshots_sampling_method_check,
drop constraint quality_snapshots_precision_check,
add constraint quality_snapshots_sampling_method_check check (
  snapshot_kind <> 'representative_audit'
  or precision_estimate is null
  or inclusion_probability_method is not null
),
add constraint quality_snapshots_precision_check check (
  (precision_estimate is null and interval_lower is null and interval_upper is null)
  or (
    precision_estimate is not null
    and interval_lower is not null
    and interval_upper is not null
    and precision_estimate between 0 and 1
    and interval_lower between 0 and 1
    and interval_upper between 0 and 1
    and interval_lower <= interval_upper
  )
),
add constraint quality_snapshots_estimator_version_check
  check (length(estimator_version) between 1 and 120),
add constraint quality_snapshots_policy_version_check
  check (length(policy_version) between 1 and 120),
add constraint quality_snapshots_revision_check check (snapshot_revision >= 1),
add constraint quality_snapshots_not_self_superseding_check check (
  supersedes_quality_snapshot_pk is null or supersedes_quality_snapshot_pk <> id
),
add constraint quality_snapshots_sampling_plan_id_check
  check (sampling_plan_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
add constraint quality_snapshots_audit_evidence_fingerprint_check
  check (audit_evidence_fingerprint ~ '^[0-9a-f]{64}$'),
add constraint quality_snapshots_sampling_design_check check (
  sampling_design in (
    'simple_random', 'stratified_random', 'clustered_random',
    'targeted_priority', 'legacy_operational'
  )
),
add constraint quality_snapshots_confidence_check check (
  confidence_level is null
  or confidence_level > 0 and confidence_level < 1
),
add constraint quality_snapshots_bootstrap_count_check
  check (bootstrap_replicates >= 200),
add constraint quality_snapshots_bootstrap_seed_check
  check (bootstrap_seed_fingerprint ~ '^[0-9a-f]{64}$'),
add constraint quality_snapshots_resampling_group_check
  check (resampling_group_count >= 0),
add constraint quality_snapshots_estimate_payload_check
  check (jsonb_typeof(estimate_payload) = 'object');

create index quality_snapshots_supersedes_pk_idx
on public.quality_snapshots (supersedes_quality_snapshot_pk)
where supersedes_quality_snapshot_pk is not null;
create unique index quality_snapshots_plan_revision_key
on public.quality_snapshots (
  project_pk, run_pk, scope_kind, coalesce(species_pk, 0),
  coalesce(verification_campaign_pk, 0), snapshot_kind,
  sampling_plan_id, snapshot_revision
);
create index quality_snapshots_current_plan_idx
on public.quality_snapshots (
  project_pk, run_pk, snapshot_kind, sampling_plan_id,
  snapshot_revision desc
);

create function private.enforce_dataset_quality_snapshot()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  previous_snapshot record;
  payload_interval jsonb;
begin
  perform pg_advisory_xact_lock(hashtextextended(
    new.project_pk::text || ':' || new.run_pk::text || ':' || new.scope_kind
    || ':' || coalesce(new.species_pk::text, '') || ':'
    || coalesce(new.verification_campaign_pk::text, '') || ':'
    || new.snapshot_kind || ':' || new.sampling_plan_id,
    0
  ));

  if new.estimator_version
       <> 'butterflylens-dataset-quality-estimator:v1.0.0'
     or new.policy_version
       <> 'butterflylens-representative-audit-policy:v1.0.0'
     or new.snapshot_kind not in (
       'representative_audit', 'targeted_failure_discovery'
     ) then
    raise exception 'new quality snapshots require exact estimator, policy, and audit lane'
      using errcode = '23514';
  end if;
  if new.estimate_payload ->> 'schema_version'
       is distinct from 'butterflylens-quality-snapshot:v1.0.0'
     or new.estimate_payload ->> 'estimator_version'
       is distinct from new.estimator_version
     or new.estimate_payload ->> 'policy_version'
       is distinct from new.policy_version
     or new.estimate_payload ->> 'audit_kind'
       is distinct from new.snapshot_kind
     or new.estimate_payload ->> 'quality_snapshot_id'
       is distinct from new.quality_snapshot_id
     or new.estimate_payload ->> 'sampling_plan_id'
       is distinct from new.sampling_plan_id
     or new.estimate_payload ->> 'audit_evidence_fingerprint'
       is distinct from new.audit_evidence_fingerprint
     or new.estimate_payload ->> 'sampling_design'
       is distinct from new.sampling_design
     or new.estimate_payload ->> 'sampling_frame_fingerprint'
       is distinct from new.sampling_frame_fingerprint
     or new.estimate_payload ->> 'snapshot_fingerprint'
       is distinct from new.snapshot_fingerprint
     or (new.estimate_payload -> 'targeted_queue_separate')
       is distinct from 'true'::jsonb
     or (new.estimate_payload -> 'model_vote_included')
       is distinct from 'false'::jsonb
     or (new.estimate_payload -> 'scientific_claim_allowed')
       is distinct from 'false'::jsonb then
    raise exception 'quality payload violates version, lineage, or scientific boundaries'
      using errcode = '23514';
  end if;
  if (new.estimate_payload ->> 'reviewed_sample')::integer
       is distinct from new.reviewed_sample
     or case
       when jsonb_typeof(new.estimate_payload -> 'audit_records') = 'array'
         then jsonb_array_length(new.estimate_payload -> 'audit_records')
           is distinct from new.reviewed_sample
       else true
     end
     or (new.estimate_payload ->> 'decisive_reviews')::integer
       is distinct from new.decisive_reviews
     or (new.estimate_payload ->> 'precision_estimate')::double precision
       is distinct from new.precision_estimate
     or (new.estimate_payload ->> 'effective_sample_size')::double precision
       is distinct from new.effective_sample_size
     or (new.estimate_payload ->> 'supported_count')::integer
       + (new.estimate_payload ->> 'failure_count')::integer
       is distinct from new.decisive_reviews
     or (new.estimate_payload ->> 'supported_count')::integer
       + (new.estimate_payload ->> 'failure_count')::integer
       + (new.estimate_payload ->> 'unresolved_count')::integer
       is distinct from new.reviewed_sample then
    raise exception 'quality counts do not reconcile'
      using errcode = '23514';
  end if;
  if new.estimate_payload -> 'blockers' is distinct from to_jsonb(new.release_blockers)
     or (new.estimate_payload ->> 'population_estimate_allowed')::boolean
       is distinct from new.population_estimate_allowed
     or (new.estimate_payload ->> 'representative')::boolean
       is distinct from new.representative
     or (new.estimate_payload ->> 'blind')::boolean is distinct from new.blind
     or new.estimate_payload ->> 'inclusion_probability_method'
       is distinct from new.inclusion_probability_method
     or new.estimate_payload ->> 'interval_method'
       is distinct from new.interval_method
     or (new.estimate_payload ->> 'bootstrap_replicates')::integer
       is distinct from new.bootstrap_replicates
     or new.estimate_payload ->> 'bootstrap_seed_fingerprint'
       is distinct from new.bootstrap_seed_fingerprint
     or (new.estimate_payload ->> 'resampling_group_count')::integer
       is distinct from new.resampling_group_count then
    raise exception 'quality columns diverge from the fingerprinted estimate payload'
      using errcode = '23514';
  end if;

  payload_interval := new.estimate_payload -> 'interval';
  if new.snapshot_kind = 'targeted_failure_discovery' then
    if new.representative or new.population_estimate_allowed
       or new.precision_estimate is not null
       or new.effective_sample_size is not null
       or new.interval_lower is not null or new.interval_upper is not null
       or payload_interval is distinct from 'null'::jsonb
       or new.estimate_payload ->> 'availability' is distinct from 'unavailable'
       or cardinality(new.release_blockers) = 0 then
      raise exception 'targeted failure discovery cannot become a population estimate'
        using errcode = '23514';
    end if;
  elsif new.precision_estimate is not null then
    if not new.representative or not new.blind
       or new.sampling_design not in (
         'simple_random', 'stratified_random', 'clustered_random'
       )
       or new.inclusion_probability_method
         <> 'hajek_inverse_inclusion_probability_v1'
       or new.interval_method
         <> 'stratified_owner_observation_group_bootstrap_v1'
       or new.confidence_level is distinct from 0.95::double precision
       or new.effective_sample_size is null
       or new.interval_lower is null or new.interval_upper is null
       or new.resampling_group_count < 2
       or not new.population_estimate_allowed
       or cardinality(new.release_blockers) <> 0
       or new.estimate_payload ->> 'availability' is distinct from 'estimated'
       or jsonb_typeof(payload_interval) is distinct from 'object'
       or not coalesce(
         new.estimate_payload -> 'grouping_keys' ? 'owner_id', false
       )
       or not coalesce(
         new.estimate_payload -> 'grouping_keys' ? 'observation_id', false
       )
       or case
         when jsonb_typeof(new.estimate_payload -> 'sampling_strata') = 'array'
           then jsonb_array_length(new.estimate_payload -> 'sampling_strata') = 0
         else true
       end
       or (payload_interval ->> 'lower')::double precision
         is distinct from new.interval_lower
       or (payload_interval ->> 'upper')::double precision
         is distinct from new.interval_upper
       or (payload_interval ->> 'level')::double precision
         is distinct from new.confidence_level then
      raise exception 'representative estimate is missing probability, strata, grouping, or interval evidence'
        using errcode = '23514';
    end if;
  elsif new.population_estimate_allowed
        or new.effective_sample_size is not null
        or new.interval_lower is not null or new.interval_upper is not null
        or payload_interval is distinct from 'null'::jsonb
        or new.estimate_payload ->> 'availability' is distinct from 'unavailable'
        or cardinality(new.release_blockers) = 0 then
    raise exception 'unavailable representative audit must retain null estimates and blockers'
      using errcode = '23514';
  end if;

  select quality.id, quality.snapshot_revision, quality.created_at
  into previous_snapshot
  from public.quality_snapshots quality
  where quality.project_pk = new.project_pk
    and quality.run_pk = new.run_pk
    and quality.scope_kind = new.scope_kind
    and quality.species_pk is not distinct from new.species_pk
    and quality.verification_campaign_pk
      is not distinct from new.verification_campaign_pk
    and quality.snapshot_kind = new.snapshot_kind
    and quality.sampling_plan_id = new.sampling_plan_id
  order by quality.snapshot_revision desc
  limit 1;

  if not found then
    new.snapshot_revision := 1;
    new.supersedes_quality_snapshot_pk := null;
  else
    if new.created_at < previous_snapshot.created_at then
      raise exception 'quality snapshot time regresses its audit lineage'
        using errcode = '23514';
    end if;
    new.snapshot_revision := previous_snapshot.snapshot_revision + 1;
    new.supersedes_quality_snapshot_pk := previous_snapshot.id;
  end if;
  return new;
end;
$$;

create trigger quality_snapshots_enforce_estimate
before insert on public.quality_snapshots
for each row execute function private.enforce_dataset_quality_snapshot();

create function private.reject_quality_snapshot_mutation()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  raise exception 'quality snapshots are append only' using errcode = '55000';
end;
$$;

create trigger quality_snapshots_reject_mutation
before update or delete on public.quality_snapshots
for each row execute function private.reject_quality_snapshot_mutation();

revoke all on function private.enforce_dataset_quality_snapshot(),
  private.reject_quality_snapshot_mutation()
from public, anon, authenticated;

comment on table public.quality_snapshots is
  'Append-only representative probability audits, kept structurally separate from targeted failure discovery; model votes never enter the estimate.';
