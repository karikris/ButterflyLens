from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))

from butterflylens.flickr import (  # noqa: E402
    FlickrDisplayPolicy,
    FlickrDisplayPolicyError,
    admit_public_display_page,
)


POLICY_PATH = ROOT / "packages/flickr/public-display-policy.v1.json"
MIGRATION = ROOT / "supabase/migrations/20260718045950_flickr_public_display_policy.sql"
DATABASE_TEST = ROOT / "supabase/tests/database/016_flickr_public_display_policy.test.sql"
NOW = datetime(2026, 7, 18, 5, 0, tzinfo=timezone.utc)


class FlickrPublicDisplayPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        cls.policy = FlickrDisplayPolicy.load(POLICY_PATH)
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")

    def test_policy_freezes_current_provider_and_project_boundaries(self) -> None:
        self.assertEqual(self.policy.maximum_photos_per_page, 30)
        self.assertEqual(self.policy.maximum_cache_age_seconds, 86_400)
        self.assertEqual(self.policy.maximum_revalidation_age_seconds, 86_400)
        self.assertEqual(self.policy.removal_deadline_hours, 24)
        self.assertFalse(self.document["branding"]["flickr_logo_permitted"])
        self.assertEqual(
            self.document["release_gate"]["public_photo_display"],
            "conditional_all_gates",
        )
        self.assertEqual(
            self.document["cache"]["purge_on_removal_case"], "immediate"
        )

    def test_complete_public_item_is_admitted_without_transport(self) -> None:
        page = admit_public_display_page(
            [valid_item()], context=approved_context(), policy=self.policy, now=NOW
        )
        self.assertEqual(len(page), 1)
        self.assertEqual(page[0]["flickr_photo_id"], "123456789")

    def test_page_limit_duplicates_private_removal_and_stale_cache_fail_closed(self) -> None:
        thirty_one = [
            valid_item(
                display_asset_id=f"flickr-display:{index}",
                flickr_photo_id=str(index + 1),
            )
            for index in range(31)
        ]
        with self.assertRaisesRegex(FlickrDisplayPolicyError, "exceeds 30"):
            admit_public_display_page(
                thirty_one, context=approved_context(), policy=self.policy, now=NOW
            )

        cases = (
            ({"visibility_state": "private"}, "visibility_state"),
            ({"removal_state": "removed"}, "removal_state"),
            ({"removal_case_id": "removal:1"}, "removal_case"),
            ({"photographer": ""}, "photographer"),
            ({"cache_expires_at": "2026-07-18T04:59:59Z"}, "expired"),
            ({"image_url": "https://live.staticflickr.com/photo.jpg"}, "internal"),
        )
        for changes, message in cases:
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(FlickrDisplayPolicyError, message):
                    admit_public_display_page(
                        [valid_item(**changes)],
                        context=approved_context(),
                        policy=self.policy,
                        now=NOW,
                    )

    def test_application_approval_and_privacy_disclosure_are_required(self) -> None:
        context = approved_context()
        context["application_approval_state"] = "not_recorded"
        with self.assertRaisesRegex(FlickrDisplayPolicyError, "approval"):
            admit_public_display_page(
                [], context=context, policy=self.policy, now=NOW
            )
        context = approved_context()
        context["privacy_disclosure_url"] = ""
        with self.assertRaisesRegex(FlickrDisplayPolicyError, "privacy"):
            admit_public_display_page(
                [], context=context, policy=self.policy, now=NOW
            )

    def test_database_gate_is_service_only_rls_and_removal_aware(self) -> None:
        for table in (
            "flickr_application_approvals",
            "flickr_removal_cases",
            "flickr_display_assets",
            "flickr_removal_events",
        ):
            self.assertIn(f"create table public.{table}", self.sql)
            self.assertIn(f"alter table public.{table} enable row level security", self.sql)
        self.assertIn("with (security_invoker = true)", self.sql)
        self.assertIn("cache_expires_at <= cached_at + interval '24 hours'", self.sql)
        self.assertIn("deadline_at = received_at + interval '24 hours'", self.sql)
        self.assertIn("flickr_removal_cases_quarantine", self.sql)
        self.assertIn("where display_state = 'eligible'", self.sql)
        self.assertIn("revoke all on table public.flickr_public_display_projection", self.sql)
        self.assertNotRegex(self.sql, r"grant .* to anon")
        self.assertNotIn("security definer", self.sql.casefold())

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


def approved_context() -> dict[str, object]:
    return {
        "schema_version": "butterflylens-flickr-display-context:v1.0.0",
        "page_id": "flickr-page:fixture",
        "application_approval_state": "noncommercial_approved",
        "privacy_disclosure_url": "https://butterflylens.example/privacy",
        "flickr_notice": (
            "This product uses the Flickr API but is not endorsed or certified "
            "by SmugMug, Inc."
        ),
    }


def valid_item(**changes: object) -> dict[str, object]:
    item: dict[str, object] = {
        "schema_version": "butterflylens-flickr-display-item:v1.0.0",
        "display_asset_id": "flickr-display:1",
        "flickr_photo_id": "123456789",
        "title": "Fixture butterfly",
        "photographer": "Example photographer",
        "owner_nsid": "owner@N00",
        "source_url": "https://www.flickr.com/photos/example/123456789/",
        "image_url": "/media/flickr/fixture.jpg",
        "licence_id": "CC BY 2.0",
        "licence_url": "https://creativecommons.org/licenses/by/2.0/",
        "attribution": "Fixture butterfly by Example photographer, CC BY 2.0",
        "visibility_state": "public",
        "is_current": True,
        "rights_status": "allowed",
        "display_allowed": True,
        "redistribution_allowed": True,
        "media_state": "committed",
        "object_kind": "public_thumbnail",
        "cached_at": "2026-07-18T04:30:00Z",
        "revalidated_at": "2026-07-18T04:59:00Z",
        "cache_expires_at": "2026-07-19T04:30:00Z",
        "removal_state": "active",
        "removal_case_id": None,
        "source_record_fingerprint": "a" * 64,
        "rights_fingerprint": "b" * 64,
        "display_fingerprint": "c" * 64,
    }
    item.update(deepcopy(changes))
    return item


if __name__ == "__main__":
    unittest.main()
