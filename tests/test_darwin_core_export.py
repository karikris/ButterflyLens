from __future__ import annotations

from dataclasses import asdict, replace
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
import subprocess
import sys

from butterflylens.contracts.darwin_core_export import (
    DARWIN_CORE_EXPORT_SCHEMA_VERSION,
    DARWIN_CORE_EXPORT_TABLES,
    DarwinCoreExportRequest,
    DarwinCoreMediaEvidence,
    DarwinCoreReleaseRecord,
    DarwinCoreTaxonEvidence,
    build_darwin_core_evidence_package,
    darwin_core_export_request_from_dict,
)
from butterflylens.contracts.fingerprint import canonicalize_json


def fp(index: int) -> str:
    return hashlib.sha256(str(index).encode()).hexdigest()


def record(*, occurrence_id: str = "bl-occurrence:1") -> DarwinCoreReleaseRecord:
    return DarwinCoreReleaseRecord(
        occurrence_id=occurrence_id,
        event_id=f"{occurrence_id}:event",
        location_id=f"{occurrence_id}:location",
        identification_id=f"{occurrence_id}:identification",
        release_candidate_id=f"{occurrence_id}:candidate",
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
            media_id=f"{occurrence_id}:media",
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


def request(*records: DarwinCoreReleaseRecord) -> DarwinCoreExportRequest:
    return DarwinCoreExportRequest(
        package_id="butterflylens-dwc:test-v1",
        dataset_id="butterflylens:test-dataset",
        dataset_title="ButterflyLens deterministic export fixture",
        created_at="2026-07-18T11:30:00Z",
        code_sha=fp(15),
        records=records or (record(),),
    )


def archive_files(package: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def table_rows(files: dict[str, bytes], name: str) -> list[dict[str, str]]:
    text = files[f"{name}.txt"].decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


class DarwinCoreExportTests(unittest.TestCase):
    def test_archive_has_occurrence_core_and_every_requested_extension(self) -> None:
        package = build_darwin_core_evidence_package(request())
        files = archive_files(package.archive_bytes)
        self.assertEqual(
            tuple(files),
            (
                "meta.xml",
                *(f"{name}.txt" for name in DARWIN_CORE_EXPORT_TABLES),
                "evidence-manifest.json",
            ),
        )
        root = ET.fromstring(files["meta.xml"])
        namespace = {"dwc": "http://rs.tdwg.org/dwc/text/"}
        self.assertEqual(len(root.findall("dwc:core", namespace)), 1)
        self.assertEqual(len(root.findall("dwc:extension", namespace)), 9)
        self.assertIsNotNone(root.find("dwc:core/dwc:id", namespace))
        self.assertTrue(
            all(
                extension.find("dwc:coreid", namespace) is not None
                for extension in root.findall("dwc:extension", namespace)
            )
        )

    def test_every_extension_links_to_the_occurrence_core(self) -> None:
        files = archive_files(build_darwin_core_evidence_package(request()).archive_bytes)
        for name in DARWIN_CORE_EXPORT_TABLES[1:]:
            rows = table_rows(files, name)
            self.assertTrue(rows)
            self.assertEqual({row["occurrenceID"] for row in rows}, {"bl-occurrence:1"})
        self.assertEqual(len(table_rows(files, "measurement")), 5)
        self.assertEqual(len(table_rows(files, "review")), 4)
        self.assertEqual(len(table_rows(files, "quality")), 3)

    def test_export_contains_only_generalized_location_and_fingerprint_review(self) -> None:
        package = build_darwin_core_evidence_package(request())
        decoded = package.archive_bytes.decode("latin-1")
        for forbidden in (
            "decimalLatitude",
            "decimalLongitude",
            "verbatimCoordinates",
            "reviewer_profile",
            "reviewer_id",
            "email",
        ):
            self.assertNotIn(forbidden, decoded)
        files = archive_files(package.archive_bytes)
        location = table_rows(files, "location")[0]
        self.assertEqual(location["countryCode"], "AU")
        self.assertIn("83be63fffffffff", location["locality"])
        self.assertIn("Raw coordinates", location["informationWithheld"])
        for row in table_rows(files, "review"):
            self.assertTrue(row["assertionReferences"].startswith("urn:sha256:"))
            self.assertIn("identity is intentionally excluded", row["assertionRemarks"])

    def test_media_rights_and_provenance_are_complete(self) -> None:
        files = archive_files(build_darwin_core_evidence_package(request()).archive_bytes)
        media = table_rows(files, "multimedia")[0]
        self.assertEqual(media["license"], "https://creativecommons.org/licenses/by/4.0/")
        self.assertEqual(media["rightsHolder"], "Fixture photographer")
        self.assertEqual(media["accessURI"], "")
        self.assertTrue(media["mediaFingerprint"].startswith("urn:sha256:"))
        provenance = table_rows(files, "provenance")[0]
        for field in (
            "candidateFingerprint",
            "releaseReceiptFingerprint",
            "locationReceiptFingerprint",
            "evidencePacketFingerprint",
        ):
            self.assertRegex(provenance[field], r"^urn:sha256:[0-9a-f]{64}$")

    def test_manifest_is_exact_checksums_and_not_a_publication_receipt(self) -> None:
        package = build_darwin_core_evidence_package(request())
        files = archive_files(package.archive_bytes)
        manifest = json.loads(files["evidence-manifest.json"])
        self.assertEqual(manifest["schema_version"], DARWIN_CORE_EXPORT_SCHEMA_VERSION)
        self.assertEqual(manifest["publication_state"], "prepared_not_published")
        self.assertEqual(manifest["provider_submission_state"], "not_submitted")
        self.assertFalse(manifest["contains_raw_coordinates"])
        self.assertFalse(manifest["contains_reviewer_identity"])
        self.assertFalse(manifest["contains_media_bytes"])
        self.assertEqual(tuple(manifest["table_order"]), DARWIN_CORE_EXPORT_TABLES)
        self.assertEqual(set(manifest["tables"]), set(DARWIN_CORE_EXPORT_TABLES))
        for table in manifest["tables"].values():
            content = files[table["path"]]
            self.assertEqual(table["byte_count"], len(content))
            self.assertEqual(table["sha256"], hashlib.sha256(content).hexdigest())
        preimage = dict(manifest)
        fingerprint = preimage.pop("package_fingerprint")
        self.assertEqual(fingerprint, hashlib.sha256(canonicalize_json(preimage)).hexdigest())

    def test_archive_is_byte_deterministic_and_atomic_writer_is_exact(self) -> None:
        first = build_darwin_core_evidence_package(request())
        second = build_darwin_core_evidence_package(request())
        self.assertEqual(first.archive_bytes, second.archive_bytes)
        self.assertEqual(first.archive_sha256, second.archive_sha256)
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "nested" / "evidence.zip"
            first.write_atomic(destination)
            self.assertEqual(destination.read_bytes(), first.archive_bytes)
            self.assertEqual(list(destination.parent.glob("*.tmp")), [])

    def test_release_state_publication_and_scientific_flags_fail_closed(self) -> None:
        base = record()
        with self.assertRaisesRegex(ValueError, "only a release-ready"):
            replace(base, release_state="blocked")  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "cannot assert publication"):
            replace(base, published_occurrence=True)  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "cannot assert publication"):
            replace(base, scientific_claim_allowed=True)  # type: ignore[arg-type]

    def test_expert_configuration_and_exact_rights_lineage_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "configured expert review"):
            replace(record(), expert_review_required=True)
        with self.assertRaisesRegex(ValueError, "configured expert review"):
            replace(record(), expert_review_fingerprint=fp(1))
        with self.assertRaisesRegex(ValueError, "rights fingerprints must match"):
            replace(record(), rights_fingerprint=fp(4))

    def test_unsafe_location_url_and_fingerprint_inputs_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "valid governed H3"):
            replace(record(), public_cell_id="not-an-h3-cell")
        with self.assertRaisesRegex(ValueError, "credential-free HTTPS"):
            replace(record().media, source_page_url="http://example.test/photo")
        with self.assertRaisesRegex(ValueError, "credential-free HTTPS"):
            replace(
                record().media,
                access_uri="https://objects.example.test/image.jpg?X-Amz-Signature=secret",
            )
        with self.assertRaisesRegex(ValueError, "lowercase SHA-256"):
            replace(record(), evidence_packet_fingerprint="unknown")

    def test_request_requires_sorted_unique_records_and_explicit_utc_time(self) -> None:
        first = record(occurrence_id="bl-occurrence:1")
        second = record(occurrence_id="bl-occurrence:2")
        with self.assertRaisesRegex(ValueError, "sorted"):
            request(second, first)
        with self.assertRaisesRegex(ValueError, "occurrence_id values must be unique"):
            request(first, first)
        with self.assertRaisesRegex(ValueError, "explicit UTC"):
            replace(request(first), created_at="2026-07-18")

    def test_exact_json_parser_and_cli_write_one_verified_archive(self) -> None:
        payload = json.loads(json.dumps(asdict(request())))
        parsed = darwin_core_export_request_from_dict(payload)
        self.assertEqual(parsed, request())
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            darwin_core_export_request_from_dict({**payload, "submit_to_ala": True})
        with tempfile.TemporaryDirectory() as temporary:
            input_path = Path(temporary) / "input.json"
            output_path = Path(temporary) / "output.zip"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/build_darwin_core_evidence_package.py",
                    "--input",
                    str(input_path),
                    "--output",
                    str(output_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            receipt = json.loads(completed.stdout)
            self.assertEqual(receipt["publication_state"], "prepared_not_published")
            self.assertEqual(receipt["provider_submission_state"], "not_submitted")
            self.assertEqual(
                receipt["archive_sha256"], hashlib.sha256(output_path.read_bytes()).hexdigest()
            )


if __name__ == "__main__":
    unittest.main()
