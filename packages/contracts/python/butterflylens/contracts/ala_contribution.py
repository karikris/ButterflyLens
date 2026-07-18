"""Deterministic, offline preparation of an ALA contribution package."""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Literal, Mapping
from urllib.parse import urlsplit
from xml.sax.saxutils import escape, quoteattr
import zipfile

from .darwin_core_export import (
    DARWIN_CORE_EXPORT_POLICY_VERSION,
    DARWIN_CORE_EXPORT_SCHEMA_VERSION,
    DARWIN_CORE_EXPORT_TABLES,
)
from .fingerprint import canonicalize_json


ALA_CONTRIBUTION_SCHEMA_VERSION = "butterflylens-ala-contribution:v1.0.0"
ALA_CONTRIBUTION_POLICY_VERSION = "butterflylens-ala-contribution-policy:v1.0.0"
ALA_DATASET_GUIDANCE_VERSION = "2024-04-30"
ALA_PREFERRED_LICENCES = (
    "CC0-1.0",
    "CC-BY-4.0",
    "CC-BY-NC-4.0",
)
ALA_PROVIDER_CHECKS = (
    "data_provider_agreement_executed",
    "authority_to_provide_occurrence_data",
    "dataset_licence_approved",
    "attribution_approved",
    "sensitive_data_reviewed",
    "administrative_contact_approved",
    "update_and_removal_process_confirmed",
    "third_party_media_terms_reviewed",
)
ALA_CONTRIBUTION_ARTIFACTS = (
    "eml.xml",
    "licence.json",
    "attribution.txt",
    "provider-agreement-checklist.json",
    "quality-report.json",
    "ala-evidence-manifest.json",
)

