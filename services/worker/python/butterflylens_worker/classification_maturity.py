"""Model-independent per-image evidence-maturity projection."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import re
from typing import Mapping, Sequence

from butterflylens.contracts.classification_maturity import (
    CLASSIFICATION_MATURITY_FIELDS,
    CLASSIFICATION_MATURITY_SCHEMA_VERSION,
)
from butterflylens.contracts.fingerprint import canonicalize_json


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STABLE_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,159}$")
_RECORD_FIELDS = {
    "schema_version",
    "image_id",
    "source_record_fingerprint",
    "observed_at",
    "maturity",
    "projection_fingerprint",
    "scientific_claim_allowed",
}


class ClassificationMaturityError(ValueError):
    """Raised when maturity would overstate or obscure available evidence."""


def available_state(
    value: bool, *, evidence_fingerprints: Sequence[str]
) -> dict[str, object]:
    return {
        "status": "available",
        "value": value,
        "reason": None,
        "evidence_fingerprints": list(evidence_fingerprints),
    }


def unavailable_state(
    reason: str, *, evidence_fingerprints: Sequence[str] = ()
) -> dict[str, object]:
    return {
        "status": "unavailable",
        "value": None,
        "reason": reason,
        "evidence_fingerprints": list(evidence_fingerprints),
    }


def build_classification_maturity(
    *,
    image_id: str,
    source_record_fingerprint: str,
    observed_at: datetime,
    maturity: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    _require_identity(image_id)
    _require_sha(source_record_fingerprint, "source record fingerprint")
    _require_utc(observed_at)
    normalized = _normalize_maturity(maturity)
    _enforce_release_gate(normalized)
    preimage = {
        "schema_version": CLASSIFICATION_MATURITY_SCHEMA_VERSION,
        "image_id": image_id,
        "source_record_fingerprint": source_record_fingerprint,
        "observed_at": _utc_text(observed_at),
        "maturity": normalized,
        "scientific_claim_allowed": False,
    }
    return {**preimage, "projection_fingerprint": _digest(preimage)}


def validate_classification_maturity(record: Mapping[str, object]) -> None:
    if set(record) != _RECORD_FIELDS:
        raise ClassificationMaturityError("maturity projection fields are not exact")
    if record["schema_version"] != CLASSIFICATION_MATURITY_SCHEMA_VERSION:
        raise ClassificationMaturityError("maturity projection version is unsupported")
    image_id = record["image_id"]
    if not isinstance(image_id, str):
        raise ClassificationMaturityError("image identity is invalid")
    _require_identity(image_id)
    _require_sha(record["source_record_fingerprint"], "source record fingerprint")
    _parse_utc(record["observed_at"])
    maturity = record["maturity"]
    if not isinstance(maturity, Mapping):
        raise ClassificationMaturityError("maturity states must be an object")
    normalized = _normalize_maturity(maturity)
    _enforce_release_gate(normalized)
    if normalized != maturity:
        raise ClassificationMaturityError("maturity states are not canonical")
    if record["scientific_claim_allowed"] is not False:
        raise ClassificationMaturityError("maturity projection cannot authorize a claim")
    _require_sha(record["projection_fingerprint"], "projection fingerprint")
    preimage = {key: deepcopy(value) for key, value in record.items() if key != "projection_fingerprint"}
    if record["projection_fingerprint"] != _digest(preimage):
        raise ClassificationMaturityError("maturity projection fingerprint mismatch")


def _normalize_maturity(
    maturity: Mapping[str, Mapping[str, object]],
) -> dict[str, dict[str, object]]:
    if set(maturity) != set(CLASSIFICATION_MATURITY_FIELDS):
        raise ClassificationMaturityError("maturity state inventory is not exact")
    return {
        field: _normalize_state(maturity[field], field)
        for field in CLASSIFICATION_MATURITY_FIELDS
    }


def _normalize_state(
    state: Mapping[str, object], field: str
) -> dict[str, object]:
    if not isinstance(state, Mapping) or set(state) != {
        "status", "value", "reason", "evidence_fingerprints"
    }:
        raise ClassificationMaturityError(f"{field} evidence fields are not exact")
    fingerprints = state["evidence_fingerprints"]
    if not isinstance(fingerprints, list):
        raise ClassificationMaturityError(f"{field} evidence fingerprints must be a list")
    for fingerprint in fingerprints:
        _require_sha(fingerprint, f"{field} evidence fingerprint")
    if len(fingerprints) != len(set(fingerprints)):
        raise ClassificationMaturityError(f"{field} evidence fingerprints repeat")
    status = state["status"]
    value = state["value"]
    reason = state["reason"]
    if status == "available":
        if not isinstance(value, bool) or reason is not None or not fingerprints:
            raise ClassificationMaturityError(
                f"{field} available state requires a boolean and evidence"
            )
    elif status == "unavailable":
        if value is not None or not isinstance(reason, str) or not 1 <= len(reason) <= 500:
            raise ClassificationMaturityError(
                f"{field} unavailable state requires a reason and null value"
            )
    else:
        raise ClassificationMaturityError(f"{field} evidence status is invalid")
    return {
        "status": status,
        "value": value,
        "reason": reason,
        "evidence_fingerprints": sorted(fingerprints),
    }


def _enforce_release_gate(maturity: Mapping[str, Mapping[str, object]]) -> None:
    release = maturity["release_ready"]
    if release["status"] == "available" and release["value"] is True:
        blockers = [
            field
            for field in CLASSIFICATION_MATURITY_FIELDS[:-1]
            if maturity[field]["status"] != "available"
            or maturity[field]["value"] is not True
        ]
        if blockers:
            raise ClassificationMaturityError(
                "release ready requires every preceding maturity state true"
            )


def _require_identity(value: str) -> None:
    if _STABLE_ID.fullmatch(value) is None:
        raise ClassificationMaturityError("image identity is invalid")


def _require_sha(value: object, field: str) -> None:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ClassificationMaturityError(f"{field} must be lowercase SHA-256")


def _require_utc(value: datetime) -> None:
    if value.tzinfo != timezone.utc:
        raise ClassificationMaturityError("observation time must use UTC")


def _parse_utc(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ClassificationMaturityError("observation time must use canonical UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ClassificationMaturityError("observation time is invalid") from error
    _require_utc(parsed)
    if _utc_text(parsed) != value:
        raise ClassificationMaturityError("observation time must use canonical UTC")
    return parsed


def _utc_text(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _digest(value: object) -> str:
    return hashlib.sha256(canonicalize_json(value)).hexdigest()
