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

from butterflylens.flickr import (  # noqa: E402
    FlickrHourlyBudget,
    LogicalAssociationLedgerError,
    SearchTransportResponse,
    build_logical_query_association,
    checkpoint_partition_count,
    compile_name_assertion,
    execute_search_page,
    persist_execution_hashes,
    persist_logical_associations,
    plan_partition_pages,
    plan_physical_query_requests,
    seed_australia_state_partitions,
)


NAMES = ROOT / "data/packs/australian_butterflies/v1/name_assertions.jsonl"
NOW = datetime(2026, 7, 18, 3, 5, tzinfo=timezone.utc)
CREDENTIAL = "synthetic-logical-ledger-credential"
CREDENTIAL_FINGERPRINT = hashlib.sha256(CREDENTIAL.encode()).hexdigest()


class MemoryStore:
    def __init__(self) -> None:
        self.request_records: list[dict[str, object]] = []
        self.association_batches: list[tuple[dict[str, object], ...]] = []
        self.drop_last_acknowledgement = False

    def insert_api_request(self, record: object) -> dict[str, object]:
        assert isinstance(record, dict)
        self.request_records.append(deepcopy(record))
        return deepcopy(record)

    def insert_api_request_associations(
        self, records: tuple[object, ...]
    ) -> tuple[dict[str, object], ...]:
        copied = tuple(deepcopy(record) for record in records)
        assert all(isinstance(record, dict) for record in copied)
        self.association_batches.append(copied)  # type: ignore[arg-type]
        if self.drop_last_acknowledgement:
            return copied[:-1]  # type: ignore[return-value]
        return copied  # type: ignore[return-value]


def planned_execution() -> tuple[
    dict[str, object],
    tuple[dict[str, object], ...],
    tuple[dict[str, object], ...],
]:
    assertions = [json.loads(line) for line in NAMES.read_text().splitlines()]
    source = next(
        row
        for row in assertions
        if row["query_eligibility"]["eligible"] and row["taxon_rank"] == "species"
    )
    duplicate_term = deepcopy(source)
    duplicate_term["assertion_id"] = "blna:v1:logical-ledger-fixture"
    duplicate_term["butterflylens_key"] = "bltx:v1:logical-ledger-fixture"
    definitions = (
        compile_name_assertion(source),
        compile_name_assertion(duplicate_term),
    )
    associations = tuple(
        build_logical_query_association(
            definition,
            associated_taxon_key=str(definition["source_taxon_key"]),
            relationship="accepted_name",
            query_lane="australia-known",
            association_reason="authoritative accepted species name fixture",
        )
        for definition in definitions
    )
    plan = plan_physical_query_requests(
        definitions,
        associations,
        fixed_parameters={"content_types": 0},
    )
    physical_request = plan["physical_requests"][0]
    scope = json.loads(
        (ROOT / "packages/flickr/australia_partition_scopes.json").read_text()
    )
    partition = seed_australia_state_partitions(
        physical_request,
        scope,
        min_upload_date=1_700_000_000,
        max_upload_date=1_700_086_399,
    )[0]
    count = checkpoint_partition_count(
        partition,
        total=1,
        source_response_fingerprint="4" * 64,
    )
    checkpoint = plan_partition_pages(partition, count)[0]
    body = json.dumps(
        {
            "stat": "ok",
            "photos": {
                "page": 1,
                "pages": 1,
                "perpage": 250,
                "total": "1",
                "photo": [{"id": "301"}],
            },
        },
        separators=(",", ":"),
    ).encode()
    budget = FlickrHourlyBudget(
        project_id="butterflylens-logical-ledger-test",
        credential_fingerprint=CREDENTIAL_FINGERPRINT,
        window_start=datetime(2026, 7, 18, 3, 0, tzinfo=timezone.utc),
    )
    execution = execute_search_page(
        checkpoint,
        budget=budget,
        credential=CREDENTIAL,
        credential_fingerprint=CREDENTIAL_FINGERPRINT,
        reserved_at=NOW,
        transport=lambda **_: SearchTransportResponse(200, body, NOW),
    )
    return execution, plan["logical_associations"], plan["request_links"]


