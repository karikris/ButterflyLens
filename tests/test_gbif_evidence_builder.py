from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock
from zipfile import ZIP_DEFLATED, ZipFile

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_gbif_evidence.py"


def load_builder():
    specification = importlib.util.spec_from_file_location("gbif_evidence", SCRIPT)
    if specification is None or specification.loader is None:
        raise RuntimeError("unable to load GBIF evidence builder")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


class GbifEvidenceBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = load_builder()

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.archive = self.root / "fixture.zip"
        self.receipt = self.root / "receipt.json"
        self._write_fixture()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def _tabular(fields: list[str], rows: list[dict[str, str]]) -> bytes:
        target = io.StringIO(newline="")
        writer = csv.DictWriter(
            target,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
            quoting=csv.QUOTE_NONE,
            escapechar="\\",
        )
        writer.writeheader()
        writer.writerows(rows)
        return target.getvalue().encode("utf-8")

    def _write_fixture(self) -> None:
        occurrence_fields = [
            source
            for _, source, _, _, _ in self.builder.OCCURRENCE_FIELDS
            if source is not None
        ]
        first = {field: "" for field in occurrence_fields}
        first.update(
            {
                "gbifID": "2",
                "occurrenceID": "fixture:2",
                "catalogNumber": "CAT-2",
                "datasetKey": "fixture-key",
                "datasetName": "Fixture Dataset",
                "publisher": "Fixture Publisher",
                "license": "CC_BY_4_0",
                "basisOfRecord": "HUMAN_OBSERVATION",
                "occurrenceStatus": "PRESENT",
                "eventDate": "2026-07-01",
                "year": "2026",
                "month": "7",
                "day": "1",
                "countryCode": "AU",
                "stateProvince": "Queensland",
                "decimalLatitude": "-27.5",
                "decimalLongitude": "153.0",
                "coordinateUncertaintyInMeters": "100",
                "scientificName": "Papilio fixture",
                "acceptedScientificName": "Papilio fixture",
                "taxonRank": "SPECIES",
                "taxonomicStatus": "ACCEPTED",
                "order": "Lepidoptera",
                "superfamily": "Papilionoidea",
                "family": "Papilionidae",
                "genus": "Papilio",
                "species": "Papilio fixture",
                "taxonKey": "fixture-taxon",
                "acceptedTaxonKey": "fixture-taxon",
                "superfamilyKey": "5G9",
                "hasCoordinate": "true",
                "hasGeospatialIssues": "false",
            }
        )
        second = {field: "" for field in occurrence_fields}
        second.update(
            {
                "gbifID": "1",
                "occurrenceID": "fixture:1",
                "datasetKey": "fixture-key",
                "datasetName": "Fixture Dataset",
                "license": "CC_BY_NC_4_0",
                "basisOfRecord": "PRESERVED_SPECIMEN",
                "occurrenceStatus": "PRESENT",
                "countryCode": "AU",
                "informationWithheld": "precise locality withheld",
                "dataGeneralizations": "coordinates removed",
                "scientificName": "Papilio fixture",
                "taxonRank": "SPECIES",
                "taxonomicStatus": "ACCEPTED",
                "order": "Lepidoptera",
                "superfamily": "Papilionoidea",
                "family": "Papilionidae",
                "genus": "Papilio",
                "taxonKey": "fixture-taxon",
                "superfamilyKey": "5G9",
                "issue": "COORDINATE_INVALID",
                "hasCoordinate": "false",
                "hasGeospatialIssues": "true",
            }
        )
        multimedia_fields = [
            source
            for _, source, _, _, _ in self.builder.MULTIMEDIA_FIELDS
            if source is not None
        ]
        media_rows = [
            {
                **{field: "" for field in multimedia_fields},
                "gbifID": "2",
                "type": "StillImage",
                "format": "image/jpeg",
                "identifier": "https://example.invalid/media/2.jpg",
                "references": "https://example.invalid/record/2",
                "creator": "Fixture Creator",
                "license": "CC_BY_4_0",
            },
            {
                **{field: "" for field in multimedia_fields},
                "gbifID": "1",
                "type": "StillImage",
                "format": "image/jpeg",
                "identifier": "https://example.invalid/media/1.jpg",
                "license": "CC_BY_NC_4_0",
            },
        ]
        dataset_xml = b"""<?xml version="1.0" encoding="utf-8"?>
<eml:eml xmlns:eml="https://eml.ecoinformatics.org/eml-2.2.0" packageId="fixture-key">
  <dataset>
    <alternateIdentifier>10.15468/fixture</alternateIdentifier>
    <title>Fixture Dataset</title>
    <pubDate>2026-07-01</pubDate>
    <licensed>
      <licenseName>Creative Commons Attribution 4.0 International</licenseName>
      <url>https://spdx.org/licenses/CC-BY-4.0.html</url>
      <identifier>CC-BY-4.0</identifier>
    </licensed>
  </dataset>
  <additionalMetadata><metadata><gbif>
    <dateStamp>2026-07-18T00:00:00Z</dateStamp>
    <citation>Fixture Publisher (2026). Fixture Dataset. Occurrence dataset.</citation>
  </gbif></metadata></additionalMetadata>
</eml:eml>
"""
        members = {
            "meta.xml": b"<archive/>\n",
            "metadata.xml": b"<metadata/>\n",
            "rights.txt": (
                b"Dataset: Fixture Dataset \n"
                b"Rights as supplied: http://creativecommons.org/licenses/by/4.0/legalcode\n"
            ),
            "citations.txt": (
                b"When using this dataset cite:\n"
                b"Fixture Publisher (2026). Fixture Dataset. Occurrence dataset.\n"
            ),
            "occurrence.txt": self._tabular(occurrence_fields, [first, second]),
            "verbatim.txt": b"gbifID\n2\n1\n",
            "multimedia.txt": self._tabular(multimedia_fields, media_rows),
            "dataset/fixture-key.xml": dataset_xml,
        }
        with ZipFile(self.archive, "w", compression=ZIP_DEFLATED) as archive:
            for name, payload in members.items():
                archive.writestr(name, payload)
        archive_sha256 = self.builder.sha256_file(self.archive)
        inventory_members: dict[str, dict[str, object]] = {}
        with ZipFile(self.archive) as archive:
            for name in (
                "meta.xml",
                "metadata.xml",
                "rights.txt",
                "citations.txt",
                "occurrence.txt",
                "verbatim.txt",
                "multimedia.txt",
            ):
                payload = archive.read(name)
                record: dict[str, object] = {
                    "uncompressed_bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
                if name in {"occurrence.txt", "verbatim.txt", "multimedia.txt"}:
                    record["row_count"] = payload.count(b"\n") - 1
                inventory_members[name] = record
            digest, count, size = self.builder.dataset_inventory_digest(archive)
            inventory_members["dataset_xml"] = {
                "file_count": count,
                "uncompressed_bytes": size,
                "inventory_sha256": digest,
            }
        receipt: dict[str, object] = {
            "schema_version": self.builder.RECEIPT_SCHEMA_VERSION,
            "receipt_id": "fixture",
            "verified_at": "2026-07-18T00:00:00Z",
            "provider": "Global Biodiversity Information Facility",
            "download": {
                "key": "fixture-download",
                "doi": "10.15468/fixture-download",
                "citation": "Fixture GBIF download citation",
                "download_url": "https://example.invalid/fixture.zip",
                "record_count": 2,
                "dataset_count": 1,
                "archive_bytes": self.archive.stat().st_size,
                "archive_sha256": archive_sha256,
            },
            "filter": {"country_code": "AU", "taxon_key": "5G9"},
            "rights": {
                "constituent_dataset_rights_distribution": {
                    "http://creativecommons.org/licenses/by/4.0/legalcode": 1
                }
            },
            "archive_inventory": {
                "file_count": len(members),
                "members": inventory_members,
            },
            "authority_policy": {
                "authoritative_ala_baseline": "ButterflyLens rebuilt baseline",
                "gbif_replaces_ala_baseline": False,
            },
            "evidence_policy": {
                "flickr_api_called": False,
                "media_downloaded": False,
                "absence_inference_permitted": False,
            },
        }
        receipt["receipt_fingerprint"] = hashlib.sha256(
            self.builder.canonical_json(receipt)
        ).hexdigest()
        self.receipt.write_bytes(self.builder.canonical_json(receipt) + b"\n")

    def _build(self, output: Path) -> None:
        self.builder.build(
            argparse.Namespace(
                archive=self.archive,
                receipt=self.receipt,
                output_dir=output,
                generated_at="2026-07-18T00:00:00Z",
            )
        )

    def test_offline_build_is_byte_deterministic_and_fingerprinted(self) -> None:
        first = self.root / "first"
        second = self.root / "second"
        with mock.patch.object(
            self.builder.urllib.request,
            "urlopen",
            side_effect=AssertionError("offline build attempted network access"),
        ):
            self._build(first)
            self._build(second)
        first_files = sorted(path.relative_to(first) for path in first.rglob("*") if path.is_file())
        second_files = sorted(path.relative_to(second) for path in second.rglob("*") if path.is_file())
        self.assertEqual(first_files, second_files)
        for relative in first_files:
            self.assertEqual((first / relative).read_bytes(), (second / relative).read_bytes())

        occurrences = pq.read_table(first / "gbif_occurrences.parquet")
        multimedia = pq.read_table(first / "gbif_multimedia.parquet")
        datasets = pq.read_table(first / "gbif_datasets.parquet")
        self.assertEqual(occurrences["gbif_id"].to_pylist(), ["1", "2"])
        self.assertEqual(multimedia["gbif_id"].to_pylist(), ["1", "2"])
        self.assertEqual(datasets["dataset_key"].to_pylist(), ["fixture-key"])
        self.assertTrue(
            all(
                len(value) == 64
                for value in occurrences["occurrence_evidence_fingerprint"].to_pylist()
            )
        )
        self.assertEqual(occurrences["information_withheld"].to_pylist()[0], "precise locality withheld")
        self.assertEqual(occurrences["data_generalizations"].to_pylist()[0], "coordinates removed")
        manifest = json.loads((first / "gbif_evidence_manifest.json").read_text())
        self.assertEqual(manifest["artifacts"]["occurrences"]["row_count"], 2)
        self.assertEqual(manifest["artifacts"]["multimedia"]["row_count"], 2)
        self.assertEqual(manifest["artifacts"]["datasets"]["row_count"], 1)
        self.assertFalse(manifest["policy"]["media_downloaded"])
        self.assertFalse(manifest["policy"]["flickr_api_calls_made"])
        self.assertFalse(manifest["policy"]["gbif_replaces_ala_baseline"])

    def test_archive_checksum_mismatch_fails_before_build(self) -> None:
        tampered = self.root / "tampered.zip"
        shutil.copyfile(self.archive, tampered)
        with tampered.open("ab") as handle:
            handle.write(b"tamper")
        with self.assertRaisesRegex(
            self.builder.GbifEvidenceError,
            "byte count does not match receipt",
        ):
            self.builder.build(
                argparse.Namespace(
                    archive=tampered,
                    receipt=self.receipt,
                    output_dir=self.root / "rejected",
                    generated_at="2026-07-18T00:00:00Z",
                )
            )

    def test_receipt_may_not_replace_ala_authority(self) -> None:
        receipt = json.loads(self.receipt.read_text())
        receipt["authority_policy"]["gbif_replaces_ala_baseline"] = True
        semantic = dict(receipt)
        semantic.pop("receipt_fingerprint")
        receipt["receipt_fingerprint"] = hashlib.sha256(
            self.builder.canonical_json(semantic)
        ).hexdigest()
        with self.assertRaisesRegex(
            self.builder.GbifEvidenceError,
            "does not preserve ALA authority",
        ):
            self.builder.validate_receipt(receipt)


if __name__ == "__main__":
    unittest.main()
