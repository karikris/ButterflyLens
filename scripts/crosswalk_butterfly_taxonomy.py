#!/usr/bin/env python3
"""Acquire provider taxon matches and build the butterfly identity crosswalk."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from build_butterfly_taxonomy import canonical_json, sha256_file, utc_now


SOURCE_SCHEMA_VERSION = "butterflylens-taxonomy-crosswalk-source/v1"
CROSSWALK_SCHEMA_VERSION = "butterflylens-taxonomy-crosswalk/v1"
CONFLICT_SCHEMA_VERSION = "butterflylens-taxonomy-conflict/v1"
ALA_ENDPOINT = (
    "https://api.ala.org.au/namematching/api/searchAllByClassification"
)
ALA_DOCS_URL = (
    "https://docs.ala.org.au/openapi/index.html?urls.primaryName=namematching"
)
GBIF_ENDPOINT = "https://api.gbif.org/v2/species/match"
GBIF_METADATA_ENDPOINT = "https://api.gbif.org/v2/species/match/metadata"
GBIF_DOCS_URL = "https://techdocs.gbif.org/en/openapi/v1/species"
INAT_ARCHIVE_URL = "https://www.inaturalist.org/taxa/inaturalist-taxonomy.dwca.zip"
INAT_DATASET_DOCS_URL = "https://www.inaturalist.org/pages/developers"
USER_AGENT = (
    "ButterflyLens-taxonomy/0.1 "
    "(https://github.com/karikris/ButterflyLens; public research pack)"
)
SUBGENUS_PATTERN = re.compile(r"^([^\s]+)\s+\([^)]+\)\s+")


class CrosswalkError(RuntimeError):
    """Raised when provider or reconciliation invariants fail closed."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_taxa(path: Path) -> list[dict[str, Any]]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    keys = [record.get("butterflylens_key") for record in records]
    if not records or len(keys) != len(set(keys)) or any(not key for key in keys):
        raise CrosswalkError("taxa input is empty or has duplicate/missing keys")
    return records


def normalized_query_name(record: dict[str, Any]) -> str:
    name = record["accepted_scientific_name"]
    if record["rank"] in {"species", "subspecies"}:
        return SUBGENUS_PATTERN.sub(r"\1 ", name)
    return name


def comparable_name(value: str | None) -> str | None:
    if value is None:
        return None
    value = SUBGENUS_PATTERN.sub(r"\1 ", value)
    return " ".join(value.casefold().split())


def lineage_names(record: dict[str, Any]) -> dict[str, str]:
    values = {
        item["rank"]: item["accepted_scientific_name"]
        for item in record["parent_path"]
    }
    values[record["rank"]] = record["accepted_scientific_name"]
    return values


