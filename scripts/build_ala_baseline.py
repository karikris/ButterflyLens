#!/usr/bin/env python3
"""Acquire and build the frozen ButterflyLens ALA baseline.

Provider access is confined to explicit acquisition commands. Downstream build
commands consume the checked-in archive and contract receipts without making
network requests.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SNAPSHOT_SCHEMA_VERSION = "butterflylens-ala-occurrence-snapshot/v1"
ATTRIBUTION_SCHEMA_VERSION = "butterflylens-ala-attribution/v1"
NORMALIZED_SCHEMA_VERSION = "butterflylens-ala-normalized-occurrence/v1"
NORMALIZATION_MANIFEST_SCHEMA_VERSION = "butterflylens-ala-normalization-manifest/v1"
AGGREGATED_SCHEMA_VERSION = "butterflylens-ala-baseline-cell/v1"
AGGREGATION_MANIFEST_SCHEMA_VERSION = "butterflylens-ala-aggregation-manifest/v1"
DATASET_SCHEMA_VERSION = "butterflylens-ala-dataset-manifest/v1"
PUBLISHED_SNAPSHOT_SCHEMA_VERSION = "butterflylens-ala-published-snapshot/v1"
ALA_PROVIDER = "Atlas of Living Australia"
ALA_ROOT_NAME = "PAPILIONOIDEA"
ALA_ROOT_TAXON_ID = (
    "https://biodiversity.org.au/afd/taxa/"
    "3ebff933-1678-4cbd-8d85-05c4bc48487c"
)
ALA_DOWNLOAD_ENDPOINT = (
    "https://api.ala.org.au/occurrences/occurrences/offline/download"
)
ALA_OPENAPI_URL = "https://docs.ala.org.au/openapi/specs/biocache.json"
ALA_INDEX_FIELDS_URL = "https://api.ala.org.au/occurrences/index/fields"
ALA_SPATIAL_OPENAPI_URL = "https://spatial.ala.org.au/ws/openapi/openapi"
ALA_SPATIAL_LAYER_URL = "https://spatial.ala.org.au/ws/layer/{layer_id}"
ALA_TERMS_URL = "https://www.ala.org.au/terms-of-use/"
ALA_CITATION_URL = (
    "https://support.ala.org.au/support/solutions/articles/"
    "6000261662-citing-the-ala"
)
ALA_DOWNLOAD_GUIDE_URL = (
    "https://support.ala.org.au/support/solutions/articles/"
    "6000196714-how-to-download-occurrence-records"
)
IBRA_LAYER_ID = "11185"
IBRA_FIELD = "cl11185"
LGA_LAYER_ID = "11170"
LGA_FIELD = "cl11170"
USER_AGENT = (
    "ButterflyLens/0.1 (+https://github.com/karikris/ButterflyLens; "
    "public ALA baseline acquisition)"
)

DOWNLOAD_FIELDS = (
    "id",
    "occurrenceID",
    "taxonConceptID",
    "names_and_lsid",
    "scientificName",
    "species",
    "speciesID",
    "subspecies",
    "subspeciesID",
    "taxonRank",
    "dataProviderName",
    "dataProviderUid",
    "dataResourceName",
    "dataResourceUid",
    "decimalLatitude",
    "decimalLongitude",
    "coordinateUncertaintyInMeters",
    "eventDate",
    "basisOfRecord",
    "raw_basisOfRecord",
    "license",
    "rights",
    "sensitive",
    "spatiallyValid",
    "assertions",
    "stateProvince",
    "country",
    "references",
)
EXTRA_FIELDS = (IBRA_FIELD, LGA_FIELD)
ALLOWED_PUBLIC_LICENCES = (
    "CC-BY",
    "CC-BY 3.0 (Au)",
    "CC-BY 3.0 (Int)",
    "CC-BY 4.0 (Au)",
    "CC-BY 4.0 (Int)",
    "CC-BY-Int",
    "CC0",
    "PDM",
)
LICENCE_FILTER = "license:(" + " OR ".join(
    f'"{licence}"' for licence in ALLOWED_PUBLIC_LICENCES
) + ")"
FILTER_QUERIES = ("country:Australia", LICENCE_FILTER)
NORMALIZED_FIELD_SPECS = (
    ("source_snapshot_id", "string", False, "Frozen ALA snapshot identifier."),
    ("source_snapshot_fingerprint", "string", False, "Semantic fingerprint of the source snapshot policy and archive."),
    ("source_archive_sha256", "string", False, "Physical SHA-256 of the frozen provider archive."),
    ("source_row_number", "int32", False, "One-based row position in the provider occurrence CSV."),
    ("ala_record_id", "string", False, "ALA stable record UUID from requested field id."),
    ("source_occurrence_id", "string", True, "Provider occurrenceID preserved without reinterpretation."),
    ("normalized_occurrence_fingerprint", "string", False, "SHA-256 of the normalized semantic row before this field is added."),
    ("butterflylens_taxon_key", "string", True, "Stable pack key only for an exact ALA taxonConceptID crosswalk match."),
    ("taxon_match_state", "string", False, "Exact-crosswalk or unmatched-provider-assertion state."),
    ("provider_taxon_concept_id", "string", True, "ALA-processed taxon concept assertion."),
    ("provider_names_and_lsid", "string", True, "ALA combined name/identifier display field."),
    ("provider_scientific_name", "string", True, "ALA-processed scientific-name assertion."),
    ("provider_taxon_rank", "string", True, "ALA-processed taxon-rank assertion."),
    ("provider_species_name", "string", True, "ALA-processed species-name assertion."),
    ("provider_species_id", "string", True, "ALA-processed species identifier."),
    ("provider_subspecies_name", "string", True, "ALA-processed subspecies-name assertion."),
    ("provider_subspecies_id", "string", True, "ALA-processed subspecies identifier."),
    ("data_provider_name", "string", True, "ALA data-provider name."),
    ("data_provider_uid", "string", True, "ALA data-provider identifier."),
    ("data_resource_name", "string", True, "Contributing data-resource name."),
    ("data_resource_uid", "string", False, "Contributing ALA data-resource identifier."),
    ("decimal_latitude", "float64", True, "Public ALA-processed WGS84 latitude."),
    ("decimal_longitude", "float64", True, "Public ALA-processed WGS84 longitude."),
    ("coordinate_uncertainty_meters", "float64", True, "Provider coordinate uncertainty in metres."),
    ("has_coordinates", "bool", False, "Both processed coordinate values are present."),
    ("coordinate_in_wgs84_range", "bool", False, "Coordinates are finite and within WGS84 latitude/longitude ranges."),
    ("spatially_valid", "bool", True, "ALA spatiallyValid assertion; null only when not supplied."),
    ("sensitive_status", "string", False, "ALA sensitive/generalisation state or not_supplied."),
    ("coordinates_publicly_generalised", "bool", False, "ALA marks coordinates generalised or alreadyGeneralised."),
    ("spatial_aggregation_eligibility", "string", False, "Explicit exclusion, coarse-only, or all-configured-resolution state."),
    ("event_date", "string", True, "ALA-processed event date preserved as supplied by the download."),
    ("event_year", "int32", True, "Leading valid four-digit event year when parseable."),
    ("temporal_evidence_band", "string", False, "Declared temporal band; historical is an analytical convention, not a provider type."),
    ("basis_of_record", "string", True, "ALA-processed basis of record."),
    ("raw_basis_of_record", "string", True, "Publisher-supplied basis of record retained by ALA."),
    ("evidence_category", "string", False, "Deterministic category distinguishing observations, machine evidence, material, specimens, fossils, and unspecified occurrences."),
    ("licence", "string", False, "ALA-processed per-record licence from the public allowlist."),
    ("rights", "string", True, "Provider rights text retained without reinterpretation."),
    ("quality_assertions", "list<string>", False, "Ordered ALA quality-assertion codes."),
    ("quality_assertion_count", "int32", False, "Number of retained quality assertions."),
    ("country", "string", True, "ALA-processed country."),
    ("state_territory", "string", True, "ALA-processed state or territory."),
    ("ibra_region", "string", True, "ALA contextual IBRA v7 region assertion (cl11185)."),
    ("lga_name", "string", True, "ALA contextual LGA 2023 statistical approximation (cl11170)."),
    ("source_reference", "string", True, "Provider source reference URL or identifier."),
)
H3_RESOLUTIONS = {"coarse": 3, "regional": 5, "local": 7}
EVIDENCE_COUNT_FIELDS = {
    "human_observation": "human_observation_count",
    "machine_observation": "machine_observation_count",
    "unspecified_observation": "unspecified_observation_count",
    "material_sample": "material_sample_count",
    "preserved_specimen": "preserved_specimen_count",
    "fossil_specimen": "fossil_specimen_count",
    "unspecified_occurrence": "unspecified_occurrence_count",
    "other_or_not_supplied": "other_or_not_supplied_count",
}
AGGREGATED_FIELD_SPECS = (
    ("source_snapshot_id", "string", False, "Frozen ALA snapshot identifier."),
    ("source_snapshot_fingerprint", "string", False, "Semantic fingerprint of the source snapshot."),
    ("source_occurrence_artifact_sha256", "string", False, "Physical SHA-256 of the normalized occurrence artifact."),
    ("scope_type", "string", False, "Closed national, provider-context, or H3 scope type."),
    ("scope_order", "int32", False, "Stable national-to-local sort order."),
    ("scope_id", "string", False, "Stable scope identifier."),
    ("scope_label", "string", False, "Provider label or H3 cell identifier."),
    ("scope_resolution_class", "string", False, "National, coarse, regional, or local presentation class."),
    ("sensitive_membership_policy", "string", False, "Whether publicly generalised rows may contribute to this scope."),
    ("contextual_source", "string", False, "Source of the scope membership assertion."),
    ("h3_resolution", "int32", True, "H3 resolution for H3 scopes only."),
    ("h3_cell_id", "string", True, "H3 cell identifier for H3 scopes only."),
    ("parent_h3_cell_id", "string", True, "Configured parent H3 cell for regional/local scopes."),
    ("cell_center_latitude", "float64", True, "Derived H3 center latitude; not an occurrence coordinate."),
    ("cell_center_longitude", "float64", True, "Derived H3 center longitude; not an occurrence coordinate."),
    ("record_count", "int64", False, "Number of eligible ALA baseline occurrence-evidence rows in the scope."),
    ("matched_taxon_record_count", "int64", False, "Rows with an exact ALA taxonConceptID crosswalk match."),
    ("unmatched_taxon_assertion_count", "int64", False, "Rows retaining an unmatched provider taxon assertion."),
    ("unique_butterflylens_taxon_count", "int64", False, "Distinct exactly crosswalked ButterflyLens taxon keys."),
    ("unique_data_resource_count", "int64", False, "Distinct contributing ALA data-resource identifiers."),
    ("human_observation_count", "int64", False, "Provider basis category count; not human verification."),
    ("machine_observation_count", "int64", False, "Machine-observation basis category count."),
    ("unspecified_observation_count", "int64", False, "Unspecified observation basis category count."),
    ("material_sample_count", "int64", False, "Material-sample basis category count."),
    ("preserved_specimen_count", "int64", False, "Preserved-specimen basis category count."),
    ("fossil_specimen_count", "int64", False, "Fossil-specimen basis category count."),
    ("unspecified_occurrence_count", "int64", False, "Unspecified occurrence basis category count."),
    ("other_or_not_supplied_count", "int64", False, "Other or missing basis category count."),
    ("earliest_event_year", "int32", True, "Earliest parseable event year in the scope."),
    ("latest_event_year", "int32", True, "Latest parseable event year in the scope."),
    ("coordinate_uncertainty_known_count", "int64", False, "Rows with supplied numeric coordinate uncertainty."),
    ("coordinate_uncertainty_missing_count", "int64", False, "Rows without supplied numeric coordinate uncertainty."),
    ("maximum_coordinate_uncertainty_meters", "float64", True, "Maximum supplied coordinate uncertainty in the scope."),
    ("publicly_generalised_record_count", "int64", False, "Rows marked generalised or alreadyGeneralised by ALA."),
    ("source_record_fingerprint_digest", "string", False, "SHA-256 over ordered normalized source-row fingerprints."),
    ("aggregate_fingerprint", "string", False, "SHA-256 of the aggregate semantic row before this field is added."),
)
LICENCE_COUNT_FIELDS = {
    "CC-BY": "licence_cc_by_count",
    "CC-BY 3.0 (Au)": "licence_cc_by_3_au_count",
    "CC-BY 3.0 (Int)": "licence_cc_by_3_int_count",
    "CC-BY 4.0 (Au)": "licence_cc_by_4_au_count",
    "CC-BY 4.0 (Int)": "licence_cc_by_4_int_count",
    "CC-BY-Int": "licence_cc_by_int_count",
    "CC0": "licence_cc0_count",
    "PDM": "licence_pdm_count",
}
DATASET_FIELD_SPECS = (
    ("source_snapshot_id", "string", False, "Frozen ALA snapshot identifier."),
    ("source_snapshot_fingerprint", "string", False, "Semantic fingerprint of the source snapshot."),
    ("source_occurrence_artifact_sha256", "string", False, "Physical SHA-256 of the normalized occurrence artifact."),
    ("data_resource_uid", "string", False, "ALA data-resource identifier and exact citation join key."),
    ("data_resource_name", "string", False, "ALA data-resource name."),
    ("data_provider_uid", "string", True, "ALA data-provider identifier when supplied on selected rows."),
    ("data_provider_name", "string", True, "ALA data-provider name when supplied on selected rows."),
    ("selected_record_count", "int64", False, "Selected normalized rows from the data resource."),
    ("citation_record_count", "int64", False, "ALA citation inventory count for the exact resource UID."),
    ("citation_count_matches_selected", "bool", False, "Whether citation and selected normalized counts agree."),
    ("licence_cc_by_count", "int64", False, "Selected rows with processed licence CC-BY."),
    ("licence_cc_by_3_au_count", "int64", False, "Selected rows with processed licence CC-BY 3.0 (Au)."),
    ("licence_cc_by_3_int_count", "int64", False, "Selected rows with processed licence CC-BY 3.0 (Int)."),
    ("licence_cc_by_4_au_count", "int64", False, "Selected rows with processed licence CC-BY 4.0 (Au)."),
    ("licence_cc_by_4_int_count", "int64", False, "Selected rows with processed licence CC-BY 4.0 (Int)."),
    ("licence_cc_by_int_count", "int64", False, "Selected rows with processed licence CC-BY-Int."),
    ("licence_cc0_count", "int64", False, "Selected rows with processed licence CC0."),
    ("licence_pdm_count", "int64", False, "Selected rows with processed licence PDM."),
    ("doi", "string", True, "Provider citation DOI when supplied; not minted by ButterflyLens."),
    ("citation", "string", False, "Exact ALA citation-inventory text for the resource."),
    ("citation_rights", "string", True, "Exact ALA citation-inventory rights text."),
    ("data_generalisations", "string", True, "Exact ALA citation-inventory data-generalisation text."),
    ("information_withheld", "string", True, "Exact ALA citation-inventory information-withheld text."),
    ("download_limit", "string", True, "Exact ALA citation-inventory download-limit text."),
    ("more_information", "string", False, "ALA citation-inventory resource information link text."),
    ("publicly_generalised_record_count", "int64", False, "Selected rows marked generalised or alreadyGeneralised by ALA."),
    ("spatially_eligible_record_count", "int64", False, "Selected rows eligible for at least the configured coarse aggregate."),
    ("citation_restrictive_rights_terms_detected", "bool", False, "Conservative textual screening flag; not a legal conclusion."),
    ("citation_provider_conditions_present", "bool", False, "Whether rights/generalisation/withheld/download-limit text is supplied."),
    ("public_product_rights_review_state", "string", False, "Downstream public-product rights gate based on selected licences and citation text."),
    ("source_dataset_receipt_fingerprint", "string", False, "SHA-256 of the exact dataset and citation receipt pair."),
    ("dataset_manifest_fingerprint", "string", False, "SHA-256 of the dataset semantic row before this field is added."),
)
RESTRICTIVE_CITATION_RIGHTS_PATTERN = re.compile(
    r"non[ -]?commercial|cc[ -]?by[ -]?nc|no[ -]?derivatives|cc[ -]?by[ -]?nd|share[ -]?alike|cc[ -]?by[ -]?sa",
    re.IGNORECASE,
)


class AlaBaselineError(RuntimeError):
    """Raised when a provider receipt or frozen ALA artifact is invalid."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def normalized_timestamp(value: str) -> str:
    if value.endswith("Z"):
        datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
        return value
    parsed = parsedate_to_datetime(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(value)
    os.replace(temporary, path)


def request_bytes(
    url: str,
    *,
    accept: str = "application/json",
    attempts: int = 4,
) -> tuple[bytes, dict[str, str | None]]:
    request = urllib.request.Request(
        url, headers={"Accept": accept, "User-Agent": USER_AGENT}
    )
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return response.read(), {
                    "content_type": response.headers.get("Content-Type"),
                    "etag": response.headers.get("ETag"),
                    "last_modified": response.headers.get("Last-Modified"),
                    "date": response.headers.get("Date"),
                }
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code not in {429, 500, 502, 503, 504}:
                break
        except (TimeoutError, urllib.error.URLError) as error:
            last_error = error
        if attempt + 1 < attempts:
            time.sleep(2**attempt)
    raise AlaBaselineError(f"unable to retrieve {url}: {last_error}")


def download_file(url: str, path: Path, *, attempts: int = 4) -> dict[str, str | None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = urllib.request.Request(
            url, headers={"Accept": "application/zip", "User-Agent": USER_AGENT}
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                with temporary.open("wb") as handle:
                    for chunk in iter(lambda: response.read(1024 * 1024), b""):
                        handle.write(chunk)
                headers = {
                    "content_type": response.headers.get("Content-Type"),
                    "etag": response.headers.get("ETag"),
                    "last_modified": response.headers.get("Last-Modified"),
                    "date": response.headers.get("Date"),
                }
                os.replace(temporary, path)
                return headers
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code not in {429, 500, 502, 503, 504}:
                break
        except (TimeoutError, urllib.error.URLError) as error:
            last_error = error
        temporary.unlink(missing_ok=True)
        if attempt + 1 < attempts:
            time.sleep(2**attempt)
    raise AlaBaselineError(f"unable to download {url}: {last_error}")


def load_crosswalk_root(path: Path) -> dict[str, Any]:
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("rank") == "superfamily":
            if row.get("accepted_scientific_name") != ALA_ROOT_NAME:
                raise AlaBaselineError("crosswalk superfamily is not PAPILIONOIDEA")
            if row.get("ala_taxon_id") != ALA_ROOT_TAXON_ID:
                raise AlaBaselineError("crosswalk ALA root differs from snapshot policy")
            return row
    raise AlaBaselineError("crosswalk has no superfamily root")


def public_request_parameters() -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = [
        ("q", f"lsid:{ALA_ROOT_TAXON_ID}"),
        *(("fq", value) for value in FILTER_QUERIES),
        ("disableAllQualityFilters", "true"),
        ("fields", ",".join(DOWNLOAD_FIELDS)),
        ("extra", ",".join(EXTRA_FIELDS)),
        ("qa", "none"),
        ("file", "butterflylens-ala-papilionoidea-australia-public-20260717"),
        ("reason", "scientific research"),
        ("reasonTypeId", "2"),
        ("sourceTypeId", "0"),
        ("fileType", "csv"),
        ("dwcHeaders", "false"),
        ("includeMisc", "false"),
        ("mintDoi", "false"),
        ("emailNotify", "false"),
    ]
    return values


def submit_download(email: str) -> tuple[bytes, dict[str, str | None]]:
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise AlaBaselineError("ALA asynchronous download requires a valid contact email")
    parameters = [("email", email), *public_request_parameters()]
    url = ALA_DOWNLOAD_ENDPOINT + "?" + urllib.parse.urlencode(parameters)
    try:
        return request_bytes(url)
    except AlaBaselineError as error:
        raise AlaBaselineError(
            "ALA download submission failed; contact email withheld"
        ) from error


def poll_download(
    initial: dict[str, Any], *, interval_seconds: float, timeout_seconds: float
) -> tuple[dict[str, Any], bytes]:
    if interval_seconds < 1:
        raise AlaBaselineError("poll interval must be at least one second")
    status_url = initial.get("statusUrl")
    if not isinstance(status_url, str) or not status_url.startswith("https://"):
        raise AlaBaselineError("ALA response has no HTTPS status URL")
    deadline = time.monotonic() + timeout_seconds
    while True:
        body, _ = request_bytes(status_url)
        payload = json.loads(body)
        status = payload.get("status")
        download_url = payload.get("downloadUrl") or payload.get("downloadURL")
        if isinstance(download_url, str) and download_url.startswith("https://"):
            return payload, body
        if status in {"error", "failed", "cancelled"}:
            raise AlaBaselineError(f"ALA download ended with status {status!r}")
        if time.monotonic() >= deadline:
            raise AlaBaselineError(f"ALA download did not complete; last status {status!r}")
        time.sleep(interval_seconds)


def safe_zip_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    members = archive.infolist()
    for member in members:
        path = PurePosixPath(member.filename)
        if path.is_absolute() or ".." in path.parts:
            raise AlaBaselineError(f"unsafe archive member {member.filename!r}")
    return members


def record_csv_member(members: Iterable[zipfile.ZipInfo]) -> zipfile.ZipInfo:
    candidates = [
        member
        for member in members
        if member.filename.lower().endswith(".csv")
        and not any(
            term in member.filename.lower()
            for term in ("citation", "headings", "README")
        )
    ]
    if not candidates:
        raise AlaBaselineError("ALA archive has no occurrence CSV")
    return max(candidates, key=lambda member: member.file_size)


def first_value(row: dict[str, str], *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value is not None:
            return value.strip()
    return ""


def inspect_archive(path: Path) -> dict[str, Any]:
    licences: Counter[str] = Counter()
    bases: Counter[str] = Counter()
    sensitive: Counter[str] = Counter()
    spatial: Counter[str] = Counter()
    dataset_rows: Counter[tuple[str, str, str, str]] = Counter()
    dataset_licences: dict[tuple[str, str, str, str], Counter[str]] = defaultdict(Counter)
    missing_latitude = 0
    missing_longitude = 0
    row_count = 0
    with zipfile.ZipFile(path) as archive:
        members = safe_zip_members(archive)
        data_member = record_csv_member(members)
        heading_members = [
            member for member in members if member.filename.lower().endswith("headings.csv")
        ]
        if len(heading_members) != 1:
            raise AlaBaselineError("ALA archive must contain exactly one headings.csv")
        citation_members = [
            member for member in members if member.filename.lower().endswith("citation.csv")
        ]
        if len(citation_members) != 1:
            raise AlaBaselineError("ALA archive must contain exactly one citation.csv")
        import io

        with archive.open(heading_members[0]) as binary:
            heading_reader = csv.DictReader(
                io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
            )
            heading_map = {
                row["Column name"]: row["Requested field"]
                for row in heading_reader
                if row.get("Column name") and row.get("Requested field")
            }
        with archive.open(data_member) as binary:
            reader = csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8-sig", newline=""))
            if reader.fieldnames is None:
                raise AlaBaselineError("ALA occurrence CSV has no header")
            normalized_fields = {heading_map.get(name, name) for name in reader.fieldnames}
            required = {
                "id",
                "dataResourceUid",
                "dataResourceName",
                "license",
                "basisOfRecord",
                "sensitive",
                "spatiallyValid",
            }
            missing = sorted(required - normalized_fields)
            if missing:
                raise AlaBaselineError(f"ALA occurrence CSV is missing fields: {missing}")
            for provider_row in reader:
                row = {
                    heading_map.get(name, name): value
                    for name, value in provider_row.items()
                }
                row_count += 1
                licence = first_value(row, "license")
                if licence not in ALLOWED_PUBLIC_LICENCES:
                    raise AlaBaselineError(
                        f"public snapshot contains non-allowlisted licence {licence!r}"
                    )
                provider_uid = first_value(row, "dataProviderUid")
                provider_name = first_value(row, "dataProviderName")
                resource_uid = first_value(row, "dataResourceUid")
                resource_name = first_value(row, "dataResourceName")
                dataset_key = (
                    provider_uid,
                    provider_name,
                    resource_uid,
                    resource_name,
                )
                dataset_rows[dataset_key] += 1
                dataset_licences[dataset_key][licence] += 1
                licences[licence] += 1
                bases[first_value(row, "basisOfRecord") or "not_supplied"] += 1
                sensitive[first_value(row, "sensitive") or "not_supplied"] += 1
                spatial[first_value(row, "spatiallyValid") or "not_supplied"] += 1
                missing_latitude += not first_value(row, "decimalLatitude")
                missing_longitude += not first_value(row, "decimalLongitude")
        with archive.open(citation_members[0]) as binary:
            citation_reader = csv.DictReader(
                io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
            )
            citation_entries = [
                {
                    "uid": first_value(row, "UID") or None,
                    "name": first_value(row, "Name") or None,
                    "doi": first_value(row, "DOI") or None,
                    "citation": first_value(row, "Citation") or None,
                    "rights": first_value(row, "Rights") or None,
                    "more_information": first_value(row, "More Information") or None,
                    "data_generalisations": first_value(row, "Data generalisations")
                    or None,
                    "information_withheld": first_value(row, "Information withheld")
                    or None,
                    "download_limit": first_value(row, "Download limit") or None,
                    "record_count": int(first_value(row, "Number of Records in Download") or 0),
                }
                for row in citation_reader
            ]
        member_inventory = [
            {
                "path": member.filename,
                "compressed_bytes": member.compress_size,
                "uncompressed_bytes": member.file_size,
                "crc32": f"{member.CRC:08x}",
            }
            for member in members
        ]
    dataset_inventory = [
        {
            "data_provider_uid": key[0] or None,
            "data_provider_name": key[1] or None,
            "data_resource_uid": key[2] or None,
            "data_resource_name": key[3] or None,
            "row_count": count,
            "licence_counts": dict(sorted(dataset_licences[key].items())),
        }
        for key, count in sorted(dataset_rows.items())
    ]
    return {
        "record_member": data_member.filename,
        "row_count": row_count,
        "dataset_count": len(dataset_inventory),
        "datasets": dataset_inventory,
        "citation_entry_count": len(citation_entries),
        "citation_entries": citation_entries,
        "licence_counts": dict(sorted(licences.items())),
        "basis_of_record_counts": dict(sorted(bases.items())),
        "sensitive_counts": dict(sorted(sensitive.items())),
        "spatial_validity_counts": dict(sorted(spatial.items())),
        "missing_latitude_count": missing_latitude,
        "missing_longitude_count": missing_longitude,
        "members": member_inventory,
    }


def optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def optional_float(value: str | None) -> float | None:
    cleaned = optional_text(value)
    if cleaned is None:
        return None
    try:
        parsed = float(cleaned)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def optional_bool(value: str | None) -> bool | None:
    cleaned = optional_text(value)
    if cleaned is None:
        return None
    normalized = cleaned.casefold()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise AlaBaselineError(f"unexpected boolean value {cleaned!r}")


def assertion_codes(value: str | None) -> list[str]:
    cleaned = optional_text(value)
    if cleaned is None:
        return []
    values = [item.strip() for item in cleaned.split("|") if item.strip()]
    if len(values) != len(set(values)):
        raise AlaBaselineError("ALA quality assertion list contains duplicates")
    return values


def parsed_event_year(value: str | None) -> int | None:
    cleaned = optional_text(value)
    if cleaned is None:
        return None
    match = re.match(r"^(\d{4})(?:-|$)", cleaned)
    return int(match.group(1)) if match else None


def temporal_evidence_band(year: int | None, snapshot_year: int) -> str:
    if year is None:
        return "undated_or_unparseable"
    if year < 1600 or year > snapshot_year:
        return "outside_declared_valid_year_range"
    if year < 1900:
        return "pre_1900_historical"
    if year < 1950:
        return "1900_1949_historical"
    if year < 2000:
        return "1950_1999"
    return "2000_snapshot_year"


def evidence_category(basis: str | None) -> str:
    return {
        "HUMAN_OBSERVATION": "human_observation",
        "OBSERVATION": "unspecified_observation",
        "MACHINE_OBSERVATION": "machine_observation",
        "MATERIAL_SAMPLE": "material_sample",
        "PRESERVED_SPECIMEN": "preserved_specimen",
        "FOSSIL_SPECIMEN": "fossil_specimen",
        "OCCURRENCE": "unspecified_occurrence",
    }.get(basis or "", "other_or_not_supplied")


def spatial_eligibility(
    *,
    has_coordinates: bool,
    coordinate_in_range: bool,
    spatially_valid: bool | None,
    publicly_generalised: bool,
) -> str:
    if not has_coordinates:
        return "excluded_missing_coordinates"
    if not coordinate_in_range:
        return "excluded_invalid_coordinates"
    if spatially_valid is False:
        return "excluded_spatially_suspect"
    if spatially_valid is None:
        return "excluded_spatial_validity_not_supplied"
    if publicly_generalised:
        return "eligible_generalised_coarse_only"
    return "eligible_all_configured_resolutions"


def provider_rows(path: Path) -> Iterable[tuple[int, dict[str, str]]]:
    import io

    with zipfile.ZipFile(path) as archive:
        members = safe_zip_members(archive)
        data_member = record_csv_member(members)
        heading_members = [
            member for member in members if member.filename.lower().endswith("headings.csv")
        ]
        if len(heading_members) != 1:
            raise AlaBaselineError("ALA archive must contain exactly one headings.csv")
        with archive.open(heading_members[0]) as binary:
            heading_reader = csv.DictReader(
                io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
            )
            heading_map = {
                row["Column name"]: row["Requested field"]
                for row in heading_reader
                if row.get("Column name") and row.get("Requested field")
            }
        with archive.open(data_member) as binary:
            reader = csv.DictReader(
                io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
            )
            if reader.fieldnames is None:
                raise AlaBaselineError("ALA occurrence CSV has no header")
            for row_number, provider_row in enumerate(reader, start=1):
                yield row_number, {
                    heading_map.get(name, name): value
                    for name, value in provider_row.items()
                }


def exact_taxon_crosswalk(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        identifier = row.get("ala_taxon_id")
        key = row.get("butterflylens_key")
        if not identifier:
            continue
        if not isinstance(key, str) or not key:
            raise AlaBaselineError("crosswalk row with ALA ID has no ButterflyLens key")
        if identifier in result:
            raise AlaBaselineError(f"duplicate ALA taxon ID in crosswalk: {identifier}")
        result[identifier] = key
    if not result:
        raise AlaBaselineError("crosswalk contains no exact ALA identifiers")
    return result


def normalized_row(
    source: dict[str, str],
    *,
    row_number: int,
    receipt: dict[str, Any],
    taxon_crosswalk: dict[str, str],
) -> dict[str, Any]:
    record_id = optional_text(source.get("id"))
    if record_id is None:
        raise AlaBaselineError(f"ALA source row {row_number} has no record ID")
    resource_uid = optional_text(source.get("dataResourceUid"))
    if resource_uid is None:
        raise AlaBaselineError(f"ALA source row {row_number} has no data resource ID")
    licence = optional_text(source.get("license"))
    if licence not in ALLOWED_PUBLIC_LICENCES:
        raise AlaBaselineError(
            f"ALA source row {row_number} has non-allowlisted licence {licence!r}"
        )
    latitude_raw = optional_text(source.get("decimalLatitude"))
    longitude_raw = optional_text(source.get("decimalLongitude"))
    latitude = optional_float(latitude_raw)
    longitude = optional_float(longitude_raw)
    has_coordinates = latitude_raw is not None and longitude_raw is not None
    coordinate_in_range = (
        latitude is not None
        and longitude is not None
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    )
    spatially_valid = optional_bool(source.get("spatiallyValid"))
    sensitive_status = optional_text(source.get("sensitive")) or "not_supplied"
    if sensitive_status not in {"not_supplied", "generalised", "alreadyGeneralised"}:
        raise AlaBaselineError(
            f"ALA source row {row_number} has unexpected sensitive state {sensitive_status!r}"
        )
    publicly_generalised = sensitive_status in {"generalised", "alreadyGeneralised"}
    provider_taxon_id = optional_text(source.get("taxonConceptID"))
    butterflylens_key = taxon_crosswalk.get(provider_taxon_id or "")
    event_date = optional_text(source.get("eventDate"))
    event_year = parsed_event_year(event_date)
    snapshot_year = int(receipt["retrieved_at"][:4])
    basis = optional_text(source.get("basisOfRecord"))
    assertions = assertion_codes(source.get("assertions"))
    row = {
        "source_snapshot_id": receipt["snapshot_id"],
        "source_snapshot_fingerprint": receipt["snapshot_fingerprint"],
        "source_archive_sha256": receipt["download"]["archive_sha256"],
        "source_row_number": row_number,
        "ala_record_id": record_id,
        "source_occurrence_id": optional_text(source.get("occurrenceID")),
        "butterflylens_taxon_key": butterflylens_key,
        "taxon_match_state": (
            "exact_ala_taxon_concept_crosswalk"
            if butterflylens_key
            else "unmatched_provider_taxon_assertion"
        ),
        "provider_taxon_concept_id": provider_taxon_id,
        "provider_names_and_lsid": optional_text(source.get("names_and_lsid")),
        "provider_scientific_name": optional_text(source.get("scientificName")),
        "provider_taxon_rank": optional_text(source.get("taxonRank")),
        "provider_species_name": optional_text(source.get("species")),
        "provider_species_id": optional_text(source.get("speciesID")),
        "provider_subspecies_name": optional_text(source.get("subspecies")),
        "provider_subspecies_id": optional_text(source.get("subspeciesID")),
        "data_provider_name": optional_text(source.get("dataProviderName")),
        "data_provider_uid": optional_text(source.get("dataProviderUid")),
        "data_resource_name": optional_text(source.get("dataResourceName")),
        "data_resource_uid": resource_uid,
        "decimal_latitude": latitude,
        "decimal_longitude": longitude,
        "coordinate_uncertainty_meters": optional_float(
            source.get("coordinateUncertaintyInMeters")
        ),
        "has_coordinates": has_coordinates,
        "coordinate_in_wgs84_range": coordinate_in_range,
        "spatially_valid": spatially_valid,
        "sensitive_status": sensitive_status,
        "coordinates_publicly_generalised": publicly_generalised,
        "spatial_aggregation_eligibility": spatial_eligibility(
            has_coordinates=has_coordinates,
            coordinate_in_range=coordinate_in_range,
            spatially_valid=spatially_valid,
            publicly_generalised=publicly_generalised,
        ),
        "event_date": event_date,
        "event_year": event_year,
        "temporal_evidence_band": temporal_evidence_band(event_year, snapshot_year),
        "basis_of_record": basis,
        "raw_basis_of_record": optional_text(source.get("raw_basisOfRecord")),
        "evidence_category": evidence_category(basis),
        "licence": licence,
        "rights": optional_text(source.get("rights")),
        "quality_assertions": assertions,
        "quality_assertion_count": len(assertions),
        "country": optional_text(source.get("country")),
        "state_territory": optional_text(source.get("stateProvince")),
        "ibra_region": optional_text(source.get(IBRA_FIELD)),
        "lga_name": optional_text(source.get(LGA_FIELD)),
        "source_reference": optional_text(source.get("references")),
    }
    row["normalized_occurrence_fingerprint"] = sha256_bytes(canonical_json(row))
    return row


def arrow_type(pa: Any, type_name: str) -> Any:
    return {
        "string": pa.string(),
        "int32": pa.int32(),
        "int64": pa.int64(),
        "float64": pa.float64(),
        "bool": pa.bool_(),
        "list<string>": pa.list_(pa.string()),
    }[type_name]


def normalized_arrow_schema(pa: Any, receipt: dict[str, Any]) -> Any:
    metadata = {
        b"schema_version": NORMALIZED_SCHEMA_VERSION.encode(),
        b"snapshot_id": receipt["snapshot_id"].encode(),
        b"snapshot_fingerprint": receipt["snapshot_fingerprint"].encode(),
        b"source_archive_sha256": receipt["download"]["archive_sha256"].encode(),
        b"evidence_label": b"ALA baseline occurrence evidence",
    }
    return pa.schema(
        [
            pa.field(name, arrow_type(pa, type_name), nullable=nullable)
            for name, type_name, nullable, _ in NORMALIZED_FIELD_SPECS
        ],
        metadata=metadata,
    )


def normalized_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": "butterflylens-parquet-schema/v1",
        "artifact_schema_version": NORMALIZED_SCHEMA_VERSION,
        "format": "parquet",
        "closed": True,
        "fields": [
            {
                "name": name,
                "type": type_name,
                "nullable": nullable,
                "description": description,
            }
            for name, type_name, nullable, description in NORMALIZED_FIELD_SPECS
        ],
        "invariants": [
            "ala_record_id is unique and rows are sorted by ala_record_id",
            "butterflylens_taxon_key is populated only for an exact ALA taxonConceptID crosswalk match",
            "licence is a member of the frozen public allowlist",
            "provider taxon fields remain provider assertions, not human verification",
            "generalised sensitive coordinates are never promoted beyond coarse-only spatial eligibility",
            "quality_assertions retains ordered ALA assertion codes",
        ],
    }


def normalize_occurrences(args: argparse.Namespace) -> None:
    try:
        import pyarrow as pa
        import pyarrow.compute as pc
        import pyarrow.parquet as pq
    except ImportError as error:
        raise AlaBaselineError(
            "normalization requires the locked PyArrow dependency; run uv sync --frozen"
        ) from error

    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    if receipt.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise AlaBaselineError("unexpected ALA snapshot receipt schema")
    if sha256_file(args.archive) != receipt["download"]["archive_sha256"]:
        raise AlaBaselineError("ALA source archive checksum does not match receipt")
    taxon_crosswalk = exact_taxon_crosswalk(args.crosswalk)
    columns: dict[str, list[Any]] = {
        name: [] for name, _, _, _ in NORMALIZED_FIELD_SPECS
    }
    seen_record_ids: set[str] = set()
    counters: dict[str, Counter[str]] = {
        "taxon_match_state": Counter(),
        "spatial_aggregation_eligibility": Counter(),
        "evidence_category": Counter(),
        "temporal_evidence_band": Counter(),
        "licence": Counter(),
        "sensitive_status": Counter(),
    }
    for row_number, source in provider_rows(args.archive):
        row = normalized_row(
            source,
            row_number=row_number,
            receipt=receipt,
            taxon_crosswalk=taxon_crosswalk,
        )
        record_id = row["ala_record_id"]
        if record_id in seen_record_ids:
            raise AlaBaselineError(f"duplicate ALA record ID {record_id!r}")
        seen_record_ids.add(record_id)
        for name in columns:
            columns[name].append(row[name])
        for name, counter in counters.items():
            counter[row[name]] += 1
    expected_rows = receipt["download"]["row_count"]
    if len(seen_record_ids) != expected_rows:
        raise AlaBaselineError(
            f"normalized row count {len(seen_record_ids)} != snapshot rows {expected_rows}"
        )
    schema = normalized_arrow_schema(pa, receipt)
    table = pa.Table.from_pydict(columns, schema=schema)
    order = pc.sort_indices(table, sort_keys=[("ala_record_id", "ascending")])
    table = pc.take(table, order)
    ordered_ids = table.column("ala_record_id").to_pylist()
    if ordered_ids != sorted(ordered_ids) or len(ordered_ids) != len(set(ordered_ids)):
        raise AlaBaselineError("normalized ALA record IDs are not uniquely sorted")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
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
    os.replace(temporary, args.output)
    schema_payload = normalized_schema_contract()
    write_bytes(args.schema_output, canonical_json(schema_payload))
    logical_digest = hashlib.sha256()
    for fingerprint in table.column("normalized_occurrence_fingerprint").to_pylist():
        logical_digest.update(fingerprint.encode())
        logical_digest.update(b"\n")
    parquet_file = pq.ParquetFile(args.output)
    manifest = {
        "schema_version": NORMALIZATION_MANIFEST_SCHEMA_VERSION,
        "artifact_schema_version": NORMALIZED_SCHEMA_VERSION,
        "generated_at": args.generated_at or utc_now(),
        "snapshot_id": receipt["snapshot_id"],
        "snapshot_fingerprint": receipt["snapshot_fingerprint"],
        "input": {
            "archive_path": receipt["download"]["archive_path"],
            "archive_sha256": sha256_file(args.archive),
            "receipt_path": "ala_snapshot_receipt.json",
            "receipt_sha256": sha256_file(args.receipt),
            "crosswalk_path": receipt["taxon_scope"]["input_crosswalk_path"],
            "crosswalk_sha256": sha256_file(args.crosswalk),
        },
        "artifact": {
            "path": args.output.name,
            "physical_sha256": sha256_file(args.output),
            "logical_row_fingerprint_sha256": logical_digest.hexdigest(),
            "row_count": table.num_rows,
            "column_count": table.num_columns,
            "row_group_count": parquet_file.metadata.num_row_groups,
            "physical_bytes": args.output.stat().st_size,
            "compression": "zstd",
            "row_group_size": 65_536,
            "sort_order": ["ala_record_id:ascending"],
        },
        "schema": {
            "path": f"schemas/{args.schema_output.name}",
            "physical_sha256": sha256_file(args.schema_output),
            "field_count": len(NORMALIZED_FIELD_SPECS),
        },
        "counts": {
            name: dict(sorted(counter.items())) for name, counter in counters.items()
        },
        "policies": {
            "taxon_match": "exact taxonConceptID only; unmatched provider assertions remain explicit",
            "historical_bands": [
                "pre_1900_historical",
                "1900_1949_historical",
                "1950_1999",
                "2000_snapshot_year",
                "undated_or_unparseable",
                "outside_declared_valid_year_range",
            ],
            "sensitive_coordinates": "ALA-public generalised values are coarse-only; no reconstruction",
            "spatial_eligibility": "requires finite in-range coordinates and ALA spatiallyValid=true",
            "provider_assertions": "taxon labels, quality flags, and contextual geography are not human verification",
            "absence_inference_permitted": False,
        },
        "build": {
            "python": ".".join(map(str, __import__("sys").version_info[:3])),
            "pyarrow": pa.__version__,
        },
    }
    write_bytes(args.manifest, canonical_json(manifest))
    print(
        json.dumps(
            {
                "rows": table.num_rows,
                "columns": table.num_columns,
                "row_groups": parquet_file.metadata.num_row_groups,
                "parquet_bytes": args.output.stat().st_size,
                "parquet_sha256": sha256_file(args.output),
                "manifest_sha256": sha256_file(args.manifest),
            },
            sort_keys=True,
        )
    )


class AggregateAccumulator:
    def __init__(self, metadata: dict[str, Any]) -> None:
        self.metadata = metadata
        self.record_count = 0
        self.matched_taxon_record_count = 0
        self.unmatched_taxon_assertion_count = 0
        self.taxon_keys: set[str] = set()
        self.data_resources: set[str] = set()
        self.evidence_counts: Counter[str] = Counter()
        self.earliest_event_year: int | None = None
        self.latest_event_year: int | None = None
        self.coordinate_uncertainty_known_count = 0
        self.coordinate_uncertainty_missing_count = 0
        self.maximum_coordinate_uncertainty_meters: float | None = None
        self.publicly_generalised_record_count = 0
        self.source_record_digest = hashlib.sha256()

    def add(self, row: dict[str, Any]) -> None:
        self.record_count += 1
        taxon_key = row["butterflylens_taxon_key"]
        match_state = row["taxon_match_state"]
        if taxon_key is not None:
            if match_state != "exact_ala_taxon_concept_crosswalk":
                raise AlaBaselineError("matched taxon key has inconsistent match state")
            self.matched_taxon_record_count += 1
            self.taxon_keys.add(taxon_key)
        else:
            if match_state != "unmatched_provider_taxon_assertion":
                raise AlaBaselineError("unmatched taxon assertion has inconsistent state")
            self.unmatched_taxon_assertion_count += 1
        self.data_resources.add(row["data_resource_uid"])
        category = row["evidence_category"]
        if category not in EVIDENCE_COUNT_FIELDS:
            raise AlaBaselineError(f"unexpected evidence category {category!r}")
        self.evidence_counts[category] += 1
        event_year = row["event_year"]
        if (
            event_year is not None
            and row["temporal_evidence_band"]
            != "outside_declared_valid_year_range"
        ):
            self.earliest_event_year = (
                event_year
                if self.earliest_event_year is None
                else min(self.earliest_event_year, event_year)
            )
            self.latest_event_year = (
                event_year
                if self.latest_event_year is None
                else max(self.latest_event_year, event_year)
            )
        uncertainty = row["coordinate_uncertainty_meters"]
        if uncertainty is None:
            self.coordinate_uncertainty_missing_count += 1
        else:
            self.coordinate_uncertainty_known_count += 1
            self.maximum_coordinate_uncertainty_meters = (
                uncertainty
                if self.maximum_coordinate_uncertainty_meters is None
                else max(self.maximum_coordinate_uncertainty_meters, uncertainty)
            )
        if row["coordinates_publicly_generalised"]:
            self.publicly_generalised_record_count += 1
        self.source_record_digest.update(
            row["normalized_occurrence_fingerprint"].encode("ascii")
        )
        self.source_record_digest.update(b"\n")

    def finish(self, source: dict[str, str]) -> dict[str, Any]:
        row = {
            **source,
            **self.metadata,
            "record_count": self.record_count,
            "matched_taxon_record_count": self.matched_taxon_record_count,
            "unmatched_taxon_assertion_count": self.unmatched_taxon_assertion_count,
            "unique_butterflylens_taxon_count": len(self.taxon_keys),
            "unique_data_resource_count": len(self.data_resources),
            **{
                output_field: self.evidence_counts.get(category, 0)
                for category, output_field in EVIDENCE_COUNT_FIELDS.items()
            },
            "earliest_event_year": self.earliest_event_year,
            "latest_event_year": self.latest_event_year,
            "coordinate_uncertainty_known_count": self.coordinate_uncertainty_known_count,
            "coordinate_uncertainty_missing_count": self.coordinate_uncertainty_missing_count,
            "maximum_coordinate_uncertainty_meters": self.maximum_coordinate_uncertainty_meters,
            "publicly_generalised_record_count": self.publicly_generalised_record_count,
            "source_record_fingerprint_digest": self.source_record_digest.hexdigest(),
        }
        row["aggregate_fingerprint"] = sha256_bytes(canonical_json(row))
        return row


def aggregate_arrow_schema(
    pa: Any,
    normalization_manifest: dict[str, Any],
    h3_version: str,
) -> Any:
    metadata = {
        b"schema_version": AGGREGATED_SCHEMA_VERSION.encode(),
        b"snapshot_id": normalization_manifest["snapshot_id"].encode(),
        b"snapshot_fingerprint": normalization_manifest["snapshot_fingerprint"].encode(),
        b"source_occurrence_artifact_sha256": normalization_manifest["artifact"][
            "physical_sha256"
        ].encode(),
        b"evidence_label": b"aggregated ALA baseline occurrence evidence",
        b"h3_version": h3_version.encode(),
        b"h3_resolutions": b"coarse=3,regional=5,local=7",
    }
    return pa.schema(
        [
            pa.field(name, arrow_type(pa, type_name), nullable=nullable)
            for name, type_name, nullable, _ in AGGREGATED_FIELD_SPECS
        ],
        metadata=metadata,
    )


def aggregated_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": "butterflylens-parquet-schema/v1",
        "artifact_schema_version": AGGREGATED_SCHEMA_VERSION,
        "format": "parquet",
        "closed": True,
        "fields": [
            {
                "name": name,
                "type": type_name,
                "nullable": nullable,
                "description": description,
            }
            for name, type_name, nullable, description in AGGREGATED_FIELD_SPECS
        ],
        "scope_types": [
            "australia",
            "state_territory",
            "ibra_region",
            "lga_2023_statistical_approximation",
            "h3_coarse",
            "h3_regional",
            "h3_local",
        ],
        "h3_resolutions": H3_RESOLUTIONS,
        "invariants": [
            "scope_id is unique and rows are sorted by scope_order then scope_id",
            "every record_count decomposes into matched and unmatched taxon rows",
            "every record_count decomposes into the closed evidence-category counts",
            "publicly generalised rows contribute only to Australia, state/territory, and H3 resolution 3",
            "IBRA and LGA values remain ALA contextual assertions and no boundary geometry is copied",
            "H3 centers are derived cell centers and are not occurrence coordinates",
            "source_record_fingerprint_digest binds each aggregate to ordered normalized source rows",
        ],
    }


def encoded_scope_id(prefix: str, label: str) -> str:
    return f"{prefix}:{urllib.parse.quote(label, safe='')}"


def contextual_scope_metadata(scope_type: str, label: str) -> dict[str, Any]:
    definitions = {
        "australia": {
            "scope_order": 0,
            "scope_id": "country:AU",
            "scope_resolution_class": "national",
            "sensitive_membership_policy": "eligible_all_and_generalised_coarse",
            "contextual_source": "ALA selected country filter: Australia",
        },
        "state_territory": {
            "scope_order": 1,
            "scope_id": encoded_scope_id("ala:state_territory", label),
            "scope_resolution_class": "coarse",
            "sensitive_membership_policy": "eligible_all_and_generalised_coarse",
            "contextual_source": "ALA stateProvince provider assertion",
        },
        "ibra_region": {
            "scope_order": 2,
            "scope_id": encoded_scope_id("ala:ibra_v7", label),
            "scope_resolution_class": "regional",
            "sensitive_membership_policy": "eligible_all_configured_resolutions_only",
            "contextual_source": "ALA cl11185 indexed IBRA v7 contextual assertion",
        },
        "lga_2023_statistical_approximation": {
            "scope_order": 3,
            "scope_id": encoded_scope_id(
                "ala:lga_2023_statistical_approximation", label
            ),
            "scope_resolution_class": "local",
            "sensitive_membership_policy": "eligible_all_configured_resolutions_only",
            "contextual_source": (
                "ALA cl11170 indexed LGA 2023 Mesh Block statistical "
                "approximation; not a legal boundary"
            ),
        },
    }
    try:
        metadata = definitions[scope_type]
    except KeyError as error:
        raise AlaBaselineError(f"unknown contextual scope type {scope_type!r}") from error
    return {
        "scope_type": scope_type,
        "scope_label": label,
        "h3_resolution": None,
        "h3_cell_id": None,
        "parent_h3_cell_id": None,
        "cell_center_latitude": None,
        "cell_center_longitude": None,
        **metadata,
    }


def h3_scope_metadata(h3: Any, resolution_class: str, cell_id: str) -> dict[str, Any]:
    resolution = H3_RESOLUTIONS[resolution_class]
    scope_order = {"coarse": 4, "regional": 5, "local": 6}[resolution_class]
    parent_resolution = {
        "coarse": None,
        "regional": H3_RESOLUTIONS["coarse"],
        "local": H3_RESOLUTIONS["regional"],
    }[resolution_class]
    center_latitude, center_longitude = h3.cell_to_latlng(cell_id)
    return {
        "scope_type": f"h3_{resolution_class}",
        "scope_order": scope_order,
        "scope_id": f"h3:{resolution}:{cell_id}",
        "scope_label": cell_id,
        "scope_resolution_class": resolution_class,
        "sensitive_membership_policy": (
            "eligible_all_and_generalised_coarse"
            if resolution_class == "coarse"
            else "eligible_all_configured_resolutions_only"
        ),
        "contextual_source": (
            f"h3-py {h3.__version__} projection of ALA public processed coordinates"
        ),
        "h3_resolution": resolution,
        "h3_cell_id": cell_id,
        "parent_h3_cell_id": (
            h3.cell_to_parent(cell_id, parent_resolution)
            if parent_resolution is not None
            else None
        ),
        "cell_center_latitude": float(center_latitude),
        "cell_center_longitude": float(center_longitude),
    }


def add_aggregate_membership(
    groups: dict[tuple[str, str], AggregateAccumulator],
    *,
    scope_type: str,
    scope_id: str,
    metadata_factory: Any,
    row: dict[str, Any],
) -> None:
    key = (scope_type, scope_id)
    accumulator = groups.get(key)
    if accumulator is None:
        accumulator = AggregateAccumulator(metadata_factory())
        groups[key] = accumulator
    accumulator.add(row)


def aggregate_occurrences(args: argparse.Namespace) -> None:
    try:
        import h3
        import pyarrow as pa
        import pyarrow.compute as pc
        import pyarrow.parquet as pq
    except ImportError as error:
        raise AlaBaselineError(
            "aggregation requires the locked h3 and PyArrow dependencies; run uv sync --frozen"
        ) from error

    normalization_manifest = json.loads(
        args.normalization_manifest.read_text(encoding="utf-8")
    )
    if (
        normalization_manifest.get("schema_version")
        != NORMALIZATION_MANIFEST_SCHEMA_VERSION
    ):
        raise AlaBaselineError("unexpected ALA normalization manifest schema")
    observed_occurrence_sha = sha256_file(args.occurrences)
    if observed_occurrence_sha != normalization_manifest["artifact"]["physical_sha256"]:
        raise AlaBaselineError("normalized occurrence checksum does not match manifest")
    if h3.__version__ != "4.5.0":
        raise AlaBaselineError(f"unexpected h3 version {h3.__version__!r}")

    required_columns = [
        "ala_record_id",
        "normalized_occurrence_fingerprint",
        "butterflylens_taxon_key",
        "taxon_match_state",
        "data_resource_uid",
        "decimal_latitude",
        "decimal_longitude",
        "coordinate_uncertainty_meters",
        "coordinates_publicly_generalised",
        "spatial_aggregation_eligibility",
        "event_year",
        "temporal_evidence_band",
        "evidence_category",
        "state_territory",
        "ibra_region",
        "lga_name",
    ]
    table = pq.read_table(args.occurrences, columns=required_columns)
    if table.num_rows != normalization_manifest["artifact"]["row_count"]:
        raise AlaBaselineError("normalized occurrence row count does not match manifest")
    groups: dict[tuple[str, str], AggregateAccumulator] = {}
    missing_scope_labels: Counter[str] = Counter()
    eligible_all_count = 0
    eligible_generalised_count = 0
    previous_record_id: str | None = None

    for batch in table.to_batches(max_chunksize=65_536):
        for row in batch.to_pylist():
            record_id = row["ala_record_id"]
            if previous_record_id is not None and record_id <= previous_record_id:
                raise AlaBaselineError("normalized occurrence rows are not uniquely sorted")
            previous_record_id = record_id
            eligibility = row["spatial_aggregation_eligibility"]
            if eligibility not in {
                "eligible_all_configured_resolutions",
                "eligible_generalised_coarse_only",
            }:
                continue
            if row["decimal_latitude"] is None or row["decimal_longitude"] is None:
                raise AlaBaselineError("spatially eligible row has no public coordinates")
            is_all_resolution = eligibility == "eligible_all_configured_resolutions"
            if is_all_resolution:
                eligible_all_count += 1
                if row["coordinates_publicly_generalised"]:
                    raise AlaBaselineError(
                        "publicly generalised row has all-resolution eligibility"
                    )
            else:
                eligible_generalised_count += 1
                if not row["coordinates_publicly_generalised"]:
                    raise AlaBaselineError(
                        "coarse-only row lacks public generalisation evidence"
                    )

            australia_metadata = contextual_scope_metadata("australia", "Australia")
            add_aggregate_membership(
                groups,
                scope_type="australia",
                scope_id=australia_metadata["scope_id"],
                metadata_factory=lambda value=australia_metadata: value,
                row=row,
            )

            state = row["state_territory"]
            if state is None:
                missing_scope_labels["state_territory"] += 1
            else:
                state_metadata = contextual_scope_metadata("state_territory", state)
                add_aggregate_membership(
                    groups,
                    scope_type="state_territory",
                    scope_id=state_metadata["scope_id"],
                    metadata_factory=lambda value=state_metadata: value,
                    row=row,
                )

            if is_all_resolution:
                ibra = row["ibra_region"]
                if ibra is None:
                    missing_scope_labels["ibra_region"] += 1
                else:
                    ibra_metadata = contextual_scope_metadata("ibra_region", ibra)
                    add_aggregate_membership(
                        groups,
                        scope_type="ibra_region",
                        scope_id=ibra_metadata["scope_id"],
                        metadata_factory=lambda value=ibra_metadata: value,
                        row=row,
                    )
                lga = row["lga_name"]
                if lga is None:
                    missing_scope_labels["lga_2023_statistical_approximation"] += 1
                else:
                    lga_metadata = contextual_scope_metadata(
                        "lga_2023_statistical_approximation", lga
                    )
                    add_aggregate_membership(
                        groups,
                        scope_type="lga_2023_statistical_approximation",
                        scope_id=lga_metadata["scope_id"],
                        metadata_factory=lambda value=lga_metadata: value,
                        row=row,
                    )

            latitude = row["decimal_latitude"]
            longitude = row["decimal_longitude"]
            for resolution_class in (
                ("coarse",)
                if not is_all_resolution
                else ("coarse", "regional", "local")
            ):
                resolution = H3_RESOLUTIONS[resolution_class]
                cell_id = h3.latlng_to_cell(latitude, longitude, resolution)
                scope_type = f"h3_{resolution_class}"
                scope_id = f"h3:{resolution}:{cell_id}"
                add_aggregate_membership(
                    groups,
                    scope_type=scope_type,
                    scope_id=scope_id,
                    metadata_factory=lambda value=resolution_class, cell=cell_id: h3_scope_metadata(
                        h3, value, cell
                    ),
                    row=row,
                )

    source_metadata = {
        "source_snapshot_id": normalization_manifest["snapshot_id"],
        "source_snapshot_fingerprint": normalization_manifest[
            "snapshot_fingerprint"
        ],
        "source_occurrence_artifact_sha256": observed_occurrence_sha,
    }
    rows = [accumulator.finish(source_metadata) for accumulator in groups.values()]
    schema = aggregate_arrow_schema(pa, normalization_manifest, h3.__version__)
    aggregate_table = pa.Table.from_pylist(rows, schema=schema)
    order = pc.sort_indices(
        aggregate_table,
        sort_keys=[("scope_order", "ascending"), ("scope_id", "ascending")],
    )
    aggregate_table = pc.take(aggregate_table, order)
    scope_ids = aggregate_table.column("scope_id").to_pylist()
    if len(scope_ids) != len(set(scope_ids)):
        raise AlaBaselineError("aggregate scope IDs are not unique")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    pq.write_table(
        aggregate_table,
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
    os.replace(temporary, args.output)
    schema_payload = aggregated_schema_contract()
    write_bytes(args.schema_output, canonical_json(schema_payload))

    scope_row_counts: Counter[str] = Counter(
        aggregate_table.column("scope_type").to_pylist()
    )
    scope_record_memberships: Counter[str] = Counter()
    scope_generalised_memberships: Counter[str] = Counter()
    for scope_type, count, generalised_count in zip(
        aggregate_table.column("scope_type").to_pylist(),
        aggregate_table.column("record_count").to_pylist(),
        aggregate_table.column("publicly_generalised_record_count").to_pylist(),
        strict=True,
    ):
        scope_record_memberships[scope_type] += count
        scope_generalised_memberships[scope_type] += generalised_count
    logical_digest = hashlib.sha256()
    for fingerprint in aggregate_table.column("aggregate_fingerprint").to_pylist():
        logical_digest.update(fingerprint.encode("ascii"))
        logical_digest.update(b"\n")
    parquet_file = pq.ParquetFile(args.output)
    source_spatial_counts = normalization_manifest["counts"][
        "spatial_aggregation_eligibility"
    ]
    manifest = {
        "schema_version": AGGREGATION_MANIFEST_SCHEMA_VERSION,
        "artifact_schema_version": AGGREGATED_SCHEMA_VERSION,
        "generated_at": args.generated_at or utc_now(),
        "snapshot_id": normalization_manifest["snapshot_id"],
        "snapshot_fingerprint": normalization_manifest["snapshot_fingerprint"],
        "input": {
            "occurrence_path": args.occurrences.name,
            "occurrence_sha256": observed_occurrence_sha,
            "normalization_manifest_path": args.normalization_manifest.name,
            "normalization_manifest_sha256": sha256_file(
                args.normalization_manifest
            ),
        },
        "artifact": {
            "path": args.output.name,
            "physical_sha256": sha256_file(args.output),
            "logical_aggregate_fingerprint_sha256": logical_digest.hexdigest(),
            "row_count": aggregate_table.num_rows,
            "column_count": aggregate_table.num_columns,
            "row_group_count": parquet_file.metadata.num_row_groups,
            "physical_bytes": args.output.stat().st_size,
            "compression": "zstd",
            "row_group_size": 65_536,
            "sort_order": ["scope_order:ascending", "scope_id:ascending"],
        },
        "schema": {
            "path": f"schemas/{args.schema_output.name}",
            "physical_sha256": sha256_file(args.schema_output),
            "field_count": len(AGGREGATED_FIELD_SPECS),
        },
        "grid": {
            "name": "H3",
            "python_package": "h3",
            "python_version": h3.__version__,
            "core_version": h3.versions()["c"],
            "resolutions": H3_RESOLUTIONS,
            "coordinate_source": "ALA public processed coordinates only",
        },
        "counts": {
            "scope_rows": dict(sorted(scope_row_counts.items())),
            "scope_record_memberships": dict(
                sorted(scope_record_memberships.items())
            ),
            "scope_publicly_generalised_memberships": dict(
                sorted(scope_generalised_memberships.items())
            ),
            "missing_scope_label_eligible_rows": dict(
                sorted(missing_scope_labels.items())
            ),
            "source_spatial_eligibility": source_spatial_counts,
            "unique_spatially_eligible_source_rows": (
                eligible_all_count + eligible_generalised_count
            ),
        },
        "policies": {
            "generalised_membership": (
                "publicly generalised rows contribute only to Australia, "
                "state/territory, and H3 resolution 3"
            ),
            "contextual_geography": (
                "state, IBRA, and LGA values are ALA assertions; LGA is a "
                "statistical approximation, not a legal boundary"
            ),
            "boundary_geometry_copied": False,
            "cell_center_is_occurrence_coordinate": False,
            "provider_assertions_are_human_verification": False,
            "absence_inference_permitted": False,
        },
        "build": {
            "python": ".".join(map(str, __import__("sys").version_info[:3])),
            "pyarrow": pa.__version__,
            "h3": h3.__version__,
        },
    }
    write_bytes(args.manifest, canonical_json(manifest))
    print(
        json.dumps(
            {
                "rows": aggregate_table.num_rows,
                "columns": aggregate_table.num_columns,
                "row_groups": parquet_file.metadata.num_row_groups,
                "parquet_bytes": args.output.stat().st_size,
                "parquet_sha256": sha256_file(args.output),
                "manifest_sha256": sha256_file(args.manifest),
                "scope_rows": dict(sorted(scope_row_counts.items())),
            },
            sort_keys=True,
        )
    )


def dataset_arrow_schema(
    pa: Any,
    receipt: dict[str, Any],
    occurrence_sha256: str,
) -> Any:
    metadata = {
        b"schema_version": DATASET_SCHEMA_VERSION.encode(),
        b"snapshot_id": receipt["snapshot_id"].encode(),
        b"snapshot_fingerprint": receipt["snapshot_fingerprint"].encode(),
        b"source_occurrence_artifact_sha256": occurrence_sha256.encode(),
        b"evidence_label": b"ALA contributing dataset and citation evidence",
        b"rights_review_semantics": (
            b"textual screening is conservative and not a legal conclusion"
        ),
    }
    return pa.schema(
        [
            pa.field(name, arrow_type(pa, type_name), nullable=nullable)
            for name, type_name, nullable, _ in DATASET_FIELD_SPECS
        ],
        metadata=metadata,
    )


def dataset_schema_contract() -> dict[str, Any]:
    return {
        "schema_version": "butterflylens-parquet-schema/v1",
        "artifact_schema_version": DATASET_SCHEMA_VERSION,
        "format": "parquet",
        "closed": True,
        "fields": [
            {
                "name": name,
                "type": type_name,
                "nullable": nullable,
                "description": description,
            }
            for name, type_name, nullable, description in DATASET_FIELD_SPECS
        ],
        "rights_review_states": [
            "selected_record_licences_allowlisted_no_restrictive_citation_term_detected",
            "blocked_pending_citation_rights_resolution",
        ],
        "invariants": [
            "data_resource_uid is unique and rows are sorted by data_resource_uid",
            "every resource has one exact citation entry joined by UID",
            "selected_record_count equals citation_record_count",
            "selected_record_count equals the sum of the closed processed-licence counts",
            "citation rights, generalisation, withheld, and download-limit text are preserved verbatim",
            "restrictive-term screening blocks downstream public-product release but is not a legal conclusion",
            "provider labels and citations are not human verification",
        ],
    }


def normalized_dataset_statistics(
    pq: Any,
    occurrences: Path,
) -> dict[str, dict[str, Any]]:
    columns = [
        "data_resource_uid",
        "data_resource_name",
        "data_provider_uid",
        "data_provider_name",
        "licence",
        "coordinates_publicly_generalised",
        "spatial_aggregation_eligibility",
    ]
    table = pq.read_table(occurrences, columns=columns)
    result: dict[str, dict[str, Any]] = {}
    for batch in table.to_batches(max_chunksize=65_536):
        for row in batch.to_pylist():
            uid = row["data_resource_uid"]
            stats = result.setdefault(
                uid,
                {
                    "record_count": 0,
                    "resource_names": set(),
                    "provider_uids": set(),
                    "provider_names": set(),
                    "licence_counts": Counter(),
                    "publicly_generalised_record_count": 0,
                    "spatially_eligible_record_count": 0,
                },
            )
            stats["record_count"] += 1
            if row["data_resource_name"] is not None:
                stats["resource_names"].add(row["data_resource_name"])
            if row["data_provider_uid"] is not None:
                stats["provider_uids"].add(row["data_provider_uid"])
            if row["data_provider_name"] is not None:
                stats["provider_names"].add(row["data_provider_name"])
            licence = row["licence"]
            if licence not in LICENCE_COUNT_FIELDS:
                raise AlaBaselineError(
                    f"dataset {uid!r} contains unexpected licence {licence!r}"
                )
            stats["licence_counts"][licence] += 1
            if row["coordinates_publicly_generalised"]:
                stats["publicly_generalised_record_count"] += 1
            if row["spatial_aggregation_eligibility"].startswith("eligible_"):
                stats["spatially_eligible_record_count"] += 1
    return result


def one_or_none(values: set[str], *, field: str, uid: str) -> str | None:
    if len(values) > 1:
        raise AlaBaselineError(f"dataset {uid!r} has multiple {field} values")
    return next(iter(values)) if values else None


def build_dataset_manifest_rows(
    *,
    receipt: dict[str, Any],
    normalization_manifest: dict[str, Any],
    statistics: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    receipt_datasets = {
        row["data_resource_uid"]: row for row in receipt["download"]["datasets"]
    }
    citation_by_uid: dict[str, dict[str, Any]] = {}
    for citation in receipt["download"]["citation_entries"]:
        uid = citation["uid"]
        if uid in citation_by_uid:
            raise AlaBaselineError(f"duplicate ALA citation UID {uid!r}")
        citation_by_uid[uid] = citation
    if set(statistics) != set(receipt_datasets):
        raise AlaBaselineError("normalized and receipt dataset UID inventories differ")

    rows: list[dict[str, Any]] = []
    for uid in sorted(statistics):
        stats = statistics[uid]
        receipt_dataset = receipt_datasets[uid]
        citation = citation_by_uid.get(uid)
        if citation is None:
            raise AlaBaselineError(f"dataset {uid!r} has no exact citation entry")
        resource_name = one_or_none(
            stats["resource_names"], field="resource name", uid=uid
        )
        provider_uid = one_or_none(
            stats["provider_uids"], field="provider UID", uid=uid
        )
        provider_name = one_or_none(
            stats["provider_names"], field="provider name", uid=uid
        )
        if resource_name is None:
            raise AlaBaselineError(f"dataset {uid!r} has no resource name")
        expected = {
            "data_resource_name": resource_name,
            "data_provider_uid": provider_uid,
            "data_provider_name": provider_name,
            "row_count": stats["record_count"],
            "licence_counts": dict(sorted(stats["licence_counts"].items())),
        }
        for key, value in expected.items():
            if receipt_dataset.get(key) != value:
                raise AlaBaselineError(
                    f"dataset {uid!r} receipt {key} does not match normalized rows"
                )
        if citation.get("name") != resource_name:
            raise AlaBaselineError(f"dataset {uid!r} citation name does not match")
        citation_text = citation.get("citation")
        more_information = citation.get("more_information")
        if not citation_text or not more_information:
            raise AlaBaselineError(f"dataset {uid!r} citation text/link is incomplete")
        citation_rights = citation.get("rights")
        restrictive_terms = bool(
            citation_rights
            and RESTRICTIVE_CITATION_RIGHTS_PATTERN.search(citation_rights)
        )
        provider_conditions_present = any(
            citation.get(field)
            for field in (
                "rights",
                "data_generalisations",
                "information_withheld",
                "download_limit",
            )
        )
        source_receipt = {
            "dataset": receipt_dataset,
            "citation": citation,
        }
        row = {
            "source_snapshot_id": receipt["snapshot_id"],
            "source_snapshot_fingerprint": receipt["snapshot_fingerprint"],
            "source_occurrence_artifact_sha256": normalization_manifest["artifact"][
                "physical_sha256"
            ],
            "data_resource_uid": uid,
            "data_resource_name": resource_name,
            "data_provider_uid": provider_uid,
            "data_provider_name": provider_name,
            "selected_record_count": stats["record_count"],
            "citation_record_count": citation["record_count"],
            "citation_count_matches_selected": (
                citation["record_count"] == stats["record_count"]
            ),
            **{
                field: stats["licence_counts"].get(licence, 0)
                for licence, field in LICENCE_COUNT_FIELDS.items()
            },
            "doi": citation.get("doi"),
            "citation": citation_text,
            "citation_rights": citation_rights,
            "data_generalisations": citation.get("data_generalisations"),
            "information_withheld": citation.get("information_withheld"),
            "download_limit": citation.get("download_limit"),
            "more_information": more_information,
            "publicly_generalised_record_count": stats[
                "publicly_generalised_record_count"
            ],
            "spatially_eligible_record_count": stats[
                "spatially_eligible_record_count"
            ],
            "citation_restrictive_rights_terms_detected": restrictive_terms,
            "citation_provider_conditions_present": provider_conditions_present,
            "public_product_rights_review_state": (
                "blocked_pending_citation_rights_resolution"
                if restrictive_terms
                else "selected_record_licences_allowlisted_no_restrictive_citation_term_detected"
            ),
            "source_dataset_receipt_fingerprint": sha256_bytes(
                canonical_json(source_receipt)
            ),
        }
        if not row["citation_count_matches_selected"]:
            raise AlaBaselineError(f"dataset {uid!r} citation count does not match")
        if sum(row[field] for field in LICENCE_COUNT_FIELDS.values()) != stats[
            "record_count"
        ]:
            raise AlaBaselineError(f"dataset {uid!r} licence counts do not match")
        row["dataset_manifest_fingerprint"] = sha256_bytes(canonical_json(row))
        rows.append(row)
    return rows


def relative_posix(path: Path, parent: Path) -> str:
    try:
        return path.resolve().relative_to(parent.resolve()).as_posix()
    except ValueError as error:
        raise AlaBaselineError(f"{path} is outside expected root {parent}") from error


def published_artifact(
    path: Path,
    *,
    root: Path,
    schema_version: str,
    row_count: int | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "path": relative_posix(path, root),
        "physical_sha256": sha256_file(path),
        "physical_bytes": path.stat().st_size,
        "schema_version": schema_version,
    }
    if row_count is not None:
        value["row_count"] = row_count
    return value


def publish_snapshot(args: argparse.Namespace) -> None:
    try:
        import h3
        import pyarrow as pa
        import pyarrow.compute as pc
        import pyarrow.parquet as pq
    except ImportError as error:
        raise AlaBaselineError(
            "publication requires the locked h3 and PyArrow dependencies; run uv sync --frozen"
        ) from error

    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    normalization_manifest = json.loads(
        args.normalization_manifest.read_text(encoding="utf-8")
    )
    aggregation_manifest = json.loads(
        args.aggregation_manifest.read_text(encoding="utf-8")
    )
    attribution = json.loads(args.attribution.read_text(encoding="utf-8"))
    if receipt.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise AlaBaselineError("unexpected ALA snapshot receipt schema")
    if normalization_manifest.get("schema_version") != NORMALIZATION_MANIFEST_SCHEMA_VERSION:
        raise AlaBaselineError("unexpected ALA normalization manifest schema")
    if aggregation_manifest.get("schema_version") != AGGREGATION_MANIFEST_SCHEMA_VERSION:
        raise AlaBaselineError("unexpected ALA aggregation manifest schema")
    if attribution.get("schema_version") != ATTRIBUTION_SCHEMA_VERSION:
        raise AlaBaselineError("unexpected ALA attribution schema")
    if len(
        {
            receipt["snapshot_id"],
            normalization_manifest["snapshot_id"],
            aggregation_manifest["snapshot_id"],
            attribution["snapshot_id"],
        }
    ) != 1:
        raise AlaBaselineError("ALA publication inputs use different snapshot IDs")
    occurrence_sha = sha256_file(args.occurrences)
    cell_sha = sha256_file(args.cells)
    if occurrence_sha != normalization_manifest["artifact"]["physical_sha256"]:
        raise AlaBaselineError("published occurrence checksum does not match manifest")
    if cell_sha != aggregation_manifest["artifact"]["physical_sha256"]:
        raise AlaBaselineError("published cell checksum does not match manifest")

    statistics = normalized_dataset_statistics(pq, args.occurrences)
    rows = build_dataset_manifest_rows(
        receipt=receipt,
        normalization_manifest=normalization_manifest,
        statistics=statistics,
    )
    schema = dataset_arrow_schema(pa, receipt, occurrence_sha)
    dataset_table = pa.Table.from_pylist(rows, schema=schema)
    order = pc.sort_indices(
        dataset_table, sort_keys=[("data_resource_uid", "ascending")]
    )
    dataset_table = pc.take(dataset_table, order)
    dataset_uids = dataset_table.column("data_resource_uid").to_pylist()
    if len(dataset_uids) != len(set(dataset_uids)):
        raise AlaBaselineError("dataset manifest UIDs are not unique")
    write_bytes(args.dataset_schema_output, canonical_json(dataset_schema_contract()))
    args.dataset_output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.dataset_output.with_suffix(args.dataset_output.suffix + ".tmp")
    pq.write_table(
        dataset_table,
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
    os.replace(temporary, args.dataset_output)

    ala_root = args.snapshot_manifest.parent
    pack_root = args.pack_manifest.parent
    archive_path = ala_root / receipt["download"]["archive_path"]
    occurrence_schema = ala_root / normalization_manifest["schema"]["path"]
    cell_schema = ala_root / aggregation_manifest["schema"]["path"]
    for path in (archive_path, occurrence_schema, cell_schema):
        if not path.is_file():
            raise AlaBaselineError(f"missing publication input {path}")
    restrictive_rows = [
        row
        for row in dataset_table.to_pylist()
        if row["citation_restrictive_rights_terms_detected"]
    ]
    restrictive_uids = sorted(row["data_resource_uid"] for row in restrictive_rows)
    restrictive_record_count = sum(
        row["selected_record_count"] for row in restrictive_rows
    )
    dataset_uid_set = set(dataset_uids)
    non_dataset_citation_uids = sorted(
        citation["uid"]
        for citation in receipt["download"]["citation_entries"]
        if citation["uid"] not in dataset_uid_set
    )
    dataset_fingerprint_digest = hashlib.sha256()
    for fingerprint in dataset_table.column("dataset_manifest_fingerprint").to_pylist():
        dataset_fingerprint_digest.update(fingerprint.encode("ascii"))
        dataset_fingerprint_digest.update(b"\n")
    artifacts = {
        "source_archive": published_artifact(
            archive_path,
            root=ala_root,
            schema_version="ALA offline download ZIP",
            row_count=receipt["download"]["row_count"],
        ),
        "snapshot_receipt": published_artifact(
            args.receipt,
            root=ala_root,
            schema_version=SNAPSHOT_SCHEMA_VERSION,
            row_count=1,
        ),
        "attribution": published_artifact(
            args.attribution,
            root=ala_root,
            schema_version=ATTRIBUTION_SCHEMA_VERSION,
            row_count=1,
        ),
        "normalized_occurrences": published_artifact(
            args.occurrences,
            root=ala_root,
            schema_version=NORMALIZED_SCHEMA_VERSION,
            row_count=normalization_manifest["artifact"]["row_count"],
        ),
        "normalization_manifest": published_artifact(
            args.normalization_manifest,
            root=ala_root,
            schema_version=NORMALIZATION_MANIFEST_SCHEMA_VERSION,
            row_count=1,
        ),
        "occurrence_schema": published_artifact(
            occurrence_schema,
            root=ala_root,
            schema_version="butterflylens-parquet-schema/v1",
            row_count=1,
        ),
        "aggregate_cells": published_artifact(
            args.cells,
            root=ala_root,
            schema_version=AGGREGATED_SCHEMA_VERSION,
            row_count=aggregation_manifest["artifact"]["row_count"],
        ),
        "aggregation_manifest": published_artifact(
            args.aggregation_manifest,
            root=ala_root,
            schema_version=AGGREGATION_MANIFEST_SCHEMA_VERSION,
            row_count=1,
        ),
        "cell_schema": published_artifact(
            cell_schema,
            root=ala_root,
            schema_version="butterflylens-parquet-schema/v1",
            row_count=1,
        ),
        "dataset_manifest": published_artifact(
            args.dataset_output,
            root=ala_root,
            schema_version=DATASET_SCHEMA_VERSION,
            row_count=dataset_table.num_rows,
        ),
        "dataset_schema": published_artifact(
            args.dataset_schema_output,
            root=ala_root,
            schema_version="butterflylens-parquet-schema/v1",
            row_count=1,
        ),
    }
    snapshot_manifest = {
        "schema_version": PUBLISHED_SNAPSHOT_SCHEMA_VERSION,
        "generated_at": args.generated_at or utc_now(),
        "snapshot_id": receipt["snapshot_id"],
        "snapshot_fingerprint": receipt["snapshot_fingerprint"],
        "evidence_label": "ALA baseline occurrence evidence",
        "provider": ALA_PROVIDER,
        "query": receipt["query_policy"],
        "taxon_scope": receipt["taxon_scope"],
        "artifacts": artifacts,
        "counts": {
            "selected_occurrence_rows": normalization_manifest["artifact"][
                "row_count"
            ],
            "dataset_resources": dataset_table.num_rows,
            "citation_entries": receipt["download"]["citation_entry_count"],
            "dataset_citation_entries": dataset_table.num_rows,
            "non_dataset_citation_entries": len(non_dataset_citation_uids),
            "non_dataset_citation_uids": non_dataset_citation_uids,
            "exact_crosswalk_rows": normalization_manifest["counts"][
                "taxon_match_state"
            ]["exact_ala_taxon_concept_crosswalk"],
            "unmatched_provider_taxon_assertion_rows": normalization_manifest[
                "counts"
            ]["taxon_match_state"]["unmatched_provider_taxon_assertion"],
            "spatially_eligible_rows": aggregation_manifest["counts"][
                "unique_spatially_eligible_source_rows"
            ],
            "aggregate_scope_rows": aggregation_manifest["counts"]["scope_rows"],
            "rights_review_required_datasets": len(restrictive_uids),
            "rights_review_required_records": restrictive_record_count,
            "citation_information_withheld_datasets": sum(
                row["information_withheld"] is not None
                for row in dataset_table.to_pylist()
            ),
            "citation_data_generalisation_datasets": sum(
                row["data_generalisations"] is not None
                for row in dataset_table.to_pylist()
            ),
        },
        "rights": {
            "attribution_path": relative_posix(args.attribution, ala_root),
            "attribution_sha256": sha256_file(args.attribution),
            "selected_record_licence_allowlist": list(ALLOWED_PUBLIC_LICENCES),
            "dataset_fingerprint_digest": dataset_fingerprint_digest.hexdigest(),
            "citation_restrictive_rights_review_required_uids": restrictive_uids,
            "citation_restrictive_rights_screening": (
                "Conservative text detection only; this is not a legal conclusion. Exact citation "
                "rights remain in ala_dataset_manifest.parquet and the source receipt."
            ),
            "downstream_public_product_release_state": (
                "blocked_pending_dataset_rights_resolution"
                if restrictive_uids
                else "selected_record_licences_allowlisted_no_restrictive_citation_term_detected"
            ),
            "repository_evidence_status": (
                "preserved with exact provider licences, citations, conditions, and release gate"
            ),
        },
        "policies": {
            "provider_taxon_assertions_are_human_verification": False,
            "absence_inference_permitted": False,
            "sensitive_coordinates": (
                "ALA public generalisation is preserved; generalized rows are coarse-only"
            ),
            "boundary_geometry_copied": False,
            "citation_join": "exact data-resource UID only; no provider hierarchy inferred",
            "non_dataset_citations": (
                "provider, collection, and institution entries remain in the source receipt"
            ),
        },
        "build": {
            "python": ".".join(map(str, __import__("sys").version_info[:3])),
            "pyarrow": pa.__version__,
            "h3": h3.__version__,
        },
    }
    snapshot_manifest["snapshot_manifest_fingerprint"] = sha256_bytes(
        canonical_json(snapshot_manifest)
    )
    write_bytes(args.snapshot_manifest, canonical_json(snapshot_manifest))

    pack_manifest = json.loads(args.pack_manifest.read_text(encoding="utf-8"))
    snapshot_manifest_sha = sha256_file(args.snapshot_manifest)
    pack_manifest["ala_state"] = {
        "status": (
            "built_rights_review_required"
            if restrictive_uids
            else "built"
        ),
        "generated_at": snapshot_manifest["generated_at"],
        "snapshot_id": receipt["snapshot_id"],
        "snapshot_fingerprint": receipt["snapshot_fingerprint"],
        "selected_occurrence_rows": sum(
            dataset_table.column("selected_record_count").to_pylist()
        ),
        "dataset_resources": dataset_table.num_rows,
        "citation_entries": receipt["download"]["citation_entry_count"],
        "spatially_eligible_rows": aggregation_manifest["counts"][
            "unique_spatially_eligible_source_rows"
        ],
        "rights_review_required_datasets": len(restrictive_uids),
        "rights_review_required_records": restrictive_record_count,
        "snapshot_manifest_path": "ala/ala_snapshot_manifest.json",
        "snapshot_manifest_sha256": snapshot_manifest_sha,
    }
    pack_artifacts = pack_manifest.setdefault("artifacts", {})
    pack_artifacts.update(
        {
            "ala/ala_baseline_occurrences.parquet": {
                "schema_version": NORMALIZED_SCHEMA_VERSION,
                "physical_sha256": occurrence_sha,
                "row_count": normalization_manifest["artifact"]["row_count"],
            },
            "ala/ala_baseline_cells.parquet": {
                "schema_version": AGGREGATED_SCHEMA_VERSION,
                "physical_sha256": cell_sha,
                "row_count": aggregation_manifest["artifact"]["row_count"],
            },
            "ala/ala_dataset_manifest.parquet": {
                "schema_version": DATASET_SCHEMA_VERSION,
                "physical_sha256": sha256_file(args.dataset_output),
                "row_count": dataset_table.num_rows,
            },
            "ala/ala_snapshot_manifest.json": {
                "schema_version": PUBLISHED_SNAPSHOT_SCHEMA_VERSION,
                "physical_sha256": snapshot_manifest_sha,
                "row_count": 1,
            },
            "ala/ala_attribution.json": {
                "schema_version": ATTRIBUTION_SCHEMA_VERSION,
                "physical_sha256": sha256_file(args.attribution),
                "row_count": 1,
            },
        }
    )
    pack_manifest["sources"] = [
        source
        for source in pack_manifest.get("sources", [])
        if source.get("path") != "ala/ala_snapshot_receipt.json"
    ]
    occurrence_sources = [
        source
        for source in pack_manifest.get("occurrence_sources", [])
        if source.get("path") != "ala/ala_snapshot_receipt.json"
    ]
    occurrence_sources.append(
        {
            "path": "ala/ala_snapshot_receipt.json",
            "physical_sha256": sha256_file(args.receipt),
            "retrieved_at": receipt["retrieved_at"],
            "provider": ALA_PROVIDER,
            "snapshot_id": receipt["snapshot_id"],
            "snapshot_fingerprint": receipt["snapshot_fingerprint"],
        }
    )
    pack_manifest["occurrence_sources"] = occurrence_sources
    write_bytes(args.pack_manifest, canonical_json(pack_manifest))
    print(
        json.dumps(
            {
                "dataset_rows": dataset_table.num_rows,
                "dataset_parquet_sha256": sha256_file(args.dataset_output),
                "snapshot_manifest_sha256": snapshot_manifest_sha,
                "pack_manifest_sha256": sha256_file(args.pack_manifest),
                "rights_review_required_datasets": len(restrictive_uids),
                "rights_review_required_records": restrictive_record_count,
            },
            sort_keys=True,
        )
    )


def acquire_contracts(source_dir: Path, retrieved_at: str) -> dict[str, Any]:
    definitions = (
        ("occurrence_openapi", ALA_OPENAPI_URL, "ala_occurrence_openapi.json", "application/json"),
        ("index_fields", ALA_INDEX_FIELDS_URL, "ala_index_fields.json", "application/json"),
        ("spatial_openapi", ALA_SPATIAL_OPENAPI_URL, "ala_spatial_openapi.yaml", "application/yaml,text/yaml,*/*"),
    )
    contracts: dict[str, Any] = {}
    for key, url, filename, accept in definitions:
        body, headers = request_bytes(url, accept=accept)
        stored_body = canonical_json(json.loads(body)) if filename.endswith(".json") else body
        path = source_dir / filename
        write_bytes(path, stored_body)
        contracts[key] = {
            "url": url,
            "path": f"sources/{filename}",
            "retrieved_at": retrieved_at,
            "response_sha256": sha256_bytes(body),
            "physical_sha256": sha256_bytes(stored_body),
            "headers": headers,
        }
    layers = []
    for layer_id, index_field in (
        (IBRA_LAYER_ID, IBRA_FIELD),
        (LGA_LAYER_ID, LGA_FIELD),
    ):
        url = ALA_SPATIAL_LAYER_URL.format(layer_id=layer_id)
        body, headers = request_bytes(url)
        payload = json.loads(body)
        layers.append(
            {
                "layer_id": layer_id,
                "index_field": index_field,
                "metadata": payload,
                "source_url": url,
                "retrieved_at": retrieved_at,
                "response_sha256": sha256_bytes(body),
                "headers": headers,
            }
        )
    layer_path = source_dir / "ala_spatial_layers.json"
    write_bytes(
        layer_path,
        canonical_json(
            {
                "schema_version": "butterflylens-ala-spatial-layer-receipt/v1",
                "provider": ALA_PROVIDER,
                "retrieved_at": retrieved_at,
                "layers": layers,
            }
        ),
    )
    contracts["spatial_layers"] = {
        "path": "sources/ala_spatial_layers.json",
        "physical_sha256": sha256_file(layer_path),
        "layers": [
            {
                "layer_id": layer["layer_id"],
                "index_field": layer["index_field"],
                "display_name": layer["metadata"].get("displayname"),
                "source": layer["metadata"].get("source"),
                "source_link": layer["metadata"].get("source_link"),
                "licence": layer["metadata"].get("licence_notes"),
                "licence_url": layer["metadata"].get("licence_link"),
                "metadata_date": layer["metadata"].get("mddatest"),
            }
            for layer in layers
        ],
    }
    return contracts


def attribution_payload(snapshot_id: str, retrieved_at: str) -> dict[str, Any]:
    return {
        "schema_version": ATTRIBUTION_SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "provider": ALA_PROVIDER,
        "retrieved_at": retrieved_at,
        "attribution": (
            "Atlas of Living Australia occurrence data and each contributing "
            "data provider and data resource identified in the snapshot."
        ),
        "citation": (
            "Atlas of Living Australia occurrence download for Papilionoidea "
            f"in Australia, accessed {retrieved_at[:10]}. No DOI was minted."
        ),
        "terms_url": ALA_TERMS_URL,
        "citation_guidance_url": ALA_CITATION_URL,
        "download_guide_url": ALA_DOWNLOAD_GUIDE_URL,
        "licence_policy": (
            "Mixed per-record licences; every row retains the ALA-processed "
            "licence value. The public snapshot admits only CC0, Public Domain "
            "Mark, and attribution-only CC BY variants."
        ),
        "doi": None,
        "spatial_attribution": [
            {
                "field": IBRA_FIELD,
                "layer": "IBRA version 7 regions",
                "source": "Department of Climate Change, Energy, the Environment and Water",
                "licence": "CC-BY-4.0",
                "licence_url": "https://creativecommons.org/licenses/by/4.0/",
            },
            {
                "field": LGA_FIELD,
                "layer": "Local Government Areas 2023",
                "source": "Australian Bureau of Statistics",
                "licence": "CC-BY-4.0",
                "licence_url": "https://creativecommons.org/licenses/by/4.0/",
                "qualification": (
                    "ABS Mesh Block approximation for statistical use; not an "
                    "official legal boundary."
                ),
            },
        ],
        "required_public_notice": (
            "ALA baseline occurrence evidence is a selected snapshot, not complete "
            "truth; provider taxon labels are provider assertions, not human verification."
        ),
    }


def freeze_snapshot(args: argparse.Namespace) -> None:
    output_dir = args.output_dir.resolve()
    source_dir = output_dir / "sources"
    source_dir.mkdir(parents=True, exist_ok=True)
    crosswalk_root = load_crosswalk_root(args.crosswalk)
    if args.resume_job_response:
        initial_body = args.resume_job_response.read_bytes()
        initial_headers: dict[str, str | None] = {}
    else:
        initial_body, initial_headers = submit_download(args.email)
    initial = json.loads(initial_body)
    raw_submitted_at = args.submitted_at or initial_headers.get("date") or utc_now()
    submitted_at = normalized_timestamp(raw_submitted_at)
    final, final_body = poll_download(
        initial,
        interval_seconds=args.poll_interval,
        timeout_seconds=args.timeout,
    )
    download_url = final.get("downloadUrl") or final.get("downloadURL")
    if not isinstance(download_url, str):
        raise AlaBaselineError("completed ALA response has no download URL")
    archive_path = source_dir / "ala_occurrence_download.zip"
    archive_headers = download_file(download_url, archive_path)
    inspection = inspect_archive(archive_path)
    expected_rows = final.get("totalRecords", initial.get("totalRecords"))
    if inspection["row_count"] != expected_rows:
        raise AlaBaselineError(
            f"archive row count {inspection['row_count']} != job count {expected_rows}"
        )
    retrieved_at = args.retrieved_at or utc_now()
    contracts = acquire_contracts(source_dir, retrieved_at)
    public_parameters = public_request_parameters()
    policy_fingerprint = sha256_bytes(
        canonical_json(
            {
                "endpoint": ALA_DOWNLOAD_ENDPOINT,
                "parameters": public_parameters,
                "archive_sha256": sha256_file(archive_path),
                "crosswalk_sha256": sha256_file(args.crosswalk),
            }
        )
    )
    snapshot_id = f"ala-papilionoidea-au-{retrieved_at[:10].replace('-', '')}-{policy_fingerprint[:12]}"
    receipt = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "provider": ALA_PROVIDER,
        "submitted_at": submitted_at,
        "retrieved_at": retrieved_at,
        "taxon_scope": {
            "accepted_name": ALA_ROOT_NAME,
            "rank": "superfamily",
            "ala_taxon_id": ALA_ROOT_TAXON_ID,
            "butterflylens_key": crosswalk_root["butterflylens_key"],
            "input_crosswalk_path": str(args.crosswalk),
            "input_crosswalk_sha256": sha256_file(args.crosswalk),
            "query": f"lsid:{ALA_ROOT_TAXON_ID}",
        },
        "query_policy": {
            "endpoint": ALA_DOWNLOAD_ENDPOINT,
            "filter_queries": list(FILTER_QUERIES),
            "default_quality_filters_disabled": True,
            "coordinate_filters": [],
            "basis_of_record_filters": [],
            "licence_allowlist": list(ALLOWED_PUBLIC_LICENCES),
            "requested_fields": list(DOWNLOAD_FIELDS),
            "extra_contextual_fields": list(EXTRA_FIELDS),
            "quality_assertion_mode": "assertions_field; no expanded QA columns",
            "public_request_fingerprint": sha256_bytes(canonical_json(public_parameters)),
            "contact_email_required_by_provider": True,
            "contact_email_persisted": False,
            "email_notification": False,
            "doi_minted": False,
        },
        "evidence_policy": {
            "description": "ALA baseline occurrence evidence",
            "provider_taxon_labels": "provider assertions; not human verification",
            "absence_inference_permitted": False,
            "coordinates": (
                "Retain public processed WGS84 coordinates and uncertainty without "
                "acquisition-time coordinate filtering; spatial eligibility is derived later."
            ),
            "basis_of_record": (
                "Retain every selected basis and distinguish observation, machine, "
                "specimen, fossil, occurrence, and historical evidence downstream."
            ),
            "sensitive_data": (
                "Retain only public ALA-processed values; preserve sensitive/generalised "
                "flags; never reconstruct withheld coordinates or imply greater precision."
            ),
            "quality": (
                "Retain ALA assertions and spatial-validity state; disabled provider "
                "default filters are not a quality endorsement."
            ),
        },
        "provider_contracts": contracts,
        "download": {
            "initial_response_sha256": sha256_bytes(initial_body),
            "final_response_sha256": sha256_bytes(final_body),
            "initial_status": initial.get("status"),
            "final_status": final.get("status"),
            "status_url": initial.get("statusUrl"),
            "search_url": initial.get("searchUrl"),
            "download_url": download_url,
            "archive_path": "sources/ala_occurrence_download.zip",
            "archive_bytes": archive_path.stat().st_size,
            "archive_sha256": sha256_file(archive_path),
            "archive_headers": archive_headers,
            "expected_record_count": expected_rows,
            **inspection,
        },
        "snapshot_fingerprint": policy_fingerprint,
        "terms_url": ALA_TERMS_URL,
        "attribution_path": "ala_attribution.json",
    }
    receipt_path = output_dir / "ala_snapshot_receipt.json"
    write_bytes(receipt_path, canonical_json(receipt))
    write_bytes(
        output_dir / "ala_attribution.json",
        canonical_json(attribution_payload(snapshot_id, retrieved_at)),
    )
    print(
        json.dumps(
            {
                "snapshot_id": snapshot_id,
                "rows": inspection["row_count"],
                "datasets": inspection["dataset_count"],
                "archive_bytes": archive_path.stat().st_size,
                "archive_sha256": sha256_file(archive_path),
                "receipt_sha256": sha256_file(receipt_path),
            },
            sort_keys=True,
        )
    )


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    commands = value.add_subparsers(dest="command", required=True)
    acquire = commands.add_parser(
        "acquire-snapshot", help="submit or resume and freeze an ALA bulk download"
    )
    acquire.add_argument("--crosswalk", type=Path, required=True)
    acquire.add_argument("--output-dir", type=Path, required=True)
    acquire.add_argument("--email", default=None)
    acquire.add_argument("--resume-job-response", type=Path)
    acquire.add_argument("--submitted-at")
    acquire.add_argument("--retrieved-at")
    acquire.add_argument("--poll-interval", type=float, default=10.0)
    acquire.add_argument("--timeout", type=float, default=3600.0)
    acquire.set_defaults(handler=freeze_snapshot)
    normalize = commands.add_parser(
        "normalize", help="build deterministic normalized occurrence Parquet"
    )
    normalize.add_argument("--archive", type=Path, required=True)
    normalize.add_argument("--receipt", type=Path, required=True)
    normalize.add_argument("--crosswalk", type=Path, required=True)
    normalize.add_argument("--output", type=Path, required=True)
    normalize.add_argument("--schema-output", type=Path, required=True)
    normalize.add_argument("--manifest", type=Path, required=True)
    normalize.add_argument("--generated-at")
    normalize.set_defaults(handler=normalize_occurrences)
    aggregate = commands.add_parser(
        "aggregate", help="build deterministic national, contextual, and H3 rollups"
    )
    aggregate.add_argument("--occurrences", type=Path, required=True)
    aggregate.add_argument("--normalization-manifest", type=Path, required=True)
    aggregate.add_argument("--output", type=Path, required=True)
    aggregate.add_argument("--schema-output", type=Path, required=True)
    aggregate.add_argument("--manifest", type=Path, required=True)
    aggregate.add_argument("--generated-at")
    aggregate.set_defaults(handler=aggregate_occurrences)
    publish = commands.add_parser(
        "publish-manifest", help="publish dataset and snapshot manifests"
    )
    publish.add_argument("--receipt", type=Path, required=True)
    publish.add_argument("--attribution", type=Path, required=True)
    publish.add_argument("--occurrences", type=Path, required=True)
    publish.add_argument("--normalization-manifest", type=Path, required=True)
    publish.add_argument("--cells", type=Path, required=True)
    publish.add_argument("--aggregation-manifest", type=Path, required=True)
    publish.add_argument("--dataset-output", type=Path, required=True)
    publish.add_argument("--dataset-schema-output", type=Path, required=True)
    publish.add_argument("--snapshot-manifest", type=Path, required=True)
    publish.add_argument("--pack-manifest", type=Path, required=True)
    publish.add_argument("--generated-at")
    publish.set_defaults(handler=publish_snapshot)
    return value


def main() -> None:
    args = parser().parse_args()
    if args.command == "acquire-snapshot" and not args.resume_job_response and not args.email:
        raise AlaBaselineError("--email is required when submitting a new ALA download")
    args.handler(args)


if __name__ == "__main__":
    try:
        main()
    except (AlaBaselineError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        raise SystemExit(f"ALA baseline build failed: {error}") from error
