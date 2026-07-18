"""Deterministic, rights-safe Darwin Core evidence package export."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime
import csv
import hashlib
import io
import os
from pathlib import Path
import re
import tempfile
from typing import Literal, Mapping, Sequence
from urllib.parse import urlsplit
import zipfile

import h3

from .fingerprint import canonicalize_json


DARWIN_CORE_EXPORT_SCHEMA_VERSION = "butterflylens-darwin-core-export:v1.0.0"
DARWIN_CORE_TEXT_GUIDE_VERSION = "2023-09-13"
DARWIN_CORE_TERMS_VERSION = "2026-05-26"
DARWIN_CORE_EXPORT_POLICY_VERSION = "butterflylens-darwin-core-export-policy:v1.0.0"
DARWIN_CORE_EXPORT_TABLES = (
    "occurrence",
    "taxon",
    "event",
    "location",
    "identification",
    "measurement",
    "multimedia",
    "provenance",
    "review",
    "quality",
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_DWC = "http://rs.tdwg.org/dwc/terms/"
_DCTERMS = "http://purl.org/dc/terms/"
_DC = "http://purl.org/dc/elements/1.1/"
_AC = "http://rs.tdwg.org/ac/terms/"
_BL = "https://butterflylens.org/terms/"
_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def _fingerprint(value: str, field: str) -> None:
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")


def _text(value: str, field: str, *, maximum: int = 800) -> None:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError(f"{field} must contain 1 to {maximum} characters")
    if _CONTROL.search(value):
        raise ValueError(f"{field} cannot contain control characters")


def _identifier(value: str, field: str) -> None:
    _text(value, field, maximum=400)
    if any(character.isspace() for character in value):
        raise ValueError(f"{field} cannot contain whitespace")


def _https_url(value: str, field: str) -> None:
    _text(value, field, maximum=1_500)
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"{field} must be a public credential-free HTTPS URL")


def _event_date(value: str) -> None:
    if not _DATE.fullmatch(value):
        raise ValueError("event_date must be a complete ISO 8601 calendar date")
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("event_date must be a valid calendar date") from error


def _created_at(value: str) -> None:
    _text(value, "created_at", maximum=64)
    if not value.endswith("Z"):
        raise ValueError("created_at must be an explicit UTC RFC 3339 timestamp")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ValueError("created_at must be an explicit UTC RFC 3339 timestamp") from error


@dataclass(frozen=True, slots=True)
class DarwinCoreTaxonEvidence:
    taxon_id: str
    scientific_name: str
    taxon_rank: str
    family: str
    genus: str
    taxon_concept_fingerprint: str
    concept_source: str = "Australian Faunal Directory"
    kingdom: Literal["Animalia"] = "Animalia"
    phylum: Literal["Arthropoda"] = "Arthropoda"
    class_name: Literal["Insecta"] = "Insecta"
    order: Literal["Lepidoptera"] = "Lepidoptera"

    def __post_init__(self) -> None:
        for field, value in (
            ("taxon_id", self.taxon_id),
            ("scientific_name", self.scientific_name),
            ("taxon_rank", self.taxon_rank),
            ("family", self.family),
            ("genus", self.genus),
            ("concept_source", self.concept_source),
        ):
            _text(value, field)
        _identifier(self.taxon_id, "taxon_id")
        _fingerprint(self.taxon_concept_fingerprint, "taxon_concept_fingerprint")
        if self.kingdom != "Animalia" or self.phylum != "Arthropoda":
            raise ValueError("export taxon must remain in the Australian butterfly scope")
        if self.class_name != "Insecta" or self.order != "Lepidoptera":
            raise ValueError("export taxon must remain in the Australian butterfly scope")


@dataclass(frozen=True, slots=True)
class DarwinCoreMediaEvidence:
    media_id: str
    source_page_url: str
    licence_url: str
    rights_holder: str
    creator: str
    attribution: str
    media_fingerprint: str
    rights_fingerprint: str
    title: str
    media_format: str = "image/jpeg"
    access_uri: str | None = None

    def __post_init__(self) -> None:
        _identifier(self.media_id, "media_id")
        _https_url(self.source_page_url, "source_page_url")
        _https_url(self.licence_url, "licence_url")
        if self.access_uri is not None:
            _https_url(self.access_uri, "access_uri")
        for field, value in (
            ("rights_holder", self.rights_holder),
            ("creator", self.creator),
            ("attribution", self.attribution),
            ("title", self.title),
            ("media_format", self.media_format),
        ):
            _text(value, field)
        _fingerprint(self.media_fingerprint, "media_fingerprint")
        _fingerprint(self.rights_fingerprint, "media rights_fingerprint")


@dataclass(frozen=True, slots=True)
class DarwinCoreReleaseRecord:
    occurrence_id: str
    event_id: str
    location_id: str
    identification_id: str
    release_candidate_id: str
    event_date: str
    public_cell_id: str
    information_withheld: str
    data_generalizations: str
    taxon: DarwinCoreTaxonEvidence
    media: DarwinCoreMediaEvidence
    candidate_fingerprint: str
    release_receipt_fingerprint: str
    location_receipt_fingerprint: str
    coordinate_evidence_fingerprint: str
    date_evidence_fingerprint: str
    duplicate_independence_fingerprint: str
    human_consensus_fingerprint: str
    qualified_consensus_fingerprint: str
    expert_gate_evidence_fingerprint: str
    conflict_audit_fingerprint: str
    quality_snapshot_fingerprint: str
    quality_threshold_fingerprint: str
    evidence_packet_fingerprint: str
    rights_fingerprint: str
    expert_review_required: bool = False
    expert_review_fingerprint: str | None = None
    release_state: Literal["release_ready_occurrence_candidate"] = (
        "release_ready_occurrence_candidate"
    )
    published_occurrence: Literal[False] = False
    scientific_claim_allowed: Literal[False] = False

    def __post_init__(self) -> None:
        for field, value in (
            ("occurrence_id", self.occurrence_id),
            ("event_id", self.event_id),
            ("location_id", self.location_id),
            ("identification_id", self.identification_id),
            ("release_candidate_id", self.release_candidate_id),
        ):
            _identifier(value, field)
        _event_date(self.event_date)
        _identifier(self.public_cell_id, "public_cell_id")
        if not h3.is_valid_cell(self.public_cell_id):
            raise ValueError("public_cell_id must be a valid governed H3 cell")
        _text(self.information_withheld, "information_withheld")
        _text(self.data_generalizations, "data_generalizations")
        if self.release_state != "release_ready_occurrence_candidate":
            raise ValueError("only a release-ready occurrence candidate can be exported")
        if self.published_occurrence or self.scientific_claim_allowed:
            raise ValueError("package preparation cannot assert publication or scientific truth")
        if not isinstance(self.expert_review_required, bool):
            raise ValueError("expert_review_required must be boolean")
        if self.expert_review_required != (self.expert_review_fingerprint is not None):
            raise ValueError("configured expert review requires its exact event fingerprint")
        for field, value in (
            ("candidate_fingerprint", self.candidate_fingerprint),
            ("release_receipt_fingerprint", self.release_receipt_fingerprint),
            ("location_receipt_fingerprint", self.location_receipt_fingerprint),
            ("coordinate_evidence_fingerprint", self.coordinate_evidence_fingerprint),
            ("date_evidence_fingerprint", self.date_evidence_fingerprint),
            ("duplicate_independence_fingerprint", self.duplicate_independence_fingerprint),
            ("human_consensus_fingerprint", self.human_consensus_fingerprint),
            ("qualified_consensus_fingerprint", self.qualified_consensus_fingerprint),
            ("expert_gate_evidence_fingerprint", self.expert_gate_evidence_fingerprint),
            ("conflict_audit_fingerprint", self.conflict_audit_fingerprint),
            ("quality_snapshot_fingerprint", self.quality_snapshot_fingerprint),
            ("quality_threshold_fingerprint", self.quality_threshold_fingerprint),
            ("evidence_packet_fingerprint", self.evidence_packet_fingerprint),
            ("rights_fingerprint", self.rights_fingerprint),
        ):
            _fingerprint(value, field)
        if self.expert_review_fingerprint is not None:
            _fingerprint(self.expert_review_fingerprint, "expert_review_fingerprint")
        if self.rights_fingerprint != self.media.rights_fingerprint:
            raise ValueError("candidate and media rights fingerprints must match")


@dataclass(frozen=True, slots=True)
class DarwinCoreExportRequest:
    package_id: str
    dataset_id: str
    dataset_title: str
    created_at: str
    code_sha: str
    records: tuple[DarwinCoreReleaseRecord, ...]
    package_version: str = "1.0.0"

    def __post_init__(self) -> None:
        _identifier(self.package_id, "package_id")
        _identifier(self.dataset_id, "dataset_id")
        _text(self.dataset_title, "dataset_title", maximum=300)
        _created_at(self.created_at)
        _fingerprint(self.code_sha, "code_sha")
        _text(self.package_version, "package_version", maximum=64)
        if not self.records:
            raise ValueError("an evidence package requires at least one release-ready record")
        if tuple(sorted(self.records, key=lambda item: item.occurrence_id)) != self.records:
            raise ValueError("release records must be sorted by occurrence_id")
        for field in (
            "occurrence_id",
            "event_id",
            "location_id",
            "identification_id",
            "release_candidate_id",
            "release_receipt_fingerprint",
        ):
            values = [getattr(record, field) for record in self.records]
            if len(values) != len(set(values)):
                raise ValueError(f"{field} values must be unique")


@dataclass(frozen=True, slots=True)
class DarwinCoreEvidencePackage:
    archive_bytes: bytes
    archive_sha256: str
    package_fingerprint: str
    manifest: dict[str, object]

    def write_atomic(self, destination: Path) -> None:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(self.archive_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, destination)
        except BaseException:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise


@dataclass(frozen=True, slots=True)
class _Table:
    name: str
    filename: str
    row_type: str
    columns: tuple[tuple[str, str], ...]


_TABLES = (
    _Table("occurrence", "occurrence.txt", _DWC + "Occurrence", (
        ("occurrenceID", _DWC + "occurrenceID"),
        ("basisOfRecord", _DWC + "basisOfRecord"),
        ("occurrenceStatus", _DWC + "occurrenceStatus"),
        ("eventID", _DWC + "eventID"),
        ("taxonID", _DWC + "taxonID"),
        ("scientificName", _DWC + "scientificName"),
        ("taxonRank", _DWC + "taxonRank"),
        ("identificationVerificationStatus", _DWC + "identificationVerificationStatus"),
        ("informationWithheld", _DWC + "informationWithheld"),
        ("dataGeneralizations", _DWC + "dataGeneralizations"),
        ("references", _DCTERMS + "references"),
        ("license", _DCTERMS + "license"),
        ("rightsHolder", _DCTERMS + "rightsHolder"),
        ("occurrenceRemarks", _DWC + "occurrenceRemarks"),
    )),
    _Table("taxon", "taxon.txt", _DWC + "Taxon", (
        ("occurrenceID", ""), ("taxonID", _DWC + "taxonID"),
        ("scientificName", _DWC + "scientificName"), ("taxonRank", _DWC + "taxonRank"),
        ("kingdom", _DWC + "kingdom"), ("phylum", _DWC + "phylum"),
        ("class", _DWC + "class"), ("order", _DWC + "order"),
        ("family", _DWC + "family"), ("genus", _DWC + "genus"),
        ("taxonRemarks", _DWC + "taxonRemarks"),
    )),
    _Table("event", "event.txt", _DWC + "Event", (
        ("occurrenceID", ""), ("eventID", _DWC + "eventID"),
        ("eventDate", _DWC + "eventDate"), ("eventType", _DWC + "eventType"),
        ("locationID", _DWC + "locationID"),
        ("eventReferences", _DWC + "eventReferences"),
        ("eventRemarks", _DWC + "eventRemarks"),
    )),
    _Table("location", "location.txt", _DCTERMS + "Location", (
        ("occurrenceID", ""), ("locationID", _DWC + "locationID"),
        ("higherGeography", _DWC + "higherGeography"),
        ("continent", _DWC + "continent"), ("country", _DWC + "country"),
        ("countryCode", _DWC + "countryCode"), ("locality", _DWC + "locality"),
        ("locationRemarks", _DWC + "locationRemarks"),
        ("georeferenceVerificationStatus", _DWC + "georeferenceVerificationStatus"),
        ("informationWithheld", _DWC + "informationWithheld"),
        ("dataGeneralizations", _DWC + "dataGeneralizations"),
        ("preferredSpatialRepresentation", _DWC + "preferredSpatialRepresentation"),
    )),
    _Table("identification", "identification.txt", _DWC + "Identification", (
        ("occurrenceID", ""), ("identificationID", _DWC + "identificationID"),
        ("identificationType", _DWC + "identificationType"),
        ("isAcceptedIdentification", _DWC + "isAcceptedIdentification"),
        ("taxonID", _DWC + "taxonID"), ("scientificName", _DWC + "scientificName"),
        ("taxonRank", _DWC + "taxonRank"),
        ("identificationVerificationStatus", _DWC + "identificationVerificationStatus"),
        ("identificationReferences", _DWC + "identificationReferences"),
        ("identificationRemarks", _DWC + "identificationRemarks"),
    )),
    _Table("measurement", "measurement.txt", _DWC + "MeasurementOrFact", (
        ("occurrenceID", ""), ("measurementID", _DWC + "measurementID"),
        ("measurementType", _DWC + "measurementType"),
        ("measurementValue", _DWC + "measurementValue"),
        ("measurementMethod", _DWC + "measurementMethod"),
        ("measurementRemarks", _DWC + "measurementRemarks"),
    )),
    _Table("multimedia", "multimedia.txt", _AC + "Media", (
        ("occurrenceID", ""), ("identifier", _DCTERMS + "identifier"),
        ("type", _DCTERMS + "type"), ("format", _DC + "format"),
        ("title", _DCTERMS + "title"), ("description", _DCTERMS + "description"),
        ("creator", _DCTERMS + "creator"), ("references", _DCTERMS + "references"),
        ("accessURI", _AC + "accessURI"), ("license", _DCTERMS + "license"),
        ("rightsHolder", _DCTERMS + "rightsHolder"),
        ("mediaFingerprint", _BL + "mediaFingerprint"),
        ("rightsFingerprint", _BL + "rightsFingerprint"),
    )),
    _Table("provenance", "provenance.txt", _DWC + "Provenance", (
        ("occurrenceID", ""), ("identifier", _DCTERMS + "identifier"),
        ("projectTitle", _DWC + "projectTitle"), ("projectID", _DWC + "projectID"),
        ("source", _DC + "source"), ("references", _DCTERMS + "references"),
        ("candidateFingerprint", _BL + "candidateFingerprint"),
        ("releaseReceiptFingerprint", _BL + "releaseReceiptFingerprint"),
        ("locationReceiptFingerprint", _BL + "locationReceiptFingerprint"),
        ("evidencePacketFingerprint", _BL + "evidencePacketFingerprint"),
    )),
    _Table("review", "review.txt", _DWC + "Assertion", (
        ("occurrenceID", ""), ("assertionID", _DWC + "assertionID"),
        ("assertionType", _DWC + "assertionType"),
        ("assertionValue", _DWC + "assertionValue"),
        ("assertionReferences", _DWC + "assertionReferences"),
        ("assertionRemarks", _DWC + "assertionRemarks"),
    )),
    _Table("quality", "quality.txt", _DWC + "Assertion", (
        ("occurrenceID", ""), ("assertionID", _DWC + "assertionID"),
        ("assertionType", _DWC + "assertionType"),
        ("assertionValue", _DWC + "assertionValue"),
        ("assertionReferences", _DWC + "assertionReferences"),
        ("assertionRemarks", _DWC + "assertionRemarks"),
    )),
)


def _strict_kwargs(
    value: Mapping[str, object], target: type[object], field: str
) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    allowed = {item.name for item in fields(target)}
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(f"{field} has unknown fields: {unknown}")
    return dict(value)


def darwin_core_export_request_from_dict(
    value: Mapping[str, object],
) -> DarwinCoreExportRequest:
    """Parse an exact JSON-shaped request without accepting unknown fields."""

    request_payload = _strict_kwargs(value, DarwinCoreExportRequest, "request")
    raw_records = request_payload.get("records")
    if not isinstance(raw_records, list):
        raise ValueError("request.records must be an array")
    records: list[DarwinCoreReleaseRecord] = []
    for index, raw_record in enumerate(raw_records):
        record_payload = _strict_kwargs(
            raw_record, DarwinCoreReleaseRecord, f"request.records[{index}]"  # type: ignore[arg-type]
        )
        record_payload["taxon"] = DarwinCoreTaxonEvidence(
            **_strict_kwargs(
                record_payload.get("taxon"),  # type: ignore[arg-type]
                DarwinCoreTaxonEvidence,
                f"request.records[{index}].taxon",
            )
        )
        record_payload["media"] = DarwinCoreMediaEvidence(
            **_strict_kwargs(
                record_payload.get("media"),  # type: ignore[arg-type]
                DarwinCoreMediaEvidence,
                f"request.records[{index}].media",
            )
        )
        records.append(DarwinCoreReleaseRecord(**record_payload))  # type: ignore[arg-type]
    request_payload["records"] = tuple(records)
    return DarwinCoreExportRequest(**request_payload)  # type: ignore[arg-type]


def _urn(fingerprint: str) -> str:
    return f"urn:sha256:{fingerprint}"


def _csv_bytes(columns: Sequence[tuple[str, str]], rows: Sequence[Sequence[str]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([name for name, _ in columns])
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def _meta_xml() -> bytes:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<archive xmlns="http://rs.tdwg.org/dwc/text/"',
        '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
        '  xsi:schemaLocation="http://rs.tdwg.org/dwc/text/ http://rs.tdwg.org/dwc/text/tdwg_dwc_text.xsd">',
    ]
    for index, table in enumerate(_TABLES):
        element = "core" if index == 0 else "extension"
        lines.append(
            f'  <{element} encoding="UTF-8" fieldsTerminatedBy="," linesTerminatedBy="\\n" '
            f'fieldsEnclosedBy="&quot;" ignoreHeaderLines="1" rowType="{table.row_type}">'
        )
        lines.extend(("    <files>", f"      <location>{table.filename}</location>", "    </files>"))
        lines.append("    <id index=\"0\"/>" if index == 0 else "    <coreid index=\"0\"/>")
        for field_index, (_, term) in enumerate(table.columns):
            if index > 0 and field_index == 0:
                continue
            lines.append(f'    <field index="{field_index}" term="{term}"/>')
        lines.append(f"  </{element}>")
    lines.append("</archive>")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _rows(request: DarwinCoreExportRequest) -> dict[str, list[list[str]]]:
    rows: dict[str, list[list[str]]] = {name: [] for name in DARWIN_CORE_EXPORT_TABLES}
    for record in request.records:
        taxon = record.taxon
        media = record.media
        rows["occurrence"].append([
            record.occurrence_id, "HumanObservation", "present", record.event_id,
            taxon.taxon_id, taxon.scientific_name, taxon.taxon_rank,
            "human-supported; qualified consensus; release-ready",
            record.information_withheld, record.data_generalizations,
            media.source_page_url, media.licence_url, media.rights_holder,
            "Prepared release-ready evidence package; not published or provider-submitted.",
        ])
        rows["taxon"].append([
            record.occurrence_id, taxon.taxon_id, taxon.scientific_name, taxon.taxon_rank,
            taxon.kingdom, taxon.phylum, taxon.class_name, taxon.order, taxon.family,
            taxon.genus,
            f"conceptSource={taxon.concept_source}; conceptFingerprint={_urn(taxon.taxon_concept_fingerprint)}",
        ])
        rows["event"].append([
            record.occurrence_id, record.event_id, record.event_date, "organism occurrence",
            record.location_id, media.source_page_url,
            f"dateEvidence={_urn(record.date_evidence_fingerprint)}",
        ])
        rows["location"].append([
            record.occurrence_id, record.location_id, "Oceania | Australia", "Oceania",
            "Australia", "AU", f"Generalised public H3 cell {record.public_cell_id}",
            f"publicCell={record.public_cell_id}; locationReceipt={_urn(record.location_receipt_fingerprint)}",
            "verified by versioned ButterflyLens sensitive-location receipt",
            record.information_withheld, record.data_generalizations, "H3 cell",
        ])
        rows["identification"].append([
            record.occurrence_id, record.identification_id, "media", "true", taxon.taxon_id,
            taxon.scientific_name, taxon.taxon_rank,
            "human-supported; qualified consensus; release-ready",
            _urn(record.release_receipt_fingerprint),
            f"candidate={record.release_candidate_id}; candidateFingerprint={_urn(record.candidate_fingerprint)}",
        ])
        measurements = (
            ("coordinate_validity", record.coordinate_evidence_fingerprint),
            ("date_validity", record.date_evidence_fingerprint),
            ("duplicate_independence", record.duplicate_independence_fingerprint),
            ("rights_provenance", record.rights_fingerprint),
            ("evidence_packet_complete", record.evidence_packet_fingerprint),
        )
        for measurement_type, fingerprint in measurements:
            rows["measurement"].append([
                record.occurrence_id,
                f"{record.occurrence_id}:measurement:{measurement_type}",
                measurement_type, "passed", DARWIN_CORE_EXPORT_POLICY_VERSION,
                f"evidence={_urn(fingerprint)}",
            ])
        rows["multimedia"].append([
            record.occurrence_id, media.media_id, "StillImage", media.media_format,
            media.title, media.attribution, media.creator, media.source_page_url,
            media.access_uri or "", media.licence_url, media.rights_holder,
            _urn(media.media_fingerprint), _urn(media.rights_fingerprint),
        ])
        rows["provenance"].append([
            record.occurrence_id, f"{record.occurrence_id}:provenance", "ButterflyLens",
            request.dataset_id, media.source_page_url, _urn(record.release_receipt_fingerprint),
            _urn(record.candidate_fingerprint), _urn(record.release_receipt_fingerprint),
            _urn(record.location_receipt_fingerprint), _urn(record.evidence_packet_fingerprint),
        ])
        review_evidence = (
            ("human_supported_identity", "supported", record.human_consensus_fingerprint),
            ("qualified_consensus", "supported", record.qualified_consensus_fingerprint),
            (
                "expert_review_when_configured",
                "passed" if record.expert_review_required else "not_configured",
                record.expert_review_fingerprint or record.expert_gate_evidence_fingerprint,
            ),
            ("no_unresolved_conflict", "passed", record.conflict_audit_fingerprint),
        )
        for assertion_type, value, fingerprint in review_evidence:
            rows["review"].append([
                record.occurrence_id, f"{record.occurrence_id}:review:{assertion_type}",
                assertion_type, value, _urn(fingerprint),
                "Fingerprint-only evidence; reviewer identity is intentionally excluded.",
            ])
        quality_evidence = (
            ("quality_snapshot_kind", "representative_audit", record.quality_snapshot_fingerprint),
            ("quality_sampling", "blind_representative", record.quality_snapshot_fingerprint),
            ("quality_threshold", "passed", record.quality_threshold_fingerprint),
        )
        for assertion_type, value, fingerprint in quality_evidence:
            rows["quality"].append([
                record.occurrence_id, f"{record.occurrence_id}:quality:{assertion_type}",
                assertion_type, value, _urn(fingerprint),
                "Targeted failure-discovery evidence is excluded from population quality claims.",
            ])
    return rows


def build_darwin_core_evidence_package(
    request: DarwinCoreExportRequest,
) -> DarwinCoreEvidencePackage:
    """Build deterministic DwC-A bytes; preparation does not publish or submit."""

    rows = _rows(request)
    files: dict[str, bytes] = {"meta.xml": _meta_xml()}
    table_inventory: dict[str, dict[str, object]] = {}
    for table in _TABLES:
        content = _csv_bytes(table.columns, rows[table.name])
        files[table.filename] = content
        table_inventory[table.name] = {
            "path": table.filename,
            "row_type": table.row_type,
            "row_count": len(rows[table.name]),
            "byte_count": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }

    file_inventory = {
        name: {
            "byte_count": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        for name, content in sorted(files.items())
    }
    manifest_preimage = {
        "schema_version": DARWIN_CORE_EXPORT_SCHEMA_VERSION,
        "policy_version": DARWIN_CORE_EXPORT_POLICY_VERSION,
        "darwin_core_text_guide_version": DARWIN_CORE_TEXT_GUIDE_VERSION,
        "darwin_core_terms_version": DARWIN_CORE_TERMS_VERSION,
        "package_id": request.package_id,
        "dataset_id": request.dataset_id,
        "dataset_title": request.dataset_title,
        "package_version": request.package_version,
        "created_at": request.created_at,
        "code_sha": request.code_sha,
        "publication_state": "prepared_not_published",
        "provider_submission_state": "not_submitted",
        "record_count": len(request.records),
        "table_order": list(DARWIN_CORE_EXPORT_TABLES),
        "tables": table_inventory,
        "files": file_inventory,
        "release_receipt_fingerprints": sorted(
            record.release_receipt_fingerprint for record in request.records
        ),
        "contains_raw_coordinates": False,
        "contains_reviewer_identity": False,
        "contains_media_bytes": False,
    }
    package_fingerprint = hashlib.sha256(canonicalize_json(manifest_preimage)).hexdigest()
    manifest: dict[str, object] = {
        **manifest_preimage,
        "package_fingerprint": package_fingerprint,
    }
    files["evidence-manifest.json"] = canonicalize_json(manifest) + b"\n"

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in ("meta.xml", *(table.filename for table in _TABLES), "evidence-manifest.json"):
            info = zipfile.ZipInfo(name, _ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.flag_bits |= 0x800
            archive.writestr(info, files[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    archive_bytes = output.getvalue()
    return DarwinCoreEvidencePackage(
        archive_bytes=archive_bytes,
        archive_sha256=hashlib.sha256(archive_bytes).hexdigest(),
        package_fingerprint=package_fingerprint,
        manifest=manifest,
    )