def request_json(
    url: str,
    *,
    method: str = "GET",
    body: Any | None = None,
    attempts: int = 3,
) -> tuple[Any, bytes, dict[str, str | None]]:
    payload = canonical_json(body) if body is not None else None
    request = urllib.request.Request(
        url,
        data=payload,
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
                return json.loads(raw), raw, {
                    "content_type": response.headers.get("Content-Type"),
                    "etag": response.headers.get("ETag"),
                    "last_modified": response.headers.get("Last-Modified"),
                }
        except urllib.error.HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == attempts:
                raise CrosswalkError(f"request failed for {url}: HTTP {error.code}") from error
            retry_after = error.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
            time.sleep(delay)
        except (urllib.error.URLError, json.JSONDecodeError) as error:
            if attempt == attempts:
                raise CrosswalkError(f"request failed for {url}: {error}") from error
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def ala_query(record: dict[str, Any]) -> dict[str, str]:
    lineage = lineage_names(record)
    query = {
        "scientificName": normalized_query_name(record),
        "kingdom": "Animalia",
        "phylum": "Arthropoda",
        "clazz": "Insecta",
        "order": "Lepidoptera",
        "rank": record["rank"],
    }
    for rank in ("family", "genus"):
        if rank in lineage:
            query[rank] = lineage[rank]
    return query


def acquire_ala(taxa_path: Path, output: Path, batch_size: int) -> None:
    if batch_size < 1 or batch_size > 500:
        raise CrosswalkError("ALA batch size must be between 1 and 500")
    records = load_taxa(taxa_path)
    retrieved_at = utc_now()
    batches: list[dict[str, Any]] = []
    for offset in range(0, len(records), batch_size):
        batch_records = records[offset : offset + batch_size]
        request_body = [ala_query(record) for record in batch_records]
        response, raw, headers = request_json(
            ALA_ENDPOINT, method="POST", body=request_body
        )
        if not isinstance(response, list) or len(response) != len(batch_records):
            raise CrosswalkError("ALA bulk response length does not match request")
        batches.append(
            {
                "butterflylens_keys": [
                    record["butterflylens_key"] for record in batch_records
                ],
                "request_sha256": sha256_bytes(canonical_json(request_body)),
                "response_sha256": sha256_bytes(raw),
                "headers": headers,
                "request": request_body,
                "response": response,
            }
        )
        print(
            f"ALA matches: {min(offset + batch_size, len(records))}/{len(records)}",
            flush=True,
        )
    snapshot = {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "provider": "Atlas of Living Australia",
        "retrieved_at": retrieved_at,
        "input_taxa_sha256": sha256_file(taxa_path),
        "source": {
            "endpoint": ALA_ENDPOINT,
            "documentation_url": ALA_DOCS_URL,
            "terms_url": "https://www.ala.org.au/terms-of-use/",
            "source_authority": "Australian Faunal Directory via ALA namematching",
        },
        "batches": batches,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json(snapshot))


def gbif_query(record: dict[str, Any]) -> dict[str, str]:
    lineage = lineage_names(record)
    query = {
        "scientificName": normalized_query_name(record),
        "taxonRank": record["rank"].upper(),
        "kingdom": "Animalia",
        "phylum": "Arthropoda",
        "class": "Insecta",
        "order": "Lepidoptera",
    }
    for rank in ("superfamily", "family", "subfamily", "tribe", "genus"):
        if rank in lineage:
            query[rank] = lineage[rank]
    return query


def acquire_gbif(
    taxa_path: Path, output: Path, delay_seconds: float, workers: int
) -> None:
    if delay_seconds < 0.1:
        raise CrosswalkError("GBIF acquisition delay must be at least 0.1 seconds")
    if workers < 1 or workers > 4:
        raise CrosswalkError("GBIF workers must be between 1 and 4")
    records = load_taxa(taxa_path)
    retrieved_at = utc_now()
    metadata, metadata_raw, metadata_headers = request_json(GBIF_METADATA_ENDPOINT)

    def fetch(record: dict[str, Any]) -> dict[str, Any]:
        time.sleep(delay_seconds)
        query = gbif_query(record)
        url = GBIF_ENDPOINT + "?" + urllib.parse.urlencode(query)
        response, raw, headers = request_json(url)
        return {
            "butterflylens_key": record["butterflylens_key"],
            "query": query,
            "url": url,
            "response_sha256": sha256_bytes(raw),
            "headers": headers,
            "response": response,
        }

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(fetch, record) for record in records]
        entries: list[dict[str, Any]] = []
        for index, future in enumerate(futures, 1):
            entries.append(future.result())
            if index % 100 == 0 or index == len(records):
                print(f"GBIF matches: {index}/{len(records)}", flush=True)
    snapshot = {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "provider": "GBIF",
        "retrieved_at": retrieved_at,
        "input_taxa_sha256": sha256_file(taxa_path),
        "source": {
            "endpoint": GBIF_ENDPOINT,
            "metadata_endpoint": GBIF_METADATA_ENDPOINT,
            "documentation_url": GBIF_DOCS_URL,
            "terms_url": "https://www.gbif.org/terms",
            "metadata_response_sha256": sha256_bytes(metadata_raw),
            "metadata_headers": metadata_headers,
            "metadata": metadata,
        },
        "entries": entries,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json(snapshot))


