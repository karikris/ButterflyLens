"""Per-image classification evidence-maturity wire declarations."""

from __future__ import annotations

from typing import Literal, TypedDict


CLASSIFICATION_MATURITY_SCHEMA_VERSION = (
    "butterflylens-classification-maturity:v1.0.0"
)
CLASSIFICATION_MATURITY_FIELDS = (
    "butterfly_detected",
    "species_candidate_available",
    "community_reviewed",
    "quality_estimate_available",
    "expert_reviewed",
    "release_ready",
)
CLASSIFICATION_MATURITY_STATUSES = ("available", "unavailable")


class ClassificationEvidenceState(TypedDict):
    status: Literal["available", "unavailable"]
    value: bool | None
    reason: str | None
    evidence_fingerprints: list[str]


class ClassificationMaturity(TypedDict):
    schema_version: Literal["butterflylens-classification-maturity:v1.0.0"]
    image_id: str
    source_record_fingerprint: str
    observed_at: str
    maturity: dict[str, ClassificationEvidenceState]
    projection_fingerprint: str
    scientific_claim_allowed: Literal[False]
