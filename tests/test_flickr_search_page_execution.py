from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))

from butterflylens.flickr import (  # noqa: E402
    FlickrHourlyBudget,
    SearchPageExecutionError,
    SearchTransportResponse,
    checkpoint_partition_count,
    execute_search_page,
    plan_partition_pages,
    seed_australia_state_partitions,
)
from butterflylens.contracts.fingerprint import canonicalize_json  # noqa: E402


NOW = datetime(2026, 7, 18, 1, 5, tzinfo=timezone.utc)
WINDOW = datetime(2026, 7, 18, 1, 0, tzinfo=timezone.utc)
CREDENTIAL = "synthetic-test-credential-never-sent"
CREDENTIAL_FINGERPRINT = hashlib.sha256(CREDENTIAL.encode()).hexdigest()


def pending_page() -> dict[str, object]:
    parameters = {"content_types": 0, "text": "Papilio testus"}
    request_preimage = {
        "provider": "flickr",
        "method": "flickr.photos.search",
        "endpoint": "https://www.flickr.com/services/rest/",
        "normalized_parameters": parameters,
    }
    request_fingerprint = hashlib.sha256(canonicalize_json(request_preimage)).hexdigest()
    request = {
        "physical_query_request_id": "blpr:v1:execution-fixture",
        "request_fingerprint": request_fingerprint,
        **request_preimage,
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
        total=2,
        source_response_fingerprint="2" * 64,
    )
    return plan_partition_pages(partition, count)[0]


def budget(*, credential_fingerprint: str = CREDENTIAL_FINGERPRINT) -> FlickrHourlyBudget:
    return FlickrHourlyBudget(
        project_id="butterflylens-test",
        credential_fingerprint=credential_fingerprint,
        window_start=WINDOW,
    )


def response(*, page: int = 1, photo_ids: tuple[str, ...] = ("101", "102")) -> SearchTransportResponse:
    body = json.dumps(
        {
            "stat": "ok",
            "photos": {
                "page": page,
                "pages": 1,
                "perpage": 250,
                "total": "2",
                "photo": [{"id": photo_id} for photo_id in photo_ids],
            },
        },
        separators=(",", ":"),
    ).encode()
    return SearchTransportResponse(http_status=200, body=body, received_at=NOW)


class FlickrSearchPageExecutionTests(unittest.TestCase):
    def test_valid_page_is_sent_once_budgeted_and_checkpointed(self) -> None:
        calls: list[dict[str, object]] = []

        def transport(**kwargs: object) -> SearchTransportResponse:
            calls.append(kwargs)
            return response()

        ledger = budget()
        result = execute_search_page(
            pending_page(),
            budget=ledger,
            credential=CREDENTIAL,
            credential_fingerprint=CREDENTIAL_FINGERPRINT,
            reserved_at=NOW,
            transport=transport,
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["credential"], CREDENTIAL)
        self.assertNotIn("api_key", calls[0]["normalized_parameters"])
        self.assertEqual(result["completed_checkpoint"]["status"], "succeeded")
        self.assertEqual(result["completed_checkpoint"]["returned_count"], 2)
        self.assertEqual(result["budget_outcome"], "consumed")
        self.assertEqual(ledger.normal_committed, 1)
        self.assertEqual(result["execution_state"], "checkpointed")
        self.assertEqual(result["credential_persisted"], False)
        safe_result = {key: value for key, value in result.items() if key != "response_body"}
        self.assertNotIn(CREDENTIAL, repr(safe_result))

    def test_transport_cannot_mutate_persisted_public_parameters(self) -> None:
        def transport(**kwargs: object) -> SearchTransportResponse:
            parameters = kwargs["normalized_parameters"]
            assert isinstance(parameters, dict)
            parameters["transport_mutation"] = CREDENTIAL
            return response()

        result = execute_search_page(
            pending_page(),
            budget=budget(),
            credential=CREDENTIAL,
            credential_fingerprint=CREDENTIAL_FINGERPRINT,
            reserved_at=NOW,
            transport=transport,
        )
        self.assertNotIn("transport_mutation", result["normalized_parameters"])

    def test_invalid_checkpoint_or_credential_never_crosses_transport(self) -> None:
        calls = 0

        def transport(**_: object) -> SearchTransportResponse:
            nonlocal calls
            calls += 1
            return response()

        completed = pending_page()
        completed["status"] = "succeeded"
        with self.assertRaisesRegex(Exception, "not pending"):
            execute_search_page(
                completed,
                budget=budget(),
                credential=CREDENTIAL,
                credential_fingerprint=CREDENTIAL_FINGERPRINT,
                reserved_at=NOW,
                transport=transport,
            )
        with self.assertRaisesRegex(SearchPageExecutionError, "fingerprint mismatch"):
            execute_search_page(
                pending_page(),
                budget=budget(),
                credential="wrong",
                credential_fingerprint=CREDENTIAL_FINGERPRINT,
                reserved_at=NOW,
                transport=transport,
            )
        self.assertEqual(calls, 0)

    def test_invalid_sent_response_consumes_reservation_without_checkpoint(self) -> None:
        ledger = budget()
        with self.assertRaisesRegex(SearchPageExecutionError, "page identity") as raised:
            execute_search_page(
                pending_page(),
                budget=ledger,
                credential=CREDENTIAL,
                credential_fingerprint=CREDENTIAL_FINGERPRINT,
                reserved_at=NOW,
                transport=lambda **_: response(page=2),
            )
        self.assertEqual(raised.exception.budget_outcome, "consumed")
        self.assertEqual(ledger.normal_committed, 1)
        self.assertFalse(ledger.frozen)

    def test_transport_uncertainty_freezes_budget(self) -> None:
        ledger = budget()

        def unavailable(**_: object) -> SearchTransportResponse:
            raise TimeoutError("synthetic boundary timeout")

        with self.assertRaisesRegex(SearchPageExecutionError, "uncertain") as raised:
            execute_search_page(
                pending_page(),
                budget=ledger,
                credential=CREDENTIAL,
                credential_fingerprint=CREDENTIAL_FINGERPRINT,
                reserved_at=NOW,
                transport=unavailable,
            )
        self.assertEqual(raised.exception.budget_outcome, "uncertain")
        self.assertTrue(ledger.frozen)
        self.assertEqual(ledger.normal_committed, 1)

    def test_duplicate_or_malformed_photos_fail_closed(self) -> None:
        for bad_response in (
            response(photo_ids=("101", "101")),
            SearchTransportResponse(200, b"not-json", NOW),
            SearchTransportResponse(429, b"{}", NOW),
        ):
            with self.subTest(status=bad_response.http_status, body=bad_response.body):
                with self.assertRaises(SearchPageExecutionError):
                    execute_search_page(
                        pending_page(),
                        budget=budget(),
                        credential=CREDENTIAL,
                        credential_fingerprint=CREDENTIAL_FINGERPRINT,
                        reserved_at=NOW,
                        transport=lambda result=bad_response, **_: result,
                    )

    def test_executor_has_no_built_in_http_client_or_live_call(self) -> None:
        source = (
            ROOT
            / "packages/contracts/python/butterflylens/flickr/execution.py"
        ).read_text()
        for forbidden in ("requests", "urllib", "httpx", "aiohttp"):
            self.assertNotIn(f"import {forbidden}", source)
        self.assertNotIn("api_key", source)


if __name__ == "__main__":
    unittest.main()