_LICENCE_URLS = {
    "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC-BY-NC-4.0": "https://creativecommons.org/licenses/by-nc/4.0/",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_SOURCE_MEMBERS = (
    "meta.xml",
    *(f"{name}.txt" for name in DARWIN_CORE_EXPORT_TABLES),
    "evidence-manifest.json",
)


def _text(value: str, field: str, *, maximum: int = 4_000) -> None:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError(f"{field} must contain 1 to {maximum} characters")
    if _CONTROL.search(value):
        raise ValueError(f"{field} cannot contain control characters")


def _identifier(value: str, field: str) -> None:
    _text(value, field, maximum=400)
    if any(character.isspace() for character in value):
        raise ValueError(f"{field} cannot contain whitespace")


def _fingerprint(value: str, field: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")


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


def _created_at(value: str) -> None:
    _text(value, "prepared_at", maximum=64)
    if not value.endswith("Z"):
        raise ValueError("prepared_at must be an explicit UTC RFC 3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ValueError("prepared_at must be an explicit UTC RFC 3339 timestamp") from error
    if parsed.utcoffset() is None:
        raise ValueError("prepared_at must be an explicit UTC RFC 3339 timestamp")


def _unique_text(values: tuple[str, ...], field: str, *, maximum: int = 800) -> None:
    if not values:
        raise ValueError(f"{field} requires at least one value")
    if tuple(sorted(set(values))) != values:
        raise ValueError(f"{field} must be sorted and unique")
    for index, value in enumerate(values):
        _text(value, f"{field}[{index}]", maximum=maximum)


@dataclass(frozen=True, slots=True)
class AlaDatasetMetadata:
    dataset_id: str
    title: str
    description: str
    purpose: str
    geographic_scope: str
    taxonomic_scope: str
    temporal_scope: str
    methods: str
    creator_name: str
    creator_organisation: str
    administrative_contact_name: str
    administrative_contact_email: str
    provider_url: str
    citation: str
    keywords: tuple[str, ...]
    language: str = "en"

    def __post_init__(self) -> None:
        _identifier(self.dataset_id, "dataset_id")
        for field, value, maximum in (
            ("title", self.title, 300),
            ("description", self.description, 4_000),
            ("purpose", self.purpose, 1_500),
            ("geographic_scope", self.geographic_scope, 1_500),
            ("taxonomic_scope", self.taxonomic_scope, 1_500),
            ("temporal_scope", self.temporal_scope, 1_500),
            ("methods", self.methods, 4_000),
            ("creator_name", self.creator_name, 300),
            ("creator_organisation", self.creator_organisation, 300),
            ("administrative_contact_name", self.administrative_contact_name, 300),
            ("citation", self.citation, 1_500),
        ):
            _text(value, field, maximum=maximum)
        _text(self.administrative_contact_email, "administrative_contact_email", maximum=320)
        if not _EMAIL.fullmatch(self.administrative_contact_email):
            raise ValueError("administrative_contact_email must be a valid email address")
        _https_url(self.provider_url, "provider_url")
        _unique_text(self.keywords, "keywords", maximum=100)
        if self.language != "en":
            raise ValueError("language must be en for this ALA contribution policy version")


@dataclass(frozen=True, slots=True)
class AlaDatasetLicence:
    identifier: Literal["CC0-1.0", "CC-BY-4.0", "CC-BY-NC-4.0"]
    url: str
    rights_holder: str
    rights_authority_fingerprint: str
    applies_to_dataset_records: Literal[True] = True
    third_party_media_licences_retained: Literal[True] = True

    def __post_init__(self) -> None:
        if self.identifier not in ALA_PREFERRED_LICENCES:
            raise ValueError("identifier must be an ALA-preferred Creative Commons licence")
        if self.url != _LICENCE_URLS[self.identifier]:
            raise ValueError("url must be the canonical URL for the selected licence")
        _text(self.rights_holder, "rights_holder", maximum=300)
        _fingerprint(self.rights_authority_fingerprint, "rights_authority_fingerprint")
        if not self.applies_to_dataset_records:
            raise ValueError("the selected dataset licence must apply to dataset records")
        if not self.third_party_media_licences_retained:
            raise ValueError("third-party media licences must remain record-specific")


@dataclass(frozen=True, slots=True)
class AlaProviderCheck:
    check_id: str
    status: Literal["passed", "pending"]
    evidence_reference: str | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        if self.check_id not in ALA_PROVIDER_CHECKS:
            raise ValueError(f"unknown provider check: {self.check_id}")
        if self.status not in ("passed", "pending"):
            raise ValueError("provider check status must be passed or pending")
        if self.status == "passed" and self.evidence_reference is None:
            raise ValueError("a passed provider check requires an evidence_reference")
        if self.status == "pending" and self.evidence_reference is not None:
            raise ValueError("a pending provider check cannot claim evidence")
        if self.evidence_reference is not None:
            _text(self.evidence_reference, "evidence_reference", maximum=800)
            if not self.evidence_reference.startswith("urn:sha256:"):
                raise ValueError("evidence_reference must be a SHA-256 URN")
            _fingerprint(
                self.evidence_reference.removeprefix("urn:sha256:"),
                "evidence_reference",
            )
        if self.note is not None:
            _text(self.note, "note", maximum=800)


@dataclass(frozen=True, slots=True)
class AlaProviderAgreementChecklist:
    checks: tuple[AlaProviderCheck, ...]

    def __post_init__(self) -> None:
        if tuple(check.check_id for check in self.checks) != ALA_PROVIDER_CHECKS:
            raise ValueError("provider checks must contain every required check in policy order")

    @property
    def passed(self) -> bool:
        return all(check.status == "passed" for check in self.checks)


@dataclass(frozen=True, slots=True)
class AlaQualityDeclaration:
    unresolved_blockers: tuple[str, ...]
    limitations: tuple[str, ...]
    representative_audit_reviewed: bool

    def __post_init__(self) -> None:
        if tuple(sorted(set(self.unresolved_blockers))) != self.unresolved_blockers:
            raise ValueError("unresolved_blockers must be sorted and unique")
        for index, value in enumerate(self.unresolved_blockers):
            _text(value, f"unresolved_blockers[{index}]", maximum=800)
        _unique_text(self.limitations, "limitations", maximum=1_500)
        if not isinstance(self.representative_audit_reviewed, bool):
            raise ValueError("representative_audit_reviewed must be boolean")


@dataclass(frozen=True, slots=True)
class AlaContributionRequest:
    package_id: str
    prepared_at: str
    code_sha: str
    source_archive_sha256: str
    source_package_fingerprint: str
    dataset: AlaDatasetMetadata
    licence: AlaDatasetLicence
    provider_checklist: AlaProviderAgreementChecklist
    quality: AlaQualityDeclaration
    attribution_statement: str
    package_version: str = "1.0.0"

    def __post_init__(self) -> None:
        _identifier(self.package_id, "package_id")
        _created_at(self.prepared_at)
        _fingerprint(self.code_sha, "code_sha")
        _fingerprint(self.source_archive_sha256, "source_archive_sha256")
        _fingerprint(self.source_package_fingerprint, "source_package_fingerprint")
        _text(self.attribution_statement, "attribution_statement", maximum=2_000)
        _text(self.package_version, "package_version", maximum=64)
        if self.dataset.citation not in self.attribution_statement:
            raise ValueError("attribution_statement must retain the dataset citation")
        if self.dataset.creator_organisation not in self.attribution_statement:
            raise ValueError("attribution_statement must name the creator organisation")
        if self.licence.url not in self.attribution_statement:
            raise ValueError("attribution_statement must retain the dataset licence URL")
        if "record-specific media rights" not in self.attribution_statement.lower():
            raise ValueError("attribution_statement must retain record-specific media rights")


@dataclass(frozen=True, slots=True)
class AlaContributionPackage:
    archive_bytes: bytes
    archive_sha256: str
    package_fingerprint: str
    preparation_state: Literal[
        "ready_for_human_submission",
        "blocked_pending_provider_requirements",
        "blocked_quality_review",
    ]
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
class _VerifiedSource:
    files: dict[str, bytes]
    manifest: dict[str, object]
    record_count: int
    representative_audit_fingerprints: tuple[str, ...]


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


def ala_contribution_request_from_dict(
    value: Mapping[str, object],
) -> AlaContributionRequest:
    """Parse an exact JSON-shaped preparation request."""

    payload = _strict_kwargs(value, AlaContributionRequest, "request")
    dataset_payload = _strict_kwargs(
        payload.get("dataset"), AlaDatasetMetadata, "request.dataset"  # type: ignore[arg-type]
    )
    raw_keywords = dataset_payload.get("keywords")
    if not isinstance(raw_keywords, list) or not all(
        isinstance(item, str) for item in raw_keywords
    ):
        raise ValueError("request.dataset.keywords must be an array of strings")
    dataset_payload["keywords"] = tuple(raw_keywords)
    payload["dataset"] = AlaDatasetMetadata(**dataset_payload)  # type: ignore[arg-type]

    payload["licence"] = AlaDatasetLicence(
        **_strict_kwargs(
            payload.get("licence"), AlaDatasetLicence, "request.licence"  # type: ignore[arg-type]
        )
    )

    checklist_payload = _strict_kwargs(
        payload.get("provider_checklist"),
        AlaProviderAgreementChecklist,
        "request.provider_checklist",  # type: ignore[arg-type]
    )
    raw_checks = checklist_payload.get("checks")
    if not isinstance(raw_checks, list):
        raise ValueError("request.provider_checklist.checks must be an array")
    checklist_payload["checks"] = tuple(
        AlaProviderCheck(
            **_strict_kwargs(
                check,
                AlaProviderCheck,
                f"request.provider_checklist.checks[{index}]",  # type: ignore[arg-type]
            )
        )
        for index, check in enumerate(raw_checks)
    )
    payload["provider_checklist"] = AlaProviderAgreementChecklist(
        **checklist_payload  # type: ignore[arg-type]
    )

    quality_payload = _strict_kwargs(
        payload.get("quality"), AlaQualityDeclaration, "request.quality"  # type: ignore[arg-type]
    )
    for field in ("unresolved_blockers", "limitations"):
        raw_values = quality_payload.get(field)
        if not isinstance(raw_values, list) or not all(
            isinstance(item, str) for item in raw_values
        ):
            raise ValueError(f"request.quality.{field} must be an array of strings")
        quality_payload[field] = tuple(raw_values)
    payload["quality"] = AlaQualityDeclaration(**quality_payload)  # type: ignore[arg-type]
    return AlaContributionRequest(**payload)  # type: ignore[arg-type]


def _safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts and "\\" not in name


def _object(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


def _verify_source_archive(
    source_archive: bytes, request: AlaContributionRequest
) -> _VerifiedSource:
    if hashlib.sha256(source_archive).hexdigest() != request.source_archive_sha256:
        raise ValueError("source Darwin Core archive SHA-256 does not match request")
    try:
        with zipfile.ZipFile(io.BytesIO(source_archive)) as archive:
            infos = archive.infolist()
            names = tuple(info.filename for info in infos)
            if names != _SOURCE_MEMBERS:
                raise ValueError("source archive member order or inventory is not governed")
            if len(names) != len(set(names)) or not all(_safe_member(name) for name in names):
                raise ValueError("source archive contains duplicate or unsafe members")
            if any(info.flag_bits & 0x1 for info in infos):
                raise ValueError("source archive cannot contain encrypted members")
            files = {name: archive.read(name) for name in names}
    except (zipfile.BadZipFile, RuntimeError) as error:
        raise ValueError("source archive must be a readable Darwin Core ZIP") from error

    try:
        raw_manifest = json.loads(files["evidence-manifest.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("source evidence manifest must be valid UTF-8 JSON") from error
    manifest = _object(raw_manifest, "source evidence manifest")
    if manifest.get("schema_version") != DARWIN_CORE_EXPORT_SCHEMA_VERSION:
        raise ValueError("source archive schema version is not supported")
    if manifest.get("policy_version") != DARWIN_CORE_EXPORT_POLICY_VERSION:
        raise ValueError("source archive policy version is not supported")
    if manifest.get("publication_state") != "prepared_not_published":
        raise ValueError("source archive must remain prepared_not_published")
    if manifest.get("provider_submission_state") != "not_submitted":
        raise ValueError("source archive must remain not_submitted")
    for field in ("contains_raw_coordinates", "contains_reviewer_identity", "contains_media_bytes"):
        if manifest.get(field) is not False:
            raise ValueError(f"source archive {field} boundary is not safe")
    if manifest.get("package_fingerprint") != request.source_package_fingerprint:
        raise ValueError("source package fingerprint does not match request")
    fingerprint_preimage = dict(manifest)
    fingerprint = fingerprint_preimage.pop("package_fingerprint", None)
    if fingerprint != hashlib.sha256(canonicalize_json(fingerprint_preimage)).hexdigest():
        raise ValueError("source evidence manifest fingerprint is invalid")
    if manifest.get("dataset_id") != request.dataset.dataset_id:
        raise ValueError("source dataset_id does not match ALA metadata")
    if manifest.get("dataset_title") != request.dataset.title:
        raise ValueError("source dataset_title does not match ALA metadata")

    source_inventory = _object(manifest.get("files"), "source manifest files")
    for name, item in source_inventory.items():
        if name not in files or name == "evidence-manifest.json":
            raise ValueError("source manifest inventories an unexpected file")
        entry = _object(item, f"source manifest files.{name}")
        content = files[name]
        if entry.get("byte_count") != len(content):
            raise ValueError(f"source member byte count mismatch: {name}")
        if entry.get("sha256") != hashlib.sha256(content).hexdigest():
            raise ValueError(f"source member checksum mismatch: {name}")
    if set(source_inventory) != set(_SOURCE_MEMBERS) - {"evidence-manifest.json"}:
        raise ValueError("source manifest file inventory is incomplete")

    record_count = manifest.get("record_count")
    if not isinstance(record_count, int) or isinstance(record_count, bool) or record_count < 1:
        raise ValueError("source record_count must be a positive integer")
    release_receipts = manifest.get("release_receipt_fingerprints")
    if (
        not isinstance(release_receipts, list)
        or not all(isinstance(item, str) for item in release_receipts)
        or len(release_receipts) != record_count
        or len(set(release_receipts)) != record_count
    ):
        raise ValueError("source release receipt inventory must match record_count")
    for release_receipt in release_receipts:
        _fingerprint(release_receipt, "source release receipt fingerprint")
    try:
        rows = list(csv.DictReader(io.StringIO(files["quality.txt"].decode("utf-8"))))
    except UnicodeDecodeError as error:
        raise ValueError("source quality extension must be UTF-8") from error
    audit_fingerprints: set[str] = set()
    for row in rows:
        if row.get("assertionType") != "quality_snapshot_kind":
            continue
        reference = row.get("assertionReferences", "")
        if not reference.startswith("urn:sha256:"):
            raise ValueError("quality snapshot references must be SHA-256 URNs")
        value = reference.removeprefix("urn:sha256:")
        _fingerprint(value, "quality snapshot fingerprint")
        audit_fingerprints.add(value)
    if not audit_fingerprints:
        raise ValueError("source archive has no representative quality snapshot evidence")
    return _VerifiedSource(
        files=files,
        manifest=manifest,
        record_count=record_count,
        representative_audit_fingerprints=tuple(sorted(audit_fingerprints)),
    )


def _eml(request: AlaContributionRequest) -> bytes:
    dataset = request.dataset
    licence = request.licence
    keywords = "\n".join(
        f"      <keyword>{escape(keyword)}</keyword>" for keyword in dataset.keywords
    )
    description = (
        f"{dataset.description} Purpose: {dataset.purpose} Geographic scope: "
        f"{dataset.geographic_scope} Taxonomic scope: {dataset.taxonomic_scope} "
        f"Temporal scope: {dataset.temporal_scope}"
    )
    lines = (
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<eml:eml packageId={quoteattr(dataset.dataset_id)} system="ButterflyLens"',
        '  xmlns:eml="eml://ecoinformatics.org/eml-2.1.1"',
        '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
        '  xsi:schemaLocation="eml://ecoinformatics.org/eml-2.1.1 '
        'https://eml.ecoinformatics.org/eml-2.1.1/eml.xsd">',
        "  <dataset>",
        f"    <title>{escape(dataset.title)}</title>",
        "    <creator>",
        f"      <individualName><surName>{escape(dataset.creator_name)}</surName></individualName>",
        f"      <organizationName>{escape(dataset.creator_organisation)}</organizationName>",
        "    </creator>",
        "    <contact>",
        "      <individualName><surName>"
        f"{escape(dataset.administrative_contact_name)}</surName></individualName>",
        "      <electronicMailAddress>"
        f"{escape(dataset.administrative_contact_email)}</electronicMailAddress>",
        "    </contact>",
        f"    <language>{escape(dataset.language)}</language>",
        f"    <abstract><para>{escape(description)}</para></abstract>",
        "    <keywordSet>",
        keywords,
        "    </keywordSet>",
        f"    <intellectualRights><para>{escape(licence.identifier)} {escape(licence.url)}. "
        "Dataset-record licence only; record-specific media rights and attribution "
        "remain authoritative."
        "</para></intellectualRights>",
        "    <distribution><online><url function=\"information\">"
        f"{escape(dataset.provider_url)}</url></online></distribution>",
        "    <coverage>",
        "      <geographicCoverage><geographicDescription>"
        f"{escape(dataset.geographic_scope)}</geographicDescription></geographicCoverage>",
        "      <taxonomicCoverage><generalTaxonomicCoverage>"
        f"{escape(dataset.taxonomic_scope)}</generalTaxonomicCoverage></taxonomicCoverage>",
        "      <temporalCoverage><singleDateTime><calendarDate>"
        f"{escape(dataset.temporal_scope)}</calendarDate></singleDateTime></temporalCoverage>",
        "    </coverage>",
        "    <methods><methodStep><description><para>"
        f"{escape(dataset.methods)}</para></description></methodStep></methods>",
        f"    <alternateIdentifier>{escape(dataset.citation)}</alternateIdentifier>",
        "  </dataset>",
        "</eml:eml>",
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def _licence(request: AlaContributionRequest) -> bytes:
    value = {
        "schema_version": "butterflylens-ala-dataset-licence:v1.0.0",
        "dataset_id": request.dataset.dataset_id,
        "identifier": request.licence.identifier,
        "url": request.licence.url,
        "rights_holder": request.licence.rights_holder,
        "rights_authority_fingerprint": request.licence.rights_authority_fingerprint,
        "applies_to_dataset_records": True,
        "third_party_media_licences_retained": True,
        "media_rights_rule": (
            "record-specific media licence, creator, rights holder, attribution, "
            "and source URL remain authoritative"
        ),
    }
    return canonicalize_json(value) + b"\n"


def _checklist(request: AlaContributionRequest) -> bytes:
    value = {
        "schema_version": "butterflylens-ala-provider-checklist:v1.0.0",
        "ala_terms_reviewed_at": request.prepared_at,
        "passed": request.provider_checklist.passed,
        "checks": [
            {
                "check_id": check.check_id,
                "status": check.status,
                "evidence_reference": check.evidence_reference,
                "note": check.note,
            }
            for check in request.provider_checklist.checks
        ],
    }
    return canonicalize_json(value) + b"\n"


def _quality_report(
    request: AlaContributionRequest, source: _VerifiedSource
) -> tuple[bytes, bool]:
    passed = (
        request.quality.representative_audit_reviewed
        and not request.quality.unresolved_blockers
    )
    value = {
        "schema_version": "butterflylens-ala-quality-report:v1.0.0",
        "dataset_id": request.dataset.dataset_id,
        "record_count": source.record_count,
        "release_gate_state": "release_ready_occurrence_candidate",
        "source_darwin_core_package_fingerprint": request.source_package_fingerprint,
        "release_receipt_count": source.record_count,
        "representative_audit_fingerprints": list(source.representative_audit_fingerprints),
        "representative_audit_reviewed": request.quality.representative_audit_reviewed,
        "unresolved_blockers": list(request.quality.unresolved_blockers),
        "limitations": list(request.quality.limitations),
        "quality_gate_passed": passed,
        "targeted_failure_discovery_used_as_population_metric": False,
        "model_score_interpreted_as_probability": False,
        "absence_claimed_from_no_detection": False,
        "provider_or_ala_acceptance_claimed": False,
    }
    return canonicalize_json(value) + b"\n", passed


def build_ala_contribution_package(
    request: AlaContributionRequest, source_archive: bytes
) -> AlaContributionPackage:
    """Prepare a verified ALA handoff archive without any submission action."""

    source = _verify_source_archive(source_archive, request)
    quality_report, quality_passed = _quality_report(request, source)
    if not quality_passed:
        preparation_state = "blocked_quality_review"
    elif not request.provider_checklist.passed:
        preparation_state = "blocked_pending_provider_requirements"
    else:
        preparation_state = "ready_for_human_submission"

    files = dict(source.files)
    files.update(
        {
            "eml.xml": _eml(request),
            "licence.json": _licence(request),
            "attribution.txt": (request.attribution_statement + "\n").encode("utf-8"),
            "provider-agreement-checklist.json": _checklist(request),
            "quality-report.json": quality_report,
        }
    )
    member_order = (
        "meta.xml",
        "eml.xml",
        *(f"{name}.txt" for name in DARWIN_CORE_EXPORT_TABLES),
        "evidence-manifest.json",
        "licence.json",
        "attribution.txt",
        "provider-agreement-checklist.json",
        "quality-report.json",
    )
    file_inventory = {
        name: {
            "byte_count": len(files[name]),
            "sha256": hashlib.sha256(files[name]).hexdigest(),
            "origin": "source_darwin_core_archive" if name in source.files else "ala_preparation",
        }
        for name in member_order
    }
    manifest_preimage = {
        "schema_version": ALA_CONTRIBUTION_SCHEMA_VERSION,
        "policy_version": ALA_CONTRIBUTION_POLICY_VERSION,
        "ala_dataset_guidance_version": ALA_DATASET_GUIDANCE_VERSION,
        "package_id": request.package_id,
        "package_version": request.package_version,
        "prepared_at": request.prepared_at,
        "code_sha": request.code_sha,
        "dataset_id": request.dataset.dataset_id,
        "dataset_title": request.dataset.title,
        "source_archive_sha256": request.source_archive_sha256,
        "source_package_fingerprint": request.source_package_fingerprint,
        "record_count": source.record_count,
        "preparation_state": preparation_state,
        "publication_state": "prepared_not_published",
        "provider_submission_state": "not_submitted",
        "provider_checklist_passed": request.provider_checklist.passed,
        "quality_gate_passed": quality_passed,
        "contains_administrative_contact": True,
        "intended_access": "private_operator_handoff",
        "contains_raw_coordinates": False,
        "contains_reviewer_identity": False,
        "contains_media_bytes": False,
        "dataset_metadata_artifact": "eml.xml",
        "licence_artifact": "licence.json",
        "attribution_artifact": "attribution.txt",
        "provider_agreement_artifact": "provider-agreement-checklist.json",
        "quality_report_artifact": "quality-report.json",
        "evidence_manifest_artifact": "ala-evidence-manifest.json",
        "source_member_order": list(_SOURCE_MEMBERS),
        "file_order": [*member_order, "ala-evidence-manifest.json"],
        "files": file_inventory,
        "automatic_submission_available": False,
        "human_submission_required": True,
    }
    package_fingerprint = hashlib.sha256(canonicalize_json(manifest_preimage)).hexdigest()
    manifest: dict[str, object] = {
        **manifest_preimage,
        "package_fingerprint": package_fingerprint,
    }
    files["ala-evidence-manifest.json"] = canonicalize_json(manifest) + b"\n"

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in (*member_order, "ala-evidence-manifest.json"):
            info = zipfile.ZipInfo(name, _ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.flag_bits |= 0x800
            archive.writestr(
                info,
                files[name],
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )
    archive_bytes = output.getvalue()
    return AlaContributionPackage(
        archive_bytes=archive_bytes,
        archive_sha256=hashlib.sha256(archive_bytes).hexdigest(),
        package_fingerprint=package_fingerprint,
        preparation_state=preparation_state,  # type: ignore[arg-type]
        manifest=manifest,
    )
