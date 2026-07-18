from __future__ import annotations

import ast
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))
sys.path.insert(0, str(ROOT / "services/worker/python"))

from butterflylens.contracts import (  # noqa: E402
    EVIDENCE_FINGERPRINT_LEGACY_SCHEMA_VERSION,
    EVIDENCE_FINGERPRINT_SCHEMA_VERSION,
    FINGERPRINT_CANONICALIZATION,
    FINGERPRINT_HASH_ALGORITHM,
    FINGERPRINT_KINDS,
    FINGERPRINT_KINDS_V1_0,
    FINGERPRINT_PARENT_RELATIONSHIPS,
    FingerprintValidationError,
    semantic_fingerprint_digest,
    validate_evidence_fingerprint,
)
from butterflylens_worker.restart import (  # noqa: E402
    RestartError,
    build_public_offline_projection,
)


SHA256 = re.compile(r"^[0-9a-f]{64}$")
POLICY_LINE = re.compile(r"^Policy version: `([^`]+)`", re.MULTILINE)
SUBMITTED_EXPORT = re.compile(r"^export const (submitted[A-Za-z0-9_]+)", re.MULTILINE)
PROJECTION_EXPORT = re.compile(
    r"^export function ([A-Za-z0-9_]*Projection)", re.MULTILINE
)
PYTHON_PROJECTION = re.compile(r"^def ([a-z0-9_]*projection)\(", re.MULTILINE)


SCHEMA_GROUPS = {
    "ala-baseline": {
        "prefix": "data/packs/australian_butterflies/v1/ala/schemas/",
        "count": 3,
        "positive": (
            "tests/test_ala_baseline_snapshot.py#test_manifest_schema_and_physical_artifact_reconcile",
        ),
        "negative": (
            "tests/test_ala_baseline_snapshot.py#test_rights_conflicts_are_explicit_and_block_public_release",
        ),
    },
    "butterflylens-contracts": {
        "prefix": "packages/contracts/schemas/",
        "count": 25,
        "positive": (
            "packages/contracts/tests/fixtures/parity-cases.json#valid_documents",
            "packages/contracts/tests/check_parity.py#validate_python_cases",
        ),
        "negative": (
            "packages/contracts/tests/fixtures/parity-cases.json#invalid_cases",
            "packages/contracts/tests/check_parity.py#Python accepted invalid case",
        ),
    },
    "first-nations-names": {
        "prefix": "data/packs/australian_butterflies/v1/schemas/",
        "count": 2,
        "positive": (
            "tests/test_first_nations_name_policy.py#test_assertion_contract_accepts_blocked_proposal",
        ),
        "negative": (
            "tests/test_first_nations_name_policy.py#test_assertion_contract_rejects_missing_community",
        ),
    },
    "openai": {
        "prefix": "packages/openai/",
        "count": 5,
        "positive": (
            "tests/test_openai_evaluations.py#test_generated_suite_and_result_match_strict_schemas",
            "tests/test_openai_replay.py#test_catalogue_matches_strict_generated_schema",
        ),
        "negative": (
            "tests/test_openai_evaluations.py#test_grader_rejects_wrong_tool_citation_and_incomplete_direct_claim",
            "apps/web/src/analyst/analystModel.test.ts#exact public shape",
        ),
    },
    "storage": {
        "prefix": "packages/storage/schemas/",
        "count": 1,
        "positive": (
            "tests/test_artifact_storage_layout.py#test_complete_manifest_is_schema_valid_and_recomputed",
        ),
        "negative": (
            "tests/test_artifact_storage_layout.py#test_public_thumbnail_and_crop_permissions_fail_closed",
        ),
    },
}


