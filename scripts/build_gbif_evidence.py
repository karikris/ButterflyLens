#!/usr/bin/env python3
"""Acquire and build the fingerprinted ButterflyLens GBIF evidence pack.

Network access is confined to the explicit ``acquire`` command. The ``build``
command consumes a locally supplied, receipt-matched Darwin Core Archive and
produces deterministic Parquet projections without downloading media.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
from typing import Any
import urllib.request
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZipInfo


RECEIPT_SCHEMA_VERSION = "butterflylens-gbif-download-receipt/v1"
MANIFEST_SCHEMA_VERSION = "butterflylens-gbif-evidence-manifest/v1"
OCCURRENCE_SCHEMA_VERSION = "butterflylens-gbif-occurrence-evidence/v1"
MULTIMEDIA_SCHEMA_VERSION = "butterflylens-gbif-multimedia-evidence/v1"
DATASET_SCHEMA_VERSION = "butterflylens-gbif-dataset-evidence/v1"
PARQUET_SCHEMA_VERSION = "butterflylens-parquet-schema/v1"
USER_AGENT = (
    "ButterflyLens/0.1 (+https://github.com/karikris/ButterflyLens; "
    "GBIF receipt-bound evidence acquisition)"
)
ROOT = Path(__file__).resolve().parents[1]

FieldSpec = tuple[str, str | None, str, bool, str]


OCCURRENCE_FIELDS: tuple[FieldSpec, ...] = (
    ("source_download_key", None, "string", False, "Frozen GBIF download key."),
    ("source_archive_sha256", None, "string", False, "Physical SHA-256 of the source DWCA."),
    ("source_row_number", None, "int64", False, "One-based source occurrence row number."),
    ("source_record_fingerprint", None, "string", False, "SHA-256 of the selected exact source field vector."),
    ("occurrence_evidence_fingerprint", None, "string", False, "Archive-bound SHA-256 evidence identity."),
    ("gbif_id", "gbifID", "string", False, "GBIF occurrence identifier."),
    ("occurrence_id", "occurrenceID", "string", True, "Publisher occurrence identifier."),
    ("catalog_number", "catalogNumber", "string", True, "Publisher catalogue number."),
    ("dataset_key", "datasetKey", "string", False, "GBIF constituent dataset key."),
    ("dataset_name", "datasetName", "string", True, "Constituent dataset name."),
    ("publisher", "publisher", "string", True, "Occurrence publisher."),
    ("bibliographic_citation", "bibliographicCitation", "string", True, "Record bibliographic citation."),
    ("source_reference", "references", "string", True, "Provider record reference."),
    ("licence", "license", "string", False, "GBIF-processed per-record licence."),
    ("rights_holder", "rightsHolder", "string", True, "Provider rights holder."),
    ("basis_of_record", "basisOfRecord", "string", True, "GBIF-processed basis of record."),
    ("occurrence_status", "occurrenceStatus", "string", True, "Provider occurrence status."),
    ("sex", "sex", "string", True, "Provider sex assertion."),
    ("life_stage", "lifeStage", "string", True, "Provider life-stage assertion."),
    ("event_date", "eventDate", "string", True, "GBIF-processed event date."),
    ("year", "year", "int32", True, "GBIF-processed event year."),
    ("month", "month", "int8", True, "GBIF-processed event month."),
    ("day", "day", "int8", True, "GBIF-processed event day."),
    ("country_code", "countryCode", "string", True, "Darwin Core country code."),
    ("state_province", "stateProvince", "string", True, "Public processed state or province."),
    ("locality", "locality", "string", True, "Public processed locality; may be generalised."),
    ("decimal_latitude", "decimalLatitude", "float64", True, "Public GBIF-processed WGS84 latitude."),
    ("decimal_longitude", "decimalLongitude", "float64", True, "Public GBIF-processed WGS84 longitude."),
    ("coordinate_uncertainty_meters", "coordinateUncertaintyInMeters", "float64", True, "Provider coordinate uncertainty in metres."),
    ("information_withheld", "informationWithheld", "string", True, "Exact information-withheld text."),
    ("data_generalizations", "dataGeneralizations", "string", True, "Exact data-generalisation text."),
    ("scientific_name", "scientificName", "string", True, "GBIF-processed scientific-name assertion."),
    ("accepted_scientific_name", "acceptedScientificName", "string", True, "GBIF-processed accepted-name assertion."),
    ("vernacular_name", "vernacularName", "string", True, "Provider vernacular-name assertion."),
    ("taxon_rank", "taxonRank", "string", True, "GBIF-processed taxon rank."),
    ("taxonomic_status", "taxonomicStatus", "string", True, "GBIF-processed taxonomic status."),
    ("order_name", "order", "string", True, "GBIF-processed order assertion."),
    ("superfamily_name", "superfamily", "string", True, "GBIF-processed superfamily assertion."),
    ("family_name", "family", "string", True, "GBIF-processed family assertion."),
    ("subfamily_name", "subfamily", "string", True, "GBIF-processed subfamily assertion."),
    ("tribe_name", "tribe", "string", True, "GBIF-processed tribe assertion."),
    ("genus_name", "genus", "string", True, "GBIF-processed genus assertion."),
    ("species_name", "species", "string", True, "GBIF-processed species assertion."),
    ("taxon_key", "taxonKey", "string", True, "Catalogue of Life taxon key."),
    ("accepted_taxon_key", "acceptedTaxonKey", "string", True, "Catalogue of Life accepted taxon key."),
    ("superfamily_key", "superfamilyKey", "string", True, "Catalogue of Life superfamily key."),
    ("family_key", "familyKey", "string", True, "Catalogue of Life family key."),
    ("species_key", "speciesKey", "string", True, "Catalogue of Life species key."),
    ("issue", "issue", "string", True, "Exact ordered GBIF issue codes."),
    ("taxonomic_issue", "taxonomicIssue", "string", True, "Exact GBIF taxonomic issue codes."),
    ("non_taxonomic_issue", "nonTaxonomicIssue", "string", True, "Exact GBIF non-taxonomic issue codes."),
    ("media_type", "mediaType", "string", True, "GBIF media-type summary."),
    ("has_coordinate", "hasCoordinate", "bool", False, "GBIF processed coordinate-presence flag."),
    ("has_geospatial_issues", "hasGeospatialIssues", "bool", False, "GBIF processed geospatial-warning flag."),
    ("last_interpreted", "lastInterpreted", "string", True, "GBIF interpretation timestamp."),
)

MULTIMEDIA_FIELDS: tuple[FieldSpec, ...] = (
    ("source_download_key", None, "string", False, "Frozen GBIF download key."),
    ("source_archive_sha256", None, "string", False, "Physical SHA-256 of the source DWCA."),
    ("source_row_number", None, "int64", False, "One-based source multimedia row number."),
    ("source_record_fingerprint", None, "string", False, "SHA-256 of the exact source multimedia field vector."),
    ("media_evidence_fingerprint", None, "string", False, "Archive-bound SHA-256 media-metadata identity."),
    ("gbif_id", "gbifID", "string", False, "Parent GBIF occurrence identifier."),
    ("media_type", "type", "string", True, "Darwin Core media type."),
    ("format", "format", "string", True, "Provider media MIME type."),
    ("identifier", "identifier", "string", True, "Provider media identifier URL or value; no bytes fetched."),
    ("media_reference", "references", "string", True, "Provider media landing-page reference."),
    ("title", "title", "string", True, "Provider media title."),
    ("description", "description", "string", True, "Provider media description."),
    ("source", "source", "string", True, "Provider media source."),
    ("audience", "audience", "string", True, "Provider audience assertion."),
    ("created", "created", "string", True, "Provider creation date or timestamp."),
    ("creator", "creator", "string", True, "Provider creator attribution."),
    ("contributor", "contributor", "string", True, "Provider contributor attribution."),
    ("publisher", "publisher", "string", True, "Provider media publisher."),
    ("licence", "license", "string", True, "Provider media licence."),
    ("rights_holder", "rightsHolder", "string", True, "Provider media rights holder."),
)

DATASET_FIELDS: tuple[FieldSpec, ...] = (
    ("source_download_key", None, "string", False, "Frozen GBIF download key."),
    ("source_archive_sha256", None, "string", False, "Physical SHA-256 of the source DWCA."),
    ("dataset_key", None, "string", False, "GBIF dataset key and XML package identifier."),
    ("title", None, "string", False, "Constituent dataset title."),
    ("doi", None, "string", True, "Dataset DOI when supplied in EML."),
    ("publication_date", None, "string", True, "Dataset publication date from EML."),
    ("metadata_updated", None, "string", True, "GBIF dataset metadata timestamp."),
    ("licence_name", None, "string", True, "Dataset EML licence name."),
    ("licence_url", None, "string", True, "Dataset EML licence URL."),
    ("licence_identifier", None, "string", True, "Dataset EML licence identifier."),
    ("rights_as_supplied", None, "string", False, "Exact rights.txt value for the dataset."),
    ("citation", None, "string", False, "Exact GBIF dataset citation from EML."),
    ("selected_occurrence_count", None, "int64", False, "Occurrences in this exact download."),
    ("dataset_metadata_xml_sha256", None, "string", False, "Physical SHA-256 of the dataset EML member."),
    ("dataset_evidence_fingerprint", None, "string", False, "SHA-256 of the semantic dataset evidence row."),
)


class GbifEvidenceError(RuntimeError):
    """Raised when a GBIF evidence or build invariant is violated."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_json(value) + b"\n")
    os.replace(temporary, path)


