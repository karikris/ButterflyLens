import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "FIRST_NATIONS_NAMES.md"
PACK = ROOT / "data/packs/australian_butterflies/v1"


class FirstNationsNamePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = POLICY.read_text(encoding="utf-8")
        cls.folded = cls.policy.casefold()
        cls.assertion_schema = json.loads(
            (PACK / "schemas/first_nations_name_assertion.schema.json").read_text(
                encoding="utf-8"
            )
        )
        cls.decision_schema = json.loads(
            (PACK / "schemas/first_nations_name_decision.schema.json").read_text(
                encoding="utf-8"
            )
        )
        cls.assertion_validator = Draft202012Validator(
            cls.assertion_schema,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        )
        cls.decision_validator = Draft202012Validator(
            cls.decision_schema,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        )
        cls.review = json.loads(
            (PACK / "first_nations_name_review_manifest.json").read_text(
                encoding="utf-8"
            )
        )

    @staticmethod
    def proposed_assertion():
        permission = {
            "state": "blocked",
            "scope": None,
            "decision_id": None,
            "expires_at": None,
        }
        query_permission = dict(permission, provider_purposes=[])
        return {
            "schema_version": "butterflylens-first-nations-name-assertion/v1",
            "assertion_id": "blfn:v1:" + "a" * 24,
            "butterflylens_key": "bltx:v1:" + "b" * 24,
            "name": "Controlled fixture only",
            "language": {
                "display_name": "Fixture language",
                "identifier": "X00",
                "identifier_scheme": "community_defined",
                "identifier_source": None,
                "identifier_version": None,
                "authority_confirmed": False,
            },
            "country_community": {
                "preferred_name": "Fixture community",
                "stable_identifier": None,
                "authority_confirmed": False,
                "public_scope_note": None,
            },
            "source": {
                "source_type": "delegated_decision_process",
                "citation": "Synthetic schema-validation fixture",
                "reference": "private:fixture-source",
                "retrieved_at": "2026-07-17T00:00:00Z",
                "fingerprint": "sha256:" + "c" * 64,
                "controlled_access": True,
            },
            "cultural_authority": {
                "authority_type": "delegated_decision_process",
                "public_name": "Fixture authority",
                "scope": "schema validation only",
                "private_contact_reference": "private:fixture-contact",
                "decision_evidence_refs": [],
            },
            "permissions": {
                "private_storage": permission,
                "public_display": permission,
                "query_use": query_permission,
                "redistribution": permission,
                "research_export": permission,
                "derived_model_use": permission,
            },
            "attribution": {
                "public_text": "Synthetic fixture; not a real name assertion.",
                "protocols": [],
                "local_contexts_identifiers": [],
            },
            "query_eligibility": {
                "eligible": False,
                "reason": "all permissions blocked",
            },
            "homonym_risk": "not_assessed",
            "scientific_review": {
                "state": "pending",
                "taxon_link_rationale": "Synthetic fixture",
                "evidence_fingerprints": [],
            },
            "cultural_review": {
                "state": "proposed",
                "decision_date": None,
                "permission_version": None,
                "review_due_at": None,
            },
            "provenance": {
                "policy_sha256": "d" * 64,
                "pack_version": "v1",
                "created_at": "2026-07-17T00:00:00Z",
            },
        }

    def test_required_assertion_dimensions_are_explicit(self) -> None:
        for term in (
            "language display name",
            "austlang code",
            "country/community",
            "cultural authority",
            "permitted use",
            "attribution",
            "query eligibility",
            "homonym risk",
            "review state",
            "retrieval date",
        ):
            self.assertIn(term, self.folded)

    def test_permissions_are_independent_and_blocked_by_default(self) -> None:
        for permission in (
            "private metadata storage",
            "public display",
            "search-query use",
            "redistribution",
            "research export",
            "derived/model use",
        ):
            self.assertIn(f"| {permission} | blocked |", self.folded)
        self.assertIn("approval for one purpose does not approve another", self.folded)

    def test_prohibited_shortcuts_are_named(self) -> None:
        for safeguard in (
            "machine-translate",
            "pan-aboriginal",
            "infer country/community",
            "model output",
            "majority review",
            "provider repetition",
            "aiatsis map",
        ):
            self.assertIn(safeguard, self.folded)

    def test_query_and_withdrawal_gates_are_explicit(self) -> None:
        self.assertIn("affirmative `query_use` permission", self.folded)
        self.assertIn("query term remains a", self.folded)
        self.assertIn("never becomes a species label", self.folded)
        for downstream in ("public pages", "query definitions", "caches", "exports"):
            self.assertIn(downstream, self.folded)

    def test_current_approved_count_is_zero(self) -> None:
        self.assertIn("approved assertions in the current pack: **0**", self.folded)
        self.assertIn("dataset is intentionally\nempty", self.folded)

    def test_primary_governance_sources_are_linked(self) -> None:
        for url in (
            "https://aiatsis.gov.au/research/ethical-research/code-ethics",
            "https://www.gida-global.org/careprinciples",
            "https://aiatsis.gov.au/research/languages/austlang",
            "https://localcontexts.org/labels/about-the-labels/",
        ):
            self.assertIn(url, self.policy)

    def test_assertion_contract_accepts_blocked_proposal(self) -> None:
        self.assertEqual(
            list(self.assertion_validator.iter_errors(self.proposed_assertion())), []
        )

    def test_assertion_contract_rejects_missing_community(self) -> None:
        fixture = self.proposed_assertion()
        del fixture["country_community"]
        self.assertTrue(list(self.assertion_validator.iter_errors(fixture)))

    def test_query_eligibility_requires_authorized_scoped_query_permission(self) -> None:
        fixture = self.proposed_assertion()
        fixture["query_eligibility"] = {"eligible": True, "reason": "invalid fixture"}
        self.assertTrue(list(self.assertion_validator.iter_errors(fixture)))
        query = fixture["permissions"]["query_use"]
        query.update(
            {
                "state": "authorized",
                "scope": "Flickr discovery only",
                "decision_id": "blfd:v1:" + "e" * 24,
                "provider_purposes": [
                    {"provider": "Flickr", "purpose": "published discovery plan"}
                ],
            }
        )
        self.assertEqual(list(self.assertion_validator.iter_errors(fixture)), [])

    def test_authorized_state_requires_authority_evidence(self) -> None:
        fixture = self.proposed_assertion()
        fixture["cultural_review"].update(
            {
                "state": "authorized_limited",
                "decision_date": "2026-07-17",
                "permission_version": "fixture-v1",
            }
        )
        self.assertTrue(list(self.assertion_validator.iter_errors(fixture)))
        fixture["cultural_authority"]["decision_evidence_refs"] = [
            "private:fixture-decision"
        ]
        self.assertEqual(list(self.assertion_validator.iter_errors(fixture)), [])

    def test_decision_contract_blocks_withdrawn_public_uses(self) -> None:
        decision = {
            "schema_version": "butterflylens-first-nations-name-decision/v1",
            "decision_id": "blfd:v1:" + "1" * 24,
            "assertion_id": "blfn:v1:" + "2" * 24,
            "event_sequence": 2,
            "previous_state": "authorized_limited",
            "new_state": "withdrawn",
            "decided_at": "2026-07-17T00:00:00Z",
            "authority": {
                "public_name": "Fixture authority",
                "scope": "schema validation only",
                "private_contact_reference": "private:fixture-contact",
            },
            "permissions": {
                "private_storage": "blocked",
                "public_display": "blocked",
                "query_use": "blocked",
                "redistribution": "blocked",
                "research_export": "blocked",
                "derived_model_use": "blocked",
            },
            "attribution": "Synthetic fixture",
            "evidence_references": ["private:fixture-withdrawal"],
            "permission_version": None,
            "expires_at": None,
            "review_due_at": None,
            "policy_sha256": "3" * 64,
            "supersedes_decision_id": "blfd:v1:" + "4" * 24,
        }
        self.assertEqual(list(self.decision_validator.iter_errors(decision)), [])
        decision["permissions"]["public_display"] = "authorized"
        self.assertTrue(list(self.decision_validator.iter_errors(decision)))

    def test_empty_datasets_and_review_manifest_are_fingerprinted(self) -> None:
        empty_sha = hashlib.sha256(b"").hexdigest()
        for name in (
            "first_nations_name_assertions.jsonl",
            "first_nations_name_decisions.jsonl",
        ):
            path = PACK / name
            self.assertEqual(path.read_bytes(), b"")
        self.assertEqual(self.review["status"], "empty_no_authorized_source")
        self.assertEqual(self.review["counts"]["approved_assertions"], 0)
        self.assertEqual(self.review["counts"]["pending_assertions"], 0)
        self.assertEqual(self.review["datasets"]["assertions"]["sha256"], empty_sha)
        self.assertEqual(self.review["datasets"]["decisions"]["sha256"], empty_sha)
        self.assertEqual(
            self.review["policy"]["sha256"], hashlib.sha256(POLICY.read_bytes()).hexdigest()
        )
        self.assertEqual(set(self.review["permission_defaults"].values()), {"blocked"})

    def test_pack_manifest_records_zero_approved_names(self) -> None:
        manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
        state = manifest["name_state"]
        self.assertEqual(state["first_nations_approved_count"], 0)
        self.assertEqual(state["first_nations_pending_count"], 0)
        self.assertEqual(
            state["first_nations_names"], "built_empty_no_authorized_source"
        )
        self.assertEqual(
            manifest["artifacts"]["first_nations_name_assertions.jsonl"]["row_count"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
