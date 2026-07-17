"""Deterministic, reserve-budget Flickr retry planning without sleeping."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
from math import ceil
from typing import Mapping

from butterflylens.contracts.fingerprint import canonicalize_json

from .budget import FlickrHourlyBudget
from .execution import (
    SearchPageExecutionError,
    SearchPageTransport,
    execute_search_page,
)


RETRY_PLAN_SCHEMA_VERSION = "butterflylens-flickr-retry-plan:v1.0.0"


class RetryPlanError(ValueError):
    """Raised when retry scheduling could double-send or weaken accounting."""


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = 3
    base_delay_seconds: int = 2
    maximum_backoff_seconds: int = 300
    retryable_http_statuses: frozenset[int] = frozenset(
        {429, 500, 502, 503, 504}
    )

    def validate(self) -> None:
        if self.max_retries < 0 or self.max_retries > 10:
            raise RetryPlanError("max_retries must be between zero and ten")
        if self.base_delay_seconds < 1 or self.maximum_backoff_seconds < 1:
            raise RetryPlanError("retry delays must be positive")
        if self.base_delay_seconds > self.maximum_backoff_seconds:
            raise RetryPlanError("base retry delay exceeds maximum backoff")
        if any(status < 400 or status > 599 for status in self.retryable_http_statuses):
            raise RetryPlanError("retryable HTTP status is outside the error range")


def plan_search_retry(
    error: SearchPageExecutionError,
    *,
    as_of: datetime,
    policy: RetryPolicy | None = None,
) -> dict[str, object]:
    """Turn a failed sent attempt into a replayable retry disposition."""

    selected_policy = policy or RetryPolicy()
    selected_policy.validate()
    if as_of.tzinfo != timezone.utc:
        raise RetryPlanError("retry planning time must use UTC")
    if (
        not isinstance(error.execution_id, str)
        or not error.execution_id.startswith("blfx:v1:")
        or error.attempt_number is None
        or isinstance(error.attempt_number, bool)
        or error.attempt_number < 0
        or not isinstance(error.page_checkpoint_id, str)
        or not error.page_checkpoint_id.startswith("blfp:v1:")
    ):
        raise RetryPlanError("error does not identify a sent page attempt")
    if error.received_at is not None and as_of < error.received_at:
        raise RetryPlanError("retry planning predates the failed response")

    status = "not_retryable"
    reason = "response_not_retryable"
    next_attempt_number: int | None = None
    delay_seconds: int | None = None
    not_before: datetime | None = None
    retry_after_seconds: int | None = None
    if error.budget_outcome == "uncertain":
        status = "blocked_accounting_reconciliation"
        reason = "uncertain_send_may_have_reached_provider"
    elif error.budget_outcome != "consumed":
        reason = "no_consumed_provider_attempt"
    elif error.attempt_number >= selected_policy.max_retries:
        status = "exhausted"
        reason = "maximum_retry_attempts_reached"
    elif error.http_status in selected_policy.retryable_http_statuses:
        next_attempt_number = error.attempt_number + 1
        retry_after_seconds = _retry_after_seconds(error.response_headers, as_of)
        exponential = min(
            selected_policy.base_delay_seconds * (2**error.attempt_number),
            selected_policy.maximum_backoff_seconds,
        )
        jittered = ceil(exponential * _deterministic_jitter(error.execution_id, next_attempt_number))
        delay_seconds = max(jittered, retry_after_seconds or 0)
        not_before = as_of + timedelta(seconds=delay_seconds)
        status = "scheduled"
        reason = "retryable_http_status"

    preimage = {
        "failed_execution_id": error.execution_id,
        "page_checkpoint_id": error.page_checkpoint_id,
        "failed_attempt_number": error.attempt_number,
        "http_status": error.http_status,
        "budget_outcome": error.budget_outcome,
        "as_of": _utc_text(as_of),
        "policy": _policy_record(selected_policy),
        "status": status,
        "reason": reason,
        "next_attempt_number": next_attempt_number,
        "retry_after_seconds": retry_after_seconds,
        "delay_seconds": delay_seconds,
        "not_before": None if not_before is None else _utc_text(not_before),
    }
    fingerprint = _digest(preimage)
    return {
        "schema_version": RETRY_PLAN_SCHEMA_VERSION,
        "retry_plan_id": f"blrt:v1:{fingerprint[:24]}",
        **preimage,
        "budget_lane": "reserve" if status == "scheduled" else None,
        "budget_purpose": "retry" if status == "scheduled" else None,
        "automatic_send_allowed": status == "scheduled",
        "plan_fingerprint": fingerprint,
    }


def execute_scheduled_retry(
    plan: Mapping[str, object],
    checkpoint: Mapping[str, object],
    parent_request_receipt: Mapping[str, object],
    *,
    budget: FlickrHourlyBudget,
    credential: str,
    credential_fingerprint: str,
    attempted_at: datetime,
    transport: SearchPageTransport,
) -> dict[str, object]:
    """Execute one due retry through the reserve lane and injected transport."""

    _validate_plan(plan)
    if plan["status"] != "scheduled" or plan["automatic_send_allowed"] is not True:
        raise RetryPlanError("retry plan does not authorize a send")
    _validate_parent_receipt(plan, parent_request_receipt)
    if checkpoint.get("page_checkpoint_id") != plan["page_checkpoint_id"]:
        raise RetryPlanError("retry plan references another page checkpoint")
    if attempted_at.tzinfo != timezone.utc:
        raise RetryPlanError("retry attempt time must use UTC")
    not_before = _parse_utc(plan["not_before"], "not_before")
    if attempted_at < not_before:
        raise RetryPlanError("retry backoff has not elapsed")
    next_attempt_number = plan["next_attempt_number"]
    if not isinstance(next_attempt_number, int) or isinstance(next_attempt_number, bool):
        raise RetryPlanError("retry attempt number is invalid")
    return execute_search_page(
        checkpoint,
        budget=budget,
        credential=credential,
        credential_fingerprint=credential_fingerprint,
        reserved_at=attempted_at,
        transport=transport,
        attempt_number=next_attempt_number,
        retry_of_execution_id=str(plan["failed_execution_id"]),
    )


def _validate_plan(plan: Mapping[str, object]) -> None:
    required = {
        "schema_version",
        "retry_plan_id",
        "failed_execution_id",
        "page_checkpoint_id",
        "failed_attempt_number",
        "http_status",
        "budget_outcome",
        "as_of",
        "policy",
        "status",
        "reason",
        "next_attempt_number",
        "retry_after_seconds",
        "delay_seconds",
        "not_before",
        "budget_lane",
        "budget_purpose",
        "automatic_send_allowed",
        "plan_fingerprint",
    }
    if set(plan) != required:
        raise RetryPlanError("retry plan fields are not exact")
    if plan.get("schema_version") != RETRY_PLAN_SCHEMA_VERSION:
        raise RetryPlanError("retry plan version is unsupported")
    excluded = {
        "schema_version",
        "retry_plan_id",
        "budget_lane",
        "budget_purpose",
        "automatic_send_allowed",
        "plan_fingerprint",
    }
    preimage = {key: value for key, value in plan.items() if key not in excluded}
    expected = _digest(preimage)
    if plan.get("plan_fingerprint") != expected:
        raise RetryPlanError("retry plan fingerprint mismatch")
    if plan.get("retry_plan_id") != f"blrt:v1:{expected[:24]}":
        raise RetryPlanError("retry plan ID mismatch")
    if plan.get("status") == "scheduled" and (
        plan.get("budget_lane") != "reserve"
        or plan.get("budget_purpose") != "retry"
    ):
        raise RetryPlanError("scheduled retry does not use the reserve lane")


def _validate_parent_receipt(
    plan: Mapping[str, object], receipt: Mapping[str, object]
) -> None:
    record = receipt.get("record")
    failed_execution_id = str(plan.get("failed_execution_id"))
    expected_request_id = failed_execution_id.replace("blfx:v1:", "blfr:v1:", 1)
    if (
        receipt.get("storage_state") != "persisted"
        or receipt.get("storage_table") != "public.api_requests"
        or receipt.get("status") != "failed"
        or not isinstance(receipt.get("api_request_pk"), int)
        or isinstance(receipt.get("api_request_pk"), bool)
        or int(receipt["api_request_pk"]) < 1
        or not isinstance(record, dict)
        or receipt.get("api_request_id") != expected_request_id
        or record.get("api_request_id") != receipt.get("api_request_id")
        or record.get("retry_count") != plan.get("failed_attempt_number")
    ):
        raise RetryPlanError("failed parent attempt is not durably persisted")


def _retry_after_seconds(headers: Mapping[str, str], as_of: datetime) -> int | None:
    value = next(
        (
            raw.strip()
            for key, raw in headers.items()
            if isinstance(key, str)
            and isinstance(raw, str)
            and key.casefold() == "retry-after"
        ),
        None,
    )
    if not value:
        return None
    if value.isdigit():
        return int(value)
    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if retry_at.tzinfo is None:
        return None
    return max(0, ceil((retry_at.astimezone(timezone.utc) - as_of).total_seconds()))


def _deterministic_jitter(execution_id: str, attempt_number: int) -> float:
    digest = hashlib.sha256(f"{execution_id}:{attempt_number}".encode()).digest()
    fraction = int.from_bytes(digest[:8], "big") / ((1 << 64) - 1)
    return 0.5 + (fraction * 0.5)


def _policy_record(policy: RetryPolicy) -> dict[str, object]:
    record = asdict(policy)
    record["retryable_http_statuses"] = sorted(policy.retryable_http_statuses)
    return record


def _parse_utc(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise RetryPlanError(f"{field} must be a UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise RetryPlanError(f"{field} is invalid") from error
    if parsed.tzinfo != timezone.utc:
        raise RetryPlanError(f"{field} must use UTC")
    return parsed


def _utc_text(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _digest(value: object) -> str:
    return hashlib.sha256(canonicalize_json(value)).hexdigest()
