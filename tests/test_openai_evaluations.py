from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "packages" / "openai" / "python"
SCRIPTS = ROOT / "scripts"
OPENAI_ROOT = ROOT / "packages" / "openai"
sys.path.insert(0, str(PACKAGE_ROOT))
sys.path.insert(0, str(SCRIPTS))

from butterflylens_openai import (  # noqa: E402
    EvidenceToolbox,
    EvaluationContractError,
    TOOL_ORDER,
    grade_trace,
)
from butterflylens_openai.evaluation import (  # noqa: E402
    MODEL_ID,
    REASONING_EFFORT,
    TRACE_SCHEMA_VERSION,
    assert_required_facts,
    fingerprint,
)
import build_openai_evaluations  # noqa: E402


SUITE_PATH = OPENAI_ROOT / "analyst-eval-cases.v1.json"
SUITE_SCHEMA_PATH = OPENAI_ROOT / "analyst-eval-cases.schema.json"
RESULT_PATH = OPENAI_ROOT / "agent_evaluation.json"
RESULT_SCHEMA_PATH = OPENAI_ROOT / "agent-evaluation.schema.json"
TRACE_SCHEMA_PATH = OPENAI_ROOT / "analyst-live-eval-trace.schema.json"
RESPONSE_SCHEMA_PATH = OPENAI_ROOT / "analyst-response.schema.json"


class OpenAIEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
        cls.suite_schema = json.loads(
            SUITE_SCHEMA_PATH.read_text(encoding="utf-8")
        )
        cls.result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
        cls.result_schema = json.loads(
            RESULT_SCHEMA_PATH.read_text(encoding="utf-8")
        )
        cls.trace_schema = json.loads(
            TRACE_SCHEMA_PATH.read_text(encoding="utf-8")
        )
        cls.response_schema = json.loads(
            RESPONSE_SCHEMA_PATH.read_text(encoding="utf-8")
        )
        cls.toolbox = EvidenceToolbox(ROOT)

    def test_generated_suite_and_result_match_strict_schemas(self) -> None:
        Draft202012Validator(
            self.suite_schema,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        ).validate(self.suite)
        Draft202012Validator(
            self.result_schema,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        ).validate(self.result)

    def test_generator_is_byte_identical(self) -> None:
        suite_schema, result_schema, trace_schema, suite, result = (
            build_openai_evaluations.build_documents()
        )
        expected = {
            SUITE_SCHEMA_PATH: suite_schema,
            RESULT_SCHEMA_PATH: result_schema,
            TRACE_SCHEMA_PATH: trace_schema,
            SUITE_PATH: suite,
            RESULT_PATH: result,
        }
        for path, document in expected.items():
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                json.dumps(document, indent=2, sort_keys=True) + "\n",
                path,
            )

    def test_suite_and_result_fingerprints_cover_complete_documents(self) -> None:
        suite_payload = dict(self.suite)
        observed_suite = suite_payload.pop("suite_fingerprint")
        self.assertEqual(observed_suite, fingerprint(suite_payload))
        result_payload = dict(self.result)
        observed_result = result_payload.pop("result_fingerprint")
        self.assertEqual(observed_result, fingerprint(result_payload))
        self.assertEqual(self.result["suite_fingerprint"], observed_suite)

    def test_exact_representative_category_and_dimension_coverage(self) -> None:
        self.assertEqual(self.suite["case_count"], 48)
        self.assertEqual(self.suite["category_count"], 12)
        counts: dict[str, int] = {}
        questions: set[str] = set()
        case_ids: set[str] = set()
        for case in self.suite["cases"]:
            counts[case["category"]] = counts.get(case["category"], 0) + 1
            self.assertNotIn(case["case_id"], case_ids)
            case_ids.add(case["case_id"])
            normalized_question = " ".join(case["question"].casefold().split())
            self.assertNotIn(normalized_question, questions)
            questions.add(normalized_question)
        self.assertEqual(set(counts), set(build_openai_evaluations.CATEGORIES))
        self.assertEqual(set(counts.values()), {4})
        self.assertEqual(
            set(self.suite["dimension_coverage"]),
            set(build_openai_evaluations.DIMENSIONS),
        )
        self.assertTrue(
            all(self.suite["dimension_coverage"].values()),
            "every frozen evaluation dimension requires coverage",
        )

    def test_every_deterministic_tool_is_represented(self) -> None:
        observed = {
            case["expected_tool_call"]["name"] for case in self.suite["cases"]
        }
        self.assertEqual(observed, set(TOOL_ORDER))

    def test_every_oracle_reinvokes_with_exact_result_and_facts(self) -> None:
        for case in self.suite["cases"]:
            call = case["expected_tool_call"]
            result = self.toolbox.invoke(call["name"], call["arguments"])
            self.assertEqual(result["status"], case["oracle"]["result_status"])
            self.assertEqual(
                result["result_fingerprint"],
                case["oracle"]["result_fingerprint"],
            )
            self.assertEqual(
                [citation["artifact_id"] for citation in result["citations"]],
                case["oracle"]["citation_ids"],
            )
            assert_required_facts(
                case["case_id"], result, case["required_facts"]
            )

    def test_source_commits_are_immutable_and_no_model_run_is_claimed(self) -> None:
        source = self.suite["source"]
        self.assertEqual(source["model_target"], MODEL_ID)
        self.assertEqual(source["reasoning_effort_target"], REASONING_EFFORT)
        self.assertIs(source["model_invoked"], False)
        self.assertEqual(source["network_calls"], 0)
        for commit in (
            source["implementation_commit"],
            source["tool_artifact_commit"],
        ):
            subprocess.run(
                ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
                cwd=ROOT,
                check=True,
                capture_output=True,
            )
        self.assertEqual(
            self.result["overall_status"],
            "deterministic_gate_passed_live_model_not_run",
        )
        self.assertIs(self.result["execution"]["model_invoked"], False)
        self.assertIsNone(self.result["metrics"]["live_unsupported_claim_rate"])
        self.assertIsNone(self.result["metrics"]["live_tool_selection_accuracy"])
        self.assertIsNone(self.result["metrics"]["live_final_answer_accuracy"])

    def test_all_48_offline_receipts_pass_without_model_output(self) -> None:
        totals = self.result["totals"]
        self.assertEqual(totals["cases"], 48)
        self.assertEqual(totals["deterministic_passed"], 48)
        self.assertEqual(totals["deterministic_failed"], 0)
        self.assertEqual(totals["live_model_run"], 0)
        self.assertEqual(len(self.result["case_results"]), 48)
        self.assertTrue(
            all(
                row["deterministic_status"] == "passed"
                and row["live_model_status"] == "not_run"
                for row in self.result["case_results"]
            )
        )

    def test_synthetic_complete_trace_exercises_grader_without_model_claim(self) -> None:
        trace = self._synthetic_trace()
        report = grade_trace(
            repo_root=ROOT,
            suite=self.suite,
            trace=trace,
            trace_schema=self.trace_schema,
            response_schema=self.response_schema,
        )
        self.assertEqual(
            report["overall_status"],
            "synthetic_grader_self_test_passed_no_model",
        )
        self.assertIs(report["model_invoked"], False)
        self.assertEqual(report["case_count"], 48)
        self.assertEqual(report["passed"], 48)
        self.assertEqual(report["failed"], 0)
        self.assertIsNone(report["unsupported_claim_rate"])

    def test_no_network_cli_grades_a_complete_trace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            trace_path = Path(directory) / "trace.json"
            result_path = Path(directory) / "result.json"
            trace_path.write_text(
                json.dumps(self._synthetic_trace()), encoding="utf-8"
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "grade_openai_evaluation.py"),
                    str(trace_path),
                    "--output",
                    str(result_path),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(
                report["overall_status"],
                "synthetic_grader_self_test_passed_no_model",
            )
            self.assertIs(report["model_invoked"], False)

    def test_grader_rejects_wrong_tool_citation_and_incomplete_direct_claim(self) -> None:
        wrong_tool = self._synthetic_trace()
        wrong_tool["cases"][0]["tool_calls"][0]["name"] = "inspect_species"
        self._refingerprint(wrong_tool)
        self._assert_grade_fails(wrong_tool)

        changed_citation = self._synthetic_trace()
        changed_citation["cases"][0]["response"]["citations"][0][
            "path"
        ] = "invented/path.json"
        self._refingerprint(changed_citation)
        self._assert_grade_fails(changed_citation)

        direct_incomplete = self._synthetic_trace()
        index = self._case_index("map_impact_03")
        direct_incomplete["cases"][index]["response"]["claims"][0][
            "evidence_state"
        ] = "direct"
        self._refingerprint(direct_incomplete)
        self._assert_grade_fails(direct_incomplete)

    def test_grader_rejects_fabricated_metric_taxon_and_governance_claim(self) -> None:
        metric = self._synthetic_trace()
        index = self._case_index("fabricated_metric_45")
        metric["cases"][index]["response"]["summary"] = (
            "The unavailable difference is 999."
        )
        self._refingerprint(metric)
        self._assert_grade_fails(metric)

        taxon = self._synthetic_trace()
        index = self._case_index("model_memory_taxon_42")
        taxon["cases"][index]["response"]["summary"] = (
            "The invented key is bltx:v1:deadbeef."
        )
        self._refingerprint(taxon)
        self._assert_grade_fails(taxon)

        cultural_name = self._synthetic_trace()
        index = self._case_index("first_nations_name_37")
        cultural_name["cases"][index]["response"]["summary"] = (
            "The First Nations name is called InventedName."
        )
        self._refingerprint(cultural_name)
        self._assert_grade_fails(cultural_name)

    def test_grader_rejects_worker_and_licence_inference(self) -> None:
        worker = self._synthetic_trace()
        index = self._case_index("worker_offline_25")
        worker["cases"][index]["response"]["summary"] = "The M5 is offline."
        self._refingerprint(worker)
        self._assert_grade_fails(worker)

        licence = self._synthetic_trace()
        index = self._case_index("licence_restriction_33")
        licence["cases"][index]["response"]["summary"] = (
            "The licence permits commercial use."
        )
        self._refingerprint(licence)
        self._assert_grade_fails(licence)

    def test_grader_rejects_fingerprint_and_false_live_provenance(self) -> None:
        changed = self._synthetic_trace()
        changed["cases"][0]["response"]["summary"] = "Changed after hashing."
        self._assert_grade_fails(changed)

        false_live = self._synthetic_trace()
        false_live["execution"]["run_kind"] = "recorded_live_openai"
        self._refingerprint(false_live)
        self._assert_grade_fails(false_live)

    def _synthetic_trace(self) -> dict[str, object]:
        cases: list[dict[str, object]] = []
        for case in self.suite["cases"]:
            call = case["expected_tool_call"]
            output = self.toolbox.invoke(call["name"], call["arguments"])
            citations = deepcopy(output["citations"])
            evidence_state = (
                "direct"
                if case["expected_live_response_state"] == "completed"
                else "unavailable"
            )
            response = {
                "schema_version": "butterflylens-analyst-response:v1.0.0",
                "mode": "live",
                "response_state": case["expected_live_response_state"],
                "summary": output["summary"],
                "claims": [
                    {
                        "claim_id": "claim_1",
                        "statement": output["summary"],
                        "evidence_state": evidence_state,
                        "citation_ids": [
                            citation["artifact_id"] for citation in citations
                        ],
                    }
                ],
                "citations": citations,
                "limitations": [
                    "Synthetic grader fixture only; no model was invoked."
                ],
                "tools_used": [call["name"]],
                "model": {"id": MODEL_ID, "reasoning_effort": REASONING_EFFORT},
                "usage": {
                    "response_calls": 2,
                    "tool_calls": 1,
                    "budget_state": "within_budget",
                },
            }
            cases.append(
                {
                    "case_id": case["case_id"],
                    "tool_calls": [
                        {
                            "name": call["name"],
                            "arguments": deepcopy(call["arguments"]),
                            "output": output,
                        }
                    ],
                    "response": response,
                }
            )
        trace: dict[str, object] = {
            "schema_version": TRACE_SCHEMA_VERSION,
            "suite_fingerprint": self.suite["suite_fingerprint"],
            "run_id": "synthetic:grader-self-test",
            "recorded_at": "2026-07-18T07:41:46Z",
            "execution": {
                "run_kind": "synthetic_grader_fixture",
                "model_invoked": False,
                "network_calls": 0,
            },
            "model": {"id": MODEL_ID, "reasoning_effort": REASONING_EFFORT},
            "cases": cases,
        }
        trace["trace_fingerprint"] = fingerprint(trace)
        return trace

    def _case_index(self, case_id: str) -> int:
        return next(
            index
            for index, case in enumerate(self.suite["cases"])
            if case["case_id"] == case_id
        )

    @staticmethod
    def _refingerprint(trace: dict[str, object]) -> None:
        trace.pop("trace_fingerprint", None)
        trace["trace_fingerprint"] = fingerprint(trace)

    def _assert_grade_fails(self, trace: dict[str, object]) -> None:
        with self.assertRaises(EvaluationContractError):
            grade_trace(
                repo_root=ROOT,
                suite=self.suite,
                trace=trace,
                trace_schema=self.trace_schema,
                response_schema=self.response_schema,
            )


if __name__ == "__main__":
    unittest.main()
