from __future__ import annotations

import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = next((ROOT / "supabase/migrations").glob("*_rls_role_policies.sql"))
DATABASE_TEST = ROOT / "supabase/tests/database/006_rls_role_policies.test.sql"


class RlsRolePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")

    def test_project_memberships_are_typed_indexed_and_rls_enabled(self) -> None:
        self.assertIn("create table public.project_memberships", self.sql)
        self.assertIn("project_memberships_profile_identity_fk", self.sql)
        self.assertIn("'reviewer', 'expert', 'curator', 'administrator'", self.sql)
        self.assertIn("alter table public.project_memberships enable row level security", self.sql)
        for index in (
            "project_memberships_project_pk_idx",
            "project_memberships_reviewer_profile_pk_idx",
            "project_memberships_auth_project_role_idx",
            "project_memberships_approver_pk_idx",
        ):
            self.assertIn(index, self.sql)

    def test_role_helper_is_private_fixed_and_uses_cached_auth_uid(self) -> None:
        self.assertIn("create schema if not exists private", self.sql)
        self.assertIn("security definer\nset search_path = ''", self.sql)
        self.assertIn("membership.auth_user_id = (select auth.uid())", self.sql)
        self.assertIn("revoke all on function private.has_project_role", self.sql)
        self.assertNotIn("auth.role()", self.sql)
        self.assertNotIn("security definer\nset search_path = public", self.sql)

    def test_guest_projection_is_narrow_and_release_is_fully_gated(self) -> None:
        self.assertIn("projects_public_read", self.sql)
        self.assertIn("species_public_read", self.sql)
        self.assertIn("visibility_state = 'public'", self.sql)
        self.assertIn("candidate_state in ('approved', 'exported') and all_release_gates_passed", self.sql)
        self.assertNotIn("grant select on table public.api_requests to anon", self.sql)
        self.assertNotIn("grant select on table public.reviewer_reliability to anon", self.sql)
        for view in (
            "public_projects",
            "public_species",
            "public_geographic_impact",
            "public_release_candidates",
        ):
            self.assertIn(f"create view public.{view}\nwith (security_invoker = true)", self.sql)
        projects_view = self.sql.split("create view public.public_projects", 1)[1].split(
            "create view public.public_species", 1
        )[0]
        release_view = self.sql.split(
            "create view public.public_release_candidates", 1
        )[1].split("revoke all on table", 1)[0]
        self.assertNotIn("created_by", projects_view)
        self.assertNotIn("authorized_by_reviewer_pk", release_view)
        self.assertNotIn("media_object_pk", release_view)

    def test_review_write_is_own_assignment_insert_only(self) -> None:
        self.assertIn("review_events_self_insert", self.sql)
        self.assertIn("assignment.reviewer_profile_pk = review_events.reviewer_profile_pk", self.sql)
        self.assertIn("profile.auth_user_id = (select auth.uid())", self.sql)
        self.assertIn("campaign.status = 'open'", self.sql)
        self.assertIn("grant select, insert on table public.review_events", self.sql)
        self.assertNotIn("grant update on table public.review_events", self.sql)
        self.assertIn("create function private.validate_review_event_context()", self.sql)
        self.assertIn("review_events_validate_context", self.sql)
        self.assertIn("new.image_sha256 <> expected_image_sha256", self.sql)
        self.assertIn("new.question <> expected_question", self.sql)

    def test_consensus_blinding_and_reliability_privacy_are_policy_enforced(self) -> None:
        self.assertIn("consensus_respondent_read", self.sql)
        self.assertIn("assignment.status = 'responded'", self.sql)
        self.assertIn("reviewer_reliability_self_read", self.sql)
        self.assertIn("reviewer_reliability_curator_read", self.sql)
        self.assertNotIn("reviewer_reliability_public", self.sql)

    def test_browser_roles_cannot_mutate_server_evidence_or_release(self) -> None:
        for table in (
            "api_requests",
            "flickr_photos",
            "media_objects",
            "worker_leases",
            "worker_heartbeats",
            "model_evidence",
            "geographic_impact",
            "release_candidates",
        ):
            self.assertNotRegex(
                self.sql,
                rf"grant\s+(?:insert|update|delete).*public\.{table}.*to authenticated",
            )

    def test_nullable_shape_hardening_is_present(self) -> None:
        for constraint in (
            "media_objects_content_nulls_match_check",
            "media_objects_dimension_nulls_match_check",
            "media_objects_perceptual_nulls_match_check",
            "model_evidence_calibration_nulls_match_check",
            "geographic_impact_heartbeat_fingerprint_check",
        ):
            self.assertIn(constraint, self.sql)

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
        self.assertTrue(self.database_test.rstrip().endswith("rollback;"))


if __name__ == "__main__":
    unittest.main()