def inat_archive_metadata(archive: zipfile.ZipFile) -> dict[str, Any]:
    eml_raw = archive.read("eml.xml")
    root = ElementTree.fromstring(eml_raw)
    dataset = next((item for item in root.iter() if item.tag.endswith("dataset")), None)
    if dataset is None:
        raise CrosswalkError("iNaturalist archive EML has no dataset")

    def first_text(suffix: str) -> str | None:
        for item in dataset.iter():
            if item.tag.endswith(suffix) and item.text and item.text.strip():
                return " ".join(item.text.split())
        return None

    rights = next(
        (
            " ".join(" ".join(item.itertext()).split())
            for item in dataset.iter()
            if item.tag.endswith("intellectualRights")
        ),
        None,
    )

    taxon_info = archive.getinfo("taxa.csv")
    return {
        "title": first_text("title"),
        "publication_date": first_text("pubDate"),
        "intellectual_rights": rights,
        "eml_sha256": sha256_bytes(eml_raw),
        "taxa_member_size": taxon_info.file_size,
        "taxa_member_crc32": f"{taxon_info.CRC:08x}",
    }


def selected_inat_row(row: dict[str, str]) -> dict[str, str | None]:
    fields = (
        "id",
        "taxonID",
        "parentNameUsageID",
        "kingdom",
        "phylum",
        "class",
        "order",
        "family",
        "genus",
        "specificEpithet",
        "infraspecificEpithet",
        "modified",
        "scientificName",
        "taxonRank",
    )
    return {field: row.get(field) or None for field in fields}


def acquire_inaturalist(taxa_path: Path, archive_path: Path, output: Path) -> None:
    records = load_taxa(taxa_path)
    targets: dict[tuple[str, str], list[str]] = defaultdict(list)
    queries: dict[str, dict[str, str]] = {}
    for record in records:
        query_name = normalized_query_name(record)
        target = (comparable_name(query_name) or "", record["rank"])
        targets[target].append(record["butterflylens_key"])
        queries[record["butterflylens_key"]] = {
            "scientific_name": query_name,
            "rank": record["rank"],
        }
    candidates: dict[str, list[dict[str, str | None]]] = defaultdict(list)
    with zipfile.ZipFile(archive_path) as archive:
        metadata = inat_archive_metadata(archive)
        with archive.open("taxa.csv") as binary:
            reader = csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8", newline=""))
            for row in reader:
                if (
                    comparable_name(row.get("kingdom")) != "animalia"
                    or comparable_name(row.get("class")) != "insecta"
                    or comparable_name(row.get("order")) != "lepidoptera"
                ):
                    continue
                target = (
                    comparable_name(row.get("scientificName")) or "",
                    (row.get("taxonRank") or "").casefold(),
                )
                for butterflylens_key in targets.get(target, []):
                    candidates[butterflylens_key].append(selected_inat_row(row))
    entries = [
        {
            "butterflylens_key": record["butterflylens_key"],
            "query": queries[record["butterflylens_key"]],
            "candidates": candidates.get(record["butterflylens_key"], []),
        }
        for record in records
    ]
    snapshot = {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "provider": "iNaturalist",
        "retrieved_at": utc_now(),
        "input_taxa_sha256": sha256_file(taxa_path),
        "source": {
            "archive_url": INAT_ARCHIVE_URL,
            "dataset_documentation_url": INAT_DATASET_DOCS_URL,
            "terms_url": "https://www.inaturalist.org/pages/terms",
            "archive_sha256": sha256_file(archive_path),
            **metadata,
        },
        "entries": entries,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json(snapshot))


def expected_classification(record: dict[str, Any]) -> dict[str, str]:
    expected = lineage_names(record)
    return {
        "kingdom": "Animalia",
        "phylum": "Arthropoda",
        "class": "Insecta",
        "order": "Lepidoptera",
        **expected,
    }


