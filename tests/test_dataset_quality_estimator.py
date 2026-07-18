from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))
sys.path.insert(0, str(ROOT / "packages/verification/python"))

from butterflylens_verification import (  # noqa: E402
    AuditPlan,
    AuditRecord,
    QualityEvidenceError,
    SamplingStratum,
    estimate_dataset_quality,
    quality_storage_fields,
)
from butterflylens_verification.dataset_quality import (  # noqa: E402
    INCLUSION_PROBABILITY_METHOD,
)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def plan(kind: str = "representative_audit") -> AuditPlan:
    representative = kind == "representative_audit"
    return AuditPlan(
        plan_id=f"plan:{kind}",
        audit_kind=kind,
        design="stratified_random" if representative else "targeted_priority",
        representative=representative,
        blind=True,
        inclusion_probability_method=(
            INCLUSION_PROBABILITY_METHOD if representative else None
        ),
        sampling_frame_fingerprint=digest("sampling-frame"),
        grouping_keys=("owner_id", "observation_id"),
        strata=(
            SamplingStratum("stratum:north", "North", 600, 0.6),
            SamplingStratum("stratum:south", "South", 400, 0.4),
        ),
    )


def records() -> list[AuditRecord]:
    outcomes = (
        ("stratum:north", "supported"),
        ("stratum:north", "supported"),
        ("stratum:north", "supported"),
        ("stratum:north", "not_supported"),
        ("stratum:south", "supported"),
        ("stratum:south", "not_supported"),
        ("stratum:south", "uncertain"),
        ("stratum:south", "media_failure"),
    )
    return [
        AuditRecord(
            record_id=f"record:{index}",
            stratum_id=stratum,
            inclusion_probability=0.1,
            owner_group_id=f"owner:{index}",
            observation_group_id=f"observation:{index}",
            outcome=outcome,
            consensus_status={
                "supported": "complete_agreement",
                "not_supported": "complete_agreement",
                "uncertain": "uncertain_only",
                "media_failure": "media_failure",
            }[outcome],
            review_fingerprint=digest(f"review:{index}"),
            consensus_fingerprint=digest(f"consensus:{index}"),
        )
        for index, (stratum, outcome) in enumerate(outcomes, start=1)
    ]


def estimate(
    audit_plan: AuditPlan | None = None,
    audit_records: list[AuditRecord] | None = None,
) -> dict[str, object]:
    return estimate_dataset_quality(
        quality_snapshot_id="quality:fixture",
        project_id="project:butterflies",
        run_id="run:quality",
        plan=audit_plan or plan(),
        records=records() if audit_records is None else audit_records,
        generated_at="2026-07-18T04:00:00Z",
        bootstrap_seed="credential-free-fixture-seed",
        bootstrap_replicates=200,
    )


