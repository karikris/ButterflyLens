from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase/migrations/20260718103000_media_takedown_workflow.sql"
DATABASE_TEST = ROOT / "supabase/tests/database/022_media_takedown_workflow.test.sql"
POLICY = ROOT / "MEDIA_RIGHTS.md"


class MediaTakedownWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")
        cls.policy = POLICY.read_text(encoding="utf-8")

    def test_private_requester_data_is_separate_and_never_browser_granted(self) -> None:
        self.assertIn("create table private.media_rights_requesters", self.sql)
        self.assertIn("private_request_detail text not null", self.sql)
        self.assertIn("contact_reference_fingerprint text not null", self.sql)
        private_grants = self.sql.split(
            "grant select, insert on table private.media_rights_requesters", 1
        )[1].split(";", 1)[0]
        self.assertEqual(private_grants.strip(), "to service_role")
        self.assertNotIn("grant select on table private.media_rights_requesters", self.sql)

    def test_intake_quarantines_before_review_and_fixes_pending_flickr_shape(self) -> None:
        self.assertIn("validate_and_quarantine_media_rights_request", self.sql)
        self.assertGreaterEqual(self.sql.count("rights_status = 'quarantined'"), 3)
        self.assertIn("when media_state = 'committed' then 'quarantined'", self.sql)
        self.assertIn("media_state in ('pending', 'committed')", self.sql)
        self.assertIn("source_kind <> 'flickr'", self.sql)
        self.assertIn("deadline_at = received_at + interval '24 hours'", self.sql)

    def test_inventory_is_exact_sealed_and_append_only(self) -> None:
        self.assertIn("create table public.media_takedown_dependencies", self.sql)
        self.assertIn("create table public.media_takedown_inventory_receipts", self.sql)
        self.assertIn("new.dependency_entries <> expected_entries", self.sql)
        self.assertIn("takedown inventory is already sealed", self.sql)
        self.assertIn("media rights ledgers are append only", self.sql)
        for kind in (
            "source_record", "source_cache", "public_display", "thumbnail",
            "model_input", "embedding", "review", "public_cell", "packet",
            "export", "mirror", "signed_url",
        ):
            self.assertIn(f"'{kind}'", self.sql)

    def test_completion_requires_authority_inventory_and_terminal_actions(self) -> None:
        self.assertIn("event.action = 'authority_verified'", self.sql)
        self.assertIn("receipt.inventory_fingerprint = any(new.evidence_fingerprints)", self.sql)
        for action in (
            "dependency_purged", "dependency_removed",
            "dependency_invalidated", "dependency_retained_independent_rights",
        ):
            self.assertIn(f"'{action}'", self.sql)
        self.assertIn(
            "verified authority, exact inventory, and terminal dependency actions",
            self.sql,
        )
        self.assertIn("dependency already has a terminal action", self.sql)
        self.assertIn("media takedown is already complete", self.sql)

    def test_public_release_and_map_fail_closed_on_requests(self) -> None:
        self.assertIn("drop policy release_candidates_public_read", self.sql)
        self.assertIn("not private.has_media_takedown_for_release(id)", self.sql)
        self.assertIn("drop policy geographic_impact_public_read", self.sql)
        self.assertIn("not private.has_media_takedown_for_impact(id)", self.sql)
        self.assertIn("join lineage child on parent.id = child.parent_media_pk", self.sql)

    def test_status_view_is_identity_free_and_security_invoking(self) -> None:
        view = self.sql.split("create view public.media_rights_request_status", 1)[1]
        view = view.split("drop policy geographic_impact_public_read", 1)[0]
        self.assertIn("with (security_invoker = true)", view)
        self.assertIn("resolving_dependencies", view)
        for private_field in (
            "private_request_detail", "contact_reference_fingerprint",
            "authority_evidence_fingerprint", "external_request_reference",
        ):
            self.assertNotIn(private_field, view)

    def test_rpc_authority_is_narrow(self) -> None:
        self.assertIn("to authenticated", self.sql)
        self.assertIn("to service_role", self.sql)
        self.assertIn("media rights decision requires curator authority", self.sql)
        self.assertIn("media takedown completion requires curator authority", self.sql)
        self.assertNotRegex(
            self.sql,
            r"grant\s+(?:insert|update|delete)[^;]*media_rights_request_events[^;]*authenticated",
        )

    def test_policy_is_truthful_about_prelaunch_and_provider_deadline(self) -> None:
        normalized = " ".join(self.policy.split())
        for phrase in (
            "prelaunch workflow",
            "Do not submit contact details",
            "does not yet publish a private operator-controlled request channel",
            "within 24 hours",
            "append-only audit",
            "retained under independently verified rights",
        ):
            self.assertIn(phrase, normalized)

    def test_pgtap_plan_matches_assertion_count(self) -> None:
        plan = int(re.search(r"select plan\((\d+)\)", self.database_test).group(1))
        assertions = len(
            re.findall(
                r"^select (?:has_|col_|ok\(|is\(|throws_ok\()",
                self.database_test,
                flags=re.MULTILINE,
            )
        )
        self.assertEqual(assertions, plan)


if __name__ == "__main__":
    unittest.main()