POLICY_COVERAGE = {
    "butterflylens-ala-contribution-policy:v1.0.0": {
        "sources": (
            "ALA_CONTRIBUTION.md",
            "packages/contracts/python/butterflylens/contracts/ala_contribution.py",
        ),
        "positive": (
            "tests/test_ala_contribution.py#test_archive_preserves_dwc_and_adds_every_requested_artifact",
        ),
        "negative": (
            "tests/test_ala_contribution.py#test_source_archive_tamper_and_identity_mismatch_fail_closed",
        ),
    },
    "butterflylens-community-moderation:v1.0.0": {
        "sources": ("MODERATION.md",),
        "positive": (
            "tests/test_moderation_workflow.py#test_exact_report_hide_suspension_audit_appeal_and_note_actions_exist",
        ),
        "negative": (
            "tests/test_moderation_workflow.py#test_audit_and_moderation_cannot_create_reliability_or_scientific_truth",
        ),
    },
    "butterflylens-community-privacy:v1.0.0": {
        "sources": (
            "PRIVACY.md",
            "policies/community-privacy-policy.v1.json",
        ),
        "positive": (
            "tests/test_community_privacy_policy.py#test_policy_and_manifest_share_one_versioned_prelaunch_boundary",
        ),
        "negative": (
            "tests/test_community_privacy_policy.py#test_unresolved_operator_contact_regions_and_retention_fail_closed",
        ),
    },
    "butterflylens-darwin-core-export-policy:v1.0.0": {
        "sources": (
            "DARWIN_CORE_EXPORT.md",
            "packages/contracts/python/butterflylens/contracts/darwin_core_export.py",
        ),
        "positive": (
            "tests/test_darwin_core_export.py#test_archive_has_occurrence_core_and_every_requested_extension",
        ),
        "negative": (
            "tests/test_darwin_core_export.py#test_release_state_publication_and_scientific_flags_fail_closed",
        ),
    },
    "butterflylens-flickr-public-display-policy:v1.0.0": {
        "sources": (
            "packages/contracts/python/butterflylens/flickr/display.py",
        ),
        "positive": (
            "tests/test_flickr_public_display_policy.py#test_complete_public_item_is_admitted_without_transport",
        ),
        "negative": (
            "tests/test_flickr_public_display_policy.py#test_page_limit_duplicates_private_removal_and_stale_cache_fail_closed",
        ),
    },
    "butterflylens-layered-consensus-policy:v1.0.0": {
        "sources": (
            "policies/layered-consensus.md",
            "packages/verification/python/butterflylens_verification/consensus.py",
        ),
        "positive": (
            "tests/test_layered_consensus.py#test_unweighted_community_and_weighted_qualified_layers_are_separate",
        ),
        "negative": (
            "tests/test_layered_consensus.py#test_adjudication_independence_and_exact_lineage_fail_closed",
        ),
    },
    "butterflylens-media-rights:v1.0.0": {
        "sources": ("MEDIA_RIGHTS.md",),
        "positive": (
            "tests/test_media_takedown_workflow.py#test_completion_requires_authority_inventory_and_terminal_actions",
        ),
        "negative": (
            "tests/test_media_takedown_workflow.py#test_public_release_and_map_fail_closed_on_requests",
        ),
    },
    "butterflylens-occurrence-release:v1.0.0": {
        "sources": (
            "OCCURRENCE_RELEASE.md",
            "packages/contracts/python/butterflylens/contracts/occurrence_release.py",
        ),
        "positive": (
            "tests/test_occurrence_release_policy.py#test_every_evidenced_gate_is_required_for_release_ready",
        ),
        "negative": (
            "tests/test_occurrence_release_policy.py#test_missing_duplicate_or_unknown_gate_fails_closed",
        ),
    },
    "butterflylens-representative-audit-policy:v1.0.0": {
        "sources": (
            "policies/representative-audit.md",
            "packages/verification/python/butterflylens_verification/dataset_quality.py",
        ),
        "positive": (
            "tests/test_dataset_quality_estimator.py#test_stratified_hajek_estimate_ess_and_grouped_interval",
        ),
        "negative": (
            "tests/test_dataset_quality_estimator.py#test_targeted_queue_never_emits_population_statistics",
        ),
    },
    "butterflylens-reviewer-reliability-policy:v1.0.0": {
        "sources": (
            "policies/reviewer-reliability.md",
            "packages/verification/python/butterflylens_verification/reliability.py",
        ),
        "positive": (
            "tests/test_reviewer_reliability_estimator.py#test_estimated_case_measures_every_required_metric",
        ),
        "negative": (
            "tests/test_reviewer_reliability_estimator.py#test_independence_and_exact_adjudication_lineage_fail_closed",
        ),
    },
    "butterflylens-sensitive-location-policy:v1.0.0": {
        "sources": (
            "SENSITIVE_LOCATIONS.md",
            "packages/contracts/python/butterflylens/contracts/sensitive_locations.py",
        ),
        "positive": (
            "tests/test_sensitive_location_controls.py#test_authoritative_ala_generalisation_allows_only_the_coarse_cell",
        ),
        "negative": (
            "tests/test_sensitive_location_controls.py#test_unknown_sensitivity_and_exact_sensitive_source_fail_closed",
        ),
    },
}


