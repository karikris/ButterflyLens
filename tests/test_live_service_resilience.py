from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))
sys.path.insert(0, str(ROOT / "services/worker/python"))

from butterflylens_worker import (  # noqa: E402
    INCIDENT_KINDS,
    CommittedWorkJournal,
    IncidentPlanningError,
    WorkItem,
    build_incident_fallback_plan,
    build_public_offline_projection,
    build_resume_plan,
    verify_checkpoint_file,
)


NOW = datetime(2026, 7, 18, 9, 30, tzinfo=timezone.utc)
ARTIFACT = hashlib.sha256(b"last committed artifact").hexdigest()
CHECKPOINT = hashlib.sha256(b"verified checkpoint").hexdigest()


def plan(kind: str, **overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "observed_at": NOW,
        "last_committed_artifact_fingerprint": ARTIFACT,
    }
    values.update(overrides)
    return build_incident_fallback_plan(kind, **values)  # type: ignore[arg-type]


class LiveServiceResilienceTests(unittest.TestCase):
    def assert_common_safety(self, incident: dict[str, object]) -> None:
        durability = incident["durability"]
        self.assertIsInstance(durability, dict)
        assert isinstance(durability, dict)
        self.assertTrue(durability["last_committed_artifact_queryable"])
        self.assertTrue(durability["submitted_snapshot_queryable"])
        self.assertTrue(durability["local_sources_retained"])
        self.assertTrue(durability["committed_journal_append_only"])
        self.assertFalse(durability["duplicate_work_allowed"])
        self.assertFalse(incident["side_effects_executed"])
        self.assertFalse(incident["model_execution_occurred"])
        self.assertFalse(incident["scientific_claim_allowed"])
        self.assertEqual(
            incident["model_components"],
            {"yoloe": "unfinished", "bioclip": "unfinished"},
        )

    def test_m5_sleep_keeps_committed_and_submitted_site_state(self) -> None:
        incident = plan(
            "m5_sleep",
            checkpoint_fingerprint=CHECKPOINT,
            checkpoint_verified=True,
        )
        self.assertEqual(incident["worker_state"], "offline")
        self.assertEqual(incident["stage_action"], "pause_all_worker_stages")
        self.assertIn("worker_execution", incident["blocked_actions"])
        self.assertIn("model_execution", incident["blocked_actions"])
        projection = build_public_offline_projection(
            submitted_snapshot={
                "snapshot_id": "submitted:build-week",
                "mode": "submitted",
                "artifact_fingerprint": hashlib.sha256(b"submitted").hexdigest(),
                "query_uri": "/api/snapshots/submitted",
            },
            committed_live_snapshot={
                "snapshot_id": "live:committed:41",
                "mode": "live",
                "artifact_fingerprint": ARTIFACT,
                "query_uri": "/api/snapshots/live/41",
            },
            heartbeat_observed_at=NOW - timedelta(minutes=30),
            as_of=NOW,
            stale_after=timedelta(minutes=5),
        )
        self.assertEqual(projection["worker_status"], "offline")
        self.assertTrue(projection["site_available"])
        self.assertEqual(
            projection["current_snapshot"]["artifact_fingerprint"], ARTIFACT
        )
        self.assert_common_safety(incident)

    def test_network_outage_pauses_every_outbound_boundary_without_retry(self) -> None:
        incident = plan("network_outage")
        self.assertEqual(
            incident["stage_action"], "pause_network_dependent_stages"
        )
        self.assertEqual(
            set(incident["blocked_actions"]),
            {"flickr_requests", "b2_writes", "supabase_writes", "immediate_retry"},
        )
        self.assertEqual(
            incident["resume_condition"],
            "bounded_health_probe_after_scheduler_backoff",
        )
        self.assert_common_safety(incident)

    def test_flickr_outage_freezes_only_governed_provider_work(self) -> None:
        incident = plan("flickr_outage")
        self.assertEqual(incident["affected_boundary"], "flickr")
        self.assertEqual(incident["stage_action"], "pause_flickr_stages")
        self.assertIn("flickr_requests", incident["blocked_actions"])
        self.assertIn("unbounded_retry", incident["blocked_actions"])
        self.assertIn("credential_rotation", incident["blocked_actions"])
        self.assert_common_safety(incident)

    def test_b2_outage_retains_sources_until_durable_acknowledgement(self) -> None:
        incident = plan("b2_outage")
        self.assertEqual(
            incident["stage_action"], "pause_artifact_commit_and_publication"
        )
        self.assertEqual(
            incident["resume_condition"], "durable_write_acknowledged"
        )
        self.assertIn("local_source_deletion", incident["blocked_actions"])
        self.assertIn("ambiguous_write_retry", incident["blocked_actions"])
        self.assert_common_safety(incident)

    def test_supabase_outage_keeps_static_site_and_local_journal_authoritative(self) -> None:
        incident = plan("supabase_outage")
        self.assertEqual(incident["monitoring_state"], "unavailable")
        self.assertEqual(
            incident["checkpoint_action"], "retain_local_append_only_journals"
        )
        self.assertIn("supabase_writes", incident["blocked_actions"])
        self.assertIn(
            "fabricated_remote_acknowledgement", incident["blocked_actions"]
        )
        self.assert_common_safety(incident)

    def test_model_crash_is_a_no_model_policy_simulation(self) -> None:
        incident = plan(
            "model_crash",
            checkpoint_fingerprint=CHECKPOINT,
            checkpoint_verified=True,
        )
        self.assertEqual(incident["affected_boundary"], "model_runtime")
        self.assertIn("model_execution", incident["blocked_actions"])
        self.assertIn("model_evidence_publication", incident["blocked_actions"])
        self.assertIn("fallback_identity_claim", incident["blocked_actions"])
        self.assert_common_safety(incident)

    def test_corrupted_checkpoint_is_rejected_then_only_uncommitted_work_rebuilds(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkpoint_path = root / "checkpoint.bin"
            checkpoint_path.write_bytes(b"verified checkpoint")
            verification = verify_checkpoint_file(
                checkpoint_path,
                expected_sha256=CHECKPOINT,
            )
            self.assertTrue(verification["verified"])
            with self.assertRaisesRegex(IncidentPlanningError, "byte ceiling"):
                verify_checkpoint_file(
                    checkpoint_path,
                    expected_sha256=CHECKPOINT,
                    max_bytes=4,
                )
            symlink = root / "checkpoint-link.bin"
            symlink.symlink_to(checkpoint_path)
            with self.assertRaisesRegex(IncidentPlanningError, "unsafe"):
                verify_checkpoint_file(symlink, expected_sha256=CHECKPOINT)
            checkpoint_path.write_bytes(b"corrupted checkpoint")
            with self.assertRaisesRegex(IncidentPlanningError, "checksum mismatch"):
                verify_checkpoint_file(
                    checkpoint_path,
                    expected_sha256=CHECKPOINT,
                )

            journal = CommittedWorkJournal(root / "committed-work.jsonl")
            committed = WorkItem("download", hashlib.sha256(b"input").hexdigest())
            output = hashlib.sha256(b"output").hexdigest()
            journal.record_commit(
                committed,
                output_fingerprint=output,
                committed_at=NOW,
                acknowledgement={
                    "storage_state": "persisted",
                    "output_fingerprint": output,
                },
            )
            resumed = build_resume_plan(
                [committed],
                lease_fingerprint=hashlib.sha256(b"new lease").hexdigest(),
                checkpoint_fingerprint=hashlib.sha256(b"new checkpoint").hexdigest(),
                journal=CommittedWorkJournal(journal.path),
            )

        incident = plan(
            "corrupted_checkpoint",
            checkpoint_fingerprint=CHECKPOINT,
            checkpoint_verified=False,
        )
        self.assertEqual(
            incident["stage_action"],
            "quarantine_checkpoint_and_rebuild_uncommitted_work",
        )
        self.assertEqual(incident["checkpoint"]["verification_state"], "corrupt")
        self.assertIn("checkpoint_reuse", incident["blocked_actions"])
        self.assertEqual(resumed["reuse_count"], 1)
        self.assertEqual(resumed["execute_count"], 0)
        self.assert_common_safety(incident)

    def test_rate_limit_exhaustion_waits_for_a_new_ledger_window(self) -> None:
        reset = NOW + timedelta(minutes=30)
        incident = plan("rate_limit_exhaustion", budget_resets_at=reset)
        self.assertEqual(incident["not_before"], "2026-07-18T10:00:00Z")
        self.assertEqual(
            incident["resume_condition"], "new_utc_window_and_fresh_budget_ledger"
        )
        self.assertIn("flickr_requests", incident["blocked_actions"])
        self.assertIn("budget_lane_bypass", incident["blocked_actions"])
        self.assertIn("credential_rotation", incident["blocked_actions"])
        with self.assertRaisesRegex(IncidentPlanningError, "must be in the future"):
            plan("rate_limit_exhaustion", budget_resets_at=NOW)
        self.assert_common_safety(incident)

    def test_incident_vocabulary_fingerprints_and_inputs_are_closed(self) -> None:
        self.assertEqual(
            INCIDENT_KINDS,
            (
                "m5_sleep",
                "network_outage",
                "flickr_outage",
                "b2_outage",
                "supabase_outage",
                "model_crash",
                "corrupted_checkpoint",
                "rate_limit_exhaustion",
            ),
        )
        first = plan("network_outage")
        second = plan("network_outage")
        self.assertEqual(first, second)
        self.assertRegex(first["incident_id"], r"^blinc:v1:[0-9a-f]{24}$")
        self.assertRegex(first["plan_fingerprint"], r"^[0-9a-f]{64}$")
        with self.assertRaisesRegex(IncidentPlanningError, "incident kind"):
            plan("delete_everything")
        with self.assertRaisesRegex(IncidentPlanningError, "supplied together"):
            plan("m5_sleep", checkpoint_fingerprint=CHECKPOINT)
        with self.assertRaisesRegex(IncidentPlanningError, "failed verification"):
            plan(
                "corrupted_checkpoint",
                checkpoint_fingerprint=CHECKPOINT,
                checkpoint_verified=True,
            )

    def test_planner_and_tests_import_no_provider_storage_database_or_model_client(self) -> None:
        source = (
            ROOT / "services/worker/python/butterflylens_worker/resilience.py"
        ).read_text(encoding="utf-8")
        test_source = Path(__file__).read_text(encoding="utf-8")
        for forbidden in (
            "import requests",
            "import httpx",
            "import aiohttp",
            "urllib",
            "boto3",
            "supabase.create_client",
            "from_pretrained",
            "load_state_dict",
            "import torch",
            "flickr.photos.search(",
        ):
            self.assertNotIn(forbidden, source)
        imported_roots = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(ast.parse(test_source))
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            str(node.module).split(".", 1)[0]
            for node in ast.walk(ast.parse(test_source))
            if isinstance(node, ast.ImportFrom)
        }
        self.assertTrue(
            {"requests", "httpx", "aiohttp", "urllib", "boto3", "supabase", "torch"}
            .isdisjoint(imported_roots)
        )


if __name__ == "__main__":
    unittest.main()