def classification_reasons(
    expected: dict[str, str], observed: dict[str, str | None]
) -> list[str]:
    reasons: list[str] = []
    for rank in ("kingdom", "phylum", "class", "order", "family", "genus"):
        expected_name = expected.get(rank)
        observed_name = observed.get(rank)
        if (
            expected_name
            and observed_name
            and comparable_name(expected_name) != comparable_name(observed_name)
        ):
            reasons.append(f"{rank}_mismatch")
    return reasons


def evaluate_ala(record: dict[str, Any], result: Any, response_hash: str) -> tuple[dict[str, Any], str | None]:
    query_name = normalized_query_name(record)
    if not isinstance(result, dict) or not result.get("success"):
        return {
            "state": "unmatched",
            "query_name": query_name,
            "reasons": ["provider_no_match"],
            "source_response_sha256": response_hash,
        }, None
    reasons: list[str] = []
    if comparable_name(result.get("scientificName")) != comparable_name(query_name):
        reasons.append("name_mismatch")
    if (result.get("rank") or "").casefold() != record["rank"]:
        reasons.append("rank_mismatch")
    if result.get("matchType") not in {"exactMatch", "canonicalMatch"}:
        reasons.append("non_exact_match")
    issues = result.get("issues") or []
    if any(issue != "noIssue" for issue in issues):
        reasons.append("provider_issue")
    observed = {
        "kingdom": result.get("kingdom"),
        "phylum": result.get("phylum"),
        "class": result.get("classs"),
        "order": result.get("order"),
        "family": result.get("family"),
        "genus": result.get("genus"),
    }
    reasons.extend(classification_reasons(expected_classification(record), observed))
    identifier = result.get("taxonConceptID")
    if not isinstance(identifier, str) or not identifier:
        reasons.append("missing_identifier")
        identifier = None
    state = "matched" if not reasons else "conflict"
    return {
        "state": state,
        "query_name": query_name,
        "matched_name": result.get("scientificName"),
        "matched_rank": result.get("rank"),
        "provider_taxonomic_status": "not_supplied",
        "match_type": result.get("matchType"),
        "issues": issues,
        "reasons": reasons,
        "candidate_taxon_id": identifier,
        "source_response_sha256": response_hash,
    }, identifier if state == "matched" else None


def evaluate_gbif(record: dict[str, Any], result: Any, response_hash: str) -> tuple[dict[str, Any], int | None]:
    query_name = normalized_query_name(record)
    usage = result.get("usage", {}) if isinstance(result, dict) else {}
    diagnostics = result.get("diagnostics", {}) if isinstance(result, dict) else {}
    if not usage:
        return {
            "state": "unmatched",
            "query_name": query_name,
            "reasons": ["provider_no_match"],
            "source_response_sha256": response_hash,
        }, None
    reasons: list[str] = []
    if comparable_name(usage.get("canonicalName")) != comparable_name(query_name):
        reasons.append("name_mismatch")
    if (usage.get("rank") or "").casefold() != record["rank"]:
        reasons.append("rank_mismatch")
    if diagnostics.get("matchType") != "EXACT":
        reasons.append("non_exact_match")
    if usage.get("status") != "ACCEPTED" or result.get("synonym") is True:
        reasons.append("non_accepted_usage")
    classification = {
        (item.get("rank") or "").casefold(): item.get("name")
        for item in result.get("classification", [])
        if isinstance(item, dict)
    }
    reasons.extend(
        classification_reasons(expected_classification(record), classification)
    )
    raw_key = usage.get("key")
    identifier = (
        raw_key
        if isinstance(raw_key, int)
        else int(raw_key)
        if isinstance(raw_key, str) and raw_key.isdigit()
        else None
    )
    if identifier is None:
        reasons.append("missing_or_non_numeric_identifier")
    state = "matched" if not reasons else "conflict"
    return {
        "state": state,
        "query_name": query_name,
        "matched_name": usage.get("canonicalName"),
        "matched_rank": (usage.get("rank") or "").casefold() or None,
        "provider_taxonomic_status": usage.get("status"),
        "match_type": diagnostics.get("matchType"),
        "confidence": diagnostics.get("confidence"),
        "reasons": reasons,
        "candidate_taxon_key": identifier,
        "source_response_sha256": response_hash,
    }, identifier if state == "matched" else None


