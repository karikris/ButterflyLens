from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
OPENAI_PACKAGE = ROOT / "packages" / "openai" / "python"
sys.path.insert(0, str(OPENAI_PACKAGE))

from butterflylens_openai import (  # noqa: E402
    ArtifactIntegrityError,
    EvidenceToolbox,
    SubmittedEvidenceRepository,
    TOOL_ORDER,
    ToolInputError,
    contract_document,
)


SPECIES_KEY = "bltx:v1:997e8426f871a0602527d4ce"
SPECIES_NAME = "Acraea andromacha"


def fact(result: dict[str, object], name: str) -> dict[str, object]:
    return next(row for row in result["facts"] if row["name"] == name)


class OpenAIEvidenceToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.toolbox = EvidenceToolbox(ROOT)
        cls.contract_path = ROOT / "packages" / "openai" / "tool_contracts.json"
        cls.registry_path = (
            ROOT / "packages" / "openai" / "submitted-artifacts.v1.json"
        )

    def test_exact_fourteen_tool_inventory_and_order(self) -> None:
        self.assertEqual(len(TOOL_ORDER), 14)
        self.assertEqual(
            TOOL_ORDER,
            (
                "inspect_map_scope",
                "compare_ala_and_flickr",
                "inspect_species",
                "inspect_flickr_candidate",
                "trace_record_evidence",
                "explain_classification",
                "inspect_review_consensus",
                "inspect_reviewer_quality",
                "inspect_pipeline_status",
                "inspect_worker_status",
                "recommend_next_review_batch",
                "recommend_next_species",
                "explain_geographic_contribution",
                "prepare_impact_report",
            ),
        )
        self.assertEqual(
            [definition["name"] for definition in self.toolbox.definitions],
            list(TOOL_ORDER),
        )

    def test_generated_contract_matches_python_authority(self) -> None:
        tracked = json.loads(self.contract_path.read_text(encoding="utf-8"))
        self.assertEqual(tracked, contract_document())
        self.assertEqual(tracked["tool_count"], 14)
        self.assertTrue(tracked["deterministic"])
        self.assertTrue(tracked["read_only"])

    def test_every_input_object_is_recursively_strict(self) -> None:
        for definition in self.toolbox.definitions:
            self.assertTrue(definition["strict"])
            self._assert_strict_objects(definition["parameters"])

    def _assert_strict_objects(self, schema: dict[str, object]) -> None:
        schema_type = schema.get("type")
        if schema_type == "object" or (
            isinstance(schema_type, list) and "object" in schema_type
        ):
            properties = schema.get("properties")
            self.assertIsInstance(properties, dict)
            self.assertFalse(schema.get("additionalProperties"))
            self.assertEqual(set(schema.get("required", [])), set(properties))
            for value in properties.values():
                self._assert_strict_objects(value)
        items = schema.get("items")
        if isinstance(items, dict):
            self._assert_strict_objects(items)

    def test_pinned_artifact_registry_verifies_every_checksum(self) -> None:
        repository = SubmittedEvidenceRepository(ROOT)
        self.assertEqual(repository.repository, "karikris/ButterflyLens")
        self.assertEqual(
            repository.commit, "cfe6b5f38b687e83d2a601d381edde29fcb7a717"
        )
        self.assertEqual(len(repository.artifact_keys), 19)
        self.assertIn("submitted_map", repository.artifact_keys)
        for key in repository.artifact_keys:
            citation = repository.citation(key)
            self.assertEqual(citation["commit"], repository.commit)
            self.assertRegex(citation["fingerprint"], r"^sha256:[0-9a-f]{64}$")

    def test_every_citation_matches_the_exact_pinned_git_commit(self) -> None:
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        commit = payload["commit"]
        for artifact in payload["artifacts"]:
            with self.subTest(path=artifact["path"]):
                result = subprocess.run(
                    ["git", "show", f"{commit}:{artifact['path']}"],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                )
                self.assertEqual(
                    hashlib.sha256(result.stdout).hexdigest(), artifact["sha256"]
                )

    def test_tampered_artifact_registry_fails_closed(self) -> None:
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        payload["artifacts"][0]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "tampered.json"
            registry.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ArtifactIntegrityError, "checksum mismatch"):
                SubmittedEvidenceRepository(ROOT, registry_path=registry)

    def test_repository_returns_defensive_evidence_copies(self) -> None:
        repository = SubmittedEvidenceRepository(ROOT)
        projection = repository.read_json("quality_projection")
        projection["status"] = "invented"
        self.assertEqual(
            repository.read_json("quality_projection")["status"], "unavailable"
        )
        species = repository.find_species(
            species_key=SPECIES_KEY, scientific_name=None
        )
        species["acceptedScientificName"] = "Invented"
        restored = repository.find_species(
            species_key=SPECIES_KEY, scientific_name=None
        )
        self.assertEqual(restored["acceptedScientificName"], SPECIES_NAME)

    def test_repository_reads_every_artifact_from_the_exact_pinned_commit(self) -> None:
        with mock.patch(
            "butterflylens_openai.repository.subprocess.run",
            wraps=subprocess.run,
        ) as run:
            repository = SubmittedEvidenceRepository(ROOT)
            submitted_map = repository.submitted_map()
        self.assertEqual(submitted_map["counts"]["mapEligible"], 213_310)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertIn(
            [
                "git",
                "show",
                "cfe6b5f38b687e83d2a601d381edde29fcb7a717:apps/web/src/map/submittedMapSnapshot.json",
            ],
            commands,
        )

    def test_unknown_extra_and_malformed_arguments_fail(self) -> None:
        with self.assertRaisesRegex(ToolInputError, "unknown"):
            self.toolbox.invoke("invent_species", {})
        with self.assertRaisesRegex(ToolInputError, "Additional properties"):
            self.toolbox.invoke(
                "inspect_worker_status", {"worker_id": None, "live": True}
            )
        with self.assertRaisesRegex(ToolInputError, "candidate_id"):
            self.toolbox.invoke("inspect_flickr_candidate", {"candidate_id": "bad id"})

    def test_scope_semantics_fail_closed(self) -> None:
        with self.assertRaisesRegex(ToolInputError, "national"):
            self.toolbox.invoke(
                "inspect_map_scope", {"scope_type": "national", "scope_id": "AU"}
            )
        with self.assertRaisesRegex(ToolInputError, "non-national"):
            self.toolbox.invoke(
                "inspect_map_scope", {"scope_type": "state", "scope_id": None}
            )

    def test_species_selector_requires_exactly_one_field(self) -> None:
        with self.assertRaisesRegex(ToolInputError, "exactly one"):
            self.toolbox.invoke(
                "inspect_species", {"species_key": None, "scientific_name": None}
            )
        with self.assertRaisesRegex(ToolInputError, "exactly one"):
            self.toolbox.invoke(
                "inspect_species",
                {"species_key": SPECIES_KEY, "scientific_name": SPECIES_NAME},
            )

    def test_inspect_species_returns_authoritative_bounded_evidence(self) -> None:
        result = self.toolbox.invoke(
            "inspect_species",
            {"species_key": SPECIES_KEY, "scientific_name": None},
        )
        self.assertEqual(result["status"], "available")
        self.assertEqual(len(result["records"]), 1)
        record = result["records"][0]
        self.assertEqual(record["record_id"], SPECIES_KEY)
        record_facts = {row["name"]: row for row in record["facts"]}
        self.assertEqual(record_facts["accepted_scientific_name"]["value"], SPECIES_NAME)
        self.assertEqual(record_facts["human_verified_media"]["value"], 0)
        self.assertEqual(record_facts["human_verified_media"]["state"], "unfinished")
        self.assertFalse(fact(result, "scientific_claim_allowed")["value"])

    def test_species_exact_name_lookup_and_unknown_abstention(self) -> None:
        by_name = self.toolbox.invoke(
            "inspect_species", {"species_key": None, "scientific_name": SPECIES_NAME}
        )
        self.assertEqual(by_name["records"][0]["record_id"], SPECIES_KEY)
        missing = self.toolbox.invoke(
            "inspect_species",
            {"species_key": None, "scientific_name": "Invented memory butterfly"},
        )
        self.assertEqual(missing["status"], "not_found")
        self.assertFalse(fact(missing, "model_memory_lookup_permitted")["value"])

    def test_map_scope_returns_rights_screened_ala_and_unavailable_flickr(self) -> None:
        national = self.toolbox.invoke(
            "inspect_map_scope", {"scope_type": "national", "scope_id": None}
        )
        self.assertEqual(national["status"], "partial")
        self.assertEqual(fact(national, "accepted_species")["value"], 463)
        self.assertEqual(fact(national, "ala_occurrence_count")["value"], 213_310)
        self.assertEqual(fact(national, "ala_occurrence_count")["state"], "observed")
        self.assertIsNone(fact(national, "flickr_candidate_count")["value"])
        self.assertEqual(fact(national, "map_cell_count")["value"], 630)
        self.assertEqual(fact(national, "rights_excluded_selected")["value"], 16_753)
        self.assertFalse(fact(national, "absence_inference_permitted")["value"])

    def test_map_scope_supports_exact_state_ibra_lga_and_h3_drilldowns(self) -> None:
        cases = (
            ("state", "ala:state-territory:new%20south%20wales", 47_861),
            ("ibra", "ala:ibra-v7:arnhem%20coast", 812),
            ("lga", "ala:lga-2023-approx:adelaide", 560),
            ("h3", "h3:3:838c23fffffffff", 224),
        )
        for scope_type, scope_id, expected_count in cases:
            with self.subTest(scope_type=scope_type):
                result = self.toolbox.invoke(
                    "inspect_map_scope",
                    {"scope_type": scope_type, "scope_id": scope_id},
                )
                self.assertEqual(result["status"], "partial")
                self.assertEqual(
                    fact(result, "ala_occurrence_count")["value"], expected_count
                )
                self.assertEqual(len(result["records"]), 1)
                record_facts = {
                    row["name"]: row for row in result["records"][0]["facts"]
                }
                self.assertEqual(
                    record_facts["ala_occurrence_count"]["value"], expected_count
                )
                encoded = json.dumps(result)
                for forbidden in ("center", "polygon", "longitude", "latitude"):
                    self.assertNotIn(forbidden, encoded)

    def test_unknown_map_scope_fails_closed_without_approximate_match(self) -> None:
        missing = self.toolbox.invoke(
            "inspect_map_scope",
            {"scope_type": "state", "scope_id": "ala:state-territory:not-real"},
        )
        self.assertEqual(missing["status"], "not_found")
        self.assertFalse(fact(missing, "scope_found")["value"])

    def test_ala_flickr_comparison_exposes_only_available_same_scope_count(self) -> None:
        national = self.toolbox.invoke(
            "compare_ala_and_flickr",
            {"scope_type": "national", "scope_id": None, "species_key": None},
        )
        self.assertEqual(national["status"], "partial")
        self.assertEqual(fact(national, "ala_occurrence_count")["value"], 213_310)
        self.assertIsNone(fact(national, "flickr_candidate_count")["value"])
        self.assertIsNone(fact(national, "count_difference")["value"])
        self.assertFalse(fact(national, "comparison_allowed")["value"])
        species = self.toolbox.invoke(
            "compare_ala_and_flickr",
            {"scope_type": "national", "scope_id": None, "species_key": SPECIES_KEY},
        )
        self.assertEqual(species["status"], "unavailable")
        self.assertIsNone(fact(species, "ala_occurrence_count")["value"])

    def test_flickr_candidate_tool_is_local_and_honestly_unavailable(self) -> None:
        result = self.toolbox.invoke(
            "inspect_flickr_candidate", {"candidate_id": "flickr-candidate:123"}
        )
        self.assertEqual(result["status"], "unavailable")
        self.assertFalse(fact(result, "flickr_api_call_made")["value"])
        self.assertFalse(fact(result, "species_identity_inferred")["value"])

    def test_species_trace_is_available_but_other_live_lineage_is_not(self) -> None:
        species = self.toolbox.invoke(
            "trace_record_evidence",
            {"record_type": "species", "record_id": SPECIES_KEY},
        )
        self.assertEqual(species["status"], "available")
        self.assertEqual(len(species["records"]), 2)
        flickr = self.toolbox.invoke(
            "trace_record_evidence",
            {"record_type": "flickr_candidate", "record_id": "candidate:123"},
        )
        self.assertEqual(flickr["status"], "unavailable")

    def test_classification_explanation_marks_skipped_models_unfinished(self) -> None:
        result = self.toolbox.invoke(
            "explain_classification", {"classification_id": "classification:123"}
        )
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(fact(result, "yoloe_state")["state"], "unfinished")
        self.assertEqual(fact(result, "bioclip_state")["state"], "unfinished")
        self.assertFalse(fact(result, "probability_available")["value"])

    def test_review_consensus_does_not_turn_missing_into_zero(self) -> None:
        result = self.toolbox.invoke(
            "inspect_review_consensus", {"item_id": "review-item:123"}
        )
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(fact(result, "review_count")["value"])
        self.assertFalse(fact(result, "majority_is_accuracy")["value"])

    def test_reviewer_quality_is_self_only_private_and_unranked(self) -> None:
        result = self.toolbox.invoke(
            "inspect_reviewer_quality", {"subject": "self", "domain_key": None}
        )
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(fact(result, "visibility")["value"], "self_only")
        self.assertFalse(fact(result, "public_ranking_allowed")["value"])
        with self.assertRaises(ToolInputError):
            self.toolbox.invoke(
                "inspect_reviewer_quality", {"subject": "other", "domain_key": None}
            )

    def test_pipeline_status_is_submitted_not_live(self) -> None:
        result = self.toolbox.invoke(
            "inspect_pipeline_status", {"pipeline_id": None}
        )
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(result["records"]), 8)
        self.assertEqual(fact(result, "snapshot_mode")["value"], "submitted")
        self.assertFalse(fact(result, "release_ready")["value"])
        self.assertFalse(fact(result, "live_state_claimed")["value"])
        missing = self.toolbox.invoke(
            "inspect_pipeline_status", {"pipeline_id": "active-biominer"}
        )
        self.assertEqual(missing["status"], "not_found")

    def test_worker_without_heartbeat_is_unavailable_not_offline(self) -> None:
        result = self.toolbox.invoke("inspect_worker_status", {"worker_id": None})
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(fact(result, "worker_state")["value"])
        self.assertIsNone(fact(result, "last_heartbeat")["value"])

    def test_review_batch_is_bounded_targeted_and_deterministic(self) -> None:
        arguments = {
            "scope_type": "national",
            "scope_id": None,
            "species_key": None,
            "limit": 5,
        }
        first = self.toolbox.invoke("recommend_next_review_batch", arguments)
        second = self.toolbox.invoke("recommend_next_review_batch", arguments)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "available")
        self.assertEqual(len(first["records"]), 5)
        self.assertFalse(fact(first, "representative")["value"])
        self.assertFalse(fact(first, "ranking_of_people_or_species")["value"])
        self.assertEqual(
            [record["facts"][0]["value"] for record in first["records"]],
            [1, 2, 3, 4, 5],
        )

    def test_review_batch_requires_committed_scope_and_accepted_species(self) -> None:
        lower = self.toolbox.invoke(
            "recommend_next_review_batch",
            {"scope_type": "ibra", "scope_id": "IBRA:SYB", "species_key": None, "limit": 2},
        )
        self.assertEqual(lower["status"], "unavailable")
        missing = self.toolbox.invoke(
            "recommend_next_review_batch",
            {"scope_type": "national", "scope_id": None, "species_key": "bltx:v1:not-real", "limit": 2},
        )
        self.assertEqual(missing["status"], "not_found")

    def test_next_species_supports_each_explicit_workflow_criterion(self) -> None:
        for criterion in (
            "reference_gap",
            "open_conflicts",
            "reviewable_reference",
        ):
            with self.subTest(criterion=criterion):
                result = self.toolbox.invoke(
                    "recommend_next_species", {"criterion": criterion, "limit": 4}
                )
                self.assertEqual(result["status"], "available")
                self.assertEqual(len(result["records"]), 4)
                self.assertFalse(fact(result, "scientific_importance_rank")["value"])

    def test_geographic_contribution_is_self_scoped_and_not_occurrence(self) -> None:
        result = self.toolbox.invoke(
            "explain_geographic_contribution",
            {"scope_type": "national", "scope_id": None},
        )
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(fact(result, "regions_helped")["value"])
        self.assertFalse(fact(result, "potential_contribution_is_occurrence")["value"])
        self.assertFalse(fact(result, "exact_sensitive_region_returned")["value"])

    def test_impact_report_preserves_nulls_and_no_speed_or_rank(self) -> None:
        result = self.toolbox.invoke(
            "prepare_impact_report", {"report_scope": "self"}
        )
        self.assertEqual(result["status"], "unavailable")
        for metric in (
            "reviewed_images",
            "resolved_conflicts",
            "species_helped",
            "regions_helped",
            "control_coverage",
            "expert_contribution",
        ):
            self.assertIsNone(fact(result, metric)["value"])
            self.assertEqual(fact(result, metric)["state"], "unavailable")
        self.assertFalse(fact(result, "ranking_permitted")["value"])
        self.assertFalse(fact(result, "speed_metric_permitted")["value"])

    def test_every_tool_returns_valid_cited_bounded_json(self) -> None:
        cases = {
            "inspect_map_scope": {"scope_type": "national", "scope_id": None},
            "compare_ala_and_flickr": {"scope_type": "national", "scope_id": None, "species_key": None},
            "inspect_species": {"species_key": SPECIES_KEY, "scientific_name": None},
            "inspect_flickr_candidate": {"candidate_id": "candidate:123"},
            "trace_record_evidence": {"record_type": "species", "record_id": SPECIES_KEY},
            "explain_classification": {"classification_id": "classification:123"},
            "inspect_review_consensus": {"item_id": "item:123"},
            "inspect_reviewer_quality": {"subject": "self", "domain_key": None},
            "inspect_pipeline_status": {"pipeline_id": None},
            "inspect_worker_status": {"worker_id": None},
            "recommend_next_review_batch": {"scope_type": "national", "scope_id": None, "species_key": None, "limit": 3},
            "recommend_next_species": {"criterion": "reference_gap", "limit": 3},
            "explain_geographic_contribution": {"scope_type": "national", "scope_id": None},
            "prepare_impact_report": {"report_scope": "self"},
        }
        self.assertEqual(tuple(cases), TOOL_ORDER)
        for name, arguments in cases.items():
            with self.subTest(tool=name):
                result = self.toolbox.invoke(name, arguments)
                encoded = json.dumps(result, sort_keys=True)
                self.assertLessEqual(len(encoded.encode("utf-8")), 65_536)
                self.assertRegex(result["result_fingerprint"], r"^sha256:[0-9a-f]{64}$")
                citation_ids = {
                    citation["artifact_id"] for citation in result["citations"]
                }
                self.assertTrue(citation_ids)
                for row in result["facts"]:
                    self.assertTrue(set(row["citation_ids"]).issubset(citation_ids))
                    self.assertTrue(row["citation_ids"])
                for record in result["records"]:
                    self.assertTrue(set(record["citation_ids"]).issubset(citation_ids))
                    for row in record["facts"]:
                        self.assertTrue(set(row["citation_ids"]).issubset(citation_ids))
                        self.assertTrue(row["citation_ids"])


if __name__ == "__main__":
    unittest.main()