def persisted_inputs() -> tuple[
    dict[str, object],
    dict[str, object],
    tuple[dict[str, object], ...],
    tuple[dict[str, object], ...],
    MemoryStore,
]:
    execution, associations, links = planned_execution()
    store = MemoryStore()
    receipt = persist_execution_hashes(
        execution,
        run_pk=17,
        query_definition_pk=19,
        store=store,
    )
    return execution, receipt, associations, links, store


class FlickrLogicalAssociationLedgerTests(unittest.TestCase):
    def test_all_logical_meanings_survive_one_deduplicated_physical_request(self) -> None:
        execution, receipt, associations, links, store = persisted_inputs()
        mapping = {
            str(association["logical_query_association_id"]): index
            for index, association in enumerate(associations, 101)
        }
        logical_receipt = persist_logical_associations(
            execution,
            receipt,
            associations,
            links,
            api_request_pk=23,
            association_pk_by_id=mapping,
            store=store,
        )
        self.assertEqual(len(store.association_batches), 1)
        rows = store.association_batches[0]
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["api_request_pk"] for row in rows}, {23})
        self.assertEqual(
            {row["query_association_pk"] for row in rows}, set(mapping.values())
        )
        self.assertEqual(len({row["link_fingerprint"] for row in rows}), 2)
        self.assertEqual(logical_receipt["association_count"], 2)
        self.assertFalse(logical_receipt["query_term_is_taxon_label"])

    def test_tampered_incomplete_or_wrong_root_links_fail_before_storage(self) -> None:
        for mutation in ("fingerprint", "missing", "wrong_root"):
            with self.subTest(mutation=mutation):
                execution, receipt, associations, links, store = persisted_inputs()
                changed_links = [deepcopy(link) for link in links]
                if mutation == "fingerprint":
                    changed_links[0]["association_fingerprint"] = "0" * 64
                elif mutation == "missing":
                    changed_links.pop()
                else:
                    changed_links[0]["physical_query_request_id"] = "blpr:v1:wrong-root"
                mapping = {
                    str(association["logical_query_association_id"]): index
                    for index, association in enumerate(associations, 101)
                }
                with self.assertRaises(Exception):
                    persist_logical_associations(
                        execution,
                        receipt,
                        associations,
                        changed_links,
                        api_request_pk=23,
                        association_pk_by_id=mapping,
                        store=store,
                    )
                self.assertEqual(store.association_batches, [])

    def test_database_key_mapping_must_be_exact_and_unique(self) -> None:
        execution, receipt, associations, links, store = persisted_inputs()
        ids = [str(item["logical_query_association_id"]) for item in associations]
        for mapping in ({ids[0]: 1}, {ids[0]: 1, ids[1]: 1}, {**dict(zip(ids, (1, 2))), "extra": 3}):
            with self.subTest(mapping=mapping):
                with self.assertRaises(LogicalAssociationLedgerError):
                    persist_logical_associations(
                        execution,
                        receipt,
                        associations,
                        links,
                        api_request_pk=23,
                        association_pk_by_id=mapping,
                        store=store,
                    )
        self.assertEqual(store.association_batches, [])

    def test_atomic_store_acknowledgement_must_cover_every_link(self) -> None:
        execution, receipt, associations, links, store = persisted_inputs()
        store.drop_last_acknowledgement = True
        mapping = {
            str(association["logical_query_association_id"]): index
            for index, association in enumerate(associations, 101)
        }
        with self.assertRaisesRegex(LogicalAssociationLedgerError, "incomplete"):
            persist_logical_associations(
                execution,
                receipt,
                associations,
                links,
                api_request_pk=23,
                association_pk_by_id=mapping,
                store=store,
            )

    def test_page_checkpoint_binds_root_physical_request(self) -> None:
        execution, _, _ = planned_execution()
        self.assertTrue(str(execution["root_physical_query_request_id"]).startswith("blpr:v1:"))
        self.assertRegex(str(execution["root_request_fingerprint"]), r"^[0-9a-f]{64}$")
        self.assertNotEqual(
            execution["root_request_fingerprint"], execution["page_request_fingerprint"]
        )


if __name__ == "__main__":
    unittest.main()
