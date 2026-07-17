"""Physical checksums, semantic fingerprints, and RFC 8785 hashing."""

from __future__ import annotations

from collections import deque
from copy import deepcopy
from datetime import datetime
import hashlib
import hmac
import heapq
import math
import re
from typing import Iterable, Literal, Mapping, NoReturn, TypedDict

import rfc8785


CONTENT_CHECKSUM_SCHEMA_VERSION = "butterflylens-content-checksum:v1.0.0"
EVIDENCE_FINGERPRINT_LEGACY_SCHEMA_VERSION = (
    "butterflylens-evidence-fingerprint:v1.0.0"
)
EVIDENCE_FINGERPRINT_SCHEMA_VERSION = (
    "butterflylens-evidence-fingerprint:v1.1.0"
)
FINGERPRINT_CANONICALIZATION = "RFC8785-JCS"
FINGERPRINT_HASH_ALGORITHM = "sha256"

FINGERPRINT_KINDS_V1_0 = (
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
FINGERPRINT_KINDS = (
    "project_definition",
    "run_input_set",
    "taxon_concept",
    "name_assertion",
    "query_definition",
    "logical_query_association",
    "physical_api_request",
    "provider_snapshot",
    "source_response",
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
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_STABLE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]*$")
_RFC3339_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


class CanonicalizationError(ValueError):
    """Raised when a value cannot be represented by the fingerprint contract."""


class FingerprintValidationError(ValueError):
    """Raised when a fingerprint record is malformed or fails recomputation."""


class FingerprintIntegrityError(ValueError):
    """Raised when a validated fingerprint graph has broken lineage."""


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


def _validation_error(path: str, message: str) -> NoReturn:
    raise FingerprintValidationError(f"{path}: {message}")


def _expect_mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        _validation_error(path, "expected an object")
    return value


def _expect_exact_keys(
    value: Mapping[str, object], expected: set[str], path: str
) -> None:
    observed = set(value)
    missing = sorted(expected - observed)
    additional = sorted(observed - expected)
    if missing:
        _validation_error(path, f"missing required properties: {', '.join(missing)}")
    if additional:
        _validation_error(path, f"additional properties: {', '.join(additional)}")


def _validate_recorded_at(value: object) -> None:
    if not isinstance(value, str) or _RFC3339_PATTERN.fullmatch(value) is None:
        _validation_error("$.recorded_at", "invalid RFC 3339 date-time")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise FingerprintValidationError(
            "$.recorded_at: invalid RFC 3339 date-time"
        ) from error
    if parsed.tzinfo is None:
        _validation_error("$.recorded_at", "timezone offset is required")


def validate_evidence_fingerprint(record: Mapping[str, object]) -> None:
    """Validate structure, vocabulary, and recomputed semantic identity.

    Both immutable v1.0 records and current v1.1 records are accepted. New
    writers use v1.1; each version is checked against its own closed kind set.
    """

    value = _expect_mapping(record, "$")
    _expect_exact_keys(
        value,
        {
            "schema_version",
            "hash_algorithm",
            "canonicalization",
            "preimage",
            "digest",
            "recorded_at",
        },
        "$",
    )
    version = value["schema_version"]
    kinds: tuple[str, ...]
    if version == EVIDENCE_FINGERPRINT_SCHEMA_VERSION:
        kinds = FINGERPRINT_KINDS
    elif version == EVIDENCE_FINGERPRINT_LEGACY_SCHEMA_VERSION:
        kinds = FINGERPRINT_KINDS_V1_0
    else:
        _validation_error("$.schema_version", "unsupported fingerprint version")
    if value["hash_algorithm"] != FINGERPRINT_HASH_ALGORITHM:
        _validation_error("$.hash_algorithm", "expected sha256")
    if value["canonicalization"] != FINGERPRINT_CANONICALIZATION:
        _validation_error("$.canonicalization", "expected RFC8785-JCS")

    preimage = _expect_mapping(value["preimage"], "$.preimage")
    _expect_exact_keys(
        preimage,
        {"fingerprint_kind", "subject_id", "payload_schema_version", "payload", "parents"},
        "$.preimage",
    )
    kind = preimage["fingerprint_kind"]
    if not isinstance(kind, str) or kind not in kinds:
        _validation_error("$.preimage.fingerprint_kind", "kind is outside version vocabulary")
    subject_id = preimage["subject_id"]
    if (
        not isinstance(subject_id, str)
        or len(subject_id) > 160
        or _STABLE_ID_PATTERN.fullmatch(subject_id) is None
    ):
        _validation_error("$.preimage.subject_id", "invalid stable identifier")
    payload_version = preimage["payload_schema_version"]
    if not isinstance(payload_version, str) or not 1 <= len(payload_version) <= 160:
        _validation_error("$.preimage.payload_schema_version", "expected 1 to 160 characters")
    _expect_mapping(preimage["payload"], "$.preimage.payload")
    parents = preimage["parents"]
    if not isinstance(parents, list):
        _validation_error("$.preimage.parents", "expected an array")
    for index, raw_parent in enumerate(parents):
        parent = _expect_mapping(raw_parent, f"$.preimage.parents[{index}]")
        _expect_exact_keys(
            parent,
            {"relationship", "fingerprint_kind", "digest"},
            f"$.preimage.parents[{index}]",
        )
        if parent["relationship"] not in FINGERPRINT_PARENT_RELATIONSHIPS:
            _validation_error(
                f"$.preimage.parents[{index}].relationship",
                "relationship is outside vocabulary",
            )
        if parent["fingerprint_kind"] not in kinds:
            _validation_error(
                f"$.preimage.parents[{index}].fingerprint_kind",
                "kind is outside version vocabulary",
            )
        digest = parent["digest"]
        if not isinstance(digest, str) or _SHA256_PATTERN.fullmatch(digest) is None:
            _validation_error(
                f"$.preimage.parents[{index}].digest", "expected lowercase SHA-256"
            )

    digest = value["digest"]
    if not isinstance(digest, str) or _SHA256_PATTERN.fullmatch(digest) is None:
        _validation_error("$.digest", "expected lowercase SHA-256")
    _validate_recorded_at(value["recorded_at"])
    try:
        expected_digest = semantic_fingerprint_digest(preimage)
    except CanonicalizationError as error:
        raise FingerprintValidationError(f"$.preimage: {error}") from error
    if not hmac.compare_digest(digest, expected_digest):
        _validation_error("$.digest", "semantic digest mismatch")


class EvidenceLineageGraph:
    """Validated, immutable semantic-fingerprint DAG with deterministic traversal."""

    def __init__(self, records: Iterable[Mapping[str, object]]) -> None:
        self._records: dict[str, dict[str, object]] = {}
        for index, record in enumerate(records):
            try:
                validate_evidence_fingerprint(record)
            except FingerprintValidationError as error:
                raise FingerprintIntegrityError(f"records[{index}]: {error}") from error
            copied = deepcopy(dict(record))
            digest = copied["digest"]
            assert isinstance(digest, str)
            if digest in self._records:
                raise FingerprintIntegrityError(f"duplicate fingerprint digest: {digest}")
            self._records[digest] = copied

        self._parents: dict[str, tuple[str, ...]] = {}
        child_sets: dict[str, set[str]] = {digest: set() for digest in self._records}
        for digest, record in self._records.items():
            preimage = record["preimage"]
            assert isinstance(preimage, dict)
            parents = preimage["parents"]
            assert isinstance(parents, list)
            parent_digests: list[str] = []
            for parent in parents:
                assert isinstance(parent, dict)
                parent_digest = parent["digest"]
                assert isinstance(parent_digest, str)
                referenced = self._records.get(parent_digest)
                if referenced is None:
                    raise FingerprintIntegrityError(
                        f"{digest}: missing parent fingerprint {parent_digest}"
                    )
                referenced_preimage = referenced["preimage"]
                assert isinstance(referenced_preimage, dict)
                if parent["fingerprint_kind"] != referenced_preimage["fingerprint_kind"]:
                    raise FingerprintIntegrityError(
                        f"{digest}: parent kind mismatch for {parent_digest}"
                    )
                parent_digests.append(parent_digest)
                child_sets[parent_digest].add(digest)
            self._parents[digest] = tuple(sorted(parent_digests))
        self._children = {
            digest: tuple(sorted(children)) for digest, children in child_sets.items()
        }
        self._assert_acyclic()

    @property
    def digests(self) -> tuple[str, ...]:
        """Return every graph digest in lexical order."""

        return tuple(sorted(self._records))

    def record(self, digest: str) -> dict[str, object]:
        """Return a defensive copy of one validated record."""

        self._require_digest(digest)
        return deepcopy(self._records[digest])

    def parent_digests(self, digest: str) -> tuple[str, ...]:
        """Return direct parent digests in lexical order."""

        self._require_digest(digest)
        return self._parents[digest]

    def child_digests(self, digest: str) -> tuple[str, ...]:
        """Return direct child digests in lexical order."""

        self._require_digest(digest)
        return self._children[digest]

    def ancestor_digests(self, digest: str) -> tuple[str, ...]:
        """Return ancestors nearest-first, then by lexical digest at each depth."""

        return self._breadth_first(digest, self._parents)

    def descendant_digests(self, digest: str) -> tuple[str, ...]:
        """Return descendants nearest-first, then by lexical digest at each depth."""

        return self._breadth_first(digest, self._children)

    def topological_lineage(self, digest: str) -> tuple[str, ...]:
        """Return all ancestors and the subject with every parent before its child."""

        self._require_digest(digest)
        selected = {digest, *self.ancestor_digests(digest)}
        indegree = {
            node: sum(parent in selected for parent in self._parents[node])
            for node in selected
        }
        ready = [node for node, count in indegree.items() if count == 0]
        heapq.heapify(ready)
        ordered: list[str] = []
        while ready:
            node = heapq.heappop(ready)
            ordered.append(node)
            for child in self._children[node]:
                if child not in selected:
                    continue
                indegree[child] -= 1
                if indegree[child] == 0:
                    heapq.heappush(ready, child)
        if len(ordered) != len(selected):
            raise FingerprintIntegrityError("cycle detected during lineage traversal")
        return tuple(ordered)

    def has_lineage(self, descendant: str, ancestor: str) -> bool:
        """Return whether ancestor is transitively upstream of descendant."""

        self._require_digest(ancestor)
        return ancestor in self.ancestor_digests(descendant)

    def _breadth_first(
        self, digest: str, adjacency: Mapping[str, tuple[str, ...]]
    ) -> tuple[str, ...]:
        self._require_digest(digest)
        distance = {digest: 0}
        pending: deque[str] = deque([digest])
        while pending:
            node = pending.popleft()
            for adjacent in adjacency[node]:
                if adjacent in distance:
                    continue
                distance[adjacent] = distance[node] + 1
                pending.append(adjacent)
        distance.pop(digest)
        return tuple(sorted(distance, key=lambda node: (distance[node], node)))

    def _assert_acyclic(self) -> None:
        indegree = {digest: len(parents) for digest, parents in self._parents.items()}
        ready = [digest for digest, count in indegree.items() if count == 0]
        heapq.heapify(ready)
        visited = 0
        while ready:
            digest = heapq.heappop(ready)
            visited += 1
            for child in self._children[digest]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    heapq.heappush(ready, child)
        if visited != len(self._records):
            cycle_digest = min(
                digest for digest, count in indegree.items() if count > 0
            )
            raise FingerprintIntegrityError(
                f"lineage cycle detected at {cycle_digest}"
            )

    def _require_digest(self, digest: str) -> None:
        if digest not in self._records:
            raise FingerprintIntegrityError(f"unknown fingerprint digest: {digest}")


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
    schema_version: Literal[
        "butterflylens-evidence-fingerprint:v1.0.0",
        "butterflylens-evidence-fingerprint:v1.1.0",
    ]
    hash_algorithm: Literal["sha256"]
    canonicalization: Literal["RFC8785-JCS"]
    preimage: EvidenceFingerprintPreimage
    digest: str
    recorded_at: str
