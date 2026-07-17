from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))

from butterflylens.contracts.fingerprint import canonicalize_json  # noqa: E402
from butterflylens.flickr import (  # noqa: E402
    EvidenceLedgerError,
    FlickrHourlyBudget,
    RetryPlanError,
    SearchPageExecutionError,
    SearchTransportResponse,
    checkpoint_partition_count,
    execute_scheduled_retry,
    execute_search_page,
    persist_failed_execution,
    persist_execution_hashes,
    plan_partition_pages,
    plan_search_retry,
    seed_australia_state_partitions,
)


NOW = datetime(2026, 7, 18, 4, 5, tzinfo=timezone.utc)
CREDENTIAL = "synthetic-retry-credential"
CREDENTIAL_FINGERPRINT = hashlib.sha256(CREDENTIAL.encode()).hexdigest()


class MemoryStore:
    def __init__(self) -> None:
        self.records: list[dict[str, object]] = []

    def insert_api_request(self, record: object) -> dict[str, object]:
        assert isinstance(record, dict)
        self.records.append(deepcopy(record))
        return {**deepcopy(record), "id": 41 + len(self.records)}


def pending_page() -> dict[str, object]:
    parameters = {"content_types": 0, "text": "Papilio testus"}
    preimage = {
        "provider": "flickr",
        "method": "flickr.photos.search",
        "endpoint": "https://www.flickr.com/services/rest/",
        "normalized_parameters": parameters,
    }
    fingerprint = hashlib.sha256(canonicalize_json(preimage)).hexdigest()
    request = {
        "physical_query_request_id": f"blpr:v1:{fingerprint[:24]}",
        "request_fingerprint": fingerprint,
        **preimage,
        "execution_state": "planned_not_sent",
    }
    scope = json.loads(
        (ROOT / "packages/flickr/australia_partition_scopes.json").read_text()
    )
    partition = seed_australia_state_partitions(
        request,
        scope,
        min_upload_date=1_700_000_000,
        max_upload_date=1_700_086_399,
    )[0]
    count = checkpoint_partition_count(
        partition,
        total=1,
        source_response_fingerprint="5" * 64,
    )
    return plan_partition_pages(partition, count)[0]


def budget() -> FlickrHourlyBudget:
    return FlickrHourlyBudget(
        project_id="butterflylens-retry-test",
        credential_fingerprint=CREDENTIAL_FINGERPRINT,
        window_start=datetime(2026, 7, 18, 4, 0, tzinfo=timezone.utc),
    )


def success(at: datetime) -> SearchTransportResponse:
    body = json.dumps(
        {
            "stat": "ok",
            "photos": {
                "page": 1,
                "pages": 1,
                "perpage": 250,
                "total": "1",
                "photo": [{"id": "401"}],
            },
        },
        separators=(",", ":"),
    ).encode()
    return SearchTransportResponse(200, body, at)


def rate_limited() -> SearchTransportResponse:
    return SearchTransportResponse(
        429,
        b'{"stat":"fail","code":429,"message":"synthetic"}',
        NOW,
        {"Retry-After": "60"},
    )


def failed_rate_limit(
    checkpoint: dict[str, object], ledger: FlickrHourlyBudget
) -> SearchPageExecutionError:
    with unittest.TestCase().assertRaises(SearchPageExecutionError) as raised:
        execute_search_page(
            checkpoint,
            budget=ledger,
            credential=CREDENTIAL,
            credential_fingerprint=CREDENTIAL_FINGERPRINT,
            reserved_at=NOW,
            transport=lambda **_: rate_limited(),
        )
    return raised.exception


