"""Physical checksums, semantic fingerprints, and RFC 8785 hashing."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import math
from typing import Literal, Mapping, NoReturn, TypedDict

import rfc8785


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
I_JSON_MAX_INTEGER = 9_007_199_254_740_991


class CanonicalizationError(ValueError):
    """Raised when a value cannot be represented by the fingerprint contract."""


def _canonicalization_error(path: str, message: str) -> NoReturn:
    raise CanonicalizationError(f"{path}: {message}")


def _validate_i_json(value: object, path: str = "$") -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if abs(value) > I_JSON_MAX_INTEGER:
            _canonicalization_error(path, "integer exceeds the I-JSON safe range")
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            _canonicalization_error(path, "number must be finite")
        if value == 0 and math.copysign(1, value) < 0:
            _canonicalization_error(path, "negative zero is forbidden")
        if value.is_integer() and abs(value) > I_JSON_MAX_INTEGER:
            encoded = rfc8785.dumps(value)
            if b"e" not in encoded:
                _canonicalization_error(path, "integer exceeds the I-JSON safe range")
        return
    if isinstance(value, str):
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeEncodeError as error:
            raise CanonicalizationError(f"{path}: string is not valid Unicode") from error
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_i_json(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                _canonicalization_error(path, "object keys must be strings")
            _validate_i_json(key, f"{path}.<key>")
            _validate_i_json(item, f"{path}.{key}")
        return
    _canonicalization_error(path, f"unsupported JSON value {type(value).__name__}")


def canonicalize_json(value: object) -> bytes:
    """Return RFC 8785 JCS bytes after applying ButterflyLens I-JSON gates."""

    _validate_i_json(value)
    try:
        return rfc8785.dumps(value)
    except (rfc8785.CanonicalizationError, ValueError, TypeError) as error:
        raise CanonicalizationError(f"$: RFC 8785 canonicalization failed: {error}") from error


def normalize_evidence_preimage(
    preimage: Mapping[str, object],
) -> dict[str, object]:
    """Copy a preimage and deterministically order its unique parent references."""

    normalized = deepcopy(dict(preimage))
    raw_parents = normalized.get("parents")
    if not isinstance(raw_parents, list):
        raise CanonicalizationError("$.parents: expected an array")
    identities: set[tuple[object, object, object]] = set()
    parents: list[dict[str, object]] = []
    for index, raw_parent in enumerate(raw_parents):
        if not isinstance(raw_parent, dict):
            raise CanonicalizationError(f"$.parents[{index}]: expected an object")
        identity = (
            raw_parent.get("relationship"),
            raw_parent.get("fingerprint_kind"),
            raw_parent.get("digest"),
        )
        if not all(isinstance(item, str) for item in identity):
            raise CanonicalizationError(
                f"$.parents[{index}]: relationship, fingerprint_kind, and digest must be strings"
            )
        if identity in identities:
            raise CanonicalizationError(f"$.parents[{index}]: duplicate parent reference")
        identities.add(identity)
        parents.append(deepcopy(raw_parent))
    parents.sort(
        key=lambda parent: (
            str(parent["relationship"]),
            str(parent["fingerprint_kind"]),
            str(parent["digest"]),
        )
    )
    normalized["parents"] = parents
    _validate_i_json(normalized)
    return normalized


def canonicalize_evidence_preimage(preimage: Mapping[str, object]) -> bytes:
    """Return canonical bytes for the semantic preimage, excluding its digest."""

    return canonicalize_json(normalize_evidence_preimage(preimage))


def semantic_fingerprint_digest(preimage: Mapping[str, object]) -> str:
    """Calculate the lowercase SHA-256 digest of a canonical semantic preimage."""

    return hashlib.sha256(canonicalize_evidence_preimage(preimage)).hexdigest()


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