PROJECTION_COVERAGE = {
    "ala-public-baseline": {
        "json": (),
        "symbols": (),
        "positive": (
            "tests/test_ala_baseline_snapshot.py#test_snapshot_artifact_inventory_and_scientific_policies",
        ),
        "negative": (
            "tests/test_ala_baseline_snapshot.py#test_rights_conflicts_are_explicit_and_block_public_release",
        ),
    },
    "classification-maturity": {
        "json": (),
        "symbols": (),
        "positive": (
            "tests/test_classification_maturity.py#test_projection_is_deterministic_and_canonicalizes_evidence_order",
        ),
        "negative": (
            "tests/test_classification_maturity.py#test_tampering_unknown_states_and_duplicate_evidence_are_rejected",
        ),
    },
    "contributor-impact": {
        "json": ("apps/web/src/community/submittedContributorImpact.json",),
        "symbols": (
            "apps/web/src/community/contributorImpactModel.ts#submittedContributorImpact",
        ),
        "positive": (
            "tests/test_contributor_impact_experience.py#test_projection_is_order_stable_and_fingerprint_sensitive",
        ),
        "negative": (
            "tests/test_contributor_impact_experience.py#test_duplicate_or_malformed_lineage_fails_closed",
        ),
    },
    "flickr-display": {
        "json": (),
        "symbols": (
            "apps/web/src/flickr/flickrDisplayModel.ts#submittedFlickrDisplayContext",
        ),
        "positive": (
            "tests/test_flickr_public_display_policy.py#test_complete_public_item_is_admitted_without_transport",
        ),
        "negative": (
            "tests/test_flickr_public_display_policy.py#test_page_limit_duplicates_private_removal_and_stale_cache_fail_closed",
        ),
    },
    "monitoring": {
        "json": ("apps/web/src/operations/submittedMonitoringSnapshot.json",),
        "symbols": (
            "apps/web/src/operations/monitoringModel.ts#submittedMonitoringSnapshot",
        ),
        "positive": (
            "apps/web/src/operations/monitoringModel.test.ts#accepts a complete privacy-safe live snapshot",
        ),
        "negative": (
            "apps/web/src/operations/monitoringModel.test.ts#rejects a submitted snapshot claiming live telemetry",
        ),
    },
    "openai-artifacts": {
        "json": ("packages/openai/submitted-artifacts.v1.json",),
        "symbols": (),
        "positive": (
            "tests/test_openai_evidence_tools.py#test_pinned_artifact_registry_verifies_every_checksum",
        ),
        "negative": (
            "tests/test_openai_evidence_tools.py#test_tampered_artifact_registry_fails_closed",
        ),
    },
    "openai-replay": {
        "json": ("packages/openai/submitted-replays.v1.json",),
        "symbols": (
            "apps/web/src/analyst/analystModel.ts#submittedAnalystClient",
        ),
        "positive": (
            "tests/test_openai_replay.py#test_stored_calls_and_outputs_exactly_replay_deterministic_tools",
        ),
        "negative": (
            "apps/web/src/analyst/analystModel.test.ts#exact public shape",
        ),
    },
    "operations": {
        "json": ("apps/web/src/operations/submittedOperationsSnapshot.json",),
        "symbols": (
            "apps/web/src/operations/operationsModel.ts#buildOperationsProjection",
            "apps/web/src/operations/operationsModel.ts#buildSafeOperationsProjection",
            "apps/web/src/operations/operationsModel.ts#submittedOperationsSnapshot",
        ),
        "positive": (
            "apps/web/src/operations/operationsModel.test.ts#uses a fresh heartbeat without making it the data authority",
        ),
        "negative": (
            "apps/web/src/operations/operationsModel.test.ts#rejects future observations and falls back to the submitted snapshot",
        ),
    },
    "quality": {
        "json": ("apps/web/src/quality/submittedQualityProjection.json",),
        "symbols": (
            "apps/web/src/quality/qualityDashboardModel.ts#submittedQualityDashboard",
        ),
        "positive": (
            "tests/test_quality_dashboard_projection.py#test_reference_counts_and_flags_are_a_lossless_projection",
        ),
        "negative": (
            "apps/web/src/quality/qualityDashboardModel.test.ts#rejects an unavailable snapshot carrying a fake precision",
        ),
    },
    "review": {
        "json": (),
        "symbols": (
            "apps/web/src/review/blindReviewModel.ts#submittedReviewDisclosure",
            "apps/web/src/review/reviewLandingModel.ts#submittedReviewItem",
        ),
        "positive": (
            "apps/web/src/review/ReviewLanding.test.tsx#reveals allowlisted context only after locking a decision",
        ),
        "negative": (
            "apps/web/src/review/ReviewLanding.test.tsx#fails closed when review media is unavailable",
        ),
    },
    "species": {
        "json": ("apps/web/src/species/submittedSpeciesCatalogue.json",),
        "symbols": (
            "apps/web/src/species/speciesCatalogueModel.ts#submittedSpeciesCatalogue",
        ),
        "positive": (
            "apps/web/src/species/speciesCatalogueModel.test.ts#accepts the complete authoritative submitted projection",
        ),
        "negative": (
            "apps/web/src/species/speciesCatalogueModel.test.ts#rejects model or human evidence that was not run",
        ),
    },
    "submitted-freeze": {
        "json": ("data/submission/v1/submitted_snapshot.json",),
        "symbols": (),
        "positive": (
            "tests/test_submitted_snapshot_freeze.py#test_checked_in_snapshot_is_exactly_reproducible",
        ),
        "negative": (
            "tests/test_submitted_snapshot_freeze.py#test_fingerprint_rejects_tampering_and_release_stays_blocked",
        ),
    },
    "worker-offline": {
        "json": (),
        "symbols": (
            "services/worker/python/butterflylens_worker/restart.py#build_public_offline_projection",
        ),
        "positive": (
            "tests/test_worker_interruption_resume.py#test_offline_worker_keeps_committed_live_and_submitted_data_queryable",
        ),
        "negative": (
            "tests/test_contract_coverage.py#test_worker_projection_rejects_invalid_submitted_live_boundary",
        ),
    },
}