def write_pretty_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def ordered_mapping(value: dict[str, Any], key_order: tuple[str, ...]) -> dict[str, Any]:
    return {
        key: value[key]
        for key in (*key_order, *(key for key in value if key not in key_order))
        if key in value
    }


def ordered_rights_manifest(value: dict[str, Any]) -> dict[str, Any]:
    source_order = (
        "source_id",
        "provider",
        "dataset",
        "source_url",
        "retrieved_at",
        "licence",
        "licence_url",
        "terms_url",
        "citation_guidance_url",
        "attribution",
        "scope_note",
    )
    artifact_order = (
        "path",
        "fingerprint",
        "provider",
        "source_id",
        "licence",
        "attribution",
        "processing_allowed",
        "display_allowed",
        "redistribution_allowed",
        "removal_state",
        "scope_note",
    )
    result = ordered_mapping(
        value,
        ("schema_version", "generated_at", "sources", "artifacts"),
    )
    result["sources"] = [ordered_mapping(row, source_order) for row in value["sources"]]
    result["artifacts"] = [
        ordered_mapping(row, artifact_order) for row in value["artifacts"]
    ]
    return result


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_member(info: ZipInfo) -> bool:
    path = PurePosixPath(info.filename)
    mode = info.external_attr >> 16
    return (
        bool(info.filename)
        and not path.is_absolute()
        and ".." not in path.parts
        and not (mode and stat.S_ISLNK(mode))
    )


