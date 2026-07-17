from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))

from butterflylens.flickr import (  # noqa: E402
    FLICKR_ACCESSIBLE_RESULT_LIMIT,
    FLICKR_GEO_RESULTS_PER_PAGE,
    PartitionError,
    checkpoint_partition_count,
    complete_page_checkpoint,
    plan_partition_pages,
    seed_australia_state_partitions,
    split_saturated_partition,
    validate_australia_partition_scope,
    validate_partition_completion,
)
from butterflylens.contracts.fingerprint import canonicalize_json  # noqa: E402


SCOPE_PATH = ROOT / "packages/flickr/australia_partition_scopes.json"


class FlickrAustraliaPartitioningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scope = json.loads(SCOPE_PATH.read_text())
        parameters = {
            "content_types": 0,
            "media": "photos",
            "safe_search": 1,
            "text": "fixturea externa",
        }
        request_preimage = {
            "provider": "flickr",
            "method": "flickr.photos.search",
            "endpoint": "https://www.flickr.com/services/rest/",
            "normalized_parameters": parameters,
        }
        request_fingerprint = hashlib.sha256(canonicalize_json(request_preimage)).hexdigest()
        cls.request = {
            "schema_version": "butterflylens-physical-query-request:v1.0.0",
            "physical_query_request_id": "blpr:v1:partition-fixture",
            "provider": "flickr",
            "method": "flickr.photos.search",
            "endpoint": "https://www.flickr.com/services/rest/",
            "normalized_parameters": parameters,
            "request_fingerprint": request_fingerprint,
            "execution_state": "planned_not_sent",
        }
        cls.seeds = seed_australia_state_partitions(
            cls.request,
            cls.scope,
            min_upload_date=1_076_371_200,
            max_upload_date=1_784_332_799,
        )

    def test_abs_scope_and_state_seed_inventory_are_complete(self) -> None:
        validate_australia_partition_scope(self.scope)
        self.assertEqual(self.scope["national_bbox"], [96.0, -45.0, 169.0, -8.0])
        self.assertEqual(len(self.seeds), 9)
        self.assertEqual({row["state_code"] for row in self.seeds}, set("123456789"))
        self.assertEqual(len({row["partition_fingerprint"] for row in self.seeds}), 9)
        for row in self.seeds:
            self.assertEqual(row["normalized_parameters"]["per_page"], 250)
            self.assertEqual(row["normalized_parameters"]["has_geo"], 1)
            self.assertEqual(row["execution_state"], "planned_not_sent")

    def test_exact_limit_recursively_splits_time_without_gap(self) -> None:
        parent = self.seeds[0]
        checkpoint = checkpoint_partition_count(
            parent,
            total=FLICKR_ACCESSIBLE_RESULT_LIMIT,
            source_response_fingerprint="b" * 64,
        )
        left, right = split_saturated_partition(parent, checkpoint)
        self.assertEqual(left["split_reason"], "time_bisection")
        self.assertEqual(left["max_upload_date"] + 1, right["min_upload_date"])
        self.assertEqual(left["min_upload_date"], parent["min_upload_date"])
        self.assertEqual(right["max_upload_date"], parent["max_upload_date"])
        self.assertNotEqual(left["partition_fingerprint"], right["partition_fingerprint"])
        self.assertEqual(left["parent_partition_id"], parent["partition_id"])

    def test_one_second_saturation_falls_back_to_bbox_bisection(self) -> None:
        parent = seed_australia_state_partitions(
            self.request,
            self.scope,
            min_upload_date=1_784_332_799,
            max_upload_date=1_784_332_799,
        )[7]
        checkpoint = checkpoint_partition_count(
            parent,
            total=5000,
            source_response_fingerprint="d" * 64,
        )
        first, second = split_saturated_partition(parent, checkpoint)
        self.assertEqual(first["split_reason"], "bbox_bisection")
        self.assertTrue(
            first["bbox"][2] == second["bbox"][0]
            or first["bbox"][3] == second["bbox"][1]
        )
        self.assertEqual(first["min_upload_date"], first["max_upload_date"])
        self.assertNotEqual(first["partition_fingerprint"], second["partition_fingerprint"])

    def test_sub_limit_partition_has_exact_unique_page_checkpoints(self) -> None:
        partition = self.seeds[1]
        count = checkpoint_partition_count(
            partition,
            total=3999,
            source_response_fingerprint="e" * 64,
        )
        pages = plan_partition_pages(partition, count)
        self.assertEqual(FLICKR_GEO_RESULTS_PER_PAGE, 250)
        self.assertEqual(len(pages), 16)
        self.assertEqual([row["page"] for row in pages], list(range(1, 17)))
        self.assertTrue(all(row["cursor"] is None for row in pages))
        self.assertEqual(len({row["page_request_fingerprint"] for row in pages}), 16)
        with self.assertRaisesRegex(PartitionError, "split"):
            saturated = checkpoint_partition_count(
                partition, total=4000, source_response_fingerprint="f" * 64
            )
            plan_partition_pages(partition, saturated)

    def test_completion_requires_every_page_stable_total_and_exact_counts(self) -> None:
        partition = self.seeds[2]
        count = checkpoint_partition_count(
            partition,
            total=501,
            source_response_fingerprint="1" * 64,
        )
        pending = plan_partition_pages(partition, count)
        completed = tuple(
            complete_page_checkpoint(
                checkpoint,
                source_response_fingerprint=str(index) * 64,
                observed_total=501,
                returned_count=(250, 250, 1)[index - 2],
            )
            for index, checkpoint in enumerate(pending, 2)
        )
        receipt = validate_partition_completion(partition, count, completed)
        self.assertEqual(receipt["status"], "complete")
        with self.assertRaisesRegex(PartitionError, "gap"):
            validate_partition_completion(partition, count, completed[:-1])
        drifted = list(deepcopy(completed))
        drifted[-1]["observed_total"] = 502
        with self.assertRaisesRegex(PartitionError, "drifted"):
            validate_partition_completion(partition, count, drifted)

    def test_duplicate_scope_and_partition_overrides_fail_closed(self) -> None:
        duplicate_scope = deepcopy(self.scope)
        duplicate_scope["partitions"][1]["bbox"] = duplicate_scope["partitions"][0]["bbox"]
        with self.assertRaisesRegex(PartitionError, "duplicate"):
            validate_australia_partition_scope(duplicate_scope)
        overridden = deepcopy(self.request)
        overridden["normalized_parameters"]["page"] = 1
        overridden_preimage = {
            "provider": overridden["provider"],
            "method": overridden["method"],
            "endpoint": overridden["endpoint"],
            "normalized_parameters": overridden["normalized_parameters"],
        }
        overridden["request_fingerprint"] = hashlib.sha256(
            canonicalize_json(overridden_preimage)
        ).hexdigest()
        with self.assertRaisesRegex(PartitionError, "already contains"):
            seed_australia_state_partitions(
                overridden, self.scope, min_upload_date=1, max_upload_date=2
            )


if __name__ == "__main__":
    unittest.main()