def tracked(*pathspecs: str) -> tuple[str, ...]:
    completed = subprocess.run(
        ["git", "ls-files", "-z", "--", *pathspecs],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return tuple(
        sorted(path for path in completed.stdout.decode().split("\0") if path)
    )


def assert_references(test: unittest.TestCase, references: tuple[str, ...]) -> None:
    test.assertTrue(references)
    for reference in references:
        path, separator, token = reference.partition("#")
        test.assertEqual(separator, "#", reference)
        test.assertTrue(token, reference)
        source = (ROOT / path).read_text(encoding="utf-8")
        test.assertIn(token, source, reference)


def fingerprint_record(schema_version: str, kind: str) -> dict[str, object]:
    preimage: dict[str, object] = {
        "fingerprint_kind": kind,
        "subject_id": f"coverage:{kind}",
        "payload_schema_version": "coverage:v1",
        "payload": {"coverage": "positive-and-digest-mutation"},
        "parents": [],
    }
    return {
        "schema_version": schema_version,
        "hash_algorithm": FINGERPRINT_HASH_ALGORITHM,
        "canonicalization": FINGERPRINT_CANONICALIZATION,
        "preimage": preimage,
        "digest": semantic_fingerprint_digest(preimage),
        "recorded_at": "2026-07-18T12:10:00Z",
    }


def integrity_values(
    value: object, path: str = "$", *, inherited: bool = False
) -> list[tuple[str, object]]:
    found: list[tuple[str, object]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            lowered = key.lower()
            matched = (
                inherited
                or "fingerprint" in lowered
                or "checksum" in lowered
                or lowered == "sha256"
            )
            if matched and not isinstance(child, (dict, list)):
                found.append((child_path, child))
            found.extend(integrity_values(child, child_path, inherited=matched))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(
                integrity_values(child, f"{path}[{index}]", inherited=inherited)
            )
    return found


class ContractCoverageTests(unittest.TestCase):
    def test_every_fingerprint_kind_and_version_accepts_and_rejects(self) -> None:
        versions = (
            (EVIDENCE_FINGERPRINT_LEGACY_SCHEMA_VERSION, FINGERPRINT_KINDS_V1_0),
            (EVIDENCE_FINGERPRINT_SCHEMA_VERSION, FINGERPRINT_KINDS),
        )
        for schema_version, kinds in versions:
            self.assertEqual(len(kinds), len(set(kinds)))
            for kind in kinds:
                with self.subTest(schema_version=schema_version, kind=kind):
                    record = fingerprint_record(schema_version, kind)
                    validate_evidence_fingerprint(record)
                    tampered = deepcopy(record)
                    digest = str(tampered["digest"])
                    tampered["digest"] = ("0" if digest[0] != "0" else "1") + digest[1:]
                    with self.assertRaisesRegex(
                        FingerprintValidationError, "digest mismatch"
                    ):
                        validate_evidence_fingerprint(tampered)

    def test_every_parent_relationship_is_accepted_and_unknown_is_rejected(self) -> None:
        for relationship in FINGERPRINT_PARENT_RELATIONSHIPS:
            with self.subTest(relationship=relationship):
                record = fingerprint_record(
                    EVIDENCE_FINGERPRINT_SCHEMA_VERSION, "export_manifest"
                )
                preimage = record["preimage"]
                assert isinstance(preimage, dict)
                preimage["parents"] = [
                    {
                        "relationship": relationship,
                        "fingerprint_kind": "artifact_manifest",
                        "digest": "a" * 64,
                    }
                ]
                record["digest"] = semantic_fingerprint_digest(preimage)
                validate_evidence_fingerprint(record)
        invalid = fingerprint_record(
            EVIDENCE_FINGERPRINT_SCHEMA_VERSION, "export_manifest"
        )
        preimage = invalid["preimage"]
        assert isinstance(preimage, dict)
        preimage["parents"] = [
            {
                "relationship": "trusts",
                "fingerprint_kind": "artifact_manifest",
                "digest": "a" * 64,
            }
        ]
        invalid["digest"] = semantic_fingerprint_digest(preimage)
        with self.assertRaisesRegex(FingerprintValidationError, "outside vocabulary"):
            validate_evidence_fingerprint(invalid)

    def test_every_tracked_json_schema_has_structural_and_named_coverage(self) -> None:
        schema_paths = tracked("*.schema.json")
        self.assertEqual(len(schema_paths), 36)
        grouped: set[str] = set()
        for name, group in SCHEMA_GROUPS.items():
            paths = tuple(path for path in schema_paths if path.startswith(group["prefix"]))
            self.assertEqual(len(paths), group["count"], name)
            self.assertTrue(grouped.isdisjoint(paths), name)
            grouped.update(paths)
            assert_references(self, group["positive"])
            assert_references(self, group["negative"])
            for path in paths:
                schema = json.loads((ROOT / path).read_text(encoding="utf-8"))
                Draft202012Validator.check_schema(schema)
                if "$id" in schema:
                    self.assertIsInstance(schema["$id"], str, path)
                else:
                    self.assertIsInstance(schema.get("schema_version"), str, path)
                    self.assertIsInstance(schema.get("artifact_schema_version"), str, path)
                    self.assertIsInstance(schema.get("fields"), list, path)
        self.assertEqual(grouped, set(schema_paths))

    def test_contract_schema_graph_has_positive_and_negative_roots(self) -> None:
        schema_paths = tuple(
            (ROOT / "packages/contracts/schemas").glob("*.schema.json")
        )
        schemas = {
            value["$id"]: value
            for value in (
                json.loads(path.read_text(encoding="utf-8")) for path in schema_paths
            )
        }
        fixtures = json.loads(
            (
                ROOT / "packages/contracts/tests/fixtures/parity-cases.json"
            ).read_text(encoding="utf-8")
        )
        positive = {item["schema_id"] for item in fixtures["valid_documents"]}
        negative = {item["schema_id"] for item in fixtures["invalid_cases"]}
        self.assertEqual(positive, negative)
        reachable = set(positive)
        pending = list(positive)
        while pending:
            schema_id = pending.pop()
            encoded = json.dumps(schemas[schema_id], sort_keys=True)
            for candidate in schemas:
                if candidate in encoded and candidate not in reachable:
                    reachable.add(candidate)
                    pending.append(candidate)
        self.assertEqual(reachable, set(schemas))

    def test_every_discovered_policy_has_positive_and_negative_coverage(self) -> None:
        discovered: set[tuple[str, str]] = set()
        for path in tracked("*.md"):
            source = (ROOT / path).read_text(encoding="utf-8")
            for version in POLICY_LINE.findall(source):
                discovered.add((version, path))
        for path in tracked("policies/*.json"):
            value = json.loads((ROOT / path).read_text(encoding="utf-8"))
            version = value.get("policy_version")
            if isinstance(version, str):
                discovered.add((version, path))
        for path in tracked("packages/**/*.py", "services/**/*.py"):
            tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
            for node in tree.body:
                if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                    continue
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names = [target.id for target in targets if isinstance(target, ast.Name)]
                if not any("POLICY" in name and name.endswith("VERSION") for name in names):
                    continue
                value_node = node.value
                try:
                    version = ast.literal_eval(value_node)
                except (ValueError, TypeError):
                    continue
                if isinstance(version, str):
                    discovered.add((version, path))

        covered = {
            (version, source)
            for version, entry in POLICY_COVERAGE.items()
            for source in entry["sources"]
        }
        self.assertEqual(discovered, covered)
        self.assertEqual(tuple(POLICY_COVERAGE), tuple(sorted(POLICY_COVERAGE)))
        for version, entry in POLICY_COVERAGE.items():
            for source in entry["sources"]:
                self.assertIn(version, (ROOT / source).read_text(encoding="utf-8"))
            assert_references(self, entry["positive"])
            assert_references(self, entry["negative"])

    def test_every_submitted_projection_and_export_is_registered(self) -> None:
        discovered_json = set(tracked("*submitted*.json"))
        covered_json = {
            path
            for entry in PROJECTION_COVERAGE.values()
            for path in entry["json"]
        }
        self.assertEqual(discovered_json, covered_json)

        discovered_symbols: set[str] = set()
        for path in tracked("apps/web/src/**/*.ts", "apps/web/src/**/*.tsx"):
            source = (ROOT / path).read_text(encoding="utf-8")
            for symbol in (*SUBMITTED_EXPORT.findall(source), *PROJECTION_EXPORT.findall(source)):
                discovered_symbols.add(f"{path}#{symbol}")
        for path in tracked("packages/**/*.py", "services/**/*.py"):
            source = (ROOT / path).read_text(encoding="utf-8")
            for symbol in PYTHON_PROJECTION.findall(source):
                discovered_symbols.add(f"{path}#{symbol}")
        covered_symbols = {
            symbol
            for entry in PROJECTION_COVERAGE.values()
            for symbol in entry["symbols"]
        }
        self.assertEqual(discovered_symbols, covered_symbols)
        self.assertEqual(tuple(PROJECTION_COVERAGE), tuple(sorted(PROJECTION_COVERAGE)))
        for entry in PROJECTION_COVERAGE.values():
            assert_references(self, entry["positive"])
            assert_references(self, entry["negative"])

    def test_every_submitted_json_fingerprint_and_private_key_is_checked(self) -> None:
        forbidden_keys = {
            "administrativeContact",
            "decimalLatitude",
            "decimalLongitude",
            "reviewerEmail",
            "reviewerId",
        }
        for path in tracked("*submitted*.json"):
            with self.subTest(path=path):
                value = json.loads((ROOT / path).read_text(encoding="utf-8"))
                integrity_fields = integrity_values(value)
                self.assertTrue(integrity_fields, path)
                for field_path, fingerprint in integrity_fields:
                    if fingerprint is None:
                        continue
                    self.assertIsInstance(fingerprint, str, field_path)
                    digest = fingerprint.removeprefix("urn:sha256:").removeprefix(
                        "sha256:"
                    )
                    self.assertRegex(digest, SHA256, field_path)
                encoded = json.dumps(value, sort_keys=True)
                for key in forbidden_keys:
                    self.assertNotIn(f'"{key}"', encoded, path)

    def test_worker_projection_rejects_invalid_submitted_live_boundary(self) -> None:
        submitted = {
            "snapshot_id": "submitted:coverage",
            "mode": "submitted",
            "artifact_fingerprint": hashlib.sha256(b"submitted").hexdigest(),
            "query_uri": "/api/snapshots/submitted",
        }
        live = {
            "snapshot_id": "live:coverage",
            "mode": "live",
            "artifact_fingerprint": hashlib.sha256(b"live").hexdigest(),
            "query_uri": "/api/snapshots/live",
        }
        projection = build_public_offline_projection(
            submitted_snapshot=submitted,
            committed_live_snapshot=live,
            heartbeat_observed_at=datetime(
                2026, 7, 18, 12, 9, tzinfo=timezone.utc
            ),
            as_of=datetime(2026, 7, 18, 12, 10, tzinfo=timezone.utc),
            stale_after=timedelta(minutes=5),
        )
        self.assertEqual(projection["current_snapshot"], live)
        with self.assertRaisesRegex(RestartError, "mode is invalid"):
            build_public_offline_projection(
                submitted_snapshot={**submitted, "mode": "live"},
                committed_live_snapshot=live,
                heartbeat_observed_at=None,
                as_of=datetime(2026, 7, 18, 12, 10, tzinfo=timezone.utc),
                stale_after=timedelta(minutes=5),
            )


if __name__ == "__main__":
    unittest.main()