def member_digest(archive: ZipFile, name: str) -> tuple[str, int]:
    digest = hashlib.sha256()
    lines = 0
    with archive.open(name) as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
            lines += chunk.count(b"\n")
    return digest.hexdigest(), lines


def dataset_inventory_digest(archive: ZipFile) -> tuple[str, int, int]:
    parts: list[bytes] = []
    size = 0
    names = sorted(
        info.filename
        for info in archive.infolist()
        if info.filename.startswith("dataset/") and info.filename.endswith(".xml")
    )
    for name in names:
        payload = archive.read(name)
        size += len(payload)
        parts.append(f"{name}\0{sha256_bytes(payload)}\n".encode())
    return sha256_bytes(b"".join(parts)), len(names), size


def validate_receipt(receipt: dict[str, Any]) -> None:
    if receipt.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        raise GbifEvidenceError("unexpected GBIF receipt schema")
    semantic = dict(receipt)
    expected = semantic.pop("receipt_fingerprint", None)
    if expected != sha256_bytes(canonical_json(semantic)):
        raise GbifEvidenceError("GBIF receipt fingerprint mismatch")
    if receipt["authority_policy"].get("gbif_replaces_ala_baseline") is not False:
        raise GbifEvidenceError("GBIF receipt does not preserve ALA authority")
    if receipt["evidence_policy"].get("flickr_api_called") is not False:
        raise GbifEvidenceError("GBIF receipt violates the no-Flickr boundary")


def validate_archive(path: Path, receipt: dict[str, Any]) -> None:
    download = receipt["download"]
    if path.stat().st_size != download["archive_bytes"]:
        raise GbifEvidenceError("GBIF source archive byte count does not match receipt")
    if sha256_file(path) != download["archive_sha256"]:
        raise GbifEvidenceError("GBIF source archive checksum does not match receipt")
    inventory = receipt["archive_inventory"]
    with ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) != inventory["file_count"]:
            raise GbifEvidenceError("GBIF archive file count does not match receipt")
        if any(not safe_member(info) for info in infos):
            raise GbifEvidenceError("GBIF archive contains an unsafe member path")
        corrupt = archive.testzip()
        if corrupt is not None:
            raise GbifEvidenceError(f"GBIF archive member failed CRC: {corrupt}")
        for name, expected in inventory["members"].items():
            if name == "dataset_xml":
                digest, count, size = dataset_inventory_digest(archive)
                if (
                    digest != expected["inventory_sha256"]
                    or count != expected["file_count"]
                    or size != expected["uncompressed_bytes"]
                ):
                    raise GbifEvidenceError("GBIF dataset XML inventory mismatch")
                continue
            if name not in archive.namelist():
                raise GbifEvidenceError(f"GBIF archive is missing {name}")
            digest, line_count = member_digest(archive, name)
            if digest != expected["sha256"]:
                raise GbifEvidenceError(f"GBIF member checksum mismatch: {name}")
            if archive.getinfo(name).file_size != expected["uncompressed_bytes"]:
                raise GbifEvidenceError(f"GBIF member size mismatch: {name}")
            if "row_count" in expected and line_count - 1 != expected["row_count"]:
                raise GbifEvidenceError(f"GBIF member row count mismatch: {name}")


def acquire(args: argparse.Namespace) -> None:
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    validate_receipt(receipt)
    if args.output.exists():
        validate_archive(args.output, receipt)
        print(json.dumps({"archive": str(args.output), "status": "verified_existing"}, sort_keys=True))
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    request = urllib.request.Request(
        receipt["download"]["download_url"],
        headers={"User-Agent": USER_AGENT, "Accept": "application/zip"},
    )
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response, temporary.open("wb") as target:
            while chunk := response.read(8 * 1024 * 1024):
                target.write(chunk)
        validate_archive(temporary, receipt)
        os.replace(temporary, args.output)
    finally:
        temporary.unlink(missing_ok=True)
    print(
        json.dumps(
            {
                "archive": str(args.output),
                "sha256": sha256_file(args.output),
                "status": "downloaded_and_verified",
            },
            sort_keys=True,
        )
    )


def arrow_type(pa: Any, name: str) -> Any:
    return {
        "string": pa.string(),
        "int8": pa.int8(),
        "int32": pa.int32(),
        "int64": pa.int64(),
        "float64": pa.float64(),
        "bool": pa.bool_(),
    }[name]


def read_member_table(archive: ZipFile, name: str, source_fields: list[str]) -> Any:
    import pyarrow as pa
    import pyarrow.csv as pacsv

    with archive.open(name) as handle:
        return pacsv.read_csv(
            handle,
            read_options=pacsv.ReadOptions(block_size=8 * 1024 * 1024, use_threads=True),
            parse_options=pacsv.ParseOptions(
                delimiter="\t",
                quote_char=False,
                newlines_in_values=False,
            ),
            convert_options=pacsv.ConvertOptions(
                include_columns=source_fields,
                column_types={field: pa.string() for field in source_fields},
                strings_can_be_null=True,
                null_values=[""],
            ),
        )


def fingerprint_columns(
    raw: Any,
    source_fields: list[str],
    *,
    archive_sha256: str,
    download_key: str,
    member: str,
) -> tuple[list[str], list[str]]:
    source_fingerprints: list[str] = []
    evidence_fingerprints: list[str] = []
    row_number = 0
    for batch in raw.to_batches(max_chunksize=65_536):
        columns = batch.to_pydict()
        for index in range(batch.num_rows):
            row_number += 1
            values = [columns[field][index] for field in source_fields]
            source_fingerprint = sha256_bytes(canonical_json(values))
            evidence_fingerprint = sha256_bytes(
                canonical_json(
                    [
                        download_key,
                        archive_sha256,
                        member,
                        row_number,
                        source_fingerprint,
                    ]
                )
            )
            source_fingerprints.append(source_fingerprint)
            evidence_fingerprints.append(evidence_fingerprint)
    return source_fingerprints, evidence_fingerprints


