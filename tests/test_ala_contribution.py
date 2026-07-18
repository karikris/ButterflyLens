from __future__ import annotations

from dataclasses import asdict, replace
import ast
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

from butterflylens.contracts.ala_contribution import (
    ALA_CONTRIBUTION_ARTIFACTS,
    ALA_CONTRIBUTION_SCHEMA_VERSION,
    ALA_PROVIDER_CHECKS,
    AlaContributionRequest,
    AlaDatasetLicence,
    AlaDatasetMetadata,
    AlaProviderAgreementChecklist,
    AlaProviderCheck,
    AlaQualityDeclaration,
    ala_contribution_request_from_dict,
    build_ala_contribution_package,
)
from butterflylens.contracts.darwin_core_export import (
    DARWIN_CORE_EXPORT_TABLES,
    DarwinCoreExportRequest,
    DarwinCoreMediaEvidence,
    DarwinCoreReleaseRecord,
    DarwinCoreTaxonEvidence,
    build_darwin_core_evidence_package,
)
from butterflylens.contracts.fingerprint import canonicalize_json


def fp(index: int) -> str:
    return hashlib.sha256(str(index).encode()).hexdigest()


def source_package():
    record = DarwinCoreReleaseRecord(
        occurrence_id="bl-occurrence:ala-fixture",
        event_id="bl-event:ala-fixture",
        location_id="bl-location:ala-fixture",
        identification_id="bl-identification:ala-fixture",
        release_candidate_id="bl-candidate:ala-fixture",
        event_date="2026-02-03",
        public_cell_id="83be63fffffffff",
        information_withheld="Raw coordinates and reviewer identities withheld.",
        data_generalizations="Location generalized to the governed public H3 cell.",
        taxon=DarwinCoreTaxonEvidence(
            taxon_id="bltx:v1:papilio-aegeus",
            scientific_name="Papilio aegeus",
            taxon_rank="species",
            family="Papilionidae",
            genus="Papilio",
            taxon_concept_fingerprint=fp(1),
        ),
        media=DarwinCoreMediaEvidence(
            media_id="bl-media:ala-fixture",
            source_page_url="https://www.flickr.com/photos/example/123/",
            licence_url="https://creativecommons.org/licenses/by/4.0/",
            rights_holder="Fixture photographer",
            creator="Fixture photographer",
            attribution="Fixture photographer / Flickr / CC BY 4.0",
            media_fingerprint=fp(2),
            rights_fingerprint=fp(3),
            title="Human-reviewed butterfly source image",
        ),
        candidate_fingerprint=fp(4),
        release_receipt_fingerprint=fp(5),
        location_receipt_fingerprint=fp(6),
        coordinate_evidence_fingerprint=fp(7),
        date_evidence_fingerprint=fp(8),
        duplicate_independence_fingerprint=fp(9),
        human_consensus_fingerprint=fp(10),
        qualified_consensus_fingerprint=fp(11),
        expert_gate_evidence_fingerprint=fp(12),
        conflict_audit_fingerprint=fp(13),
        quality_snapshot_fingerprint=fp(14),
        quality_threshold_fingerprint=fp(15),
        evidence_packet_fingerprint=fp(16),
        rights_fingerprint=fp(3),
    )
    return build_darwin_core_evidence_package(
        DarwinCoreExportRequest(
            package_id="butterflylens-dwc:ala-fixture-v1",
            dataset_id="butterflylens:ala-fixture",
            dataset_title="ButterflyLens ALA contribution fixture",
            created_at="2026-07-18T11:30:00Z",
            code_sha=fp(17),
            records=(record,),
        )
    )


def checklist(*, passed: bool = False) -> AlaProviderAgreementChecklist:
    checks = tuple(
        AlaProviderCheck(
            check_id=check_id,
            status=(
                "passed"
                if passed or check_id != "data_provider_agreement_executed"
                else "pending"
            ),
            evidence_reference=(
                f"urn:sha256:{fp(index + 30)}"
                if passed or check_id != "data_provider_agreement_executed"
                else None
            ),
            note=(
                "Fixture agreement remains pending."
                if not passed and check_id == "data_provider_agreement_executed"
                else None
            ),
        )
        for index, check_id in enumerate(ALA_PROVIDER_CHECKS)
    )
    return AlaProviderAgreementChecklist(checks=checks)


