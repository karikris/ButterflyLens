from __future__ import annotations

import unittest

from scripts.verify_release_security import run_audit


class ReleaseSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = run_audit()

    def test_database_and_network_surfaces_are_closed_and_inventoried(self) -> None:
        self.assertEqual(self.audit.public_rls_tables, 50)
        self.assertEqual(self.audit.security_invoker_views, 11)
        self.assertEqual(self.audit.security_definer_functions, 60)
        self.assertEqual(self.audit.external_network_boundary_files, 12)

    def test_tracked_text_has_no_high_signal_secret(self) -> None:
        self.assertGreaterEqual(self.audit.tracked_files_scanned_for_secrets, 535)

    def test_privacy_block_disables_accounts_writes_and_live_analyst(self) -> None:
        self.assertEqual(self.audit.privacy_status, "prelaunch_blocked")
        self.assertFalse(self.audit.community_writes_enabled)
        self.assertFalse(self.audit.live_analyst_enabled)

    def test_verification_passes_without_claiming_release_readiness(self) -> None:
        self.assertFalse(self.audit.release_ready)
        self.assertEqual(
            self.audit.release_blockers,
            (
                "ala_dataset_rights:dr1097",
                "ala_dataset_rights:dr30019",
                "ala_dataset_rights:dr635",
                "bioclip:skipped_unfinished_by_goal_instruction",
                "community_privacy:category_retention_schedule",
                "community_privacy:legal_operator_identity",
                "community_privacy:moderation_and_removal_workflows",
                "community_privacy:overseas_recipient_countries_or_regions",
                "community_privacy:private_privacy_contact",
                "community_privacy:versioned_participant_acceptance",
                "yoloe:blocked_not_executed",
            ),
        )


if __name__ == "__main__":
    unittest.main()
