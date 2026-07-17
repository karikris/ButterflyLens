"""Budget-fenced Flickr search-page execution with no built-in network client."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from math import ceil
from typing import Mapping, Protocol

from butterflylens.contracts.fingerprint import canonicalize_json

from .budget import FlickrHourlyBudget
from .partitioning import (
    FLICKR_GEO_RESULTS_PER_PAGE,
    complete_page_checkpoint,
    validate_pending_page_checkpoint,
)
from .query_plan import FLICKR_REST_ENDPOINT, FLICKR_SEARCH_METHOD


SEARCH_PAGE_EXECUTION_SCHEMA_VERSION = (
    "butterflylens-flickr-search-page-execution:v1.0.0"
)


class SearchPageExecutionError(RuntimeError):
    """A page was not safely checkpointed after budget accounting began."""

    def __init__(
        self,
        message: str,
        *,
        budget_outcome: str | None = None,
        execution_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.budget_outcome = budget_outcome
        self.execution_id = execution_id


@dataclass(frozen=True)
class SearchTransportResponse:
    """Exact response bytes returned by an injected transport."""

    http_status: int
    body: bytes
    received_at: datetime


class SearchPageTransport(Protocol):
    """Injected boundary; this package deliberately provides no HTTP implementation."""

    def __call__(
        self,
        *,
        endpoint: str,
        method: str,
        normalized_parameters: Mapping[str, object],
        credential: str,
    ) -> SearchTransportResponse: ...


def execute_search_page(
    checkpoint: Mapping[str, object],
    *,
    budget: FlickrHourlyBudget,
    credential: str,
    credential_fingerprint: str,
    reserved_at: datetime,
    transport: SearchPageTransport,
) -> dict[str, object]:
    """Execute one pending page through an injected transport and checkpoint it.

    Validation and budget reservation happen before the transport boundary. The
    credential is passed separately and is never included in the returned
    execution record. A transport exception is conservatively accounted as an
    uncertain call and freezes the in-memory hourly ledger.
    """

    validate_pending_page_checkpoint(checkpoint)
    _validate_credential(credential, credential_fingerprint)
    if reserved_at.tzinfo != timezone.utc:
        raise SearchPageExecutionError("reserved_at must use UTC")

    execution_preimage = {
        "page_request_fingerprint": checkpoint["page_request_fingerprint"],
        "page_checkpoint_id": checkpoint["page_checkpoint_id"],
        "reserved_at": _utc_text(reserved_at),
    }
    execution_fingerprint = _digest(execution_preimage)
    execution_id = f"blfx:v1:{execution_fingerprint[:24]}"
    budget_request_id = f"blfr:v1:{execution_fingerprint[:24]}"
    budget.reserve(
        request_id=budget_request_id,
        method=FLICKR_SEARCH_METHOD,
        purpose="search_page",
        lane="normal",
        credential_fingerprint=credential_fingerprint,
        reserved_at=reserved_at,
    )

    public_parameters = deepcopy(dict(checkpoint["normalized_parameters"]))
    try:
        response = transport(
            endpoint=FLICKR_REST_ENDPOINT,
            method=FLICKR_SEARCH_METHOD,
            normalized_parameters=deepcopy(public_parameters),
            credential=credential,
        )
    except Exception as error:
        budget.settle(budget_request_id, "uncertain")
        raise SearchPageExecutionError(
            "transport outcome is uncertain; hourly budget frozen",
            budget_outcome="uncertain",
            execution_id=execution_id,
        ) from error

    try:
        if credential.encode("utf-8") in response.body:
            raise SearchPageExecutionError("response body reflected the credential")
        if response.received_at < reserved_at:
            raise SearchPageExecutionError("response predates its budget reservation")
        payload = _decode_response(response, checkpoint)
        source_response_fingerprint = _digest(payload)
        photos = payload["photos"]
        assert isinstance(photos, dict)
        observed_total = _integer(photos["total"], "response total", minimum=0)
        photo_rows = photos["photo"]
        assert isinstance(photo_rows, list)
        completed_checkpoint = complete_page_checkpoint(
            checkpoint,
            source_response_fingerprint=source_response_fingerprint,
            observed_total=observed_total,
            returned_count=len(photo_rows),
        )
    except Exception as error:
        budget.settle(budget_request_id, "consumed")
        if isinstance(error, SearchPageExecutionError):
            error.budget_outcome = "consumed"
            error.execution_id = execution_id
            raise
        raise SearchPageExecutionError(
            "sent response failed page validation",
            budget_outcome="consumed",
            execution_id=execution_id,
        ) from error

    budget.settle(budget_request_id, "consumed")
    response_body_sha256 = hashlib.sha256(response.body).hexdigest()
    return {
        "schema_version": SEARCH_PAGE_EXECUTION_SCHEMA_VERSION,
        "execution_id": execution_id,
        **execution_preimage,
        "method": FLICKR_SEARCH_METHOD,
        "endpoint": FLICKR_REST_ENDPOINT,
        "normalized_parameters": public_parameters,
        "execution_fingerprint": execution_fingerprint,
        "budget_request_id": budget_request_id,
        "budget_outcome": "consumed",
        "http_status": response.http_status,
        "received_at": _utc_text(response.received_at),
        "response_body": response.body,
        "response_body_sha256": response_body_sha256,
        "response_payload": payload,
        "source_response_fingerprint": source_response_fingerprint,
        "completed_checkpoint": completed_checkpoint,
        "execution_state": "checkpointed",
        "credential_persisted": False,
    }


def _decode_response(
    response: SearchTransportResponse, checkpoint: Mapping[str, object]
) -> dict[str, object]:
    if not isinstance(response, SearchTransportResponse):
        raise SearchPageExecutionError("transport returned an unsupported response")
    if not 200 <= response.http_status <= 299:
        raise SearchPageExecutionError("Flickr search returned a non-success status")
    if response.received_at.tzinfo != timezone.utc:
        raise SearchPageExecutionError("response received_at must use UTC")
    if not isinstance(response.body, bytes) or not response.body:
        raise SearchPageExecutionError("response body must be non-empty bytes")
    try:
        payload = json.loads(response.body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SearchPageExecutionError("response body is not valid JSON") from error
    if not isinstance(payload, dict) or set(payload) != {"stat", "photos"}:
        raise SearchPageExecutionError("Flickr response envelope is not exact")
    if payload["stat"] != "ok" or not isinstance(payload["photos"], dict):
        raise SearchPageExecutionError("Flickr response is not a successful photo page")
    photos = payload["photos"]
    required = {"page", "pages", "perpage", "total", "photo"}
    if set(photos) != required or not isinstance(photos["photo"], list):
        raise SearchPageExecutionError("Flickr photos page fields are not exact")
    page = _integer(photos["page"], "response page", minimum=1)
    pages = _integer(photos["pages"], "response pages", minimum=0)
    per_page = _integer(photos["perpage"], "response perpage", minimum=1)
    total = _integer(photos["total"], "response total", minimum=0)
    expected_page = _integer(checkpoint["page"], "checkpoint page", minimum=1)
    expected_per_page = _integer(
        checkpoint["normalized_parameters"]["per_page"],
        "checkpoint per_page",
        minimum=1,
    )
    if page != expected_page or per_page != expected_per_page:
        raise SearchPageExecutionError("response page identity differs from the checkpoint")
    if per_page > FLICKR_GEO_RESULTS_PER_PAGE:
        raise SearchPageExecutionError("response exceeds the geo page limit")
    if pages != (ceil(total / per_page) if total else 0):
        raise SearchPageExecutionError("response page count is inconsistent with total")
    expected_rows = min(per_page, max(total - ((page - 1) * per_page), 0))
    if len(photos["photo"]) != expected_rows:
        raise SearchPageExecutionError("response row count is inconsistent with its page")
    photo_ids: list[str] = []
    for row in photos["photo"]:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise SearchPageExecutionError("response photo identity is invalid")
        photo_id = row["id"]
        if not photo_id.isdigit():
            raise SearchPageExecutionError("response photo identity is invalid")
        photo_ids.append(photo_id)
    if len(photo_ids) != len(set(photo_ids)):
        raise SearchPageExecutionError("response page contains duplicate photo IDs")
    return deepcopy(payload)


def _validate_credential(credential: str, credential_fingerprint: str) -> None:
    if not isinstance(credential, str) or not credential:
        raise SearchPageExecutionError("Flickr credential is required")
    observed = hashlib.sha256(credential.encode("utf-8")).hexdigest()
    if observed != credential_fingerprint:
        raise SearchPageExecutionError("Flickr credential fingerprint mismatch")


def _integer(value: object, field: str, *, minimum: int) -> int:
    if isinstance(value, bool):
        raise SearchPageExecutionError(f"{field} is not an integer")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str) and value.isdigit():
        parsed = int(value)
    else:
        raise SearchPageExecutionError(f"{field} is not an integer")
    if parsed < minimum:
        raise SearchPageExecutionError(f"{field} is below its minimum")
    return parsed


def _utc_text(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _digest(value: object) -> str:
    return hashlib.sha256(canonicalize_json(value)).hexdigest()