class FlickrRetryTests(unittest.TestCase):
    def test_retry_after_is_honoured_and_retry_uses_reserve_lane(self) -> None:
        checkpoint = pending_page()
        ledger = budget()
        error = failed_rate_limit(checkpoint, ledger)
        plan = plan_search_retry(error, as_of=NOW)
        parent = persist_failed_execution(
            error,
            run_pk=29,
            query_definition_pk=31,
            store=MemoryStore(),
        )
        self.assertEqual(plan["status"], "scheduled")
        self.assertEqual(plan["delay_seconds"], 60)
        self.assertEqual(plan["budget_lane"], "reserve")
        self.assertEqual(ledger.normal_committed, 1)
        attempted_at = datetime.fromisoformat(str(plan["not_before"]).replace("Z", "+00:00"))
        with self.assertRaisesRegex(RetryPlanError, "durably persisted"):
            execute_scheduled_retry(
                plan,
                checkpoint,
                {},
                budget=ledger,
                credential=CREDENTIAL,
                credential_fingerprint=CREDENTIAL_FINGERPRINT,
                attempted_at=attempted_at,
                transport=lambda **_: success(attempted_at),
            )
        retried = execute_scheduled_retry(
            plan,
            checkpoint,
            parent,
            budget=ledger,
            credential=CREDENTIAL,
            credential_fingerprint=CREDENTIAL_FINGERPRINT,
            attempted_at=attempted_at,
            transport=lambda **_: success(attempted_at),
        )
        self.assertEqual(retried["attempt_number"], 1)
        self.assertEqual(retried["retry_of_execution_id"], error.execution_id)
        self.assertEqual(retried["budget_lane"], "reserve")
        self.assertEqual(ledger.reserve_committed, 1)

    def test_backoff_must_elapse_and_plan_tampering_fails_before_send(self) -> None:
        checkpoint = pending_page()
        error = failed_rate_limit(checkpoint, budget())
        plan = plan_search_retry(error, as_of=NOW)
        parent = persist_failed_execution(
            error,
            run_pk=29,
            query_definition_pk=31,
            store=MemoryStore(),
        )
        calls = 0

        def transport(**_: object) -> SearchTransportResponse:
            nonlocal calls
            calls += 1
            return success(NOW)

        with self.assertRaisesRegex(RetryPlanError, "not elapsed"):
            execute_scheduled_retry(
                plan,
                checkpoint,
                parent,
                budget=budget(),
                credential=CREDENTIAL,
                credential_fingerprint=CREDENTIAL_FINGERPRINT,
                attempted_at=NOW,
                transport=transport,
            )
        tampered = deepcopy(plan)
        tampered["delay_seconds"] = 0
        with self.assertRaisesRegex(RetryPlanError, "fingerprint mismatch"):
            execute_scheduled_retry(
                tampered,
                checkpoint,
                parent,
                budget=budget(),
                credential=CREDENTIAL,
                credential_fingerprint=CREDENTIAL_FINGERPRINT,
                attempted_at=NOW,
                transport=transport,
            )
        self.assertEqual(calls, 0)

    def test_uncertain_send_is_blocked_for_accounting_reconciliation(self) -> None:
        checkpoint = pending_page()
        ledger = budget()

        def timeout(**_: object) -> SearchTransportResponse:
            raise TimeoutError("synthetic timeout")

        with self.assertRaises(SearchPageExecutionError) as raised:
            execute_search_page(
                checkpoint,
                budget=ledger,
                credential=CREDENTIAL,
                credential_fingerprint=CREDENTIAL_FINGERPRINT,
                reserved_at=NOW,
                transport=timeout,
            )
        plan = plan_search_retry(raised.exception, as_of=NOW)
        uncertain_receipt = persist_failed_execution(
            raised.exception,
            run_pk=29,
            query_definition_pk=31,
            store=MemoryStore(),
        )
        self.assertEqual(uncertain_receipt["status"], "quarantined")
        self.assertIsNone(uncertain_receipt["response_sha256"])
        self.assertEqual(plan["status"], "blocked_accounting_reconciliation")
        self.assertFalse(plan["automatic_send_allowed"])
        self.assertTrue(ledger.frozen)
        with self.assertRaisesRegex(RetryPlanError, "does not authorize"):
            execute_scheduled_retry(
                plan,
                checkpoint,
                {},
                budget=ledger,
                credential=CREDENTIAL,
                credential_fingerprint=CREDENTIAL_FINGERPRINT,
                attempted_at=NOW,
                transport=lambda **_: success(NOW),
            )

    def test_non_retryable_and_exhausted_attempts_are_terminal(self) -> None:
        non_retryable = SearchPageExecutionError(
            "bad request",
            budget_outcome="consumed",
            execution_id="blfx:v1:terminal",
            http_status=400,
            attempt_number=0,
            page_checkpoint_id="blfp:v1:terminal",
            received_at=NOW,
        )
        exhausted = SearchPageExecutionError(
            "still limited",
            budget_outcome="consumed",
            execution_id="blfx:v1:exhausted",
            http_status=429,
            attempt_number=3,
            page_checkpoint_id="blfp:v1:exhausted",
            received_at=NOW,
        )
        self.assertEqual(plan_search_retry(non_retryable, as_of=NOW)["status"], "not_retryable")
        self.assertEqual(plan_search_retry(exhausted, as_of=NOW)["status"], "exhausted")

    def test_retry_hash_receipt_requires_parent_database_key(self) -> None:
        checkpoint = pending_page()
        ledger = budget()
        error = failed_rate_limit(checkpoint, ledger)
        plan = plan_search_retry(error, as_of=NOW)
        parent = persist_failed_execution(
            error,
            run_pk=29,
            query_definition_pk=31,
            store=MemoryStore(),
        )
        attempted_at = datetime.fromisoformat(str(plan["not_before"]).replace("Z", "+00:00"))
        retried = execute_scheduled_retry(
            plan,
            checkpoint,
            parent,
            budget=ledger,
            credential=CREDENTIAL,
            credential_fingerprint=CREDENTIAL_FINGERPRINT,
            attempted_at=attempted_at,
            transport=lambda **_: success(attempted_at),
        )
        with self.assertRaisesRegex(EvidenceLedgerError, "parent database key"):
            persist_execution_hashes(
                retried,
                run_pk=29,
                query_definition_pk=31,
                store=MemoryStore(),
            )
        store = MemoryStore()
        receipt = persist_execution_hashes(
            retried,
            run_pk=29,
            query_definition_pk=31,
            retry_of_request_pk=parent["api_request_pk"],
            store=store,
        )
        self.assertEqual(receipt["record"]["retry_count"], 1)
        self.assertEqual(
            receipt["record"]["retry_of_request_pk"], parent["api_request_pk"]
        )

    def test_retry_planning_is_deterministic_and_never_sleeps(self) -> None:
        checkpoint = pending_page()
        error = failed_rate_limit(checkpoint, budget())
        self.assertEqual(
            plan_search_retry(error, as_of=NOW),
            plan_search_retry(error, as_of=NOW),
        )
        source = (ROOT / "packages/contracts/python/butterflylens/flickr/retry.py").read_text()
        self.assertNotIn("sleep(", source)


if __name__ == "__main__":
    unittest.main()
