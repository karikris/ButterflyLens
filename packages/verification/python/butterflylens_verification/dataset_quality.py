"""Representative dataset-quality estimation with a separate targeted queue."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import re
from typing import Literal, Sequence

from butterflylens.contracts.fingerprint import canonicalize_json


SCHEMA_VERSION = "butterflylens-quality-snapshot:v1.0.0"
POLICY_VERSION = "butterflylens-representative-audit-policy:v1.0.0"
ESTIMATOR_VERSION = "butterflylens-dataset-quality-estimator:v1.0.0"
INCLUSION_PROBABILITY_METHOD = "hajek_inverse_inclusion_probability_v1"
INTERVAL_METHOD = "stratified_owner_observation_group_bootstrap_v1"
DEFAULT_BOOTSTRAP_REPLICATES = 2_000
MINIMUM_BOOTSTRAP_REPLICATES = 200
CONFIDENCE_LEVEL = 0.95

AuditKind = Literal["representative_audit", "targeted_failure_discovery"]
SamplingDesign = Literal[
    "simple_random", "stratified_random", "clustered_random", "targeted_priority"
]
AuditOutcome = Literal[
    "supported", "not_supported", "uncertain", "media_failure", "deferred"
]
ConsensusStatus = Literal[
    "pending",
    "complete_agreement",
    "unresolved_disagreement",
    "uncertain_only",
    "media_failure",
    "deferred",
    "adjudicated",
]

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STABLE_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,159}$")
_REPRESENTATIVE_DESIGNS = {"simple_random", "stratified_random", "clustered_random"}
_OUTCOMES = {"supported", "not_supported", "uncertain", "media_failure", "deferred"}


class QualityEvidenceError(ValueError):
    """Raised when audit evidence is malformed or internally inconsistent."""


@dataclass(frozen=True, slots=True)
class SamplingStratum:
    stratum_id: str
    label: str
    population_count: int | None
    population_weight: float | None


@dataclass(frozen=True, slots=True)
class AuditPlan:
    plan_id: str
    audit_kind: AuditKind
    design: SamplingDesign
    representative: bool
    blind: bool
    inclusion_probability_method: str | None
    sampling_frame_fingerprint: str
    grouping_keys: tuple[str, ...]
    strata: tuple[SamplingStratum, ...]


@dataclass(frozen=True, slots=True)
class AuditRecord:
    record_id: str
    stratum_id: str
    inclusion_probability: float | None
    owner_group_id: str | None
    observation_group_id: str | None
    outcome: AuditOutcome
    consensus_status: ConsensusStatus
    review_fingerprint: str
    consensus_fingerprint: str


def estimate_dataset_quality(
    *,
    quality_snapshot_id: str,
    project_id: str,
    run_id: str,
    plan: AuditPlan,
    records: Sequence[AuditRecord],
    generated_at: str,
    bootstrap_seed: str,
    bootstrap_replicates: int = DEFAULT_BOOTSTRAP_REPLICATES,
) -> dict[str, object]:
    """Estimate population precision only for a valid probability audit.

    Targeted failure-discovery records are summarized, but they can never be
    converted into a population estimate. Invalid or incomplete representative
    evidence fails closed with explicit blockers and null statistical fields.
    """

    for value, field in (
        (quality_snapshot_id, "quality_snapshot_id"),
        (project_id, "project_id"),
        (run_id, "run_id"),
        (plan.plan_id, "plan_id"),
    ):
        _validate_stable_id(value, field)
    _validate_timestamp(generated_at)
    _validate_plan(plan)
    canonical_records = _validate_records(records, plan)
    if (
        isinstance(bootstrap_replicates, bool)
        or not isinstance(bootstrap_replicates, int)
        or bootstrap_replicates < MINIMUM_BOOTSTRAP_REPLICATES
    ):
        raise QualityEvidenceError(
            f"bootstrap_replicates must be at least {MINIMUM_BOOTSTRAP_REPLICATES}"
        )
    if not bootstrap_seed:
        raise QualityEvidenceError("bootstrap_seed must not be empty")

    supported = sum(record.outcome == "supported" for record in canonical_records)
    failures = sum(record.outcome == "not_supported" for record in canonical_records)
    decisive = supported + failures
    unresolved = len(canonical_records) - decisive
    seed_fingerprint = hashlib.sha256(bootstrap_seed.encode("utf-8")).hexdigest()
    audit_manifest = [
        {
            "record_id": record.record_id,
            "stratum_id": record.stratum_id,
            "inclusion_probability": record.inclusion_probability,
            "owner_group_fingerprint": _group_fingerprint(
                plan.sampling_frame_fingerprint, "owner", record.owner_group_id
            ),
            "observation_group_fingerprint": _group_fingerprint(
                plan.sampling_frame_fingerprint,
                "observation",
                record.observation_group_id,
            ),
            "outcome": record.outcome,
            "consensus_status": record.consensus_status,
            "review_fingerprint": record.review_fingerprint,
            "consensus_fingerprint": record.consensus_fingerprint,
        }
        for record in canonical_records
    ]
    audit_evidence_fingerprint = hashlib.sha256(
        canonicalize_json(audit_manifest)
    ).hexdigest()
    blockers = _eligibility_blockers(plan, canonical_records)

    estimate: float | None = None
    interval: dict[str, object] | None = None
    effective_sample_size: float | None = None
    group_count = 0
    strata_summary: list[dict[str, object]] = []
    analysis_weights: dict[str, float] = {}
    groups_by_stratum: dict[str, list[list[AuditRecord]]] = {}

    decisive_records = [
        record
        for record in canonical_records
        if record.outcome in ("supported", "not_supported")
    ]
    stratum_weights, weight_blockers = _stratum_population_weights(plan.strata)
    blockers.extend(weight_blockers)
    if plan.audit_kind == "representative_audit" and not blockers:
        analysis_weights = _analysis_weights(decisive_records, stratum_weights)
        all_groups, group_blockers = _connected_groups(canonical_records)
        blockers.extend(group_blockers)
        for stratum_id, groups in all_groups.items():
            decisive_groups = [
                [
                    record
                    for record in group
                    if record.outcome in ("supported", "not_supported")
                ]
                for group in groups
            ]
            groups_by_stratum[stratum_id] = [
                group for group in decisive_groups if group
            ]
        group_count = sum(len(groups) for groups in groups_by_stratum.values())
        for stratum in plan.strata:
            if len(groups_by_stratum.get(stratum.stratum_id, [])) < 2:
                blockers.append(f"stratum_group_count_below_two:{stratum.stratum_id}")

    blockers = sorted(set(blockers))
    if plan.audit_kind == "representative_audit" and not blockers:
        estimate = _weighted_estimate(decisive_records, analysis_weights)
        weights = list(analysis_weights.values())
        effective_sample_size = sum(weights) ** 2 / sum(weight * weight for weight in weights)
        estimates = _grouped_bootstrap(
            groups_by_stratum=groups_by_stratum,
            stratum_weights=stratum_weights,
            bootstrap_seed=bootstrap_seed,
            replicates=bootstrap_replicates,
        )
        lower, upper = _percentile_interval(estimates, CONFIDENCE_LEVEL)
        interval = {
            "lower": lower,
            "upper": upper,
            "level": CONFIDENCE_LEVEL,
            "method": INTERVAL_METHOD,
        }

    for stratum in plan.strata:
        sampled = [
            record
            for record in canonical_records
            if record.stratum_id == stratum.stratum_id
        ]
        stratum_decisive = [
            record for record in sampled if record.outcome in ("supported", "not_supported")
        ]
        stratum_support = sum(record.outcome == "supported" for record in stratum_decisive)
        stratum_analysis_weight = sum(
            analysis_weights.get(record.record_id, 0.0) for record in stratum_decisive
        )
        stratum_estimate = None
        if stratum_analysis_weight > 0:
            stratum_estimate = sum(
                analysis_weights[record.record_id]
                for record in stratum_decisive
                if record.outcome == "supported"
            ) / stratum_analysis_weight
        strata_summary.append(
            {
                "stratum_id": stratum.stratum_id,
                "population_count": stratum.population_count,
                "population_weight": stratum_weights.get(stratum.stratum_id),
                "sample_count": len(sampled),
                "decisive_count": len(stratum_decisive),
                "supported_count": stratum_support,
                "failure_count": len(stratum_decisive) - stratum_support,
                "analysis_weight": stratum_analysis_weight if analysis_weights else None,
                "precision_estimate": stratum_estimate,
                "resampling_group_count": len(groups_by_stratum.get(stratum.stratum_id, [])),
            }
        )

    availability = "estimated" if estimate is not None else "unavailable"
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "estimator_version": ESTIMATOR_VERSION,
        "quality_snapshot_id": quality_snapshot_id,
        "project_id": project_id,
        "run_id": run_id,
        "audit_kind": plan.audit_kind,
        "availability": availability,
        "sampling_plan_id": plan.plan_id,
        "sampling_frame_fingerprint": plan.sampling_frame_fingerprint,
        "sampling_design": plan.design,
        "representative": plan.representative,
        "blind": plan.blind,
        "inclusion_probability_method": plan.inclusion_probability_method,
        "interval_method": INTERVAL_METHOD,
        "audit_records": audit_manifest,
        "audit_evidence_fingerprint": audit_evidence_fingerprint,
        "sampling_strata": strata_summary,
        "grouping_keys": list(plan.grouping_keys),
        "reviewed_sample": len(canonical_records),
        "decisive_reviews": decisive,
        "supported_count": supported,
        "failure_count": failures,
        "unresolved_count": unresolved,
        "precision_estimate": estimate,
        "interval": interval,
        "effective_sample_size": effective_sample_size,
        "bootstrap_replicates": bootstrap_replicates,
        "bootstrap_seed_fingerprint": seed_fingerprint,
        "resampling_group_count": group_count,
        "blockers": blockers,
        "population_estimate_allowed": estimate is not None,
        "targeted_queue_separate": True,
        "model_vote_included": False,
        "scientific_claim_allowed": False,
        "generated_at": generated_at,
    }
    payload["snapshot_fingerprint"] = hashlib.sha256(
        canonicalize_json(payload)
    ).hexdigest()
    return payload


def quality_storage_fields(snapshot: dict[str, object]) -> dict[str, object]:
    """Return database fields while enforcing targeted/representative separation."""

    if snapshot.get("schema_version") != SCHEMA_VERSION:
        raise QualityEvidenceError("storage mapping requires a quality snapshot")
    if snapshot.get("model_vote_included") is not False:
        raise QualityEvidenceError("model votes cannot enter quality estimation")
    if snapshot.get("scientific_claim_allowed") is not False:
        raise QualityEvidenceError("quality snapshot cannot make a scientific claim")
    if snapshot.get("audit_kind") == "targeted_failure_discovery" and any(
        snapshot.get(field) is not None
        for field in ("precision_estimate", "interval", "effective_sample_size")
    ):
        raise QualityEvidenceError("targeted discovery cannot store a population estimate")
    interval = snapshot.get("interval")
    return {
        "snapshot_kind": snapshot.get("audit_kind"),
        "sampling_frame_fingerprint": snapshot.get("sampling_frame_fingerprint"),
        "inclusion_probability_method": snapshot.get("inclusion_probability_method"),
        "sampling_plan_id": snapshot.get("sampling_plan_id"),
        "audit_evidence_fingerprint": snapshot.get("audit_evidence_fingerprint"),
        "sampling_design": snapshot.get("sampling_design"),
        "representative": snapshot.get("representative"),
        "blind": snapshot.get("blind"),
        "reviewed_sample": snapshot.get("reviewed_sample"),
        "decisive_reviews": snapshot.get("decisive_reviews"),
        "effective_sample_size": snapshot.get("effective_sample_size"),
        "precision_estimate": snapshot.get("precision_estimate"),
        "interval_lower": interval.get("lower") if isinstance(interval, dict) else None,
        "interval_upper": interval.get("upper") if isinstance(interval, dict) else None,
        "estimator_version": snapshot.get("estimator_version"),
        "policy_version": snapshot.get("policy_version"),
        "confidence_level": interval.get("level") if isinstance(interval, dict) else None,
        "interval_method": snapshot.get("interval_method"),
        "bootstrap_replicates": snapshot.get("bootstrap_replicates"),
        "bootstrap_seed_fingerprint": snapshot.get("bootstrap_seed_fingerprint"),
        "resampling_group_count": snapshot.get("resampling_group_count"),
        "population_estimate_allowed": snapshot.get("population_estimate_allowed"),
        "estimate_payload": snapshot,
        "release_blockers": snapshot.get("blockers"),
        "snapshot_fingerprint": snapshot.get("snapshot_fingerprint"),
    }


def _validate_plan(plan: AuditPlan) -> None:
    if plan.audit_kind not in ("representative_audit", "targeted_failure_discovery"):
        raise QualityEvidenceError("audit_kind is unsupported")
    if plan.design not in _REPRESENTATIVE_DESIGNS | {"targeted_priority"}:
        raise QualityEvidenceError("sampling design is unsupported")
    if not _SHA256.fullmatch(plan.sampling_frame_fingerprint):
        raise QualityEvidenceError("sampling_frame_fingerprint must be lowercase SHA-256")
    if not plan.strata:
        raise QualityEvidenceError("sampling plan requires at least one stratum")
    stratum_ids: set[str] = set()
    for stratum in plan.strata:
        _validate_stable_id(stratum.stratum_id, "stratum_id")
        if stratum.stratum_id in stratum_ids:
            raise QualityEvidenceError("stratum IDs must be unique")
        stratum_ids.add(stratum.stratum_id)
        if not stratum.label or len(stratum.label) > 160:
            raise QualityEvidenceError("stratum label must contain 1 to 160 characters")
        if stratum.population_count is not None and (
            isinstance(stratum.population_count, bool)
            or not isinstance(stratum.population_count, int)
            or stratum.population_count <= 0
        ):
            raise QualityEvidenceError("population_count must be a positive integer")
        if stratum.population_weight is not None and (
            isinstance(stratum.population_weight, bool)
            or not math.isfinite(stratum.population_weight)
            or not 0 < stratum.population_weight <= 1
        ):
            raise QualityEvidenceError("population_weight must be in (0, 1]")
    if len(set(plan.grouping_keys)) != len(plan.grouping_keys):
        raise QualityEvidenceError("grouping keys must be unique")


def _validate_records(records: Sequence[AuditRecord], plan: AuditPlan) -> list[AuditRecord]:
    stratum_ids = {stratum.stratum_id for stratum in plan.strata}
    seen: set[str] = set()
    result: list[AuditRecord] = []
    for record in records:
        _validate_stable_id(record.record_id, "record_id")
        if record.record_id in seen:
            raise QualityEvidenceError("audit record IDs must be unique")
        seen.add(record.record_id)
        if record.stratum_id not in stratum_ids:
            raise QualityEvidenceError("audit record references an undeclared stratum")
        if record.outcome not in _OUTCOMES:
            raise QualityEvidenceError("audit outcome is unsupported")
        allowed_statuses = {
            "supported": {"complete_agreement", "adjudicated"},
            "not_supported": {"complete_agreement", "adjudicated"},
            "uncertain": {"uncertain_only"},
            "media_failure": {"media_failure"},
            "deferred": {"pending", "deferred", "unresolved_disagreement"},
        }
        if record.consensus_status not in allowed_statuses[record.outcome]:
            raise QualityEvidenceError("audit outcome contradicts consensus status")
        for value, field in (
            (record.review_fingerprint, "review_fingerprint"),
            (record.consensus_fingerprint, "consensus_fingerprint"),
        ):
            if not _SHA256.fullmatch(value):
                raise QualityEvidenceError(f"{field} must be lowercase SHA-256")
        for value, field in (
            (record.owner_group_id, "owner_group_id"),
            (record.observation_group_id, "observation_group_id"),
        ):
            if value is not None:
                _validate_stable_id(value, field)
        result.append(record)
    return sorted(result, key=lambda item: item.record_id)


def _eligibility_blockers(plan: AuditPlan, records: Sequence[AuditRecord]) -> list[str]:
    if plan.audit_kind == "targeted_failure_discovery":
        return ["targeted_failure_discovery_is_not_population_representative"]
    blockers: list[str] = []
    if plan.design not in _REPRESENTATIVE_DESIGNS:
        blockers.append("sampling_design_is_not_probability_based")
    if not plan.representative:
        blockers.append("sampling_plan_not_representative")
    if not plan.blind:
        blockers.append("audit_not_blind")
    if plan.inclusion_probability_method != INCLUSION_PROBABILITY_METHOD:
        blockers.append("inclusion_probability_method_missing_or_unsupported")
    if "owner_id" not in plan.grouping_keys:
        blockers.append("owner_grouping_key_missing")
    if "observation_id" not in plan.grouping_keys:
        blockers.append("observation_grouping_key_missing")
    decisive_by_stratum = {stratum.stratum_id: 0 for stratum in plan.strata}
    for record in records:
        probability = record.inclusion_probability
        if (
            probability is None
            or isinstance(probability, bool)
            or not isinstance(probability, (int, float))
            or not math.isfinite(probability)
            or not 0 < probability <= 1
        ):
            blockers.append(f"invalid_inclusion_probability:{record.record_id}")
        if record.owner_group_id is None:
            blockers.append(f"owner_group_missing:{record.record_id}")
        if record.observation_group_id is None:
            blockers.append(f"observation_group_missing:{record.record_id}")
        if record.outcome in ("supported", "not_supported"):
            decisive_by_stratum[record.stratum_id] += 1
    for stratum_id, count in decisive_by_stratum.items():
        if count == 0:
            blockers.append(f"stratum_without_decisive_reviews:{stratum_id}")
    return blockers


def _stratum_population_weights(
    strata: Sequence[SamplingStratum],
) -> tuple[dict[str, float], list[str]]:
    explicit = [stratum.population_weight for stratum in strata]
    if all(weight is not None for weight in explicit):
        total = sum(float(weight) for weight in explicit)
        if not math.isclose(total, 1.0, rel_tol=0, abs_tol=1e-9):
            return {}, ["stratum_population_weights_do_not_sum_to_one"]
        return {
            stratum.stratum_id: float(stratum.population_weight)
            for stratum in strata
        }, []
    if any(weight is not None for weight in explicit):
        return {}, ["stratum_population_weights_partially_declared"]
    counts = [stratum.population_count for stratum in strata]
    if any(count is None for count in counts):
        return {}, ["stratum_population_sizes_missing"]
    total_count = sum(int(count) for count in counts)
    return {
        stratum.stratum_id: int(stratum.population_count) / total_count
        for stratum in strata
    }, []


def _analysis_weights(
    records: Sequence[AuditRecord], stratum_weights: dict[str, float]
) -> dict[str, float]:
    result: dict[str, float] = {}
    for stratum_id, population_weight in stratum_weights.items():
        sampled = [record for record in records if record.stratum_id == stratum_id]
        inverse = [1.0 / float(record.inclusion_probability) for record in sampled]
        denominator = sum(inverse)
        for record, value in zip(sampled, inverse, strict=True):
            result[record.record_id] = population_weight * value / denominator
    return result


def _connected_groups(
    records: Sequence[AuditRecord],
) -> tuple[dict[str, list[list[AuditRecord]]], list[str]]:
    parent = {record.record_id: record.record_id for record in records}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    keys: dict[tuple[str, str], str] = {}
    for record in records:
        for kind, value in (
            ("owner", record.owner_group_id),
            ("observation", record.observation_group_id),
        ):
            key = (kind, str(value))
            if key in keys:
                union(record.record_id, keys[key])
            else:
                keys[key] = record.record_id
    components: dict[str, list[AuditRecord]] = {}
    for record in records:
        components.setdefault(find(record.record_id), []).append(record)
    blockers: list[str] = []
    result: dict[str, list[list[AuditRecord]]] = {}
    for component in components.values():
        stratum_ids = {record.stratum_id for record in component}
        if len(stratum_ids) != 1:
            blockers.append("owner_observation_group_crosses_strata")
            continue
        stratum_id = next(iter(stratum_ids))
        result.setdefault(stratum_id, []).append(
            sorted(component, key=lambda item: item.record_id)
        )
    for groups in result.values():
        groups.sort(key=lambda group: group[0].record_id)
    return result, blockers


def _weighted_estimate(
    records: Sequence[AuditRecord], weights: dict[str, float]
) -> float:
    return sum(
        weights[record.record_id]
        for record in records
        if record.outcome == "supported"
    ) / sum(weights.values())


def _grouped_bootstrap(
    *,
    groups_by_stratum: dict[str, list[list[AuditRecord]]],
    stratum_weights: dict[str, float],
    bootstrap_seed: str,
    replicates: int,
) -> list[float]:
    estimates: list[float] = []
    for replicate in range(replicates):
        estimate = 0.0
        for stratum_id in sorted(groups_by_stratum):
            groups = groups_by_stratum[stratum_id]
            selected: list[AuditRecord] = []
            for draw in range(len(groups)):
                digest = hashlib.sha256(
                    f"{bootstrap_seed}\0{replicate}\0{stratum_id}\0{draw}".encode("utf-8")
                ).digest()
                index = int.from_bytes(digest[:8], "big") % len(groups)
                selected.extend(groups[index])
            inverse = [1.0 / float(record.inclusion_probability) for record in selected]
            denominator = sum(inverse)
            supported = sum(
                weight
                for record, weight in zip(selected, inverse, strict=True)
                if record.outcome == "supported"
            )
            estimate += stratum_weights[stratum_id] * supported / denominator
        estimates.append(estimate)
    return sorted(estimates)


def _percentile_interval(values: Sequence[float], level: float) -> tuple[float, float]:
    tail = (1.0 - level) / 2.0
    return _quantile(values, tail), _quantile(values, 1.0 - tail)


def _quantile(values: Sequence[float], probability: float) -> float:
    position = (len(values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    fraction = position - lower
    return values[lower] * (1.0 - fraction) + values[upper] * fraction


def _validate_stable_id(value: str, field: str) -> None:
    if not isinstance(value, str) or not _STABLE_ID.fullmatch(value):
        raise QualityEvidenceError(f"{field} must be a stable identifier")


def _validate_timestamp(value: str) -> None:
    from datetime import datetime

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as error:
        raise QualityEvidenceError("generated_at must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise QualityEvidenceError("generated_at must include a timezone")


def _group_fingerprint(
    sampling_frame_fingerprint: str, kind: str, value: str | None
) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(
        f"{sampling_frame_fingerprint}\0{kind}\0{value}".encode("utf-8")
    ).hexdigest()
