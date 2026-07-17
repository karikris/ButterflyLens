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
    FingerprintIntegrityError,
    semantic_fingerprint_digest,
)


FIXTURES = ROOT / "packages/contracts/tests/fixtures/parity-cases.json"


def make_record(preimage: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": EVIDENCE_FINGERPRINT_SCHEMA_VERSION,
        "hash_algorithm": FINGERPRINT_HASH_ALGORITHM,
        "canonicalization": FINGERPRINT_CANONICALIZATION,
        "preimage": preimage,
        "digest": semantic_fingerprint_digest(preimage),
        "recorded_at": "2026-07-17T22:10:47Z",
    }


class FingerprintLineageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
        cls.vector = fixtures["lineage_vectors"][0]
        cls.records = [make_record(preimage) for preimage in cls.vector["nodes"]]

    def test_frozen_discovery_chain_traversal(self) -> None:
        graph = EvidenceLineageGraph(self.records)
        target = self.vector["target_digest"]
        root = self.vector["root_digest"]
        self.assertEqual(graph.ancestor_digests(target), tuple(self.vector["ancestors"]))
        self.assertEqual(graph.descendant_digests(root), tuple(self.vector["descendants"]))
        self.assertEqual(graph.topological_lineage(target), tuple(self.vector["topological"]))
        self.assertTrue(graph.has_lineage(target, root))
        self.assertFalse(graph.has_lineage(root, target))

    def test_input_order_does_not_change_traversal(self) -> None:
        forward = EvidenceLineageGraph(self.records)
        reverse = EvidenceLineageGraph(reversed(self.records))
        target = self.vector["target_digest"]
        self.assertEqual(
            forward.topological_lineage(target), reverse.topological_lineage(target)
        )
        self.assertEqual(forward.digests, reverse.digests)

    def test_missing_parent_and_kind_mismatch_fail_closed(self) -> None:
        with self.assertRaisesRegex(FingerprintIntegrityError, "missing parent"):
            EvidenceLineageGraph(self.records[:-1])

        root = deepcopy(self.vector["nodes"][1])
        association = deepcopy(self.vector["nodes"][3])
        association["parents"][0]["fingerprint_kind"] = "taxon_concept"
        with self.assertRaisesRegex(FingerprintIntegrityError, "parent kind mismatch"):
            EvidenceLineageGraph([make_record(root), make_record(association)])

    def test_duplicate_and_unknown_digests_fail_closed(self) -> None:
        with self.assertRaisesRegex(FingerprintIntegrityError, "duplicate"):
            EvidenceLineageGraph([self.records[0], self.records[0]])
        graph = EvidenceLineageGraph(self.records)
        with self.assertRaisesRegex(FingerprintIntegrityError, "unknown"):
            graph.parent_digests("f" * 64)

    def test_returned_records_are_defensive_copies(self) -> None:
        graph = EvidenceLineageGraph(self.records)
        target = self.vector["target_digest"]
        returned = graph.record(target)
        returned["preimage"]["payload"]["fixture"] = "mutated"
        self.assertEqual(
            graph.record(target)["preimage"]["payload"]["fixture"],
            "flickr:lineage",
        )


if __name__ == "__main__":
    unittest.main()