def request(*, passed: bool = False) -> tuple[AlaContributionRequest, bytes]:
    source = source_package()
    citation = "ButterflyLens contributors (2026). ButterflyLens ALA contribution fixture."
    licence_url = "https://creativecommons.org/licenses/by/4.0/"
    value = AlaContributionRequest(
        package_id="butterflylens-ala:fixture-v1",
        prepared_at="2026-07-18T12:00:00Z",
        code_sha=fp(18),
        source_archive_sha256=source.archive_sha256,
        source_package_fingerprint=source.package_fingerprint,
        dataset=AlaDatasetMetadata(
            dataset_id="butterflylens:ala-fixture",
            title="ButterflyLens ALA contribution fixture",
            description="Release-ready Australian butterfly occurrence evidence.",
            purpose="Support inspectable biodiversity evidence without asserting scientific truth.",
            geographic_scope="Australia; locations generalized to governed public H3 cells.",
            taxonomic_scope="Australian Papilionoidea represented by the authoritative baseline.",
            temporal_scope="2026",
            methods=(
                "Rights checks, independent human review, release gates, and "
                "deterministic export."
            ),
            creator_name="ButterflyLens contributors",
            creator_organisation="ButterflyLens",
            administrative_contact_name="Fixture Data Management Team",
            administrative_contact_email="data@example.invalid",
            provider_url="https://karikris.github.io/ButterflyLens/",
            citation=citation,
            keywords=("Australia", "ButterflyLens", "Papilionoidea", "butterflies"),
        ),
        licence=AlaDatasetLicence(
            identifier="CC-BY-4.0",
            url=licence_url,
            rights_holder="ButterflyLens contributors",
            rights_authority_fingerprint=fp(19),
        ),
        provider_checklist=checklist(passed=passed),
        quality=AlaQualityDeclaration(
            unresolved_blockers=(),
            limitations=(
                "No provider acceptance or publication is implied.",
                "The fixture is software evidence, not a live biodiversity contribution.",
            ),
            representative_audit_reviewed=True,
        ),
        attribution_statement=(
            f"{citation} Creator organisation: ButterflyLens. Dataset licence: {licence_url} "
            "Record-specific media rights, creators, attribution, licences, and "
            "source links remain authoritative."
        ),
    )
    return value, source.archive_bytes


def files(value: bytes) -> tuple[tuple[str, ...], dict[str, bytes]]:
    with zipfile.ZipFile(io.BytesIO(value)) as archive:
        names = tuple(archive.namelist())
        return names, {name: archive.read(name) for name in names}


