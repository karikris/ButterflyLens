-- ButterflyLens 9.4: append-only layered human consensus.
-- Community counts remain unweighted. Reliability affects only the qualified
-- layer, never resolves disagreement, and never replaces exact adjudication.

alter table public.consensus
add column revision integer,
add column reviewer_weights_applied boolean not null default false,
add column reliability_snapshot_fingerprint text,
add column adjudication_event_fingerprint text
  references public.adjudication_events (adjudication_fingerprint)
  on delete restrict,
add column layer_summary jsonb not null default '{}'::jsonb;

with ranked as (
  select consensus.id,
    row_number() over (
      partition by consensus.verification_campaign_pk,
        consensus.media_object_pk, consensus.consensus_layer
      order by consensus.created_at, consensus.id
    ) as revision
  from public.consensus consensus
)
update public.consensus consensus
set revision = ranked.revision,
  layer_summary = jsonb_build_object(
    'method', consensus.method,
    'policy_version', 'legacy-unversioned',
    'status', case consensus.status
      when 'reached' then 'available'
      when 'disputed' then 'blocked'
      when 'rejected' then 'blocked'
      else 'pending'
    end,
    'outcome', case consensus.decision
      when 'yes' then 'supported'
      when 'no' then 'not_supported'
      when 'cannot_tell' then 'uncertain'
      when 'cannot_view' then 'media_failure'
      else null
    end,
    'eligible_review_count', consensus.eligible_review_count,
    'decisive_review_count', consensus.decisive_review_count,
    'support_count', 0,
    'oppose_count', 0,
    'support_total', 0,
    'oppose_total', 0,
    'uncertain_count', 0,
    'media_failure_count', 0,
    'deferred_count', 0,
    'dissent_count', consensus.minority_dissent_count,
    'event_fingerprints', to_jsonb(consensus.review_event_fingerprints),
    'blockers', '[]'::jsonb,
    'model_vote_included', false,
    'scientific_claim_allowed', false,
    'outer_consensus_fingerprint', consensus.consensus_fingerprint,
    'adjudication_event_fingerprint', null,
    'release_gates', jsonb_build_object(
      'rights_passed', false, 'provenance_passed', false,
      'conflict_resolved', false, 'quality_passed', false,
      'expert_gate_satisfied', consensus.expert_gate_satisfied,
      'authorization_passed', false
    )
  )
from ranked where ranked.id = consensus.id;

alter table public.consensus
alter column revision set not null,
add constraint consensus_revision_check check (revision >= 1),
add constraint consensus_reliability_snapshot_fingerprint_check check (
  reliability_snapshot_fingerprint is null
  or reliability_snapshot_fingerprint ~ '^[0-9a-f]{64}$'
),
add constraint consensus_adjudication_event_fingerprint_check check (
  adjudication_event_fingerprint is null
  or adjudication_event_fingerprint ~ '^[0-9a-f]{64}$'
),
add constraint consensus_layer_summary_check
  check (jsonb_typeof(layer_summary) = 'object'),
add constraint consensus_weighted_layer_check check (
  (
    reviewer_weights_applied
    and consensus_layer = 'qualified_consensus'
    and reliability_snapshot_fingerprint is not null
  ) or (
    not reviewer_weights_applied
    and reliability_snapshot_fingerprint is null
  )
);

create unique index consensus_layer_revision_key
on public.consensus (
  verification_campaign_pk, media_object_pk, consensus_layer, revision
);
create index consensus_current_layer_idx
on public.consensus (
  verification_campaign_pk, media_object_pk, consensus_layer, revision desc
);
create index consensus_adjudication_event_fingerprint_idx
on public.consensus (adjudication_event_fingerprint)
where adjudication_event_fingerprint is not null;

create function private.enforce_layered_consensus_snapshot()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  previous_snapshot record;
  expected_decision text;
  expected_status text;
