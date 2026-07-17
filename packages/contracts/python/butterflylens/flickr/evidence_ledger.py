"""Verified persistence records for Flickr request and response hashes."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Mapping, Protocol

from butterflylens.contracts.fingerprint import canonicalize_json

from .execution import SEARCH_PAGE_EXECUTION_SCHEMA_VERSION


EVIDENCE_LEDGER_ENTRY_SCHEMA_VERSION = (
    "butterflylens-flickr-evidence-ledger-entry:v1.0.0"
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SECRET_PARAMETER_NAMES = frozenset(
    {"api_key", "api_sig", "auth_token", "oauth_token", "password", "secret", "token"}
)


class EvidenceLedgerError(ValueError):
    """Raised when an execution or storage acknowledgement cannot prove its hashes."""


class EvidenceLedgerStore(Protocol):
    """Minimal service-side adapter for public.api_requests insertion."""

    def insert_api_request(
        self, record: Mapping[str, object]
    ) -> Mapping[str, object]: ...


def persist_execution_hashes(
    execution: Mapping[str, object],
    *,
    run_pk: int,
    query_definition_pk: int,
    store: EvidenceLedgerStore,
) -> dict[str, object]:
    """Verify an execution end to end and persist its hash-only request ledger row."""

    _validate_positive_key(run_pk, "run_pk")
    _validate_positive_key(query_definition_pk, "query_definition_pk")
    verified = _verify_execution(execution)
    record = {
        "api_request_id": execution["budget_request_id"],
        "run_pk": run_pk,
        "query_definition_pk": query_definition_pk,
        "retry_of_request_pk": None,
        "provider": "flickr",
        "method": execution["method"],
        "endpoint": execution["endpoint"],
        "normalized_parameters": deepcopy(execution["normalized_parameters"]),
        "request_fingerprint": verified["request_fingerprint"],
        "status": "succeeded",
        "requested_at": execution["reserved_at"],
        "started_at": execution["reserved_at"],
        "completed_at": execution["received_at"],
        "http_status": execution["http_status"],
        "response_sha256": verified["response_sha256"],
        "response_fingerprint": verified["response_fingerprint"],
        "retry_count": 0,
        "budget_units": 1,
        "error_code": None,
    }
    acknowledgement = store.insert_api_request(deepcopy(record))
    _validate_acknowledgement(acknowledgement, record)
    receipt_preimage = {
        "api_request_id": record["api_request_id"],
        "run_pk": run_pk,
        "query_definition_pk": query_definition_pk,
        "request_fingerprint": record["request_fingerprint"],
        "response_sha256": record["response_sha256"],
        "response_fingerprint": record["response_fingerprint"],
        "completed_at": record["completed_at"],
    }
    receipt_fingerprint = _digest(receipt_preimage)
    return {
        "schema_version": EVIDENCE_LEDGER_ENTRY_SCHEMA_VERSION,
        "ledger_entry_id": f"blfl:v1:{receipt_fingerprint[:24]}",
        **receipt_preimage,
        "record": record,
        "storage_table": "public.api_requests",
        "storage_state": "persisted",
        "receipt_fingerprint": receipt_fingerprint,
        "raw_response_persisted": False,
        "credential_persisted": False,
    }


def _verify_execution(execution: Mapping[str, object]) -> dict[str, str]:
    required = {
        "schema_version",
        "execution_id",
        "root_physical_query_request_id",
        "root_request_fingerprint",
        "page_request_fingerprint",
        "page_checkpoint_id",
        "reserved_at",
        "method",
        "endpoint",
        "normalized_parameters",
        "execution_fingerprint",
        "budget_request_id",
        "budget_outcome",
        "http_status",
        "received_at",
        "response_body",
        "response_body_sha256",
        "response_payload",
        "source_response_fingerprint",
        "completed_checkpoint",
        "execution_state",
        "credential_persisted",
    }
    if required - set(execution):
        raise EvidenceLedgerError("search-page execution is incomplete")
    if execution["schema_version"] != SEARCH_PAGE_EXECUTION_SCHEMA_VERSION:
        raise EvidenceLedgerError("search-page execution version is unsupported")
    if execution["execution_state"] != "checkpointed" or execution["budget_outcome"] != "consumed":
        raise EvidenceLedgerError("only consumed checkpointed executions may persist")
    if execution["credential_persisted"] is not False:
        raise EvidenceLedgerError("execution does not prove credential separation")
    parameters = execution["normalized_parameters"]
    if not isinstance(parameters, dict):
        raise EvidenceLedgerError("normalized request parameters are invalid")
    if {str(key).lower() for key in parameters} & _SECRET_PARAMETER_NAMES:
        raise EvidenceLedgerError("normalized request parameters contain a secret")
    request_preimage = {
        "provider": "flickr",
        "method": execution["method"],
        "endpoint": execution["endpoint"],
        "normalized_parameters": parameters,
    }
    request_fingerprint = _digest(request_preimage)
    if request_fingerprint != execution["page_request_fingerprint"]:
        raise EvidenceLedgerError("request fingerprint does not match canonical request bytes")
    execution_preimage = {
        "root_physical_query_request_id": execution[
            "root_physical_query_request_id"
        ],
        "root_request_fingerprint": execution["root_request_fingerprint"],
        "page_request_fingerprint": execution["page_request_fingerprint"],
        "page_checkpoint_id": execution["page_checkpoint_id"],
        "reserved_at": execution["reserved_at"],
    }
    execution_fingerprint = _digest(execution_preimage)
    if (
        execution["execution_fingerprint"] != execution_fingerprint
        or execution["execution_id"] != f"blfx:v1:{execution_fingerprint[:24]}"
        or execution["budget_request_id"] != f"blfr:v1:{execution_fingerprint[:24]}"
    ):
        raise EvidenceLedgerError("execution identity is not recomputable")
    body = execution["response_body"]
    if not isinstance(body, bytes):
        raise EvidenceLedgerError("exact response bytes are unavailable")
    response_sha256 = hashlib.sha256(body).hexdigest()
    if response_sha256 != execution["response_body_sha256"]:
        raise EvidenceLedgerError("physical response SHA-256 does not match bytes")
    try:
        decoded = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EvidenceLedgerError("exact response bytes are not JSON") from error
    if decoded != execution["response_payload"]:
        raise EvidenceLedgerError("parsed response differs from exact response bytes")
    response_fingerprint = _digest(decoded)
    completed = execution["completed_checkpoint"]
    if not isinstance(completed, dict):
        raise EvidenceLedgerError("completed checkpoint is invalid")
    if (
        response_fingerprint != execution["source_response_fingerprint"]
        or completed.get("source_response_fingerprint") != response_fingerprint
        or completed.get("status") != "succeeded"
    ):
        raise EvidenceLedgerError("semantic response fingerprint is not checkpoint-bound")
    reserved_at = _timestamp(execution["reserved_at"], "reserved_at")
    received_at = _timestamp(execution["received_at"], "received_at")
    if received_at < reserved_at:
        raise EvidenceLedgerError("response predates its request")
    http_status = execution["http_status"]
    if not isinstance(http_status, int) or isinstance(http_status, bool) or not 200 <= http_status <= 299:
        raise EvidenceLedgerError("successful execution HTTP status is invalid")
    return {
        "request_fingerprint": request_fingerprint,
        "response_sha256": response_sha256,
        "response_fingerprint": response_fingerprint,
    }


def _validate_acknowledgement(
    acknowledgement: Mapping[str, object], record: Mapping[str, object]
) -> None:
    if not isinstance(acknowledgement, Mapping):
        raise EvidenceLedgerError("evidence store acknowledgement is invalid")
    for field in (
        "api_request_id",
        "request_fingerprint",
        "response_sha256",
        "response_fingerprint",
        "status",
    ):
        if acknowledgement.get(field) != record[field]:
            raise EvidenceLedgerError(f"evidence store acknowledgement changed {field}")
    for field in ("request_fingerprint", "response_sha256", "response_fingerprint"):
        if _SHA256.fullmatch(str(acknowledgement[field])) is None:
            raise EvidenceLedgerError(f"evidence store acknowledgement has invalid {field}")


def _validate_positive_key(value: int, field: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise EvidenceLedgerError(f"{field} must be a positive database key")


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise EvidenceLedgerError(f"{field} must be a UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise EvidenceLedgerError(f"{field} is invalid") from error
    if parsed.tzinfo != timezone.utc:
        raise EvidenceLedgerError(f"{field} must use UTC")
    return parsed


def _digest(value: object) -> str:
    return hashlib.sha256(canonicalize_json(value)).hexdigest()
