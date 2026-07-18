"""Pure, side-effect-free live-service incident and fallback planning."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import stat
from typing import Literal, Mapping

from butterflylens.contracts.fingerprint import canonicalize_json


INCIDENT_PLAN_SCHEMA_VERSION = "butterflylens-incident-plan:v1.0.0"
CHECKPOINT_VERIFICATION_SCHEMA_VERSION = (
    "butterflylens-checkpoint-verification:v1.0.0"
)
IncidentKind = Literal[
    "m5_sleep",
    "network_outage",
    "flickr_outage",
    "b2_outage",
    "supabase_outage",
    "model_crash",
    "corrupted_checkpoint",
    "rate_limit_exhaustion",
]
INCIDENT_KINDS = (
    "m5_sleep",
    "network_outage",
    "flickr_outage",
    "b2_outage",
    "supabase_outage",
    "model_crash",
    "corrupted_checkpoint",
    "rate_limit_exhaustion",
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MAX_CHECKPOINT_BYTES = 256 * 1024 * 1024


class IncidentPlanningError(RuntimeError):
    """Raised when incident input could authorize unsafe recovery."""


_POLICIES: Mapping[str, Mapping[str, object]] = {
    "m5_sleep": {
        "worker_state": "offline",
        "affected_boundary": "worker",
        "stage_action": "pause_all_worker_stages",
        "resume_condition": "fresh_lease_after_wake_and_checkpoint_verification",
        "checkpoint_action": "verify_before_resume",
        "blocked_actions": [
            "worker_execution",
            "flickr_requests",
            "b2_writes",
            "supabase_writes",
            "model_execution",
        ],
        "monitoring_state": "unavailable",
    },
    "network_outage": {
        "worker_state": "degraded",
        "affected_boundary": "outbound_network",
        "stage_action": "pause_network_dependent_stages",
        "resume_condition": "bounded_health_probe_after_scheduler_backoff",
        "checkpoint_action": "retain_and_verify_before_resume",
        "blocked_actions": [
            "flickr_requests",
            "b2_writes",
            "supabase_writes",
            "immediate_retry",
        ],
        "monitoring_state": "degraded",
    },
    "flickr_outage": {
        "worker_state": "degraded",
        "affected_boundary": "flickr",
        "stage_action": "pause_flickr_stages",
        "resume_condition": "provider_recovered_and_budget_available",
        "checkpoint_action": "retain",
        "blocked_actions": [
            "flickr_requests",
            "unbounded_retry",
            "credential_rotation",
        ],
        "monitoring_state": "degraded",
    },
    "b2_outage": {
        "worker_state": "degraded",
        "affected_boundary": "b2_storage",
        "stage_action": "pause_artifact_commit_and_publication",
        "resume_condition": "durable_write_acknowledged",
        "checkpoint_action": "retain_local_sources_and_checkpoints",
        "blocked_actions": [
            "b2_writes",
            "local_source_deletion",
            "artifact_publication",
            "ambiguous_write_retry",
        ],
        "monitoring_state": "degraded",
    },
    "supabase_outage": {
        "worker_state": "degraded",
        "affected_boundary": "supabase",
        "stage_action": "pause_remote_control_and_telemetry_persistence",
        "resume_condition": "database_health_reestablished",
        "checkpoint_action": "retain_local_append_only_journals",
        "blocked_actions": [
            "supabase_writes",
            "control_state_mutation",
            "monitoring_publication",
            "fabricated_remote_acknowledgement",
        ],
        "monitoring_state": "unavailable",
    },
    "model_crash": {
        "worker_state": "degraded",
        "affected_boundary": "model_runtime",
        "stage_action": "pause_model_stages_and_mark_model_unavailable",
        "resume_condition": "operator_verified_runtime_and_checkpoint",
        "checkpoint_action": "verify_before_model_stage_resume",
        "blocked_actions": [
            "model_execution",
            "model_evidence_publication",
            "fallback_identity_claim",
        ],
        "monitoring_state": "degraded",
    },
    "corrupted_checkpoint": {
        "worker_state": "paused",
        "affected_boundary": "checkpoint",
        "stage_action": "quarantine_checkpoint_and_rebuild_uncommitted_work",
        "resume_condition": "verified_inputs_and_new_checkpoint",
        "checkpoint_action": "quarantine_without_delete",
        "blocked_actions": [
            "checkpoint_reuse",
            "affected_uncommitted_work_reuse",
            "committed_journal_mutation",
        ],
        "monitoring_state": "degraded",
    },
    "rate_limit_exhaustion": {
        "worker_state": "paused",
        "affected_boundary": "flickr_budget",
        "stage_action": "pause_flickr_stages_until_new_budget_window",
        "resume_condition": "new_utc_window_and_fresh_budget_ledger",
        "checkpoint_action": "retain",
        "blocked_actions": [
            "flickr_requests",
            "credential_rotation",
            "budget_lane_bypass",
            "early_retry",
        ],
        "monitoring_state": "degraded",
    },
}


def verify_checkpoint_file(
    path: Path,
    *,
    expected_sha256: str,
    max_bytes: int = _MAX_CHECKPOINT_BYTES,
) -> dict[str, object]:
    """Verify a bounded regular file without following symlinks or changing it."""

    _require_sha(expected_sha256, "expected checkpoint fingerprint")
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes < 1:
        raise IncidentPlanningError("checkpoint byte ceiling is invalid")
    target = Path(path)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(target, flags)
        with os.fdopen(descriptor, "rb") as handle:
            metadata = os.fstat(handle.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise IncidentPlanningError("checkpoint must be a regular file")
            if metadata.st_size > max_bytes:
                raise IncidentPlanningError("checkpoint exceeds its byte ceiling")
            digest = hashlib.sha256()
            byte_count = 0
            while chunk := handle.read(1024 * 1024):
                byte_count += len(chunk)
                if byte_count > max_bytes:
                    raise IncidentPlanningError("checkpoint exceeds its byte ceiling")
                digest.update(chunk)
    except (OSError, ValueError) as error:
        raise IncidentPlanningError("checkpoint is unavailable or unsafe") from error
    observed = digest.hexdigest()
    if observed != expected_sha256:
        raise IncidentPlanningError("checkpoint checksum mismatch")
    preimage = {
        "schema_version": CHECKPOINT_VERIFICATION_SCHEMA_VERSION,
        "byte_count": byte_count,
        "checkpoint_fingerprint": observed,
        "verified": True,
    }
    return {**preimage, "verification_fingerprint": _digest(preimage)}


def build_incident_fallback_plan(
    incident_kind: IncidentKind | str,
    *,
    observed_at: datetime,
    last_committed_artifact_fingerprint: str,
    checkpoint_fingerprint: str | None = None,
    checkpoint_verified: bool | None = None,
    budget_resets_at: datetime | None = None,
) -> dict[str, object]:
    """Create a deterministic recovery gate without executing the recovery."""

    if incident_kind not in _POLICIES:
        raise IncidentPlanningError("incident kind is invalid")
    _require_utc(observed_at, "incident observation time")
    _require_sha(
        last_committed_artifact_fingerprint,
        "last committed artifact fingerprint",
    )
    if (checkpoint_fingerprint is None) != (checkpoint_verified is None):
        raise IncidentPlanningError(
            "checkpoint fingerprint and verification state must be supplied together"
        )
    if checkpoint_fingerprint is not None:
        _require_sha(checkpoint_fingerprint, "checkpoint fingerprint")
        if not isinstance(checkpoint_verified, bool):
            raise IncidentPlanningError("checkpoint verification state is invalid")
    if incident_kind == "corrupted_checkpoint":
        if checkpoint_fingerprint is None or checkpoint_verified is not False:
            raise IncidentPlanningError(
                "corrupted checkpoint incident requires a failed verification"
            )
    elif checkpoint_verified is False:
        raise IncidentPlanningError(
            "failed checkpoint verification requires the corrupted checkpoint incident"
        )

    if incident_kind == "rate_limit_exhaustion":
        if budget_resets_at is None:
            raise IncidentPlanningError("rate-limit reset time is required")
        _require_utc(budget_resets_at, "rate-limit reset time")
        if budget_resets_at <= observed_at:
            raise IncidentPlanningError("rate-limit reset must be in the future")
    elif budget_resets_at is not None:
        raise IncidentPlanningError("reset time is valid only for rate-limit exhaustion")

    policy = dict(_POLICIES[str(incident_kind)])
    checkpoint_state = (
        "unavailable"
        if checkpoint_verified is None
        else "verified"
        if checkpoint_verified
        else "corrupt"
    )
    preimage = {
        "schema_version": INCIDENT_PLAN_SCHEMA_VERSION,
        "incident_kind": incident_kind,
        "observed_at": _utc_text(observed_at),
        **policy,
        "not_before": (
            None if budget_resets_at is None else _utc_text(budget_resets_at)
        ),
        "checkpoint": {
            "fingerprint": checkpoint_fingerprint,
            "verification_state": checkpoint_state,
            "action": policy["checkpoint_action"],
        },
        "durability": {
            "last_committed_artifact_fingerprint": (
                last_committed_artifact_fingerprint
            ),
            "last_committed_artifact_queryable": True,
            "submitted_snapshot_queryable": True,
            "local_sources_retained": True,
            "committed_journal_append_only": True,
            "duplicate_work_allowed": False,
        },
        "model_components": {
            "yoloe": "unfinished",
            "bioclip": "unfinished",
        },
        "side_effects_executed": False,
        "model_execution_occurred": False,
        "scientific_claim_allowed": False,
    }
    return {
        **preimage,
        "incident_id": f"blinc:v1:{_digest(preimage)[:24]}",
        "plan_fingerprint": _digest(preimage),
    }


def _require_sha(value: object, field: str) -> None:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise IncidentPlanningError(f"{field} must be lowercase SHA-256")


def _require_utc(value: object, field: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() != timezone.utc.utcoffset(value)
    ):
        raise IncidentPlanningError(f"{field} must be UTC")


def _utc_text(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _digest(value: Mapping[str, object]) -> str:
    return hashlib.sha256(canonicalize_json(value)).hexdigest()
