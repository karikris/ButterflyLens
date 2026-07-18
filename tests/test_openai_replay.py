from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

from jsonschema import Draft202012Validator
import rfc8785


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "packages" / "openai" / "python"
SCRIPTS = ROOT / "scripts"
CATALOGUE_PATH = ROOT / "packages" / "openai" / "submitted-replays.v1.json"
SCHEMA_PATH = ROOT / "packages" / "openai" / "replay-catalog.schema.json"
sys.path.insert(0, str(PACKAGE_ROOT))
sys.path.insert(0, str(SCRIPTS))

from butterflylens_openai import EvidenceToolbox  # noqa: E402
import build_openai_replay  # noqa: E402


def fingerprint(value: object) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(value)).hexdigest()


class OpenAIReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalogue = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.toolbox = EvidenceToolbox(ROOT)

    def test_catalogue_matches_strict_generated_schema(self) -> None:
        Draft202012Validator(
            self.schema,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        ).validate(self.catalogue)
        self.assertEqual(
            self.catalogue["schema_version"],
            "butterflylens-analyst-replay-catalog:v1.0.0",
        )
        self.assertEqual(self.catalogue["mode"], "replayed")
        self.assertEqual(len(self.catalogue["cases"]), 3)

    def test_generator_replay_is_byte_identical(self) -> None:
        expected_schema = build_openai_replay.replay_schema()
        expected_catalogue = build_openai_replay.build_catalog()
        self.assertEqual(
            SCHEMA_PATH.read_text(encoding="utf-8"),
            json.dumps(expected_schema, indent=2, sort_keys=True) + "\n",
        )
        self.assertEqual(
            CATALOGUE_PATH.read_text(encoding="utf-8"),
            json.dumps(expected_catalogue, indent=2, sort_keys=True) + "\n",
        )

    def test_source_is_immutable_and_truthfully_non_model_non_network(self) -> None:
        source = self.catalogue["source"]
        self.assertEqual(source["repository"], "karikris/ButterflyLens")
        self.assertEqual(
            source["implementation_commit"],
            "efcf45890d6da5e958f4d46240d3e8c00be8e68b",
        )
        self.assertEqual(
            source["tool_artifact_commit"],
            "f9b96814f335684cf311b70b622e2cade0188b9b",
        )
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

    def test_stored_calls_and_outputs_exactly_replay_deterministic_tools(self) -> None:
        call_ids: set[str] = set()
        for case in self.catalogue["cases"]:
            for expected_sequence, trace in enumerate(case["tool_trace"], 1):
                self.assertEqual(trace["sequence"], expected_sequence)
                self.assertNotIn(trace["call_id"], call_ids)
                call_ids.add(trace["call_id"])
                self.assertEqual(
                    trace["output"],
                    self.toolbox.invoke(trace["name"], trace["arguments"]),
                )
                self.assertEqual(trace["output"]["tool_name"], trace["name"])

    def test_fingerprints_cover_every_result_trace_and_catalogue(self) -> None:
        for case in self.catalogue["cases"]:
            for trace in case["tool_trace"]:
                output = dict(trace["output"])
                observed = output.pop("result_fingerprint")
                self.assertEqual(observed, fingerprint(output))
            self.assertEqual(
                case["response"]["replay"]["trace_fingerprint"],
                fingerprint(case["tool_trace"]),
            )
        payload = dict(self.catalogue)
        observed = payload.pop("catalog_fingerprint")
        self.assertEqual(observed, fingerprint(payload))

    def test_replay_claims_preserve_exact_trace_citations(self) -> None:
        replay_ids: set[str] = set()
        questions: set[str] = set()
        for case in self.catalogue["cases"]:
            self.assertNotIn(case["replay_id"], replay_ids)
            replay_ids.add(case["replay_id"])
            for question in case["accepted_questions"]:
                normalized = " ".join(question.casefold().split())
                self.assertNotIn(normalized, questions)
                questions.add(normalized)
            exact_citations: dict[str, dict[str, object]] = {}
            for trace in case["tool_trace"]:
                for citation in trace["output"]["citations"]:
                    exact_citations.setdefault(citation["artifact_id"], citation)
            response = case["response"]
            self.assertEqual(response["mode"], "replayed")
            self.assertEqual(response["citations"], list(exact_citations.values()))
            self.assertEqual(
                response["tools_used"],
                list(dict.fromkeys(trace["name"] for trace in case["tool_trace"])),
            )
            self.assertIs(response["replay"]["model_invoked"], False)
            self.assertEqual(response["replay"]["response_calls"], 0)
            self.assertEqual(
                response["replay"]["tool_calls"], len(case["tool_trace"])
            )
            self.assertNotIn("model", response)
            for claim in response["claims"]:
                self.assertTrue(set(claim["citation_ids"]) <= set(exact_citations))

    def test_catalogue_has_only_the_three_explicit_judge_questions(self) -> None:
        self.assertEqual(
            [case["accepted_questions"][0] for case in self.catalogue["cases"]],
            [
                "What evidence is available for Acraea andromacha?",
                "Can ALA and Flickr counts be compared yet?",
                "Which species should receive the next reference review?",
            ],
        )
        text = CATALOGUE_PATH.read_text(encoding="utf-8")
        self.assertIn("No GPT-5.6 or other model was invoked", text)
        self.assertNotIn("mode\": \"live", text)


if __name__ == "__main__":
    unittest.main()
