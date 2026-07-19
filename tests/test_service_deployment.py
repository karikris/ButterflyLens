from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase/migrations/20260718080000_deploy_service_boundaries.sql"
DATABASE_TEST = ROOT / "supabase/tests/database/018_deploy_service_boundaries.test.sql"


class ServiceDeploymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")
        cls.signer = (
            ROOT / "supabase/functions/_shared/b2Signer.ts"
        ).read_text(encoding="utf-8")
        cls.signing_boundary = (
            ROOT / "supabase/functions/_shared/b2Boundary.ts"
        ).read_text(encoding="utf-8")
        cls.signing_function = (
            ROOT / "supabase/functions/sign-b2-object/index.ts"
        ).read_text(encoding="utf-8")
        cls.action_boundary = (
            ROOT / "supabase/functions/_shared/serverActionBoundary.ts"
        ).read_text(encoding="utf-8")
        cls.action_function = (
            ROOT / "supabase/functions/control-butterflylens/index.ts"
        ).read_text(encoding="utf-8")

    def test_new_service_receipts_are_rls_append_only_and_least_privilege(self) -> None:
        for table in ("b2_signing_receipts", "server_action_receipts"):
            self.assertIn(f"create table public.{table}", self.sql)
            self.assertIn(f"alter table public.{table} enable row level security", self.sql)
        self.assertIn("service receipts are append only", self.sql)
        self.assertIn("grant select, insert on table public.b2_signing_receipts", self.sql)
        self.assertIn("to service_role", self.sql)
        self.assertIn("from public, anon, authenticated", self.sql)
        self.assertNotRegex(self.sql, r"grant insert .* authenticated")
        self.assertNotRegex(self.sql, r"grant .* to anon")
        for foreign_key_index in (
            "b2_signing_receipts_project_pk_idx",
            "b2_signing_receipts_media_object_pk_idx",
            "b2_signing_receipts_auth_user_id_idx",
            "server_action_receipts_project_pk_idx",
            "server_action_receipts_run_pk_idx",
            "server_action_receipts_requested_by_idx",
        ):
            self.assertIn(foreign_key_index, self.sql)

    def test_run_control_is_closed_authorized_atomic_and_idempotent(self) -> None:
        for action in ("pause_run", "resume_run", "cancel_run"):
            self.assertIn(f"'{action}'", self.sql)
        self.assertNotIn("delete_run", self.sql)
        self.assertIn("membership.role in ('curator', 'administrator')", self.sql)
        self.assertIn("target_revision <> new.expected_revision", self.sql)
        self.assertIn("for update", self.sql)
        self.assertIn("pg_catalog.pg_advisory_xact_lock", self.sql)
        self.assertIn("controlled server action ID already exists", self.sql)
        self.assertIn("set status = next_status", self.sql)
        self.assertIn("revision = revision + 1", self.sql)
        self.assertIn("before insert on public.server_action_receipts", self.sql)
        self.assertIn("security definer\nset search_path = ''", self.sql)

    def test_b2_signing_is_short_lived_rights_gated_and_url_free_in_storage(self) -> None:
        self.assertIn('input.method !== "GET" && input.method !== "HEAD"', self.signer)
        self.assertIn("MAXIMUM_B2_SIGNED_URL_TTL_SECONDS = 900", self.signer)
        self.assertIn('objectKey.startsWith("butterflylens/v1/")', self.signer)
        self.assertIn('endpoint.protocol !== "https:"', self.signer)
        self.assertIn("AWS4-HMAC-SHA256", self.signer)
        self.assertLess(
            self.signing_function.index("context.supabase\n"),
            self.signing_function.index("context.supabaseAdmin\n"),
        )
        for gate in (
            'media.storage_backend !== "b2"',
            'media.media_state !== "committed"',
            'media.decode_status !== "valid"',
            'media.rights_status !== "allowed"',
            "media.display_allowed !== true",
            "media.removed_at !== null",
        ):
            self.assertIn(gate, self.signing_function)
        receipt_insert = self.signing_function.split('.from("b2_signing_receipts")', 1)[1]
        self.assertNotIn("url:", receipt_insert)
        self.assertNotIn("storage_key:", receipt_insert)
        self.assertIn('"Cache-Control": "no-store"', self.signing_boundary)
        self.assertIn('"Referrer-Policy": "no-referrer"', self.signing_boundary)

    def test_controlled_edge_boundary_uses_user_rls_then_service_receipt(self) -> None:
        self.assertIn("withSupabase<EdgeDatabase>(", self.action_function)
        self.assertIn('{ auth: "user" }', self.action_function)
        self.assertLess(
            self.action_function.index("context.supabase\n"),
            self.action_function.index("context.supabaseAdmin\n"),
        )
        self.assertIn('keys.join(",") !==', self.action_boundary)
        self.assertIn("expectedRevision", self.action_boundary)
        self.assertIn("ServerActionConflictError", self.action_boundary)
        self.assertNotIn("service_role", self.action_boundary.casefold())

    def test_b2_deployment_contract_has_separate_buckets_and_scoped_keys(self) -> None:
        deployment = json.loads(
            (ROOT / "infra/b2/buckets.v1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(deployment["buckets"]["private"]["visibility"], "allPrivate")
        self.assertEqual(deployment["buckets"]["public"]["visibility"], "allPublic")
        self.assertFalse(deployment["buckets"]["private"]["object_lock"])
        self.assertFalse(deployment["buckets"]["public"]["object_lock"])
        self.assertEqual(deployment["lifecycle_rules"], [])
        self.assertNotIn(
            "writeFiles", deployment["application_keys"]["edge_signer"]["capabilities"]
        )
        self.assertNotIn(
            "deleteFiles", deployment["application_keys"]["edge_signer"]["capabilities"]
        )
        self.assertIn(
            "deleteFiles", deployment["application_keys"]["removal_worker"]["capabilities"]
        )
        provision = (ROOT / "infra/b2/provision.sh").read_text(encoding="utf-8")
        self.assertIn("put-bucket-cors", provision)
        self.assertIn("put-bucket-encryption", provision)
        self.assertNotIn("delete-bucket", provision)
        self.assertNotIn("object-lock", provision)

    def test_deployment_workflows_are_pinned_and_live_services_are_manual(self) -> None:
        pages = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
        services = (ROOT / ".github/workflows/services.yml").read_text(encoding="utf-8")
        self.assertIn("push:\n    branches: [main]", pages)
        self.assertIn("pages: write", pages)
        self.assertIn("id-token: write", pages)
        self.assertIn("BUTTERFLYLENS_BASE_PATH: /ButterflyLens/", pages)
        self.assertIn("workflow_dispatch:", services)
        self.assertNotIn("push:", services)
        self.assertIn("environment: production", services)
        self.assertIn("supabase db push", services)
        self.assertNotIn("--include-seed", services)
        self.assertIn(
            "sign-b2-object control-butterflylens operations-status",
            services,
        )
        for workflow in (pages, services):
            self.assertNotRegex(workflow, r"uses: [^\s]+@v\d")
            for action in re.findall(r"uses: [^@\s]+@([^\s]+)", workflow):
                self.assertRegex(action, r"^[0-9a-f]{40}$")

    def test_static_base_is_configurable_without_injecting_live_secrets(self) -> None:
        vite = (ROOT / "apps/web/vite.config.ts").read_text(encoding="utf-8")
        self.assertIn("BUTTERFLYLENS_BASE_PATH", vite)
        self.assertIn("const base =", vite)
        self.assertNotIn("SUPABASE_SECRET", vite)
        self.assertNotIn("OPENAI_API_KEY", vite)
        self.assertNotIn("B2_APPLICATION_KEY", vite)
        production = json.loads(
            (ROOT / "infra/supabase/production.v1.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            production["site_url"], "https://karikris.github.io/ButterflyLens/"
        )
        self.assertIn("SUPABASE_SECRET_KEY", production["browser_forbidden_values"])
        self.assertIn("B2_APPLICATION_KEY", production["browser_forbidden_values"])

    def test_pgtap_plan_matches_assertion_count(self) -> None:
        plan = int(re.search(r"select plan\((\d+)\)", self.database_test).group(1))
        assertions = len(
            re.findall(
                r"^select (?:has_|col_|ok\(|is\(|throws_ok\(|lives_ok\()",
                self.database_test,
                flags=re.MULTILINE,
            )
        )
        self.assertEqual(assertions, plan)
        self.assertTrue(self.database_test.rstrip().endswith("rollback;"))


if __name__ == "__main__":
    unittest.main()
