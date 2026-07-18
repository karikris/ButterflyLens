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
        self.assertEqual(model["explicit_id"], "gpt-5.6-sol")
        self.assertEqual(model["family_alias"], "gpt-5.6")
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
        self.assertEqual(request["max_tool_calls"], 8)
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

    def test_every_current_source_is_official_and_guide_states_repository_gap(self) -> None:
        for url in self.requirements["official_sources"]:
            self.assertTrue(url.startswith("https://developers.openai.com/"), url)
            self.assertIn(url.split("#", 1)[0], self.guide)
        self.assertIn("no OpenAI SDK dependency", self.guide)
        self.assertIn("no OpenAI SDK", self.guide)
        self.assertIn("No live OpenAI API call occurred", self.guide)


if __name__ == "__main__":
    unittest.main()
