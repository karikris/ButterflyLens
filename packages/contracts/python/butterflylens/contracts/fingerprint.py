"""Physical checksum and semantic fingerprint wire declarations."""

from __future__ import annotations

from typing import Literal, TypedDict


CONTENT_CHECKSUM_SCHEMA_VERSION = "butterflylens-content-checksum:v1.0.0"
EVIDENCE_FINGERPRINT_SCHEMA_VERSION = (
    "butterflylens-evidence-fingerprint:v1.0.0"
)
FINGERPRINT_CANONICALIZATION = "RFC8785-JCS"
FINGERPRINT_HASH_ALGORITHM = "sha256"

FINGERPRINT_KINDS = (
    "project_definition",
    "run_input_set",
    "taxon_concept",
    "name_assertion",
    "query_definition",
    "physical_api_request",
    "provider_snapshot",
    "api_response",
    "source_flickr_record",
    "downloaded_image",
    "media_object",
    "perceptual_duplicate_group",
    "model_artifact",
    "preprocessing",
    "yoloe_route",
    "full_frame_visual_input",
    "bioclip_embedding",
    "reference_bank",
    "prototype",
    "candidate_score",
    "review_event",
    "consensus",
    "quality_snapshot",
    "geographic_impact_cell",
    "map_snapshot",
    "release_candidate",
    "artifact_manifest",
    "export_manifest",
)
FINGERPRINT_PARENT_RELATIONSHIPS = (
    "derived_from",
    "contains",
    "produced_by",
    "supersedes",
    "reviews",
    "aggregates",
    "compares",
    "calibrates",
)


class ContentChecksum(TypedDict):
    schema_version: Literal["butterflylens-content-checksum:v1.0.0"]
    algorithm: Literal["sha256"]
    digest: str
    byte_count: int
    media_type: str


class EvidenceFingerprintParent(TypedDict):
    relationship: str
    fingerprint_kind: str
    digest: str


class EvidenceFingerprintPreimage(TypedDict):
    fingerprint_kind: str
    subject_id: str
    payload_schema_version: str
    payload: dict[str, object]
    parents: list[EvidenceFingerprintParent]


class EvidenceFingerprint(TypedDict):
    schema_version: Literal["butterflylens-evidence-fingerprint:v1.0.0"]
    hash_algorithm: Literal["sha256"]
    canonicalization: Literal["RFC8785-JCS"]
    preimage: EvidenceFingerprintPreimage
    digest: str
    recorded_at: str
