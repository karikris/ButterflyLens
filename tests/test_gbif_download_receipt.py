from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
GBIF = ROOT / "data/packs/australian_butterflies/v1/gbif"
RECEIPT_PATH = GBIF / "gbif_download_receipt.json"
SCHEMA_PATH = GBIF / "schemas/gbif_download_receipt.schema.json"


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


class GbifDownloadReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_receipt_matches_closed_schema(self) -> None:
        Draft202012Validator(
            self.schema,
            format_checker=FormatChecker(),
        ).validate(self.receipt)

    def test_exact_operator_supplied_download_contract_is_frozen(self) -> None:
        download = self.receipt["download"]
        self.assertEqual(download["key"], "0004170-260715120105164")
        self.assertEqual(download["doi"], "10.15468/dl.7uut3k")
        self.assertEqual(download["record_count"], 571755)
        self.assertEqual(download["dataset_count"], 126)
        self.assertEqual(download["archive_bytes"], 261743165)
        self.assertEqual(
            download["archive_sha256"],
            "7807622f6c2539ac536cb5f06d17087da3ecdd83b13a0dec54764e3800ff8f2b",
        )
        self.assertFalse(download["archive_committed_to_git"])

    def test_scope_and_authority_are_not_silently_broadened(self) -> None:
        self.assertEqual(self.receipt["filter"]["country_code"], "AU")
        self.assertEqual(self.receipt["filter"]["taxon_key"], "5G9")
        self.assertEqual(self.receipt["filter"]["checklist"], "Catalogue of Life")
        policy = self.receipt["authority_policy"]
        self.assertEqual(
            policy["authoritative_ala_baseline"],
            "ButterflyLens rebuilt baseline",
        )
        self.assertFalse(policy["gbif_replaces_ala_baseline"])

    def test_archive_inventory_and_rights_counts_reconcile(self) -> None:
        inventory = self.receipt["archive_inventory"]
        self.assertEqual(inventory["file_count"], 133)
        self.assertTrue(inventory["zip_integrity_verified"])
        members = inventory["members"]
        self.assertEqual(members["occurrence.txt"]["row_count"], 571755)
        self.assertEqual(members["verbatim.txt"]["row_count"], 571755)
        self.assertEqual(members["multimedia.txt"]["row_count"], 542052)
        self.assertEqual(members["dataset_xml"]["file_count"], 126)
        for member in members.values():
            fingerprint = member.get("sha256") or member.get("inventory_sha256")
            self.assertRegex(fingerprint, r"^[0-9a-f]{64}$")
        rights = self.receipt["rights"]
        self.assertEqual(
            sum(rights["constituent_dataset_rights_distribution"].values()),
            rights["constituent_dataset_rights_entry_count"],
        )
        self.assertEqual(
            rights["public_release_state"],
            "blocked_pending_record_and_dataset_rights_review",
        )
        self.assertFalse(rights["legal_determination"])

    def test_receipt_fingerprint_is_reproducible(self) -> None:
        semantic = dict(self.receipt)
        expected = semantic.pop("receipt_fingerprint")
        self.assertEqual(hashlib.sha256(canonical_json(semantic)).hexdigest(), expected)

    def test_evidence_policy_is_fail_closed(self) -> None:
        policy = self.receipt["evidence_policy"]
        self.assertFalse(policy["absence_inference_permitted"])
        self.assertFalse(policy["current_presence_inference_permitted"])
        self.assertFalse(policy["media_downloaded"])
        self.assertFalse(policy["flickr_api_called"])
        self.assertIn("not human verification", policy["provider_taxon_labels"])


if __name__ == "__main__":
    unittest.main()
