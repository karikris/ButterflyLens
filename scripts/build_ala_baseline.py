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
import os
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
