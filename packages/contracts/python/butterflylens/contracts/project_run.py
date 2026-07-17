"""Project and run declarations matching the JSON wire contracts."""

from __future__ import annotations

from typing import Literal, TypedDict


PROJECT_SCHEMA_VERSION = "butterflylens-project:v1.0.0"
RUN_SCHEMA_VERSION = "butterflylens-run:v1.0.0"

PROJECT_STATUSES = ("draft", "active", "paused", "archived")
RUN_KINDS = (
    "taxonomy_pack",
    "ala_baseline",
    "reference_bank",
    "flickr_discovery",
    "vision_pipeline",
    "geographic_impact",
    "quality_snapshot",
    "release_export",
    "full_pipeline",
)
RUN_MODES = ("live", "submitted", "replay")
RUN_STATUSES = (
    "queued",
    "leased",
    "running",
    "paused",
    "cancelling",
    "cancelled",
    "succeeded",
    "failed",
)
PIPELINE_STAGE_IDS = (
    "taxonomy",
    "names",
    "ala_baseline",
    "reference_admission",
    "flickr_plan",
    "flickr_fetch",
    "media",
    "yoloe",
    "bioclip",
    "scoring",
    "review",
    "geographic_impact",
    "quality",
    "release",
    "export",
)


class GeographicScope(TypedDict):
    country_code: Literal["AU"]
    boundary_id: str
    boundary_version: str
    boundary_sha256: str
    sensitive_coordinate_policy_version: str


class TaxonScope(TypedDict):
    root_taxon_keys: list[str]
    taxonomy_fingerprint: str


class DiscoveryScope(TypedDict):
    search_plan_fingerprint: str
    public_discovery_claim: Literal[
        "All butterfly candidate images discoverable through the published "
        "ButterflyLens Flickr search plan."
    ]


class ButterflyLensProject(TypedDict):
    schema_version: Literal["butterflylens-project:v1.0.0"]
    project_id: str
    slug: str
    name: str
    description: str
    status: Literal["draft", "active", "paused", "archived"]
    geographic_scope: GeographicScope
    taxon_scope: TaxonScope
    discovery_scope: DiscoveryScope
    data_policy_version: str
    consent_policy_version: str
    created_at: str
    updated_at: str


class RequestedBy(TypedDict):
    actor_type: Literal["system", "account", "operator"]
    actor_id: str | None


class RunEngine(TypedDict):
    repository: str
    commit: str
    interface_version: str
    command: str


class RunStage(TypedDict):
    stage_id: str
    status: Literal[
        "pending",
        "blocked",
        "running",
        "paused",
        "succeeded",
        "failed",
        "cancelled",
        "unavailable",
    ]
    started_at: str | None
    finished_at: str | None
    checkpoint_fingerprint: str | None
    records_processed: int
    records_total: int | None


class RunArtifact(TypedDict):
    artifact_id: str
    kind: str
    object_key: str
    sha256: str
    byte_count: int
    schema_version: str
    semantic_fingerprint: str


class RunError(TypedDict):
    code: str
    message: str
    retryable: bool
    stage_id: str | None


class ButterflyLensRun(TypedDict):
    schema_version: Literal["butterflylens-run:v1.0.0"]
    run_id: str
    project_id: str
    run_kind: str
    mode: Literal["live", "submitted", "replay"]
    status: str
    requested_by: RequestedBy
    requested_at: str
    started_at: str | None
    finished_at: str | None
    updated_at: str
    engine: RunEngine
    input_fingerprints: list[str]
    stages: list[RunStage]
    artifacts: list[RunArtifact]
    error: RunError | None
    revision: int