def evaluate_inaturalist(record: dict[str, Any], entry: dict[str, Any], source_hash: str) -> tuple[dict[str, Any], int | None]:
    query_name = normalized_query_name(record)
    expected = expected_classification(record)
    candidates = entry.get("candidates", [])
    compatible: list[dict[str, Any]] = []
    candidate_reasons: list[list[str]] = []
    for candidate in candidates:
        observed = {
            "kingdom": candidate.get("kingdom"),
            "phylum": candidate.get("phylum"),
            "class": candidate.get("class"),
            "order": candidate.get("order"),
            "family": candidate.get("family"),
            "genus": candidate.get("genus"),
        }
        reasons = classification_reasons(expected, observed)
        candidate_reasons.append(reasons)
        if not reasons:
            compatible.append(candidate)
    reasons: list[str] = []
    selected: dict[str, Any] | None = None
    if not candidates:
        reasons.append("provider_no_match")
    elif not compatible:
        reasons.append("classification_mismatch")
    elif len(compatible) > 1:
        reasons.append("ambiguous_multiple_matches")
    else:
        selected = compatible[0]
    identifier: int | None = None
    if selected:
        raw_identifier = selected.get("id")
        if isinstance(raw_identifier, str) and raw_identifier.isdigit():
            identifier = int(raw_identifier)
        else:
            reasons.append("missing_or_non_numeric_identifier")
    state = "matched" if not reasons else ("unmatched" if not candidates else "conflict")
    return {
        "state": state,
        "query_name": query_name,
        "matched_name": selected.get("scientificName") if selected else None,
        "matched_rank": selected.get("taxonRank") if selected else None,
        "provider_taxonomic_status": "current_snapshot_member" if selected else None,
        "candidate_count": len(candidates),
        "candidate_classification_reasons": candidate_reasons,
        "reasons": reasons,
        "candidate_taxon_id": identifier,
        "source_response_sha256": source_hash,
    }, identifier if state == "matched" else None


def load_source(path: Path, taxa_sha256: str, provider: str) -> dict[str, Any]:
    source = json.loads(path.read_text(encoding="utf-8"))
    if source.get("schema_version") != SOURCE_SCHEMA_VERSION:
        raise CrosswalkError(f"unsupported {provider} source snapshot schema")
    if source.get("provider") != provider:
        raise CrosswalkError(f"unexpected provider in {path}")
    if source.get("input_taxa_sha256") != taxa_sha256:
        raise CrosswalkError(f"{provider} source snapshot targets different taxa")
    return source


def indexed_ala(source: dict[str, Any]) -> dict[str, tuple[Any, str]]:
    index: dict[str, tuple[Any, str]] = {}
    for batch in source.get("batches", []):
        keys = batch.get("butterflylens_keys", [])
        responses = batch.get("response", [])
        if len(keys) != len(responses):
            raise CrosswalkError("ALA source batch length mismatch")
        for key, response in zip(keys, responses, strict=True):
            if key in index:
                raise CrosswalkError(f"duplicate ALA source match for {key}")
            index[key] = (response, batch["response_sha256"])
    return index


def indexed_entries(source: dict[str, Any], provider: str) -> dict[str, dict[str, Any]]:
    entries = source.get("entries", [])
    index = {entry.get("butterflylens_key"): entry for entry in entries}
    if len(index) != len(entries) or None in index:
        raise CrosswalkError(f"duplicate or missing {provider} source keys")
    return index