def schema_for(pa: Any, fields: tuple[FieldSpec, ...], *, version: str, receipt: dict[str, Any]) -> Any:
    return pa.schema(
        [pa.field(name, arrow_type(pa, kind), nullable=nullable) for name, _, kind, nullable, _ in fields],
        metadata={
            b"schema_version": version.encode(),
            b"source_download_key": receipt["download"]["key"].encode(),
            b"source_archive_sha256": receipt["download"]["archive_sha256"].encode(),
            b"source_receipt_fingerprint": receipt["receipt_fingerprint"].encode(),
            b"evidence_semantics": b"provider assertions; not human verification or absence evidence",
        },
    )


def projected_table(
    raw: Any,
    fields: tuple[FieldSpec, ...],
    *,
    receipt: dict[str, Any],
    member: str,
    fingerprint_name: str,
) -> Any:
    import pyarrow as pa
    import pyarrow.compute as pc

    source_fields = [source for _, source, _, _, _ in fields if source is not None]
    source_fingerprints, evidence_fingerprints = fingerprint_columns(
        raw,
        source_fields,
        archive_sha256=receipt["download"]["archive_sha256"],
        download_key=receipt["download"]["key"],
        member=member,
    )
    derived: dict[str, Any] = {
        "source_download_key": pa.array([receipt["download"]["key"]] * raw.num_rows, type=pa.string()),
        "source_archive_sha256": pa.array([receipt["download"]["archive_sha256"]] * raw.num_rows, type=pa.string()),
        "source_row_number": pa.array(range(1, raw.num_rows + 1), type=pa.int64()),
        "source_record_fingerprint": pa.array(source_fingerprints, type=pa.string()),
        fingerprint_name: pa.array(evidence_fingerprints, type=pa.string()),
    }
    arrays = []
    schema = schema_for(
        pa,
        fields,
        version=(OCCURRENCE_SCHEMA_VERSION if member == "occurrence.txt" else MULTIMEDIA_SCHEMA_VERSION),
        receipt=receipt,
    )
    for target, source, kind, nullable, _ in fields:
        array = derived[target] if source is None else pc.cast(raw[source], arrow_type(pa, kind), safe=True)
        if not nullable and array.null_count:
            raise GbifEvidenceError(f"non-nullable {member} field is null: {target}")
        arrays.append(array)
    return pa.Table.from_arrays(arrays, schema=schema)


def local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def direct_text(parent: ET.Element, name: str) -> str | None:
    for child in parent:
        if local_name(child) == name and child.text and child.text.strip():
            return child.text.strip()
    return None


def child(parent: ET.Element, name: str) -> ET.Element | None:
    return next((value for value in parent if local_name(value) == name), None)


def rights_by_title(archive: ZipFile) -> dict[str, str]:
    lines = archive.read("rights.txt").decode("utf-8").splitlines()
    result: dict[str, str] = {}
    pending: str | None = None
    for line in lines:
        if line.startswith("Dataset: "):
            pending = line.removeprefix("Dataset: ").strip()
        elif line.startswith("Rights as supplied: ") and pending is not None:
            if pending in result:
                raise GbifEvidenceError(f"duplicate rights entry for dataset {pending!r}")
            result[pending] = line.removeprefix("Rights as supplied: ").strip()
            pending = None
    return result


def dataset_table(archive: ZipFile, receipt: dict[str, Any], occurrence_raw: Any) -> Any:
    import pyarrow as pa
    import pyarrow.compute as pc

    selected_counts = Counter(occurrence_raw["datasetKey"].to_pylist())
    rights = rights_by_title(archive)
    rows: list[dict[str, Any]] = []
    names = sorted(
        name
        for name in archive.namelist()
        if name.startswith("dataset/") and name.endswith(".xml")
    )
    for name in names:
        payload = archive.read(name)
        root = ET.fromstring(payload)
        dataset = next((value for value in root if local_name(value) == "dataset"), None)
        if dataset is None:
            raise GbifEvidenceError(f"dataset EML lacks dataset node: {name}")
        dataset_key = Path(name).stem
        if root.attrib.get("packageId") != dataset_key:
            raise GbifEvidenceError(f"dataset EML package ID mismatch: {name}")
        title = direct_text(dataset, "title")
        if not title or title not in rights:
            raise GbifEvidenceError(f"dataset title has no exact rights entry: {name}")
        licensed = child(dataset, "licensed")
        gbif = next((value for value in root.iter() if local_name(value) == "gbif"), None)
        citation = direct_text(gbif, "citation") if gbif is not None else None
        if not citation:
            raise GbifEvidenceError(f"dataset EML lacks GBIF citation: {name}")
        alternate_ids = [
            value.text.strip()
            for value in dataset
            if local_name(value) == "alternateIdentifier" and value.text
        ]
        row: dict[str, Any] = {
            "source_download_key": receipt["download"]["key"],
            "source_archive_sha256": receipt["download"]["archive_sha256"],
            "dataset_key": dataset_key,
            "title": title,
            "doi": next((value for value in alternate_ids if value.startswith("10.")), None),
            "publication_date": direct_text(dataset, "pubDate"),
            "metadata_updated": direct_text(gbif, "dateStamp") if gbif is not None else None,
            "licence_name": direct_text(licensed, "licenseName") if licensed is not None else None,
            "licence_url": direct_text(licensed, "url") if licensed is not None else None,
            "licence_identifier": direct_text(licensed, "identifier") if licensed is not None else None,
            "rights_as_supplied": rights[title],
            "citation": citation,
            "selected_occurrence_count": selected_counts.get(dataset_key, 0),
            "dataset_metadata_xml_sha256": sha256_bytes(payload),
        }
        row["dataset_evidence_fingerprint"] = sha256_bytes(canonical_json(row))
        rows.append(row)
    if len(rows) != receipt["download"]["dataset_count"]:
        raise GbifEvidenceError("dataset evidence row count does not match receipt")
    if sum(row["selected_occurrence_count"] for row in rows) != receipt["download"]["record_count"]:
        raise GbifEvidenceError("dataset occurrence counts do not reconcile")
    if set(selected_counts) != {row["dataset_key"] for row in rows}:
        raise GbifEvidenceError("occurrence dataset keys do not match dataset EML inventory")
    if Counter(rights.values()) != Counter(receipt["rights"]["constituent_dataset_rights_distribution"]):
        raise GbifEvidenceError("constituent rights distribution does not match receipt")
    schema = schema_for(pa, DATASET_FIELDS, version=DATASET_SCHEMA_VERSION, receipt=receipt)
    table = pa.Table.from_pylist(rows, schema=schema)
    order = pc.sort_indices(table, sort_keys=[("dataset_key", "ascending")])
    return pc.take(table, order)