begin
  perform pg_advisory_xact_lock(hashtextextended(
    new.verification_campaign_pk::text || ':' || new.media_object_pk::text
    || ':' || new.consensus_layer,
    0
  ));

  if new.method_version <> 'butterflylens-layered-consensus:v1.0.0'
     or new.layer_summary ->> 'policy_version'
       is distinct from 'butterflylens-layered-consensus-policy:v1.0.0'
     or new.layer_summary ->> 'method' is distinct from new.method
     or (new.layer_summary -> 'model_vote_included')
       is distinct from 'false'::jsonb
     or (new.layer_summary -> 'scientific_claim_allowed')
       is distinct from 'false'::jsonb then
    raise exception 'consensus method or scientific boundary is invalid'
      using errcode = '23514';
  end if;
  if (new.layer_summary ->> 'outer_consensus_fingerprint')
       is distinct from new.consensus_fingerprint
     or (new.layer_summary ->> 'adjudication_event_fingerprint')
       is distinct from new.adjudication_event_fingerprint
     or (new.layer_summary ->> 'eligible_review_count')::integer
       is distinct from new.eligible_review_count
     or (new.layer_summary ->> 'decisive_review_count')::integer
       is distinct from new.decisive_review_count
     or (new.layer_summary ->> 'dissent_count')::integer
       is distinct from new.minority_dissent_count
     or (new.layer_summary -> 'event_fingerprints')
       is distinct from to_jsonb(new.review_event_fingerprints) then
    raise exception 'consensus columns diverge from the fingerprinted layer summary'
      using errcode = '23514';
  end if;
  if (new.layer_summary ->> 'support_count')::integer
       + (new.layer_summary ->> 'oppose_count')::integer
       is distinct from new.decisive_review_count
     or new.eligible_review_count is distinct from (
       new.decisive_review_count
       + (new.layer_summary ->> 'uncertain_count')::integer
       + (new.layer_summary ->> 'media_failure_count')::integer
       + (new.layer_summary ->> 'deferred_count')::integer
     )
     or new.minority_dissent_count is distinct from least(
       (new.layer_summary ->> 'support_count')::integer,
       (new.layer_summary ->> 'oppose_count')::integer
     ) then
    raise exception 'consensus raw counts or dissent do not reconcile'
      using errcode = '23514';
  end if;
  if jsonb_typeof(new.layer_summary -> 'support_total') <> 'number'
     or jsonb_typeof(new.layer_summary -> 'oppose_total') <> 'number'
     or (new.layer_summary ->> 'support_total')::double precision < 0
     or (new.layer_summary ->> 'oppose_total')::double precision < 0 then
    raise exception 'consensus weighted totals must be non-negative numbers'
      using errcode = '23514';
  end if;
  if new.method in (
    'unweighted_human_counts_v1', 'qualified_equal_weight_v1',
    'release_gate_v1'
  ) and (
    (new.layer_summary ->> 'support_total')::double precision
      is distinct from (new.layer_summary ->> 'support_count')::double precision
    or (new.layer_summary ->> 'oppose_total')::double precision
      is distinct from (new.layer_summary ->> 'oppose_count')::double precision
  ) then
    raise exception 'equal-weight layer totals must equal raw counts'
      using errcode = '23514';
  end if;

  if new.consensus_layer = 'community_evidence' and (
    new.method <> 'unweighted_human_counts_v1'
    or new.reviewer_weights_applied
  ) then
    raise exception 'community evidence must remain unweighted'
      using errcode = '23514';
  elsif new.consensus_layer = 'qualified_consensus' and new.method not in (
    'qualified_equal_weight_v1', 'qualified_reliability_weighted_v1',
    'qualified_adjudication_v1'
  ) then
    raise exception 'qualified consensus method is unsupported'
      using errcode = '23514';
  elsif new.consensus_layer = 'release_consensus'
        and new.method <> 'release_gate_v1' then
    raise exception 'release consensus requires the release gate method'
      using errcode = '23514';
  end if;
  if new.method = 'qualified_reliability_weighted_v1'
     and not new.reviewer_weights_applied then
    raise exception 'weighted qualified consensus requires a reliability snapshot'
      using errcode = '23514';
  end if;
  if new.reviewer_weights_applied and new.method not in (
    'qualified_reliability_weighted_v1', 'qualified_adjudication_v1'
  ) then
    raise exception 'reliability weights are restricted to qualified methods'
      using errcode = '23514';
  end if;
  if (
    new.consensus_layer = 'qualified_consensus'
    and new.qualified_review_count <> new.eligible_review_count
  ) or (
    new.consensus_layer <> 'qualified_consensus'
    and new.qualified_review_count <> 0
  ) then
    raise exception 'qualified review count disagrees with its layer'
      using errcode = '23514';
  end if;
  if new.method = 'qualified_adjudication_v1'
     and new.adjudication_event_fingerprint is null then
    raise exception 'adjudicated consensus requires exact adjudication lineage'
      using errcode = '23514';
  end if;

  expected_decision := case new.layer_summary ->> 'outcome'
    when 'supported' then 'yes'
    when 'not_supported' then 'no'
    when 'uncertain' then case
      when new.layer_summary ->> 'status' = 'available' then 'cannot_tell'
      else null
    end
    when 'media_failure' then 'cannot_view'
    when 'release_ready' then 'yes'
    else null
  end;
  expected_status := case
    when new.layer_summary ->> 'outcome' = 'not_release_ready'
      and new.layer_summary ->> 'status' = 'available' then 'rejected'
    when expected_decision is not null then 'reached'
    when new.layer_summary ->> 'status' = 'blocked' then 'disputed'
    else 'insufficient'
  end;
  if new.decision is distinct from expected_decision
     or new.status is distinct from expected_status then
    raise exception 'database consensus state disagrees with its layer summary'
      using errcode = '23514';
  end if;
  if new.consensus_layer = 'release_consensus' and (
    (new.layer_summary -> 'release_gates' -> 'expert_gate_satisfied')
      is distinct from to_jsonb(new.expert_gate_satisfied)
    or (
      new.layer_summary ->> 'outcome' = 'release_ready'
      and new.layer_summary -> 'release_gates' is distinct from
        '{"rights_passed":true,"provenance_passed":true,"conflict_resolved":true,"quality_passed":true,"expert_gate_satisfied":true,"authorization_passed":true}'::jsonb
    )
  ) then
    raise exception 'release consensus is missing an exact release gate'
      using errcode = '23514';
  end if;

  select consensus.id, consensus.revision
  into previous_snapshot
  from public.consensus consensus
  where consensus.verification_campaign_pk = new.verification_campaign_pk
    and consensus.media_object_pk = new.media_object_pk
    and consensus.consensus_layer = new.consensus_layer
  order by consensus.revision desc
  limit 1;

  if not found then
    new.revision := 1;
    new.supersedes_consensus_pk := null;
  else
    new.revision := previous_snapshot.revision + 1;
    new.supersedes_consensus_pk := previous_snapshot.id;
  end if;
  return new;
end;
$$;

create trigger consensus_enforce_layered_snapshot
before insert on public.consensus
for each row execute function private.enforce_layered_consensus_snapshot();

create function private.reject_consensus_mutation()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  raise exception 'consensus snapshots are append only' using errcode = '55000';
end;
$$;

create trigger consensus_reject_mutation
before update or delete on public.consensus
for each row execute function private.reject_consensus_mutation();

revoke all on function private.enforce_layered_consensus_snapshot(),
  private.reject_consensus_mutation()
from public, anon, authenticated;

comment on table public.consensus is
  'Append-only layered human consensus: unweighted community evidence, optionally reliability-weighted qualified evidence, and explicit release gates with retained dissent.';