class DatasetQualityEstimatorTests(unittest.TestCase):
    def test_stratified_hajek_estimate_ess_and_grouped_interval(self) -> None:
        result = estimate()
        self.assertEqual(result["availability"], "estimated")
        self.assertAlmostEqual(result["precision_estimate"], 0.65)
        self.assertAlmostEqual(result["effective_sample_size"], 1 / 0.17)
        self.assertEqual(result["decisive_reviews"], 6)
        self.assertEqual(result["supported_count"], 4)
        self.assertEqual(result["failure_count"], 2)
        self.assertEqual(result["unresolved_count"], 2)
        self.assertEqual(result["resampling_group_count"], 6)
        self.assertEqual(
            result["interval"]["method"],
            "stratified_owner_observation_group_bootstrap_v1",
        )
        self.assertLessEqual(result["interval"]["lower"], 0.65)
        self.assertGreaterEqual(result["interval"]["upper"], 0.65)
        self.assertTrue(result["population_estimate_allowed"])
        self.assertFalse(result["model_vote_included"])
        self.assertRegex(result["audit_evidence_fingerprint"], r"^[0-9a-f]{64}$")
        self.assertEqual(len(result["audit_records"]), result["reviewed_sample"])
        self.assertNotIn("owner:1", json.dumps(result["audit_records"]))
        self.assertRegex(
            result["audit_records"][0]["owner_group_fingerprint"], r"^[0-9a-f]{64}$"
        )

    def test_output_is_order_stable_and_contract_valid(self) -> None:
        forward = estimate()
        reverse = estimate(audit_records=list(reversed(records())))
        self.assertEqual(forward, reverse)
        registry = Registry()
        schemas: dict[str, dict[str, object]] = {}
        for path in sorted((ROOT / "packages/contracts/schemas").glob("*.schema.json")):
            schema = json.loads(path.read_text(encoding="utf-8"))
            schemas[schema["$id"]] = schema
            registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
        validator = Draft202012Validator(
            schemas["urn:butterflylens:schema:quality-snapshot:v1.0.0"],
            registry=registry,
            format_checker=FormatChecker(),
        )
        errors = sorted(validator.iter_errors(forward), key=lambda error: list(error.path))
        self.assertEqual([], [error.message for error in errors])
        self.assertRegex(forward["snapshot_fingerprint"], r"^[0-9a-f]{64}$")

    def test_targeted_queue_never_emits_population_statistics(self) -> None:
        result = estimate(audit_plan=plan("targeted_failure_discovery"))
        self.assertEqual(result["availability"], "unavailable")
        self.assertIsNone(result["precision_estimate"])
        self.assertIsNone(result["interval"])
        self.assertIsNone(result["effective_sample_size"])
        self.assertFalse(result["population_estimate_allowed"])
        self.assertIn(
            "targeted_failure_discovery_is_not_population_representative",
            result["blockers"],
        )
        stored = quality_storage_fields(result)
        self.assertIsNone(stored["precision_estimate"])
        self.assertIsNone(stored["interval_lower"])

    def test_missing_group_or_inclusion_probability_fails_closed(self) -> None:
        first = records()[0]
        broken = [
            AuditRecord(
                record_id=first.record_id,
                stratum_id=first.stratum_id,
                inclusion_probability=None,
                owner_group_id=None,
                observation_group_id=first.observation_group_id,
                outcome=first.outcome,
                consensus_status=first.consensus_status,
                review_fingerprint=first.review_fingerprint,
                consensus_fingerprint=first.consensus_fingerprint,
            ),
            *records()[1:],
        ]
        result = estimate(audit_records=broken)
        self.assertEqual(result["availability"], "unavailable")
        self.assertIsNone(result["precision_estimate"])
        self.assertIn("invalid_inclusion_probability:record:1", result["blockers"])
        self.assertIn("owner_group_missing:record:1", result["blockers"])

    def test_owner_or_observation_connected_component_cannot_cross_strata(self) -> None:
        audit_records = records()
        south = audit_records[4]
        audit_records[4] = AuditRecord(
            record_id=south.record_id,
            stratum_id=south.stratum_id,
            inclusion_probability=south.inclusion_probability,
            owner_group_id=audit_records[0].owner_group_id,
            observation_group_id=south.observation_group_id,
            outcome=south.outcome,
            consensus_status=south.consensus_status,
            review_fingerprint=south.review_fingerprint,
            consensus_fingerprint=south.consensus_fingerprint,
        )
        result = estimate(audit_records=audit_records)
        self.assertEqual(result["availability"], "unavailable")
        self.assertIn("owner_observation_group_crosses_strata", result["blockers"])

    def test_every_stratum_requires_decisive_evidence(self) -> None:
        result = estimate(
            audit_records=[record for record in records() if record.stratum_id == "stratum:north"]
        )
        self.assertEqual(result["availability"], "unavailable")
        self.assertIn(
            "stratum_without_decisive_reviews:stratum:south", result["blockers"]
        )

    def test_malformed_evidence_raises_instead_of_coercing(self) -> None:
        duplicate = [records()[0], records()[0]]
        with self.assertRaisesRegex(QualityEvidenceError, "IDs must be unique"):
            estimate(audit_records=duplicate)
        with self.assertRaisesRegex(QualityEvidenceError, "at least 200"):
            estimate_dataset_quality(
                quality_snapshot_id="quality:fixture",
                project_id="project:butterflies",
                run_id="run:quality",
                plan=plan(),
                records=records(),
                generated_at="2026-07-18T04:00:00Z",
                bootstrap_seed="fixture",
                bootstrap_replicates=199,
            )

    def test_decisive_outcome_requires_resolved_human_consensus(self) -> None:
        first = records()[0]
        broken = [
            AuditRecord(
                record_id=first.record_id,
                stratum_id=first.stratum_id,
                inclusion_probability=first.inclusion_probability,
                owner_group_id=first.owner_group_id,
                observation_group_id=first.observation_group_id,
                outcome="supported",
                consensus_status="unresolved_disagreement",
                review_fingerprint=first.review_fingerprint,
                consensus_fingerprint=first.consensus_fingerprint,
            ),
            *records()[1:],
        ]
        with self.assertRaisesRegex(QualityEvidenceError, "contradicts"):
            estimate(audit_records=broken)


if __name__ == "__main__":
    unittest.main()