def schema_contract(fields: tuple[FieldSpec, ...], *, artifact_version: str, invariants: list[str]) -> dict[str, Any]:
    return {
        "schema_version": PARQUET_SCHEMA_VERSION,
        "artifact_schema_version": artifact_version,
        "format": "parquet",
        "closed": True,
        "fields": [
            {
                "name": name,
                "type": kind,
                "nullable": nullable,
                "description": description,
            }
            for name, _, kind, nullable, description in fields
        ],
        "invariants": invariants,
    }


def write_parquet(path: Path, table: Any) -> None:
    import pyarrow.parquet as pq

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    pq.write_table(
        table,
        temporary,
        compression="zstd",
        compression_level=9,
        use_dictionary=True,
        write_statistics=True,
        row_group_size=65_536,
        data_page_version="2.0",
        version="2.6",
        use_compliant_nested_type=True,
    )
    os.replace(temporary, path)


def logical_digest(table: Any, field: str) -> str:
    digest = hashlib.sha256()
    for value in table[field].to_pylist():
        digest.update(value.encode())
        digest.update(b"\n")
    return digest.hexdigest()


def artifact(path: Path, table: Any, fingerprint_field: str) -> dict[str, Any]:
    import pyarrow.parquet as pq

    metadata = pq.ParquetFile(path).metadata
    return {
        "path": path.name,
        "physical_bytes": path.stat().st_size,
        "physical_sha256": sha256_file(path),
        "row_count": table.num_rows,
        "column_count": table.num_columns,
        "row_group_count": metadata.num_row_groups,
        "logical_row_fingerprint_sha256": logical_digest(table, fingerprint_field),
        "compression": "zstd",
        "row_group_size": 65_536,
    }


def counter(table: Any, field: str) -> dict[str, int]:
    return dict(sorted(Counter(value for value in table[field].to_pylist() if value is not None).items()))


