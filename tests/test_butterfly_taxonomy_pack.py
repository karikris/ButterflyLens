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
        cls.crosswalk = [
            json.loads(line)
            for line in (PACK / "crosswalk.jsonl").read_text(encoding="utf-8").splitlines()
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
        self.assertEqual(self.manifest["crosswalk_state"]["status"], "built")
        self.assertEqual(self.manifest["conflict_state"], "not_built")

    def test_crosswalk_covers_every_taxon_in_order(self) -> None:
        taxon_keys = [record["butterflylens_key"] for record in self.records]
        crosswalk_keys = [record["butterflylens_key"] for record in self.crosswalk]
        self.assertEqual(crosswalk_keys, taxon_keys)
        self.assertEqual(len(crosswalk_keys), len(set(crosswalk_keys)))
        artifact = self.manifest["artifacts"]["crosswalk.jsonl"]
        self.assertEqual(artifact["row_count"], len(self.crosswalk))
        self.assertEqual(artifact["physical_sha256"], sha256(PACK / "crosswalk.jsonl"))

    def test_crosswalk_preserves_afd_identity_and_parent_path(self) -> None:
        taxa = {record["butterflylens_key"]: record for record in self.records}
        for row in self.crosswalk:
            source = taxa[row["butterflylens_key"]]
            self.assertEqual(row["accepted_scientific_name"], source["accepted_scientific_name"])
            self.assertEqual(row["rank"], source["rank"])
            self.assertEqual(row["parent_path"], source["parent_path"])
            self.assertEqual(row["taxonomic_status"], "accepted")

    def test_provider_ids_exist_only_for_accepted_matches(self) -> None:
        mappings = (
            ("ala", "ala_taxon_id"),
            ("gbif", "gbif_taxon_key"),
            ("inaturalist", "inaturalist_taxon_id"),
        )
        for row in self.crosswalk:
            matched = 0
            for provider, field in mappings:
                state = row["provider_matches"][provider]["state"]
                self.assertEqual(row[field] is not None, state == "matched")
                matched += state == "matched"
            expected = "complete" if matched == 3 else ("partial" if matched else "unresolved")
            self.assertEqual(row["crosswalk_status"], expected)

    def test_known_crosswalk_and_declared_query_normalization(self) -> None:
        row = next(
            row
            for row in self.crosswalk
            if row["accepted_scientific_name"] == "Papilio (Princeps) demoleus"
            and row["rank"] == "species"
        )
        self.assertEqual(row["provider_query_name"], "Papilio demoleus")
        self.assertEqual(row["query_name_normalization"], "parenthesized_subgenus_removed")
        self.assertEqual(row["ala_taxon_id"], "https://biodiversity.org.au/afd/taxa/345a9663-0926-45de-80eb-6d5d6adada61")
        self.assertEqual(row["gbif_taxon_key"], 1938069)
        self.assertEqual(row["inaturalist_taxon_id"], 51583)

    def test_provider_source_receipts_are_complete_and_current_bound(self) -> None:
        taxa_sha = sha256(PACK / "taxa.jsonl")
        paths = {
            source["provider"]: PACK / source["path"]
            for source in self.manifest["sources"]
            if source.get("provider")
        }
        self.assertEqual(set(paths), {"Atlas of Living Australia", "GBIF", "iNaturalist"})
        for provider, path in paths.items():
            snapshot = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(snapshot["input_taxa_sha256"], taxa_sha)
            manifest_source = next(
                source for source in self.manifest["sources"] if source.get("provider") == provider
            )
            self.assertEqual(manifest_source["physical_sha256"], sha256(path))
        gbif = json.loads(paths["GBIF"].read_text(encoding="utf-8"))
        self.assertEqual(len(gbif["entries"]), len(self.records))
        self.assertIn("created", gbif["source"]["metadata"])
        inaturalist = json.loads(paths["iNaturalist"].read_text(encoding="utf-8"))
        self.assertEqual(inaturalist["source"]["publication_date"], "2026-07-01")
        self.assertRegex(inaturalist["source"]["archive_sha256"], r"^[0-9a-f]{64}$")
        self.assertIn("Taxonomic information", inaturalist["source"]["intellectual_rights"])

    def test_non_exact_provider_results_are_not_silently_crosswalked(self) -> None:
        superfamily = next(row for row in self.crosswalk if row["rank"] == "superfamily")
        self.assertIsNone(superfamily["gbif_taxon_key"])
        self.assertEqual(superfamily["provider_matches"]["gbif"]["state"], "conflict")
        self.assertIn("non_exact_match", superfamily["provider_matches"]["gbif"]["reasons"])


if __name__ == "__main__":
    unittest.main()
