from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))

from butterflylens.contracts import (  # noqa: E402
    EVIDENCE_FINGERPRINT_LEGACY_SCHEMA_VERSION,
    EVIDENCE_FINGERPRINT_SCHEMA_VERSION,
    FINGERPRINT_KINDS,
    FingerprintValidationError,
    semantic_fingerprint_digest,
    validate_evidence_fingerprint,
)


FIXTURES = ROOT / "packages/contracts/tests/fixtures/parity-cases.json"


class FingerprintValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))

    def test_current_vocabulary_covers_required_chain(self) -> None:
        required = {
            "taxon_concept",
            "name_assertion",
            "query_definition",
            "logical_query_association",
            "physical_api_request",
            "source_response",
            "source_flickr_record",
            "downloaded_image",
            "perceptual_duplicate_group",
            "yoloe_route",
            "full_frame_visual_input",
            "bioclip_embedding",
            "reference_bank",
            "prototype",
            "candidate_score",
            "review_event",
            "consensus",
            "quality_snapshot",
            "geographic_impact_cell",
            "release_candidate",
            "export_manifest",
        }
        self.assertTrue(required.issubset(FINGERPRINT_KINDS))
        self.assertNotIn("api_response", FINGERPRINT_KINDS)
        self.assertEqual(
            EVIDENCE_FINGERPRINT_SCHEMA_VERSION,
            "butterflylens-evidence-fingerprint:v1.1.0",
        )

    def test_frozen_validation_vectors(self) -> None:
        for vector in self.fixtures["fingerprint_validation_vectors"]:
            with self.subTest(vector["case_id"]):
                if vector["valid"]:
                    validate_evidence_fingerprint(vector["record"])
                else:
                    with self.assertRaisesRegex(
                        FingerprintValidationError, vector["error"]
                    ):
                        validate_evidence_fingerprint(vector["record"])

    def test_legacy_v1_record_remains_valid(self) -> None:
        preimage = {
            "fingerprint_kind": "api_response",
            "subject_id": "response:legacy",
            "payload_schema_version": "v1",
            "payload": {"provider": "fixture"},
            "parents": [],
        }
        record = {
            "schema_version": EVIDENCE_FINGERPRINT_LEGACY_SCHEMA_VERSION,
            "hash_algorithm": "sha256",
            "canonicalization": "RFC8785-JCS",
            "preimage": preimage,
            "digest": semantic_fingerprint_digest(preimage),
            "recorded_at": "2026-07-17T22:10:47Z",
        }
        validate_evidence_fingerprint(record)

    def test_payload_mutation_is_detected(self) -> None:
        record = deepcopy(self.fixtures["fingerprint_validation_vectors"][0]["record"])
        record["preimage"]["payload"]["accepted_taxon_key"] = "taxon:changed"
        with self.assertRaisesRegex(FingerprintValidationError, "digest mismatch"):
            validate_evidence_fingerprint(record)

    def test_unknown_fields_and_naive_time_fail_closed(self) -> None:
        record = deepcopy(self.fixtures["fingerprint_validation_vectors"][0]["record"])
        record["unexpected"] = True
        with self.assertRaisesRegex(FingerprintValidationError, "additional properties"):
            validate_evidence_fingerprint(record)
        del record["unexpected"]
        record["recorded_at"] = "2026-07-17T22:10:47"
        with self.assertRaisesRegex(FingerprintValidationError, "RFC 3339"):
            validate_evidence_fingerprint(record)


if __name__ == "__main__":
    unittest.main()