class AlaContributionTests(unittest.TestCase):
    def test_archive_preserves_dwc_and_adds_every_requested_artifact(self) -> None:
        value, source = request()
        package = build_ala_contribution_package(value, source)
        names, members = files(package.archive_bytes)
        self.assertEqual(names[0:2], ("meta.xml", "eml.xml"))
        self.assertEqual(
            names[2 : 2 + len(DARWIN_CORE_EXPORT_TABLES)],
            tuple(f"{name}.txt" for name in DARWIN_CORE_EXPORT_TABLES),
        )
        self.assertEqual(names[-1], "ala-evidence-manifest.json")
        self.assertTrue(set(ALA_CONTRIBUTION_ARTIFACTS).issubset(members))
        _, source_members = files(source)
        for name, content in source_members.items():
            self.assertEqual(members[name], content)

    def test_eml_contains_all_mandatory_ala_metadata(self) -> None:
        value, source = request()
        _, members = files(build_ala_contribution_package(value, source).archive_bytes)
        eml = members["eml.xml"].decode()
        ET.fromstring(eml)
        for expected in (
            value.dataset.title,
            value.dataset.description,
            value.dataset.creator_name,
            value.dataset.creator_organisation,
            value.dataset.administrative_contact_name,
            value.dataset.administrative_contact_email,
            value.dataset.provider_url,
            value.dataset.citation,
            value.licence.url,
        ):
            self.assertIn(expected, eml)

    def test_dataset_licence_and_attribution_retain_media_rights(self) -> None:
        value, source = request()
        _, members = files(build_ala_contribution_package(value, source).archive_bytes)
        licence = json.loads(members["licence.json"])
        self.assertEqual(licence["identifier"], "CC-BY-4.0")
        self.assertTrue(licence["applies_to_dataset_records"])
        self.assertTrue(licence["third_party_media_licences_retained"])
        attribution = members["attribution.txt"].decode()
        self.assertIn(value.dataset.citation, attribution)
        self.assertIn("Record-specific media rights", attribution)

    def test_pending_provider_agreement_is_an_explicit_blocker(self) -> None:
        value, source = request()
        package = build_ala_contribution_package(value, source)
        self.assertEqual(package.preparation_state, "blocked_pending_provider_requirements")
        _, members = files(package.archive_bytes)
        checks = json.loads(members["provider-agreement-checklist.json"])
        self.assertFalse(checks["passed"])
        agreement = next(
            check
            for check in checks["checks"]
            if check["check_id"] == "data_provider_agreement_executed"
        )
        self.assertEqual(agreement["status"], "pending")
        self.assertIsNone(agreement["evidence_reference"])

    def test_all_evidenced_checks_are_ready_only_for_human_submission(self) -> None:
        value, source = request(passed=True)
        package = build_ala_contribution_package(value, source)
        self.assertEqual(package.preparation_state, "ready_for_human_submission")
        manifest = package.manifest
        self.assertEqual(manifest["provider_submission_state"], "not_submitted")
        self.assertTrue(manifest["human_submission_required"])
        self.assertFalse(manifest["automatic_submission_available"])
        self.assertEqual(manifest["publication_state"], "prepared_not_published")

    def test_quality_report_uses_receipts_without_fabricated_metrics(self) -> None:
        value, source = request()
        package = build_ala_contribution_package(value, source)
        _, members = files(package.archive_bytes)
        report = json.loads(members["quality-report.json"])
        self.assertEqual(report["record_count"], 1)
        self.assertEqual(report["release_receipt_count"], 1)
        self.assertEqual(report["representative_audit_fingerprints"], [fp(14)])
        self.assertFalse(report["targeted_failure_discovery_used_as_population_metric"])
        self.assertFalse(report["model_score_interpreted_as_probability"])
        self.assertFalse(report["absence_claimed_from_no_detection"])
        blocked = replace(
            value,
            quality=replace(
                value.quality,
                unresolved_blockers=("operator quality approval pending",),
            ),
        )
        self.assertEqual(
            build_ala_contribution_package(blocked, source).preparation_state,
            "blocked_quality_review",
        )

    def test_source_archive_tamper_and_identity_mismatch_fail_closed(self) -> None:
        value, source = request()
        with self.assertRaisesRegex(ValueError, "SHA-256 does not match"):
            build_ala_contribution_package(replace(value, source_archive_sha256=fp(99)), source)
        names, members = files(source)
        members["occurrence.txt"] += b"tamper"
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            for name in names:
                archive.writestr(name, members[name])
        tampered = output.getvalue()
        tampered_request = replace(
            value, source_archive_sha256=hashlib.sha256(tampered).hexdigest()
        )
        with self.assertRaisesRegex(ValueError, "(byte count|checksum) mismatch"):
            build_ala_contribution_package(tampered_request, tampered)

    def test_archive_is_deterministic_atomic_and_manifest_is_exact(self) -> None:
        value, source = request()
        first = build_ala_contribution_package(value, source)
        second = build_ala_contribution_package(value, source)
        self.assertEqual(first.archive_bytes, second.archive_bytes)
        _, members = files(first.archive_bytes)
        manifest = json.loads(members["ala-evidence-manifest.json"])
        self.assertEqual(manifest["schema_version"], ALA_CONTRIBUTION_SCHEMA_VERSION)
        preimage = dict(manifest)
        fingerprint = preimage.pop("package_fingerprint")
        self.assertEqual(fingerprint, hashlib.sha256(canonicalize_json(preimage)).hexdigest())
        for name, item in manifest["files"].items():
            self.assertEqual(item["sha256"], hashlib.sha256(members[name]).hexdigest())
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "nested" / "ala.zip"
            first.write_atomic(destination)
            self.assertEqual(destination.read_bytes(), first.archive_bytes)
            self.assertEqual(list(destination.parent.glob("*.tmp")), [])

    def test_exact_parser_and_cli_prepare_one_archive_without_submission(self) -> None:
        value, source = request()
        payload = json.loads(json.dumps(asdict(value)))
        self.assertEqual(ala_contribution_request_from_dict(payload), value)
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            ala_contribution_request_from_dict({**payload, "submit": True})
        with tempfile.TemporaryDirectory() as temporary:
            request_path = Path(temporary) / "request.json"
            source_path = Path(temporary) / "source.zip"
            output_path = Path(temporary) / "ala.zip"
            request_path.write_text(json.dumps(payload), encoding="utf-8")
            source_path.write_bytes(source)
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/prepare_ala_contribution.py",
                    "--input",
                    str(request_path),
                    "--darwin-core-archive",
                    str(source_path),
                    "--output",
                    str(output_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            receipt = json.loads(completed.stdout)
            self.assertEqual(receipt["provider_submission_state"], "not_submitted")
            self.assertTrue(receipt["human_submission_required"])
            self.assertEqual(
                receipt["archive_sha256"],
                hashlib.sha256(output_path.read_bytes()).hexdigest(),
            )

    def test_private_contact_is_explicit_but_sensitive_evidence_stays_excluded(self) -> None:
        value, source = request()
        package = build_ala_contribution_package(value, source)
        decoded = package.archive_bytes.decode("latin-1")
        self.assertTrue(package.manifest["contains_administrative_contact"])
        self.assertEqual(package.manifest["intended_access"], "private_operator_handoff")
        for forbidden in ("decimalLatitude", "decimalLongitude", "reviewer_profile", "reviewer_id"):
            self.assertNotIn(forbidden, decoded)
        self.assertFalse(package.manifest["contains_raw_coordinates"])
        self.assertFalse(package.manifest["contains_reviewer_identity"])
        self.assertFalse(package.manifest["contains_media_bytes"])

    def test_cli_and_contract_have_no_network_submission_dependency(self) -> None:
        paths = (
            Path("packages/contracts/python/butterflylens/contracts/ala_contribution.py"),
            Path("scripts/prepare_ala_contribution.py"),
        )
        forbidden_imports = {"http", "requests", "socket", "smtplib", "urllib.request"}
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imports = {
                alias.name
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            } | {
                node.module or ""
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
            }
            self.assertTrue(forbidden_imports.isdisjoint(imports))
        help_text = subprocess.run(
            [sys.executable, "scripts/prepare_ala_contribution.py", "--help"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertNotIn("--submit", help_text)


if __name__ == "__main__":
    unittest.main()