def build_crosswalk(
    taxa_path: Path,
    ala_path: Path,
    gbif_path: Path,
    inat_path: Path,
    output_dir: Path,
    generated_at: str | None,
) -> None:
    records = load_taxa(taxa_path)
    taxa_sha = sha256_file(taxa_path)
    ala_source = load_source(ala_path, taxa_sha, "Atlas of Living Australia")
    gbif_source = load_source(gbif_path, taxa_sha, "GBIF")
    inat_source = load_source(inat_path, taxa_sha, "iNaturalist")
    ala_index = indexed_ala(ala_source)
    gbif_index = indexed_entries(gbif_source, "GBIF")
    inat_index = indexed_entries(inat_source, "iNaturalist")
    expected_keys = {record["butterflylens_key"] for record in records}
    for provider, index in (
        ("ALA", ala_index),
        ("GBIF", gbif_index),
        ("iNaturalist", inat_index),
    ):
        if set(index) != expected_keys:
            raise CrosswalkError(f"{provider} source coverage does not match taxa")
    source_hashes = {
        "ala": sha256_file(ala_path),
        "gbif": sha256_file(gbif_path),
        "inaturalist": sha256_file(inat_path),
    }
    crosswalk: list[dict[str, Any]] = []
    state_counts: Counter[str] = Counter()
    provider_state_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        key = record["butterflylens_key"]
        ala_result, ala_response_hash = ala_index[key]
        ala_match, ala_id = evaluate_ala(record, ala_result, ala_response_hash)
        gbif_entry = gbif_index[key]
        gbif_match, gbif_id = evaluate_gbif(
            record, gbif_entry["response"], gbif_entry["response_sha256"]
        )
        inat_entry = inat_index[key]
        inat_match, inat_id = evaluate_inaturalist(
            record, inat_entry, source_hashes["inaturalist"]
        )
        matches = {
            "ala": ala_match,
            "gbif": gbif_match,
            "inaturalist": inat_match,
        }
        matched_count = sum(match["state"] == "matched" for match in matches.values())
        status = "complete" if matched_count == 3 else ("partial" if matched_count else "unresolved")
        state_counts[status] += 1
        for provider, match in matches.items():
            provider_state_counts[provider][match["state"]] += 1
        query_name = normalized_query_name(record)
        crosswalk.append(
            {
                "schema_version": CROSSWALK_SCHEMA_VERSION,
                "butterflylens_key": key,
                "accepted_scientific_name": record["accepted_scientific_name"],
                "parent_path": record["parent_path"],
                "rank": record["rank"],
                "taxonomic_status": record["taxonomic_status"],
                "provider_query_name": query_name,
                "query_name_normalization": (
                    "parenthesized_subgenus_removed"
                    if query_name != record["accepted_scientific_name"]
                    else "none"
                ),
                "ala_taxon_id": ala_id,
                "gbif_taxon_key": gbif_id,
                "inaturalist_taxon_id": inat_id,
                "crosswalk_status": status,
                "provider_matches": matches,
                "source_versions": {
                    "ala": "sha256:" + source_hashes["ala"],
                    "gbif": "sha256:" + source_hashes["gbif"],
                    "inaturalist": "sha256:" + source_hashes["inaturalist"],
                },
            }
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    crosswalk_path = output_dir / "crosswalk.jsonl"
    crosswalk_path.write_bytes(b"".join(canonical_json(record) for record in crosswalk))
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    provider_sources = []
    for provider, path, source in (
        ("Atlas of Living Australia", ala_path, ala_source),
        ("GBIF", gbif_path, gbif_source),
        ("iNaturalist", inat_path, inat_source),
    ):
        relative = path.relative_to(output_dir).as_posix()
        provider_sources.append(
            {
                "path": relative,
                "provider": provider,
                "physical_sha256": sha256_file(path),
                "retrieved_at": source["retrieved_at"],
            }
        )
    provider_paths = {source["path"] for source in provider_sources}
    manifest["sources"] = [
        source
        for source in manifest.get("sources", [])
        if source.get("path") not in provider_paths
    ] + provider_sources
    manifest["artifacts"]["crosswalk.jsonl"] = {
        "schema_version": CROSSWALK_SCHEMA_VERSION,
        "physical_sha256": sha256_file(crosswalk_path),
        "row_count": len(crosswalk),
        "status_counts": dict(sorted(state_counts.items())),
        "provider_state_counts": {
            provider: dict(sorted(counts.items()))
            for provider, counts in sorted(provider_state_counts.items())
        },
    }
    manifest["crosswalk_state"] = {
        "status": "built",
        "generated_at": generated_at or utc_now(),
        "status_counts": dict(sorted(state_counts.items())),
    }
    manifest_path.write_bytes(canonical_json(manifest))


def conflict_type(match: dict[str, Any]) -> str:
    reasons = set(match.get("reasons", []))
    if "ambiguous_multiple_matches" in reasons:
        return "ambiguous_provider_concept"
    if reasons & {
        "name_mismatch",
        "rank_mismatch",
        "family_mismatch",
        "genus_mismatch",
        "classification_mismatch",
    }:
        return "incompatible_provider_concept"
    if "non_accepted_usage" in reasons:
        return "provider_status_conflict"
    if "non_exact_match" in reasons:
        return "non_exact_provider_match"
    if "provider_issue" in reasons:
        return "provider_reported_issue"
    if reasons & {
        "provider_no_match",
        "missing_identifier",
        "missing_or_non_numeric_identifier",
    }:
        return "missing_provider_concept"
    return "unclassified_provider_conflict"


def conflict_identifier(
    crosswalk: dict[str, Any], provider: str, match: dict[str, Any]
) -> str:
    identity = {
        "butterflylens_key": crosswalk["butterflylens_key"],
        "provider": provider,
        "provider_source_version": crosswalk["source_versions"][provider],
        "state": match["state"],
        "reasons": sorted(match.get("reasons", [])),
        "candidate_identifier": match.get("candidate_taxon_id")
        or match.get("candidate_taxon_key"),
    }
    return "bltc:v1:" + sha256_bytes(canonical_json(identity))[:24]


def build_conflicts(
    crosswalk_path: Path,
    output_dir: Path,
    generated_at: str | None,
) -> None:
    crosswalk = [
        json.loads(line)
        for line in crosswalk_path.read_text(encoding="utf-8").splitlines()
    ]
    if not crosswalk:
        raise CrosswalkError("crosswalk is empty")
    conflicts: list[dict[str, Any]] = []
    provider_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    for row in crosswalk:
        if row.get("schema_version") != CROSSWALK_SCHEMA_VERSION:
            raise CrosswalkError("unsupported crosswalk schema")
        for provider in ("ala", "gbif", "inaturalist"):
            match = row["provider_matches"][provider]
            if match["state"] == "matched":
                continue
            reasons = match.get("reasons", [])
            if not reasons:
                raise CrosswalkError(
                    f"non-matched provider relationship has no reasons: "
                    f"{row['butterflylens_key']} {provider}"
                )
            kind = conflict_type(match)
            provider_counts[provider] += 1
            type_counts[kind] += 1
            conflicts.append(
                {
                    "schema_version": CONFLICT_SCHEMA_VERSION,
                    "conflict_id": conflict_identifier(row, provider, match),
                    "butterflylens_key": row["butterflylens_key"],
                    "accepted_scientific_name": row["accepted_scientific_name"],
                    "rank": row["rank"],
                    "parent_path": row["parent_path"],
                    "provider": provider,
                    "provider_relationship_state": match["state"],
                    "conflict_type": kind,
                    "reasons": reasons,
                    "provider_query_name": match["query_name"],
                    "provider_candidate": {
                        "identifier": match.get("candidate_taxon_id")
                        or match.get("candidate_taxon_key"),
                        "name": match.get("matched_name"),
                        "rank": match.get("matched_rank"),
                        "taxonomic_status": match.get("provider_taxonomic_status"),
                        "match_type": match.get("match_type"),
                        "confidence": match.get("confidence"),
                        "issues": match.get("issues", []),
                        "candidate_count": match.get("candidate_count"),
                    },
                    "provider_identifier_withheld": True,
                    "concept_equivalence": "not_established",
                    "resolution": {
                        "status": "open",
                        "automatic_resolution_permitted": False,
                        "resolution_type": None,
                        "decided_by": None,
                        "evidence_fingerprints": [],
                    },
                    "source": {
                        "crosswalk_sha256": sha256_file(crosswalk_path),
                        "provider_source_version": row["source_versions"][provider],
                        "provider_response_sha256": match[
                            "source_response_sha256"
                        ],
                    },
                }
            )
    conflict_ids = [conflict["conflict_id"] for conflict in conflicts]
    if len(conflict_ids) != len(set(conflict_ids)):
        raise CrosswalkError("conflict IDs are not unique")
    output_dir.mkdir(parents=True, exist_ok=True)
    conflicts_path = output_dir / "conflicts.jsonl"
    conflicts_path.write_bytes(
        b"".join(canonical_json(conflict) for conflict in conflicts)
    )
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"]["conflicts.jsonl"] = {
        "schema_version": CONFLICT_SCHEMA_VERSION,
        "physical_sha256": sha256_file(conflicts_path),
        "row_count": len(conflicts),
        "open_count": len(conflicts),
        "provider_counts": dict(sorted(provider_counts.items())),
        "type_counts": dict(sorted(type_counts.items())),
    }
    manifest["conflict_state"] = {
        "status": "built",
        "generated_at": generated_at or utc_now(),
        "open_count": len(conflicts),
        "automatic_resolutions": 0,
    }
    manifest_path.write_bytes(canonical_json(manifest))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    ala = commands.add_parser("acquire-ala")
    ala.add_argument("--taxa", type=Path, required=True)
    ala.add_argument("--output", type=Path, required=True)
    ala.add_argument("--batch-size", type=int, default=250)
    gbif = commands.add_parser("acquire-gbif")
    gbif.add_argument("--taxa", type=Path, required=True)
    gbif.add_argument("--output", type=Path, required=True)
    gbif.add_argument("--delay-seconds", type=float, default=0.15)
    gbif.add_argument("--workers", type=int, default=4)
    inat = commands.add_parser("acquire-inaturalist")
    inat.add_argument("--taxa", type=Path, required=True)
    inat.add_argument("--archive", type=Path, required=True)
    inat.add_argument("--output", type=Path, required=True)
    build = commands.add_parser("build-crosswalk")
    build.add_argument("--taxa", type=Path, required=True)
    build.add_argument("--ala", type=Path, required=True)
    build.add_argument("--gbif", type=Path, required=True)
    build.add_argument("--inaturalist", type=Path, required=True)
    build.add_argument("--output-dir", type=Path, required=True)
    build.add_argument("--generated-at")
    conflicts = commands.add_parser("build-conflicts")
    conflicts.add_argument("--crosswalk", type=Path, required=True)
    conflicts.add_argument("--output-dir", type=Path, required=True)
    conflicts.add_argument("--generated-at")
    return root


def main() -> None:
    arguments = parser().parse_args()
    if arguments.command == "acquire-ala":
        acquire_ala(arguments.taxa, arguments.output, arguments.batch_size)
    elif arguments.command == "acquire-gbif":
        acquire_gbif(
            arguments.taxa,
            arguments.output,
            arguments.delay_seconds,
            arguments.workers,
        )
    elif arguments.command == "acquire-inaturalist":
        acquire_inaturalist(arguments.taxa, arguments.archive, arguments.output)
    elif arguments.command == "build-crosswalk":
        build_crosswalk(
            arguments.taxa,
            arguments.ala,
            arguments.gbif,
            arguments.inaturalist,
            arguments.output_dir,
            arguments.generated_at,
        )
    elif arguments.command == "build-conflicts":
        build_conflicts(
            arguments.crosswalk,
            arguments.output_dir,
            arguments.generated_at,
        )
    else:
        raise AssertionError("unreachable")


if __name__ == "__main__":
    try:
        main()
    except (CrosswalkError, OSError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        raise SystemExit(f"taxonomy crosswalk: FAIL: {error}") from error
