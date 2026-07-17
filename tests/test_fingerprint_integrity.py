from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))

from butterflylens.contracts import (  # noqa: E402
    EVIDENCE_FINGERPRINT_SCHEMA_VERSION,
    FINGERPRINT_CANONICALIZATION,
    FINGERPRINT_HASH_ALGORITHM,
    EvidenceLineageGraph,
    FingerprintCollisionError,
    FingerprintIntegrityError,
    FingerprintValidationError,
    assert_same_fingerprint_identity,
    canonicalize_evidence_preimage,
    semantic_fingerprint_digest,
    validate_evidence_fingerprint,
)


FIXTURES = ROOT / "packages/contracts/tests/fixtures/parity-cases.json"


def record_for(preimage: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": EVIDENCE_FINGERPRINT_SCHEMA_VERSION,
        "hash_algorithm": FINGERPRINT_HASH_ALGORITHM,
        "canonicalization": FINGERPRINT_CANONICALIZATION,
        "preimage": preimage,
        "digest": semantic_fingerprint_digest(preimage),
        "recorded_at": "2026-07-17T22:10:47Z",
    }


class FingerprintIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
        cls.valid = deepcopy(fixtures["fingerprint_validation_vectors"][0]["record"])
        cls.conflicts = fixtures["identity_conflict_vectors"]

    def test_every_semantic_field_is_digest_bound(self) -> None:
        base = self.valid["preimage"]
        mutations = []
        for field, replacement in (
            ("fingerprint_kind", "query_definition"),
            ("subject_id", "association:changed"),
            ("payload_schema_version", "v2"),
            ("payload", {"changed": True}),
            (
                "parents",
                [{
                    "relationship": "derived_from",
                    "fingerprint_kind": "query_definition",
                    "digest": "a" * 64,
                }],
            ),
        ):
            mutated = deepcopy(base)
            mutated[field] = replacement
            mutations.append(mutated)
        self.assertEqual(len({semantic_fingerprint_digest(item) for item in mutations}), 5)
        self.assertNotIn(
            semantic_fingerprint_digest(base),
            {semantic_fingerprint_digest(item) for item in mutations},
        )

    def test_canonical_equivalence_and_meaningful_array_order(self) -> None:
        duplicate = self.conflicts[0]
        distinct = self.conflicts[1]
        self.assertEqual(
            canonicalize_evidence_preimage(duplicate["left"]),
            canonicalize_evidence_preimage(duplicate["right"]),
        )
        self.assertEqual(
            semantic_fingerprint_digest(duplicate["left"]),
            semantic_fingerprint_digest(duplicate["right"]),
        )
        self.assertNotEqual(
            semantic_fingerprint_digest(distinct["left"]),
            semantic_fingerprint_digest(distinct["right"]),
        )

    def test_same_digest_conflict_distinguishes_duplicate_and_collision(self) -> None:
        shared = "f" * 64
        duplicate, collision = self.conflicts
        assert_same_fingerprint_identity(
            {"digest": shared, "preimage": duplicate["left"]},
            {"digest": shared, "preimage": duplicate["right"]},
        )
        with self.assertRaisesRegex(FingerprintCollisionError, "collision detected"):
            assert_same_fingerprint_identity(
                {"digest": shared, "preimage": collision["left"]},
                {"digest": shared, "preimage": collision["right"]},
            )

    def test_envelope_and_preimage_tampering_fail_closed(self) -> None:
        cases = {
            "schema_version": "butterflylens-evidence-fingerprint:v9.0.0",
            "hash_algorithm": "sha1",
            "canonicalization": "sorted-json",
            "digest": "0" * 64,
            "recorded_at": "not-a-time",
        }
        for field, replacement in cases.items():
            with self.subTest(field):
                record = deepcopy(self.valid)
                record[field] = replacement
                with self.assertRaises(FingerprintValidationError):
                    validate_evidence_fingerprint(record)
        record = deepcopy(self.valid)
        record["preimage"]["payload"]["accepted_taxon_key"] = "taxon:tampered"
        with self.assertRaisesRegex(FingerprintValidationError, "digest mismatch"):
            validate_evidence_fingerprint(record)

    def test_large_deterministic_set_has_no_observed_duplicate_digest(self) -> None:
        digests = {
            semantic_fingerprint_digest({
                "fingerprint_kind": "query_definition",
                "subject_id": f"query:integrity:{index}",
                "payload_schema_version": "v1",
                "payload": {"index": index, "terms": ["butterfly", str(index)]},
                "parents": [],
            })
            for index in range(2_000)
        }
        self.assertEqual(len(digests), 2_000)

    def test_deep_lineage_uses_stack_safe_cycle_and_traversal_checks(self) -> None:
        records = []
        parent = None
        for index in range(1_200):
            parents = [] if parent is None else [{
                "relationship": "derived_from",
                "fingerprint_kind": "query_definition",
                "digest": parent,
            }]
            preimage = {
                "fingerprint_kind": "query_definition",
                "subject_id": f"query:deep:{index}",
                "payload_schema_version": "v1",
                "payload": {"index": index},
                "parents": parents,
            }
            record = record_for(preimage)
            records.append(record)
            parent = record["digest"]
        graph = EvidenceLineageGraph(reversed(records))
        self.assertEqual(len(graph.ancestor_digests(parent)), 1_199)
        self.assertEqual(len(graph.topological_lineage(parent)), 1_200)

    def test_cycle_detector_fails_without_recursive_overflow(self) -> None:
        graph = EvidenceLineageGraph([])
        graph._records = {"a": {}, "b": {}}
        graph._parents = {"a": ("b",), "b": ("a",)}
        graph._children = {"a": ("b",), "b": ("a",)}
        with self.assertRaisesRegex(FingerprintIntegrityError, "cycle"):
            graph._assert_acyclic()


if __name__ == "__main__":
    unittest.main()
