"""Australian geographic-impact wire declarations."""

from __future__ import annotations

from typing import Literal, TypedDict


GEOGRAPHIC_IMPACT_CELL_SCHEMA_VERSION = (
    "butterflylens-geographic-impact-cell:v1.0.0"
)
GEOGRAPHIC_IMPACT_SNAPSHOT_SCHEMA_VERSION = (
    "butterflylens-geographic-impact-snapshot:v1.0.0"
)
GEOGRAPHIC_IMPACT_QUERY_SCHEMA_VERSION = (
    "butterflylens-geographic-impact-query:v1.0.0"
)
EVIDENCE_COUNT_STATUSES = (
    "available",
    "unavailable",
    "withheld",
    "not_applicable",
)


class EvidenceCount(TypedDict):
    status: str
    value: int | None
    reason: str | None


class ImpactFlag(TypedDict):
    status: Literal["available", "unavailable"]
    value: bool | None
    reason: str | None


class GeographicImpactCell(TypedDict):
    schema_version: Literal["butterflylens-geographic-impact-cell:v1.0.0"]
    cell_id: str
    grid: Literal["H3"]
    h3_version: str
    h3_resolution: int
    project_id: str
    run_id: str
    snapshot_mode: Literal["live", "submitted"]
    accepted_taxon_key: str
    ala_snapshot_fingerprint: str | None
    flickr_snapshot_fingerprint: str | None
    provider_union_fingerprint: str | None
    review_projection_fingerprint: str | None
    quality_snapshot_fingerprint: str | None
    counts: dict[str, EvidenceCount]
    impact: dict[str, ImpactFlag]
    nearest_ala_evidence_distance: dict[str, object]
    latest_ala_event_date: str | None
    latest_flickr_event_date: str | None
    data_deficiency_state: str
    public_geometry: dict[str, object]
    evidence_fingerprints: list[str]
    cell_fingerprint: str
    scientific_claim_allowed: Literal[False]


class GeographicImpactSnapshot(TypedDict):
    schema_version: Literal["butterflylens-geographic-impact-snapshot:v1.0.0"]
    snapshot_id: str
    project_id: str
    run_id: str
    mode: Literal["live", "submitted"]
    country_code: Literal["AU"]
    status: Literal["available", "stale", "unavailable"]
    generated_at: str
    last_updated_at: str
    submitted_source_commit: str | None
    worker_heartbeat_fingerprint: str | None
    cell_schema_version: Literal["butterflylens-geographic-impact-cell:v1.0.0"]
    cell_count: int
    cell_artifact_checksum: str
    cell_artifact_fingerprint: str
    query_fingerprint: str
    map_projection_fingerprint: str
    blockers: list[str]
    append_only_revision: int


class GeographicImpactQuery(TypedDict):
    schema_version: Literal["butterflylens-geographic-impact-query:v1.0.0"]
    project_id: str
    accepted_taxon_keys: list[str]
    snapshot_mode: Literal["live", "submitted"]
    h3_resolution: int
    scope: dict[str, str]
    event_date_from: str | None
    event_date_to: str | None
    evidence_maturity: list[str]
    ala_basis_of_record: list[str]
    review_states: list[str]
    page_size: int
    query_fingerprint: str
