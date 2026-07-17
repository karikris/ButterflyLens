from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data/packs/australian_butterflies/v1"
SCRIPT = ROOT / "scripts/build_butterfly_taxonomy.py"


def load_builder():
    specification = importlib.util.spec_from_file_location("butterfly_taxonomy", SCRIPT)
    if specification is None or specification.loader is None:
        raise RuntimeError("unable to load taxonomy builder")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ButterflyTaxonomyPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = load_builder()
        cls.manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
        cls.snapshot = json.loads(
            (PACK / "sources/afd_papilionoidea.json").read_text(encoding="utf-8")
        )
        cls.records = [
            json.loads(line)
            for line in (PACK / "taxa.jsonl").read_text(encoding="utf-8").splitlines()
        ]

    def test_snapshot_integrity(self) -> None:
        self.builder.validate_snapshot(self.snapshot)
        source = self.manifest["sources"][0]
        self.assertEqual(
            source["physical_sha256"], sha256(PACK / source["path"])
        )
        self.assertEqual(
            source["semantic_sha256"], self.snapshot["source_semantic_sha256"]
        )
        self.assertRegex(source["root_source_concept_id"], r"afd\.taxon/[0-9a-f-]{36}$")

    def test_manifest_and_taxa_checksum(self) -> None:
        artifact = self.manifest["artifacts"]["taxa.jsonl"]
        self.assertEqual(artifact["physical_sha256"], sha256(PACK / "taxa.jsonl"))
        self.assertEqual(artifact["row_count"], len(self.records))
        self.assertEqual(
            artifact["rank_counts"], dict(sorted(Counter(row["rank"] for row in self.records).items()))
        )

    def test_required_ranks_and_australian_families(self) -> None:
        counts = Counter(record["rank"] for record in self.records)
        self.assertEqual(set(counts), set(self.builder.INCLUDED_RANKS))
        self.assertEqual(counts["superfamily"], 1)
        self.assertEqual(counts["family"], 6)
        self.assertTrue(all(counts[rank] > 0 for rank in self.builder.INCLUDED_RANKS))

    def test_keys_are_unique_and_recomputable(self) -> None:
        keys = [record["butterflylens_key"] for record in self.records]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(all(re.fullmatch(r"bltx:v1:[0-9a-f]{24}", key) for key in keys))
        source_nodes = {node["source_key"]: node for node in self.snapshot["nodes"]}
        for record in self.records:
            source_node = source_nodes[record["source"]["source_key"]]
            self.assertEqual(record["butterflylens_key"], self.builder.butterflylens_key(source_node))

    def test_normalized_hierarchy_is_connected(self) -> None:
        by_key = {record["butterflylens_key"]: record for record in self.records}
        roots = [record for record in self.records if record["parent_key"] is None]
        self.assertEqual([record["accepted_scientific_name"] for record in roots], ["PAPILIONOIDEA"])
        for record in self.records:
            path_keys = [item["butterflylens_key"] for item in record["parent_path"]]
            self.assertEqual(path_keys[-1:] or [None], [record["parent_key"]])
            self.assertTrue(all(key in by_key for key in path_keys))
            self.assertNotIn(record["butterflylens_key"], path_keys)

    def test_source_lineage_preserves_excluded_intermediate_ranks(self) -> None:
        excluded = self.manifest["excluded_source_rank_counts"]
        self.assertGreater(excluded.get("subgenus", 0), 0)
        source_paths = [item for record in self.records for item in record["source_parent_path"]]
        self.assertTrue(any(item["rank"] == "subgenus" for item in source_paths))
        self.assertTrue(
            all(item["rank"] in self.builder.INCLUDED_RANKS for record in self.records for item in record["parent_path"])
        )

    def test_scope_rows_do_not_claim_occurrence_or_verification(self) -> None:
        forbidden_fields = {
            "occurrence",
            "probability",
            "model_confidence",
            "human_verified",
            "verified_occurrence",
        }
        for record in self.records:
            self.assertTrue(forbidden_fields.isdisjoint(record))
            self.assertEqual(record["taxonomic_status"], "accepted")
            self.assertEqual(record["source"]["provider"], "Australian Faunal Directory")

    def test_rights_and_citation_are_explicit(self) -> None:
        rights = self.manifest["rights"]
        self.assertEqual(rights["licence"], "CC-BY-4.0")
        self.assertIn("Australian Faunal Directory", rights["attribution"])
        self.assertIn("Viewed", rights["citation"])
        self.assertEqual(self.manifest["scope"]["additional_configured_taxa"], [])
        self.assertEqual(self.manifest["crosswalk_state"], "not_built")
        self.assertEqual(self.manifest["conflict_state"], "not_built")


if __name__ == "__main__":
    unittest.main()
