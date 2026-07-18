from __future__ import annotations

import json
from pathlib import Path
import re
import unittest
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".mcp.json"
GUIDE = ROOT / "SUPABASE_MCP.md"


class SupabaseMcpConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw_config = CONFIG.read_text(encoding="utf-8")
        cls.config = json.loads(cls.raw_config)
        cls.guide = GUIDE.read_text(encoding="utf-8")
        cls.server = cls.config["mcpServers"]["supabase"]
        cls.url = urlparse(cls.server["url"])
        cls.query = parse_qs(cls.url.query, keep_blank_values=True)

    def test_exact_remote_http_server_is_declared(self) -> None:
        self.assertEqual(set(self.config), {"mcpServers"})
        self.assertEqual(set(self.config["mcpServers"]), {"supabase"})
        self.assertEqual(set(self.server), {"type", "url"})
        self.assertEqual(self.server["type"], "http")
        self.assertEqual(self.url.scheme, "https")
        self.assertEqual(self.url.netloc, "mcp.supabase.com")
        self.assertEqual(self.url.path, "/mcp")
        self.assertFalse(self.url.fragment)
        self.assertFalse(self.url.username)
        self.assertFalse(self.url.password)

    def test_server_is_project_scoped_read_only_and_feature_limited(self) -> None:
        self.assertEqual(
            self.query,
            {
                "project_ref": ["ujfsrohgsrmssmfqgdsp"],
                "read_only": ["true"],
                "features": ["database,docs"],
            },
        )

    def test_config_contains_no_credential_or_mutating_client_option(self) -> None:
        lowered = self.raw_config.lower()
        for forbidden in (
            "authorization",
            "access_token",
            "refresh_token",
            "service_role",
            "secret",
            "headers",
            "command",
            "env",
        ):
            self.assertNotIn(forbidden, lowered)
        self.assertIsNone(re.search(r"\b(?:sb_secret_|eyj|sk-)[a-z0-9_-]{12,}", lowered))

    def test_guide_keeps_authentication_and_project_actions_unclaimed(self) -> None:
        normalized_guide = " ".join(self.guide.split())
        for required in (
            "Do not connect Supabase MCP to production data.",
            "Keep manual approval enabled for every tool call.",
            "did not complete OAuth",
            "No Supabase project read or mutation is evidenced by this file.",
        ):
            self.assertIn(required, normalized_guide)


if __name__ == "__main__":
    unittest.main()
