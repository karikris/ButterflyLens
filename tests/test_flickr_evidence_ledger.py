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
    SearchTransportResponse,
    checkpoint_partition_count,
    execute_search_page,
    persist_execution_hashes,
    plan_partition_pages,
    seed_australia_state_partitions,
)


NOW = datetime(2026, 7, 18, 2, 5, tzinfo=timezone.utc)
CREDENTIAL = "synthetic-ledger-credential"
CREDENTIAL_FINGERPRINT = hashlib.sha256(CREDENTIAL.encode()).hexdigest()


class MemoryStore:
    def __init__(self) -> None:
        self.records: list[dict[str, object]] = []
        self.override: dict[str, object] = {}

    def insert_api_request(self, record: object) -> dict[str, object]:
        assert isinstance(record, dict)
        self.records.append(deepcopy(record))
        return {**deepcopy(record), **self.override}


def successful_execution() -> dict[str, object]:
    parameters = {"content_types": 0, "text": "Papilio testus"}
    request_preimage = {
        "provider": "flickr",
        "method": "flickr.photos.search",
        "endpoint": "https://www.flickr.com/services/rest/",
        "normalized_parameters": parameters,
    }
    request_fingerprint = hashlib.sha256(canonicalize_json(request_preimage)).hexdigest()
    request = {
        "physical_query_request_id": "blpr:v1:ledger-fixture",
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
        source_response_fingerprint="3" * 64,
    )
    checkpoint = plan_partition_pages(partition, count)[0]
    body = json.dumps(
        {
            "stat": "ok",
            "photos": {
                "page": 1,
                "pages": 1,
                "perpage": 250,
                "total": "2",
                "photo": [{"id": "201"}, {"id": "202"}],
            },
        },
        separators=(",", ":"),
    ).encode()
    budget = FlickrHourlyBudget(
        project_id="butterflylens-ledger-test",
        credential_fingerprint=CREDENTIAL_FINGERPRINT,
        window_start=datetime(2026, 7, 18, 2, 0, tzinfo=timezone.utc),
    )
    return execute_search_page(
        checkpoint,
        budget=budget,
        credential=CREDENTIAL,
        credential_fingerprint=CREDENTIAL_FINGERPRINT,
        reserved_at=NOW,
        transport=lambda **_: SearchTransportResponse(200, body, NOW),
    )


class FlickrEvidenceLedgerTests(unittest.TestCase):
    def test_verified_hashes_persist_once_without_raw_body_or_credential(self) -> None:
        execution = successful_execution()
        store = MemoryStore()
        receipt = persist_execution_hashes(
            execution,
            run_pk=7,
            query_definition_pk=11,
            store=store,
        )
        self.assertEqual(len(store.records), 1)
        row = store.records[0]
        self.assertEqual(row["request_fingerprint"], execution["page_request_fingerprint"])
        self.assertEqual(
            row["response_sha256"],
            hashlib.sha256(execution["response_body"]).hexdigest(),
        )
        self.assertEqual(row["response_fingerprint"], execution["source_response_fingerprint"])
        self.assertEqual(row["status"], "succeeded")
        self.assertNotIn("response_body", row)
        self.assertNotIn(CREDENTIAL, repr(row))
        self.assertEqual(receipt["storage_table"], "public.api_requests")
        self.assertEqual(receipt["storage_state"], "persisted")
        self.assertFalse(receipt["raw_response_persisted"])

    def test_request_response_and_checkpoint_tampering_never_reaches_store(self) -> None:
        mutations = (
            ("normalized_parameters", {"text": "changed"}),
            ("response_body", b"{}"),
            ("source_response_fingerprint", "0" * 64),
            ("credential_persisted", True),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                execution = successful_execution()
                execution[field] = value
                store = MemoryStore()
                with self.assertRaises(EvidenceLedgerError):
                    persist_execution_hashes(
                        execution,
                        run_pk=7,
                        query_definition_pk=11,
                        store=store,
                    )
                self.assertEqual(store.records, [])

    def test_store_must_acknowledge_exact_hashes(self) -> None:
        store = MemoryStore()
        store.override = {"response_sha256": "0" * 64}
        with self.assertRaisesRegex(EvidenceLedgerError, "changed response_sha256"):
            persist_execution_hashes(
                successful_execution(),
                run_pk=7,
                query_definition_pk=11,
                store=store,
            )
        self.assertEqual(len(store.records), 1)

    def test_existing_supabase_ledger_is_rls_closed_and_hash_complete(self) -> None:
        migration = (
            ROOT / "supabase/migrations/20260717211848_discovery_schema.sql"
        ).read_text()
        for fragment in (
            "request_fingerprint text not null",
            "response_sha256 text",
            "response_fingerprint text",
            "alter table public.api_requests enable row level security",
            "revoke all on table public.species",
            "public.api_requests, public.flickr_photos to service_role",
        ):
            self.assertIn(fragment, migration)

    def test_invalid_database_keys_fail_before_store(self) -> None:
        for run_pk, query_definition_pk in ((0, 1), (1, 0), (True, 1)):
            store = MemoryStore()
            with self.assertRaises(EvidenceLedgerError):
                persist_execution_hashes(
                    successful_execution(),
                    run_pk=run_pk,
                    query_definition_pk=query_definition_pk,
                    store=store,
                )
            self.assertEqual(store.records, [])


if __name__ == "__main__":
    unittest.main()
