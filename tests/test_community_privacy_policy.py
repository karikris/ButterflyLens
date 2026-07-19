from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "PRIVACY.md"
MANIFEST_PATH = ROOT / "policies/community-privacy-policy.v1.json"
POLICY = POLICY_PATH.read_text(encoding="utf-8")
NORMALIZED_POLICY = " ".join(POLICY.split())
MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


class CommunityPrivacyPolicyTests(unittest.TestCase):
    def test_policy_and_manifest_share_one_versioned_prelaunch_boundary(self) -> None:
        self.assertEqual(
            MANIFEST["policy_version"],
            "butterflylens-community-privacy:v1.0.0",
        )
        self.assertIn(f'`{MANIFEST["policy_version"]}`', POLICY)
        self.assertEqual(MANIFEST["status"], "prelaunch_blocked")
        self.assertFalse(MANIFEST["community_write_access"])
        self.assertFalse(MANIFEST["live_analyst_enabled"])

    def test_unresolved_operator_contact_regions_and_retention_fail_closed(self) -> None:
        unresolved = MANIFEST["unresolved_production_details"]
        self.assertIsNone(unresolved["legal_operator"])
        self.assertIsNone(unresolved["private_privacy_contact"])
        self.assertIsNone(unresolved["overseas_recipient_countries_or_regions"])
        self.assertIsNone(unresolved["category_retention_schedule"])
        for blocker in (
            "legal_operator_identity",
            "private_privacy_contact",
            "overseas_recipient_countries_or_regions",
            "category_retention_schedule",
            "versioned_participant_acceptance",
            "moderation_and_removal_workflows",
        ):
            self.assertIn(blocker, MANIFEST["launch_blockers"])
        self.assertIn("community writes remain blocked", NORMALIZED_POLICY)

    def test_required_people_and_evidence_categories_are_addressed(self) -> None:
        for phrase in (
            "Pseudonymous accounts and user IDs",
            "Review history and retained comments",
            "Reviewer reliability and contribution summaries",
            "Flickr source and owner data",
            "Anonymous browsing and analytics",
            "Sensitive occurrence locations",
            "Access, correction, complaints, and removal",
        ):
            self.assertIn(phrase, POLICY)
        self.assertIn("a real name is not required", NORMALIZED_POLICY)
        self.assertIn("never part of a public profile", POLICY)
        self.assertIn("not a public score, leaderboard, badge", POLICY)

    def test_policy_matches_current_browser_and_analyst_boundaries(self) -> None:
        web_sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "apps/web/src").rglob("*")
            if path.is_file() and path.suffix in {".ts", ".tsx", ".js", ".jsx"}
        )
        for forbidden in ("localStorage", "sessionStorage", "document.cookie"):
            self.assertNotIn(forbidden, web_sources)
        self.assertFalse(MANIFEST["anonymous_site"]["product_analytics"])

    def test_policy_matches_private_identity_reliability_and_append_only_review(self) -> None:
        migrations = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "supabase/migrations").glob("*.sql")
        )
        for phrase in (
            "create table public.reviewer_profiles",
            "public_name !~",
            "create table public.review_events",
            "corrections supersede without mutation",
            "Private append-only domain snapshots",
            "create table public.flickr_removal_cases",
        ):
            self.assertIn(phrase, migrations)

    def test_deletion_is_not_misrepresented_as_destructive_audit_rewriting(self) -> None:
        for phrase in (
            "corrections supersede earlier events",
            "disable the account",
            "replace the public pseudonym with a neutral tombstone",
            "minimum de-identified event",
            "must not be used to re-identify",
            "state what was deleted, de-identified, retained and why",
        ):
            self.assertIn(phrase, NORMALIZED_POLICY)

    def test_policy_is_publicly_linked_from_readme_and_site_footer(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        shell = (ROOT / "apps/web/src/shell/PublicShell.tsx").read_text(
            encoding="utf-8"
        )
        self.assertIn("[community privacy policy](PRIVACY.md)", readme)
        self.assertIn(
            "https://github.com/karikris/ButterflyLens/blob/main/PRIVACY.md",
            shell,
        )


if __name__ == "__main__":
    unittest.main()
