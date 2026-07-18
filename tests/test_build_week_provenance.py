from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SESSION_ID = "019f7038-92ae-7021-8318-53ca97648404"
FIRST_COMMIT = "db0657fd432b698c167d559328a57b0befef6664"
AUDITED_COMMIT = "8ebbd37a7169d1b0a38e1f6fb6a3e0aac39bbb97"


def _jsonl(path: str) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in (ROOT / path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _migration_kinds(path: str) -> Counter[str]:
    text = (ROOT / path).read_text(encoding="utf-8")
    return Counter(re.findall(r"^    migration_kind: (\S+)$", text, re.MULTILINE))


class BuildWeekProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.delta = (ROOT / "BUILD_WEEK_DELTA.md").read_text(encoding="utf-8")
        cls.collaboration = (ROOT / "CODEX_COLLABORATION.md").read_text(
            encoding="utf-8"
        )
        cls.decisions = (ROOT / "HUMAN_DECISIONS.md").read_text(encoding="utf-8")
        cls.session_path = ROOT / "provenance" / "sessions" / f"{SESSION_ID}.json"
        cls.session = json.loads(cls.session_path.read_text(encoding="utf-8"))
        cls.commits = _jsonl("provenance/commits.jsonl")
        cls.models = _jsonl("provenance/model_usage.jsonl")

    def test_immutable_baseline_and_audit_range_match_git(self) -> None:
        baseline = (ROOT / "BUILD_WEEK_BASELINE.md").read_text(encoding="utf-8")
        self.assertIn(FIRST_COMMIT, baseline)
        self.assertEqual(_git("rev-list", "--max-parents=0", AUDITED_COMMIT), FIRST_COMMIT)
        self.assertEqual(int(_git("rev-list", "--count", "--no-merges", AUDITED_COMMIT)), 120)
        self.assertEqual(
            set(_git("ls-tree", "--name-only", "-r", FIRST_COMMIT).splitlines()),
            {".gitignore", "README.md", "provenance/githits.jsonl"},
        )
        self.assertEqual(_git("show", "-s", "--format=%T", AUDITED_COMMIT),
                         "5054e8e11aed89b0ce1517f788a033546d158090")

    def test_delta_quantifies_new_work_without_claiming_release(self) -> None:
        normalized = re.sub(r"\s+", " ", self.delta)
        for phrase in (
            "| Non-merge commits | 120 |",
            "581 files changed, 175,782 insertions, 10 deletions",
            "463 accepted species",
            "236,897 selected rows",
            "1,876 deterministic query definitions",
            "2,906 valid decodes",
            "zero human-verified species",
            "release_ready: false",
            "No live GPT-5.6 evaluation or production analyst deployment is claimed.",
        ):
            self.assertIn(phrase, normalized)
        for heading in (
            "New ButterflyLens work",
            "Imported and adapted components",
            "Codex activity and task evidence",
            "GPT-5.6 runtime boundary",
            "Human decisions and review",
            "Test and deployment evidence",
            "Incomplete and excluded work",
        ):
            self.assertIn(f"## {heading}", self.delta)

    def test_commit_and_push_receipts_cover_the_audited_history(self) -> None:
        commit_receipts = [record for record in self.commits if "commit" in record]
        push_receipts = [record for record in self.commits if record.get("event") == "push"]
        self.assertEqual(len(self.commits), 197)
        self.assertEqual(len(commit_receipts), 120)
        self.assertEqual(len(push_receipts), 77)
        audited_history = set(_git("rev-list", "--no-merges", AUDITED_COMMIT).splitlines())
        self.assertEqual({record["commit"] for record in commit_receipts}, audited_history)
        self.assertTrue(all(record["forced"] is False for record in push_receipts))

    def test_model_ledger_records_configuration_not_runtime_identity(self) -> None:
        self.assertEqual(len(self.models), 105)
        self.assertEqual({record["session_id"] for record in self.models}, {SESSION_ID})
        self.assertEqual({record["requested_model"] for record in self.models}, {"gpt-5.6-sol"})
        self.assertEqual(
            {record["requested_reasoning_effort"] for record in self.models}, {"xhigh"}
        )
        self.assertEqual(
            {record["runtime_model_identity_observed"] for record in self.models}, {False}
        )
        self.assertIn("zero model calls", self.delta)
        self.assertIn("zero network calls", self.delta)

    def test_tool_ledgers_and_headroom_receipts_are_exact(self) -> None:
        self.assertEqual(len(_jsonl("provenance/githits.jsonl")), 130)
        self.assertEqual(len(_jsonl("provenance/valyu.jsonl")), 104)
        hashes = {
            "504a09159e203964093d4131",
            "7621abd7c83707de1ab1f539",
            "6f5fcc419eaba18612635562",
        }
        self.assertEqual(set(self.session["headroom"]["compression_hashes"]), hashes)
        for value in hashes:
            self.assertIn(value, self.delta)

    def test_session_receipt_hashes_and_feedback_boundary_are_verifiable(self) -> None:
        self.assertEqual(self.session["schema_version"], "butterflylens-codex-session/v1")
        self.assertEqual(self.session["session_id"], SESSION_ID)
        self.assertEqual(self.session["feedback"]["session_id"], SESSION_ID)
        self.assertFalse(self.session["feedback"]["command_invoked"])
        self.assertFalse(self.session["feedback"]["feedback_submission_observed"])
        self.assertEqual(
            self.session["audit_boundary"]["audited_through_commit"], AUDITED_COMMIT
        )
        self.assertIsNone(
            self.session["audit_boundary"]["containing_finalization_commit"]
        )
        for artifact in self.session["provenance_artifacts"]:
            payload = (ROOT / artifact["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), artifact["sha256"])
        self.assertIn("cannot embed its own full SHA", self.delta)
        self.assertIn("no feedback opening or\n  submission is claimed", self.delta)

    def test_migration_manifests_separate_adaptation_from_one_copy(self) -> None:
        bio_path = "provenance/biominer_migration_manifest.yaml"
        taxa_path = "provenance/taxalens_migration_manifest.yaml"
        self.assertEqual(
            _migration_kinds(bio_path),
            Counter(
                {
                    "artifact_contract": 9,
                    "adapter": 2,
                    "original": 2,
                    "application_boundary_contract": 1,
                    "status_only": 1,
                }
            ),
        )
        self.assertEqual(
            _migration_kinds(taxa_path),
            Counter(
                {
                    "interface_pattern": 12,
                    "shared_contract": 2,
                    "shared_contract_and_algorithm_review": 1,
                    "contract_and_evidence_facade_pattern": 1,
                    "copied": 1,
                }
            ),
        )
        taxa = (ROOT / taxa_path).read_text(encoding="utf-8")
        self.assertIn("taxalens-wikimedia-review-fixture-47248e36944c", taxa)
        self.assertIn("source_license: CC-BY-SA-4.0", taxa)

    def test_parallel_data_and_model_work_remain_excluded(self) -> None:
        for phrase in (
            "0004170-260715120105164.zip",
            "10.15468/dl.7uut3k",
            "was not copied,\nfingerprinted, converted to Parquet, or admitted here",
            "reported active at 50,000 unique images",
            "no Flickr API call was made by this goal",
            "YOLOE and BioCLIP unfinished and skipped",
        ):
            self.assertIn(phrase, self.delta)

    def test_human_decisions_are_not_review_attestations(self) -> None:
        self.assertEqual(len(re.findall(r"^## ", self.decisions, re.MULTILINE)), 15)
        review = (ROOT / "provenance/review_attestations.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("attestations: []", review)
        self.assertIn("ButterflyLens Build Week delta through Task 17.5", review)
        self.assertEqual(self.session["provenance_counts"]["human_review_attestations"], 0)
        self.assertIn("Human direction is not post-change review", self.delta)

    def test_task_corpus_and_test_evidence_counts_are_fixed(self) -> None:
        reports = list((ROOT / "provenance" / "task_reports").glob("*.md"))
        plans = list((ROOT / "provenance" / "task_plans").glob("*.md"))
        self.assertEqual(len(reports), 65)
        self.assertEqual(len(plans), 39)
        counts = self.session["provenance_counts"]
        self.assertEqual(counts["task_reports_after_finalization_patch"], 65)
        self.assertEqual(counts["task_plans_after_finalization_patch"], 39)
        for phrase in (
            "610 Python tests",
            "620 Python tests plus 229 subtests",
            "92 Vitest tests plus three standalone Node tests",
            "45 cached Deno Edge tests",
            "10 Playwright checks",
            "25 schemas",
            "563 text files",
            "582 repository files",
            "567 text files and 586 repository files",
            "53 rights-manifest entries",
            "29649504728",
        ):
            self.assertIn(phrase, self.delta)


if __name__ == "__main__":
    unittest.main()
