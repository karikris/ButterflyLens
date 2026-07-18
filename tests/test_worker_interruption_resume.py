from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))
sys.path.insert(0, str(ROOT / "services/worker/python"))

from butterflylens_worker import (  # noqa: E402
    CommittedWorkJournal,
    RestartError,
    WorkItem,
    build_public_offline_projection,
    build_resume_plan,
)


NOW = datetime(2026, 7, 18, 1, 0, tzinfo=timezone.utc)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def item(kind: str, name: str) -> WorkItem:
    return WorkItem(kind, digest(name))  # type: ignore[arg-type]


def acknowledgement(output: str) -> dict[str, object]:
    return {"storage_state": "persisted", "output_fingerprint": output}


class WorkerInterruptionResumeTests(unittest.TestCase):
    def test_restart_reuses_every_committed_work_class_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "journal.jsonl"
            first_process = CommittedWorkJournal(path)
            work = [
                item("api_call", "physical-request"),
                item("download", "source-media"),
                item("embedding", "historical-content-model-pair"),
                item("artifact_commit", "immutable-artifact"),
            ]
            outputs = [digest(f"output:{index}") for index in range(len(work))]
            for work_item, output in zip(work, outputs, strict=True):
                first_process.record_commit(
                    work_item,
                    output_fingerprint=output,
                    committed_at=NOW,
                    acknowledgement=acknowledgement(output),
                )

            restarted_process = CommittedWorkJournal(path)
            plan = build_resume_plan(
                work,
                lease_fingerprint=digest("admitted-lease"),
                checkpoint_fingerprint=digest("admitted-checkpoint"),
                journal=restarted_process,
            )
            line_count = len(path.read_text().splitlines())
            for work_item, output in zip(work, outputs, strict=True):
                restarted_process.record_commit(
                    work_item,
                    output_fingerprint=output,
                    committed_at=NOW + timedelta(minutes=1),
                    acknowledgement=acknowledgement(output),
                )
            final_line_count = len(path.read_text().splitlines())

        self.assertEqual(plan["execute_count"], 0)
        self.assertEqual(plan["reuse_count"], 4)
        self.assertEqual(
            [row["action"] for row in plan["decisions"]],
            ["reuse_committed"] * 4,
        )
        self.assertEqual(line_count, 4)
        self.assertEqual(final_line_count, 4)

    def test_interrupted_uncommitted_work_remains_explicitly_executable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            journal = CommittedWorkJournal(Path(temporary) / "journal.jsonl")
            committed = item("download", "committed")
            pending = item("download", "interrupted-before-commit")
            output = digest("stored")
            journal.record_commit(
                committed,
                output_fingerprint=output,
                committed_at=NOW,
                acknowledgement=acknowledgement(output),
            )
            plan = build_resume_plan(
                [committed, pending],
                lease_fingerprint=digest("admitted-lease"),
                checkpoint_fingerprint=digest("checkpoint"),
                journal=CommittedWorkJournal(journal.path),
            )
        self.assertEqual(plan["reuse_count"], 1)
        self.assertEqual(plan["execute_count"], 1)

    def test_conflicting_recommit_and_incomplete_acknowledgement_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            journal = CommittedWorkJournal(Path(temporary) / "journal.jsonl")
            work = item("artifact_commit", "artifact")
            output = digest("one")
            with self.assertRaisesRegex(RestartError, "acknowledgement"):
                journal.record_commit(
                    work,
                    output_fingerprint=output,
                    committed_at=NOW,
                    acknowledgement={},
                )
            journal.record_commit(
                work,
                output_fingerprint=output,
                committed_at=NOW,
                acknowledgement=acknowledgement(output),
            )
            other = digest("other")
            with self.assertRaisesRegex(RestartError, "conflicting output"):
                journal.record_commit(
                    work,
                    output_fingerprint=other,
                    committed_at=NOW,
                    acknowledgement=acknowledgement(other),
                )

    def test_stale_worker_instances_cannot_duplicate_artifact_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "journal.jsonl"
            first = CommittedWorkJournal(path)
            stale = CommittedWorkJournal(path)
            work = item("artifact_commit", "same-immutable-artifact")
            output = digest("same-output")
            first_record = first.record_commit(
                work,
                output_fingerprint=output,
                committed_at=NOW,
                acknowledgement=acknowledgement(output),
            )
            stale_record = stale.record_commit(
                work,
                output_fingerprint=output,
                committed_at=NOW + timedelta(minutes=1),
                acknowledgement=acknowledgement(output),
            )
            self.assertEqual(stale_record, first_record)
            self.assertEqual(len(path.read_text().splitlines()), 1)

    def test_tampered_journal_never_authorizes_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "journal.jsonl"
            journal = CommittedWorkJournal(path)
            work = item("api_call", "request")
            output = digest("response")
            journal.record_commit(
                work,
                output_fingerprint=output,
                committed_at=NOW,
                acknowledgement=acknowledgement(output),
            )
            record = json.loads(path.read_text())
            record["output_fingerprint"] = digest("tampered")
            path.write_text(json.dumps(record) + "\n")
            path.chmod(0o600)
            with self.assertRaisesRegex(RestartError, "fingerprint mismatch"):
                CommittedWorkJournal(path)

    def test_offline_worker_keeps_committed_live_and_submitted_data_queryable(self) -> None:
        submitted = {
            "snapshot_id": "submitted:build-week",
            "mode": "submitted",
            "artifact_fingerprint": digest("submitted"),
            "query_uri": "/api/snapshots/submitted",
        }
        live = {
            "snapshot_id": "live:committed:41",
            "mode": "live",
            "artifact_fingerprint": digest("live"),
            "query_uri": "/api/snapshots/live/41",
        }
        projection = build_public_offline_projection(
            submitted_snapshot=submitted,
            committed_live_snapshot=live,
            heartbeat_observed_at=NOW - timedelta(minutes=30),
            as_of=NOW,
            stale_after=timedelta(minutes=5),
        )
        self.assertEqual(projection["worker_status"], "offline")
        self.assertTrue(projection["site_available"])
        self.assertTrue(projection["committed_data_queryable"])
        self.assertTrue(projection["live_is_stale"])
        self.assertEqual(projection["current_snapshot"], live)
        self.assertEqual(projection["submitted_snapshot"], submitted)

    def test_restart_contract_executes_no_provider_or_model_code(self) -> None:
        source = (
            ROOT / "services/worker/python/butterflylens_worker/restart.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "requests",
            "httpx",
            "aiohttp",
            "urllib",
            "torch",
            "from_pretrained",
            "load_state_dict",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
