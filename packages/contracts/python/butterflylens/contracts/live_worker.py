"""Persistent live-worker wire declarations."""

from __future__ import annotations

from typing import Literal, TypedDict


WORKER_IDENTITY_SCHEMA_VERSION = "butterflylens-worker-identity:v1.0.0"
WORKER_HEARTBEAT_SCHEMA_VERSION = "butterflylens-worker-heartbeat:v1.0.0"
WORKER_LEASE_SCHEMA_VERSION = "butterflylens-worker-lease:v1.0.0"
WORKER_COMMAND_SCHEMA_VERSION = "butterflylens-worker-command:v1.0.0"
WORKER_EVENT_SCHEMA_VERSION = "butterflylens-worker-event:v1.0.0"

WORKER_COMMAND_KINDS = (
    "start_run",
    "pause_run",
    "resume_run",
    "cancel_run",
    "health_check",
    "graceful_shutdown",
)
WORKER_EVENT_KINDS = (
    "stage_started",
    "progress",
    "checkpoint_committed",
    "artifact_committed",
    "stage_succeeded",
    "stage_failed",
    "run_paused",
    "run_cancelled",
    "shutdown_started",
    "shutdown_complete",
)


class WorkerIdentity(TypedDict):
    schema_version: Literal["butterflylens-worker-identity:v1.0.0"]
    worker_id: str
    registered_at: str
    machine_profile: dict[str, object]
    capabilities: dict[str, object]
    configured_models: list[dict[str, object]]
    identity_fingerprint: str
    scientific_claim_allowed: Literal[False]


class WorkerHeartbeat(TypedDict):
    schema_version: Literal["butterflylens-worker-heartbeat:v1.0.0"]
    heartbeat_id: str
    worker_id: str
    sequence: int
    observed_at: str
    state: str
    project_id: str | None
    run_id: str | None
    lease_id: str | None
    lease_revision: int | None
    lease_expires_at: str | None
    current_stage_id: str | None
    resources: dict[str, int | None]
    queues: list[dict[str, int | str]]
    models: list[dict[str, object]]
    cache: dict[str, int]
    last_committed_artifact_fingerprint: str | None
    last_committed_at: str | None
    health_checks: list[dict[str, str]]
    heartbeat_fingerprint: str
    scientific_claim_allowed: Literal[False]


class WorkerLease(TypedDict):
    schema_version: Literal["butterflylens-worker-lease:v1.0.0"]
    lease_id: str
    project_id: str
    run_id: str
    stage_id: str
    worker_id: str
    status: str
    revision: int
    fencing_token: str
    idempotency_key: str
    issued_at: str
    acquired_at: str | None
    renewed_at: str | None
    expires_at: str
    released_at: str | None
    checkpoint_fingerprint: str | None
    cancellation_requested: bool
    cancellation_requested_at: str | None
    lease_fingerprint: str


class WorkerCommand(TypedDict):
    schema_version: Literal["butterflylens-worker-command:v1.0.0"]
    command_id: str
    worker_id: str
    project_id: str | None
    run_id: str | None
    lease_id: str | None
    expected_lease_revision: int | None
    kind: str
    idempotency_key: str
    issued_at: str
    expires_at: str
    requested_by: str
    payload: dict[str, object]
    command_fingerprint: str


class WorkerEvent(TypedDict):
    schema_version: Literal["butterflylens-worker-event:v1.0.0"]
    event_id: str
    worker_id: str
    sequence: int
    project_id: str
    run_id: str
    lease_id: str
    lease_revision: int
    kind: str
    stage_id: str
    occurred_at: str
    records_processed: int
    bytes_processed: int
    checkpoint_fingerprint: str | None
    artifact_fingerprint: str | None
    error: dict[str, object] | None
    event_fingerprint: str
    scientific_claim_allowed: Literal[False]