def build(args: argparse.Namespace) -> None:
    try:
        import pyarrow as pa
        import pyarrow.compute as pc
        import pyarrow.parquet as pq  # noqa: F401
    except ImportError as error:
        raise GbifEvidenceError(
            "GBIF build requires the locked PyArrow dependency; run uv sync --frozen"
        ) from error

    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    validate_receipt(receipt)
    validate_archive(args.archive, receipt)
    occurrence_sources = [source for _, source, _, _, _ in OCCURRENCE_FIELDS if source]
    multimedia_sources = [source for _, source, _, _, _ in MULTIMEDIA_FIELDS if source]
    with ZipFile(args.archive) as archive:
        occurrence_raw = read_member_table(archive, "occurrence.txt", occurrence_sources)
        if occurrence_raw.num_rows != receipt["download"]["record_count"]:
            raise GbifEvidenceError("parsed occurrence row count does not match receipt")
        occurrences = projected_table(
            occurrence_raw,
            OCCURRENCE_FIELDS,
            receipt=receipt,
            member="occurrence.txt",
            fingerprint_name="occurrence_evidence_fingerprint",
        )
        if pc.count_distinct(occurrences["gbif_id"]).as_py() != occurrences.num_rows:
            raise GbifEvidenceError("GBIF occurrence identifiers are not unique")
        order = pc.sort_indices(occurrences, sort_keys=[("gbif_id", "ascending")])
        occurrences = pc.take(occurrences, order)

        multimedia_raw = read_member_table(archive, "multimedia.txt", multimedia_sources)
        expected_media = receipt["archive_inventory"]["members"]["multimedia.txt"]["row_count"]
        if multimedia_raw.num_rows != expected_media:
            raise GbifEvidenceError("parsed multimedia row count does not match receipt")
        multimedia = projected_table(
            multimedia_raw,
            MULTIMEDIA_FIELDS,
            receipt=receipt,
            member="multimedia.txt",
            fingerprint_name="media_evidence_fingerprint",
        )
        order = pc.sort_indices(
            multimedia,
            sort_keys=[
                ("gbif_id", "ascending"),
                ("identifier", "ascending"),
                ("source_row_number", "ascending"),
            ],
        )
        multimedia = pc.take(multimedia, order)
        occurrence_ids = set(occurrences["gbif_id"].to_pylist())
        media_parent_ids = set(multimedia["gbif_id"].to_pylist())
        if not media_parent_ids <= occurrence_ids:
            raise GbifEvidenceError("multimedia contains an unknown occurrence parent")

        datasets = dataset_table(archive, receipt, occurrence_raw)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    occurrence_path = args.output_dir / "gbif_occurrences.parquet"
    multimedia_path = args.output_dir / "gbif_multimedia.parquet"
    dataset_path = args.output_dir / "gbif_datasets.parquet"
    occurrence_schema_path = args.output_dir / "schemas/gbif_occurrence.schema.json"
    multimedia_schema_path = args.output_dir / "schemas/gbif_multimedia.schema.json"
    dataset_schema_path = args.output_dir / "schemas/gbif_dataset.schema.json"
    write_parquet(occurrence_path, occurrences)
    write_parquet(multimedia_path, multimedia)
    write_parquet(dataset_path, datasets)
    write_json(
        occurrence_schema_path,
        schema_contract(
            OCCURRENCE_FIELDS,
            artifact_version=OCCURRENCE_SCHEMA_VERSION,
            invariants=[
                "gbif_id is unique and rows are sorted lexically by gbif_id",
                "source_record_fingerprint binds the exact selected DWCA field vector",
                "occurrence_evidence_fingerprint binds source row identity to the exact archive",
                "provider taxonomy and occurrence fields are assertions, not human verification",
                "withheld/generalisation text, uncertainty, and issue fields remain attached",
                "absence and current-presence inference are prohibited",
            ],
        ),
    )
    write_json(
        multimedia_schema_path,
        schema_contract(
            MULTIMEDIA_FIELDS,
            artifact_version=MULTIMEDIA_SCHEMA_VERSION,
            invariants=[
                "rows are sorted by gbif_id, identifier, and source_row_number",
                "media_evidence_fingerprint binds metadata to the exact source archive row",
                "identifiers and attributions are metadata only; no media bytes were fetched",
                "presence does not grant public-release or model-training authority",
            ],
        ),
    )
    write_json(
        dataset_schema_path,
        schema_contract(
            DATASET_FIELDS,
            artifact_version=DATASET_SCHEMA_VERSION,
            invariants=[
                "dataset_key is unique and rows are sorted by dataset_key",
                "selected occurrence counts sum to the download record count",
                "citation and rights_as_supplied are preserved from the exact DWCA",
                "rights screening is conservative and is not a legal determination",
            ],
        ),
    )

    manifest: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "generated_at": args.generated_at,
        "source": {
            "download_key": receipt["download"]["key"],
            "doi": receipt["download"]["doi"],
            "citation": receipt["download"]["citation"],
            "archive_sha256": receipt["download"]["archive_sha256"],
            "receipt_path": "gbif_download_receipt.json",
            "receipt_physical_sha256": sha256_file(args.receipt),
            "receipt_fingerprint": receipt["receipt_fingerprint"],
        },
        "authority": receipt["authority_policy"],
        "artifacts": {
            "occurrences": artifact(occurrence_path, occurrences, "occurrence_evidence_fingerprint"),
            "multimedia": artifact(multimedia_path, multimedia, "media_evidence_fingerprint"),
            "datasets": artifact(dataset_path, datasets, "dataset_evidence_fingerprint"),
        },
        "schemas": {
            "occurrences": {"path": "schemas/gbif_occurrence.schema.json", "physical_sha256": sha256_file(occurrence_schema_path)},
            "multimedia": {"path": "schemas/gbif_multimedia.schema.json", "physical_sha256": sha256_file(multimedia_schema_path)},
            "datasets": {"path": "schemas/gbif_dataset.schema.json", "physical_sha256": sha256_file(dataset_schema_path)},
        },
        "counts": {
            "occurrence_licences": counter(occurrences, "licence"),
            "basis_of_record": counter(occurrences, "basis_of_record"),
            "taxonomic_status": counter(occurrences, "taxonomic_status"),
            "has_coordinate": counter(occurrences, "has_coordinate"),
            "has_geospatial_issues": counter(occurrences, "has_geospatial_issues"),
            "information_withheld_rows": occurrences["information_withheld"].length() - occurrences["information_withheld"].null_count,
            "data_generalized_rows": occurrences["data_generalizations"].length() - occurrences["data_generalizations"].null_count,
            "multimedia_formats": counter(multimedia, "format"),
            "multimedia_licence_summary": {
                "supplied_rows": multimedia["licence"].length() - multimedia["licence"].null_count,
                "missing_rows": multimedia["licence"].null_count,
                "unique_supplied_values": pc.count_distinct(multimedia["licence"]).as_py(),
            },
            "dataset_rights": counter(datasets, "rights_as_supplied"),
            "occurrences_with_media": len(media_parent_ids),
        },
        "policy": {
            "provider_assertions_are_human_verification": False,
            "absence_inference_permitted": False,
            "current_presence_inference_permitted": False,
            "coordinates_reconstructed_or_increased_in_precision": False,
            "media_downloaded": False,
            "flickr_api_calls_made": False,
            "authoritative_ala_baseline": "ButterflyLens rebuilt baseline",
            "gbif_replaces_ala_baseline": False,
            "public_release_state": "blocked_pending_record_and_dataset_rights_review",
            "legal_determination": False,
        },
        "build": {
            "python": ".".join(map(str, sys.version_info[:3])),
            "pyarrow": pa.__version__,
            "compression": "zstd",
            "compression_level": 9,
            "row_group_size": 65_536,
            "network_access": False,
        },
    }
    manifest["evidence_pack_fingerprint"] = sha256_bytes(canonical_json(manifest))
    manifest_path = args.output_dir / "gbif_evidence_manifest.json"
    write_json(manifest_path, manifest)
    print(
        json.dumps(
            {
                "manifest": str(manifest_path),
                "fingerprint": manifest["evidence_pack_fingerprint"],
                "occurrences": occurrences.num_rows,
                "multimedia": multimedia.num_rows,
                "datasets": datasets.num_rows,
            },
            sort_keys=True,
        )
    )


