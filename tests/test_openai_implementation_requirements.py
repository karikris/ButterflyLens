from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "packages/openai/implementation-requirements.v1.json"
GUIDE = ROOT / "OPENAI_IMPLEMENTATION.md"


class OpenAIImplementationRequirementsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.requirements = json.loads(REQUIREMENTS.read_text(encoding="utf-8"))
        cls.guide = GUIDE.read_text(encoding="utf-8")

    def test_current_model_and_responses_api_are_exact(self) -> None:
        model = self.requirements["model"]
        self.assertEqual(model["explicit_id"], "bounded-model")
        self.assertEqual(model["family_alias"], "Bounded model")
        self.assertEqual(model["reasoning_effort"], "xhigh")
        self.assertEqual(model["response_api"], "/v1/responses")
        self.assertEqual(
            self.requirements["verification_state"],
            "official_docs_verified_no_live_api_call",
        )

    def test_transport_is_server_only_and_private_by_default(self) -> None:
        architecture = self.requirements["architecture"]
        request = self.requirements["request_policy"]
        privacy = self.requirements["security_privacy"]
        self.assertFalse(architecture["browser_openai_access"])
        self.assertFalse(architecture["openai_built_in_tools_enabled"])
        self.assertFalse(architecture["remote_mcp_enabled"])
        self.assertFalse(request["store"])
        self.assertFalse(request["parallel_tool_calls"])
        self.assertFalse(privacy["api_key_in_browser"])
        self.assertFalse(privacy["api_key_in_database"])
        self.assertFalse(privacy["openai_response_storage"])

    def test_strict_schema_requirements_are_complete(self) -> None:
        policy = self.requirements["schema_policy"]
        for field in (
            "function_tools_strict",
            "final_text_format_strict",
            "all_object_properties_required",
            "optional_fields_use_nullable_type",
            "server_validates_tool_arguments",
            "server_validates_tool_outputs",
            "server_validates_final_output",
        ):
            self.assertTrue(policy[field], field)
        self.assertFalse(policy["additional_properties"])

    def test_budgets_and_failure_states_are_bounded(self) -> None:
        request = self.requirements["request_policy"]
        self.assertEqual(request["application_max_tool_calls"], 8)
        self.assertEqual(request["max_tool_loop_iterations"], 6)
        self.assertEqual(request["max_output_tokens"], 1800)
        self.assertEqual(request["per_tool_timeout_seconds"], 10)
        self.assertEqual(request["transient_tool_retries"], 1)
        handling = self.requirements["response_handling"]
        self.assertEqual(handling["budget_exhaustion_result"], "bounded_incomplete")
        self.assertTrue(handling["refusal_is_first_class"])
        self.assertTrue(handling["incomplete_details_are_first_class"])

    def test_evidence_citations_and_no_memory_guessing_are_mandatory(self) -> None:
        evidence = self.requirements["evidence_policy"]
        self.assertTrue(evidence["artifact_citations_required_for_factual_claims"])
        self.assertEqual(
            set(evidence["citation_fields"]),
            {"artifact_id", "repository", "commit", "path", "fingerprint"},
        )
        self.assertEqual(evidence["missing_evidence_result"], "unavailable_not_zero")
        self.assertFalse(evidence["species_guessing_from_model_memory"])
        self.assertFalse(evidence["scientific_claim_authority"])

    def test_evaluation_contract_covers_agent_nondeterminism(self) -> None:
        evaluation = self.requirements["evaluation_policy"]
        self.assertGreaterEqual(evaluation["minimum_cases"], 40)
        dimensions = set(evaluation["dimensions"])
        for required in (
            "tool_selection",
            "tool_argument_precision",
            "schema_adherence",
            "artifact_citation_completeness",
            "unsupported_claim_refusal",
            "missing_evidence_abstention",
            "budget_compliance",
            "privacy_boundary",
            "replay_label_integrity",
        ):
            self.assertIn(required, dimensions)
        current = evaluation["current_suite"]
        self.assertEqual(current["case_count"], 48)
        self.assertEqual(current["category_count"], 12)
        self.assertEqual(current["deterministic_oracle_state"], "passed")
        self.assertEqual(current["live_model_state"], "not_run")
        self.assertIsNone(current["live_unsupported_claim_rate"])
        self.assertIsNone(current["live_tool_selection_accuracy"])
        self.assertIsNone(current["live_final_answer_accuracy"])
        self.assertFalse(current["scripted_output_reported_as_model_run"])
        for artifact in (
            current["dataset_artifact"],
            current["result_artifact"],
            current["trace_schema"],
        ):
            self.assertTrue((ROOT / artifact).is_file(), artifact)

    def test_replay_is_non_model_offline_and_fingerprint_grounded(self) -> None:
        replay = self.requirements["replay_policy"]
        self.assertEqual(replay["mode"], "replayed")
        self.assertFalse(replay["model_invoked"])
        self.assertEqual(replay["network_calls"], 0)
        self.assertEqual(replay["response_calls"], 0)
        self.assertEqual(replay["runtime_tool_calls"], 0)
        self.assertTrue(replay["exact_stored_tool_calls_and_outputs"])
        self.assertTrue(replay["artifact_citations_preserved"])
        self.assertEqual(
            replay["result_trace_and_catalogue_fingerprints"], "rfc8785_sha256"
        )
        self.assertFalse(replay["multi_turn_simulation"])
        self.assertTrue(replay["model_identity_omitted_when_not_invoked"])

    def test_every_current_source_is_official_and_guide_states_repository_state(self) -> None:
        normalized_guide = " ".join(self.guide.split())
        for url in self.requirements["official_sources"]:
            self.assertTrue(url.startswith("https://developers.openai.com/"), url)
            self.assertIn(url.split("#", 1)[0], self.guide)
        self.assertIn("exact SDK pins", self.guide)
        self.assertIn("no live OpenAI API call", normalized_guide)
        self.assertIn("no model authored it", self.guide)
        self.assertIn("live-model evaluation remains not run", normalized_guide)


if __name__ == "__main__":
    unittest.main()
