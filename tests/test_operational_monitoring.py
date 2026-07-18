from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase/migrations/20260718090000_operational_monitoring.sql"
DATABASE_TEST = ROOT / "supabase/tests/database/019_operational_monitoring.test.sql"
OPERATIONS = ROOT / "apps/web/src/operations"


class OperationalMonitoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")
        cls.boundary = (
            ROOT / "supabase/functions/_shared/monitoringBoundary.ts"
        ).read_text(encoding="utf-8")
        cls.edge = (
            ROOT / "supabase/functions/operations-status/index.ts"
        ).read_text(encoding="utf-8")
        cls.transport = (OPERATIONS / "monitoringTransport.ts").read_text(
            encoding="utf-8"
        )
        cls.snapshot = json.loads(
            (OPERATIONS / "submittedMonitoringSnapshot.json").read_text(
                encoding="utf-8"
            )
        )

    def test_submitted_fallback_has_every_required_signal_without_fake_zeroes(self) -> None:
        self.assertEqual(
            self.snapshot["schemaVersion"],
            "butterflylens-public-monitoring:v1.0.0",
        )
        self.assertEqual(self.snapshot["snapshotMode"], "submitted")
        for key in (
            "heartbeat",
            "apiBudget",
            "stageHealth",
            "queue",
            "failures",
            "lastArtifact",
            "lastMapRefresh",
            "models",
            "resources",
        ):
            self.assertIn(key, self.snapshot)
        self.assertIsNone(self.snapshot["queue"]["depth"])
        self.assertIsNone(self.snapshot["failures"]["count"])
        self.assertEqual(self.snapshot["models"]["yoloe"], "unfinished")
        self.assertEqual(self.snapshot["models"]["bioclip"], "unfinished")
        self.assertFalse(self.snapshot["scientificClaimAllowed"])

    def test_projection_is_typed_append_only_and_not_browser_readable(self) -> None:
        self.assertIn(
            "create table public.operational_monitoring_snapshots", self.sql
        )
        self.assertIn(
            "alter table public.operational_monitoring_snapshots enable row level security",
            self.sql,
        )
        self.assertIn(
            "grant select, insert on table public.operational_monitoring_snapshots to service_role",
            self.sql,
        )
        self.assertIn("from public, anon, authenticated", self.sql)
        self.assertIn("operational monitoring snapshots are append only", self.sql)
        self.assertNotRegex(self.sql, r"grant\s+select[^;]+to\s+(?:anon|authenticated)")
        for column in (
            "api_budget_remaining bigint",
            "queue_depth bigint",
            "failure_count bigint",
            "artifact_fingerprint text",
            "map_refreshed_at timestamptz",
            "free_disk_bytes bigint",
            "process_rss_bytes bigint",
        ):
            self.assertIn(column, self.sql)
        for forbidden in ("error_message", "decimal_latitude", "storage_key"):
            self.assertNotIn(forbidden, self.sql)

    def test_public_edge_is_auth_none_but_exact_origin_and_input_closed(self) -> None:
        self.assertIn('{ auth: "none", cors: "disabled" }', self.edge)
        self.assertIn('Deno.env.get("BUTTERFLYLENS_PUBLIC_PROJECT_ID")', self.edge)
        self.assertIn('Deno.env.get("BUTTERFLYLENS_PUBLIC_ORIGIN")', self.edge)
        self.assertIn('request.method !== "GET"', self.boundary)
        self.assertIn('request.method === "OPTIONS"', self.boundary)
        self.assertIn('url.search !== ""', self.boundary)
        self.assertIn('requestOrigin !== origin', self.boundary)
        self.assertIn('"Cache-Control": "no-store, max-age=0"', self.boundary)
        self.assertIn('"Referrer-Policy": "no-referrer"', self.boundary)
        self.assertIn("scientificClaimAllowed: false", self.boundary)

    def test_public_payload_does_not_expose_private_lineage_or_raw_state(self) -> None:
        payload_source = self.boundary.split(
            "export function publicMonitoringPayload", 1
        )[1].split("export function createPublicMonitoringHandler", 1)[0]
        for forbidden in (
            "project_pk",
            "run_pk",
            "worker_heartbeat_pk",
            "machine_fingerprint",
            "storage_key",
            "error_message",
            "coordinates",
            "metrics",
        ):
            self.assertNotIn(forbidden, payload_source)

    def test_browser_transport_is_credential_free_bounded_and_fail_retaining(self) -> None:
        for required in (
            "url.protocol !== 'https:'",
            "credentials: 'omit'",
            "cache: 'no-store'",
            "referrerPolicy: 'no-referrer'",
            "AbortController",
            "bodyBytes > 32_768",
        ):
            self.assertIn(required, self.transport)
        dashboard = (OPERATIONS / "OperationsDashboard.tsx").read_text(
            encoding="utf-8"
        )
        self.assertIn("Keep the last valid snapshot", dashboard)
        self.assertIn("setTimeout(refresh, refreshMs)", dashboard)
        self.assertNotIn("setInterval", dashboard)
        self.assertIn("value < 5_000 || value > 300_000", dashboard)

    def test_deployment_contract_keeps_live_monitoring_optional_and_nonsecret(self) -> None:
        production = json.loads(
            (ROOT / "infra/supabase/production.v1.json").read_text(encoding="utf-8")
        )
        function = production["edge_functions"]["operations-status"]
        self.assertEqual(function["authentication"], "none")
        self.assertFalse(function["verify_jwt"])
        self.assertEqual(
            function["browser_origin"], "https://karikris.github.io"
        )
        self.assertIn(
            "VITE_BUTTERFLYLENS_MONITORING_URL",
            production["browser_allowed_values"],
        )
        pages = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
        services = (ROOT / ".github/workflows/services.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("VITE_BUTTERFLYLENS_MONITORING_URL", pages)
        self.assertIn("BUTTERFLYLENS_PUBLIC_PROJECT_ID", services)
        self.assertIn("operations-status", services)
        self.assertNotIn("SUPABASE_SERVICE_ROLE_KEY", pages)

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