def publish(args: argparse.Namespace) -> None:
    gbif_dir = args.gbif_dir
    evidence_path = gbif_dir / "gbif_evidence_manifest.json"
    receipt_path = gbif_dir / "gbif_download_receipt.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    validate_receipt(receipt)
    if evidence.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise GbifEvidenceError("unexpected GBIF evidence manifest schema")
    semantic = dict(evidence)
    expected_fingerprint = semantic.pop("evidence_pack_fingerprint", None)
    if expected_fingerprint != sha256_bytes(canonical_json(semantic)):
        raise GbifEvidenceError("GBIF evidence manifest fingerprint mismatch")
    artifact_versions = {
        "occurrences": OCCURRENCE_SCHEMA_VERSION,
        "multimedia": MULTIMEDIA_SCHEMA_VERSION,
        "datasets": DATASET_SCHEMA_VERSION,
    }
    for name, artifact_record in evidence["artifacts"].items():
        path = gbif_dir / artifact_record["path"]
        if not path.is_file() or sha256_file(path) != artifact_record["physical_sha256"]:
            raise GbifEvidenceError(f"GBIF evidence artifact mismatch: {name}")
    for name, schema_record in evidence["schemas"].items():
        path = gbif_dir / schema_record["path"]
        if not path.is_file() or sha256_file(path) != schema_record["physical_sha256"]:
            raise GbifEvidenceError(f"GBIF evidence schema mismatch: {name}")

    pack = json.loads(args.pack_manifest.read_text(encoding="utf-8"))
    pack["gbif_state"] = {
        "status": "built_rights_review_required",
        "generated_at": evidence["generated_at"],
        "download_key": receipt["download"]["key"],
        "doi": receipt["download"]["doi"],
        "receipt_path": "gbif/gbif_download_receipt.json",
        "receipt_fingerprint": receipt["receipt_fingerprint"],
        "evidence_manifest_path": "gbif/gbif_evidence_manifest.json",
        "evidence_manifest_sha256": sha256_file(evidence_path),
        "evidence_pack_fingerprint": evidence["evidence_pack_fingerprint"],
        "occurrence_rows": evidence["artifacts"]["occurrences"]["row_count"],
        "multimedia_metadata_rows": evidence["artifacts"]["multimedia"]["row_count"],
        "dataset_rows": evidence["artifacts"]["datasets"]["row_count"],
        "raw_archive_committed_to_git": False,
        "media_bytes_downloaded": False,
        "flickr_api_calls_made": False,
        "authoritative_ala_baseline": "ButterflyLens rebuilt baseline",
        "gbif_replaces_ala_baseline": False,
        "public_release_state": "blocked_pending_record_and_dataset_rights_review",
    }
    pack_artifacts = pack["artifacts"]
    pack_artifacts["gbif/gbif_download_receipt.json"] = {
        "physical_sha256": sha256_file(receipt_path),
        "row_count": 1,
        "schema_version": RECEIPT_SCHEMA_VERSION,
    }
    pack_artifacts["gbif/gbif_evidence_manifest.json"] = {
        "physical_sha256": sha256_file(evidence_path),
        "row_count": 1,
        "schema_version": MANIFEST_SCHEMA_VERSION,
    }
    for name, artifact_record in evidence["artifacts"].items():
        pack_artifacts[f"gbif/{artifact_record['path']}"] = {
            "physical_sha256": artifact_record["physical_sha256"],
            "row_count": artifact_record["row_count"],
            "schema_version": artifact_versions[name],
        }
    for name, schema_record in evidence["schemas"].items():
        pack_artifacts[f"gbif/{schema_record['path']}"] = {
            "physical_sha256": schema_record["physical_sha256"],
            "row_count": 1,
            "schema_version": PARQUET_SCHEMA_VERSION,
        }
    sources = [
        source
        for source in pack["occurrence_sources"]
        if source.get("provider") != "Global Biodiversity Information Facility"
    ]
    sources.append(
        {
            "path": "gbif/gbif_download_receipt.json",
            "physical_sha256": sha256_file(receipt_path),
            "retrieved_at": receipt["verified_at"],
            "provider": "Global Biodiversity Information Facility",
            "snapshot_id": receipt["download"]["key"],
            "snapshot_fingerprint": receipt["receipt_fingerprint"],
            "doi": receipt["download"]["doi"],
            "role": "complementary_occurrence_evidence_ala_baseline_remains_authoritative",
        }
    )
    pack["occurrence_sources"] = sources
    write_json(args.pack_manifest, pack)

    rights = json.loads(args.rights_manifest.read_text(encoding="utf-8"))
    source_id = f"gbif-occurrence-download-{receipt['download']['key']}"
    rights["generated_at"] = args.published_at
    source_positions = [
        index
        for index, source in enumerate(rights["sources"])
        if source.get("source_id") == source_id
    ]
    source_insert_index = (
        source_positions[0] if source_positions else len(rights["sources"])
    )
    rights["sources"] = [
        source for source in rights["sources"] if source.get("source_id") != source_id
    ]
    rights["sources"].insert(
        min(source_insert_index, len(rights["sources"])),
        {
            "source_id": source_id,
            "provider": "GBIF and the 126 constituent data publishers identified in the frozen DWCA",
            "dataset": "Australian Papilionoidea occurrence and multimedia-metadata download",
            "source_url": receipt["download"]["doi_url"],
            "retrieved_at": receipt["verified_at"],
            "licence": "MIXED-CC0-CC-BY-CC-BY-NC-DOWNLOAD-CC-BY-NC-4.0",
            "licence_url": "data/packs/australian_butterflies/v1/gbif/gbif_download_receipt.json",
            "terms_url": "https://www.gbif.org/terms",
            "attribution": receipt["download"]["citation"] + "; every constituent dataset citation and every row/media attribution retained in the evidence pack.",
            "scope_note": "571,755 processed occurrence assertions, 542,052 media-metadata rows with no media bytes, and 126 dataset citation/rights rows. Exact per-row and per-dataset rights, withheld/generalisation text, uncertainty, and quality issues remain attached. Provider labels are not human verification. Processing is permitted for the governed internal evidence workflow; display and redistribution remain blocked pending rights, sensitivity, quality, provenance, and human review. The rebuilt ALA baseline remains authoritative.",
        },
    )
    relative_root = Path("data/packs/australian_butterflies/v1/gbif")
    rights_paths = {
        relative_root / "gbif_download_receipt.json",
        relative_root / "gbif_evidence_manifest.json",
        relative_root / "gbif_occurrences.parquet",
        relative_root / "gbif_multimedia.parquet",
        relative_root / "gbif_datasets.parquet",
        relative_root / "schemas/gbif_download_receipt.schema.json",
        relative_root / "schemas/gbif_occurrence.schema.json",
        relative_root / "schemas/gbif_multimedia.schema.json",
        relative_root / "schemas/gbif_dataset.schema.json",
    }
    artifact_positions = [
        index
        for index, record in enumerate(rights["artifacts"])
        if Path(record.get("path", "")) in rights_paths
    ]
    artifact_insert_index = (
        artifact_positions[0] if artifact_positions else len(rights["artifacts"])
    )
    rights["artifacts"] = [
        record
        for record in rights["artifacts"]
        if Path(record.get("path", "")) not in rights_paths
    ]
    gbif_rights_records = []
    for relative in sorted(rights_paths, key=lambda value: value.as_posix()):
        path = ROOT / relative
        gbif_rights_records.append(
            {
                "path": relative.as_posix(),
                "fingerprint": f"sha256:{sha256_file(path)}",
                "provider": "GBIF and constituent publishers; ButterflyLens deterministic projection where applicable",
                "source_id": source_id,
                "licence": "MIXED-SEE-GBIF-RECEIPT-ROW-AND-DATASET-RIGHTS",
                "attribution": receipt["download"]["citation"] + "; constituent and media attribution retained in the frozen evidence.",
                "processing_allowed": True,
                "display_allowed": False,
                "redistribution_allowed": False,
                "removal_state": "active_internal_rights_review_required",
            }
        )
    rights["artifacts"][
        min(artifact_insert_index, len(rights["artifacts"])) : min(
            artifact_insert_index, len(rights["artifacts"])
        )
    ] = gbif_rights_records
    pack_relative = "data/packs/australian_butterflies/v1/manifest.json"
    for record in rights["artifacts"]:
        if record.get("path") == pack_relative:
            record["fingerprint"] = f"sha256:{sha256_file(args.pack_manifest)}"
            record["display_allowed"] = True
            record["redistribution_allowed"] = True
            record["scope_note"] = "Umbrella metadata over source-specific artifacts. The new GBIF evidence is internal and rights-blocked; the ALA baseline remains authoritative."
            break
    else:
        raise GbifEvidenceError("data-rights manifest lacks the root pack artifact")
    write_pretty_json(args.rights_manifest, ordered_rights_manifest(rights))
    print(
        json.dumps(
            {
                "pack_manifest": str(args.pack_manifest),
                "pack_manifest_sha256": sha256_file(args.pack_manifest),
                "rights_manifest": str(args.rights_manifest),
                "rights_artifacts": len(rights["artifacts"]),
            },
            sort_keys=True,
        )
    )


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    commands = value.add_subparsers(dest="command", required=True)
    acquire_command = commands.add_parser("acquire", help="explicitly download and verify the receipt-bound DWCA")
    acquire_command.add_argument("--receipt", type=Path, required=True)
    acquire_command.add_argument("--output", type=Path, required=True)
    acquire_command.add_argument("--timeout", type=float, default=300.0)
    acquire_command.set_defaults(handler=acquire)
    build_command = commands.add_parser("build", help="offline deterministic DWCA-to-Parquet build")
    build_command.add_argument("--archive", type=Path, required=True)
    build_command.add_argument("--receipt", type=Path, required=True)
    build_command.add_argument("--output-dir", type=Path, required=True)
    build_command.add_argument("--generated-at", required=True)
    build_command.set_defaults(handler=build)
    publish_command = commands.add_parser("publish", help="integrate built Parquet evidence into pack and rights manifests")
    publish_command.add_argument("--gbif-dir", type=Path, required=True)
    publish_command.add_argument("--pack-manifest", type=Path, required=True)
    publish_command.add_argument("--rights-manifest", type=Path, required=True)
    publish_command.add_argument("--published-at", required=True)
    publish_command.set_defaults(handler=publish)
    return value


def main() -> None:
    args = parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
