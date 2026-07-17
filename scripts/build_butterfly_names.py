#!/usr/bin/env python3
"""Acquire and build provenance-rich name assertions for the butterfly pack.

Live acquisition is explicit. Default tests and pack builds consume only the
frozen ALA profile receipt checked into the pack.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from build_butterfly_taxonomy import canonical_json, sha256_file, utc_now


PROFILE_SCHEMA_VERSION = "butterflylens-ala-species-profiles/v1"
NAME_SCHEMA_VERSION = "butterflylens-name-assertion/v1"
ALA_SPECIES_ENDPOINT = "https://api.ala.org.au/species/species/"
ALA_OPENAPI_URL = "https://docs.ala.org.au/openapi/specs/bie-index.json"
USER_AGENT = (
    "ButterflyLens/0.1 (+https://github.com/karikris/ButterflyLens; "
    "public taxonomy-pack acquisition)"
)


class NamePackError(RuntimeError):
    """Raised when a frozen name source or derived assertion is invalid."""


def sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def normalized_name(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def selected_profile(payload: dict[str, Any]) -> dict[str, Any]:
    """Retain name evidence while excluding provider media payloads."""

    return {
        "taxonConcept": payload.get("taxonConcept"),
        "taxonName": payload.get("taxonName", []),
        "classification": payload.get("classification"),
        "synonyms": payload.get("synonyms", []),
        "commonNameSingle": payload.get("commonNameSingle"),
        "commonNames": payload.get("commonNames", []),
        "variants": payload.get("variants", []),
        "linkIdentifier": payload.get("linkIdentifier"),
    }


def fetch_json(url: str, attempts: int = 4) -> tuple[bytes, dict[str, str | None]]:
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=60) as response:
                body = response.read()
                return body, {
                    "content_type": response.headers.get("Content-Type"),
                    "etag": response.headers.get("ETag"),
                    "last_modified": response.headers.get("Last-Modified"),
                }
        except HTTPError as error:
            last_error = error
            if error.code not in {429, 500, 502, 503, 504}:
                break
        except (TimeoutError, URLError) as error:
            last_error = error
        if attempt + 1 < attempts:
            time.sleep(2**attempt)
    raise NamePackError(f"unable to retrieve {url}: {last_error}")


def acquire_profile(item: tuple[int, dict[str, Any]]) -> tuple[int, dict[str, Any]]:
    index, row = item
    identifier = row["ala_taxon_id"]
    request_url = ALA_SPECIES_ENDPOINT + quote(identifier, safe="")
    body, headers = fetch_json(request_url)
    payload = json.loads(body)
    concept = payload.get("taxonConcept") or {}
    if concept.get("guid") != identifier:
        raise NamePackError(
            f"ALA profile identifier mismatch for {row['butterflylens_key']}"
        )
    return index, {
        "butterflylens_key": row["butterflylens_key"],
        "ala_taxon_id": identifier,
        "request_url": request_url,
        "response_sha256": sha256_bytes(body),
        "headers": headers,
        "profile": selected_profile(payload),
    }


def acquire_ala_profiles(
    crosswalk_path: Path,
    output_path: Path,
    workers: int,
    retrieved_at: str | None,
) -> None:
    if workers < 1 or workers > 4:
        raise NamePackError("workers must be between 1 and 4")
    rows = [
        json.loads(line)
        for line in crosswalk_path.read_text(encoding="utf-8").splitlines()
    ]
    eligible = [(index, row) for index, row in enumerate(rows) if row.get("ala_taxon_id")]
    openapi_body, openapi_headers = fetch_json(ALA_OPENAPI_URL)
    results: dict[int, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(acquire_profile, item): item[0] for item in eligible}
        for future in as_completed(futures):
            index, profile = future.result()
            results[index] = profile
    profiles = [results[index] for index, _ in eligible]
    snapshot = {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "provider": "Atlas of Living Australia",
        "retrieved_at": retrieved_at or utc_now(),
        "input_crosswalk_sha256": sha256_file(crosswalk_path),
        "source": {
            "endpoint": ALA_SPECIES_ENDPOINT + "{url_encoded_taxon_guid}",
            "openapi_url": ALA_OPENAPI_URL,
            "openapi_sha256": sha256_bytes(openapi_body),
            "openapi_headers": openapi_headers,
            "terms_url": "https://www.ala.org.au/terms-of-use/",
            "source_authority": "Australian Faunal Directory via ALA species index",
        },
        "request_policy": {
            "maximum_workers": workers,
            "retryable_http_statuses": [429, 500, 502, 503, 504],
            "attempts": 4,
            "user_agent": USER_AGENT,
        },
        "profile_count": len(profiles),
        "profiles": profiles,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_json(snapshot))


def assertion_identifier(assertion: dict[str, Any]) -> str:
    identity = {
        "butterflylens_key": assertion["butterflylens_key"],
        "name": assertion["name"],
        "name_type": assertion["name_type"],
        "language_code": assertion["language"]["code"],
        "region_code": assertion["region"]["code"],
        "source_version": assertion["source"]["source_version"],
        "source_response_sha256": assertion["source"].get(
            "source_response_sha256"
        ),
        "provider_name_id": assertion.get("provider_name_id"),
    }
    return "blna:v1:" + sha256_bytes(canonical_json(identity))[:24]


def source_for_accepted(taxon: dict[str, Any]) -> dict[str, Any]:
    source = taxon["source"]
    return {
        "provider": source["provider"],
        "dataset": "Australian Faunal Directory",
        "source_url": source["source_url"],
        "source_version": source["source_version"],
        "source_response_sha256": None,
        "retrieved_at": source["retrieved_at"],
    }


def source_for_profile_name(
    snapshot: dict[str, Any],
    snapshot_sha256: str,
    profile: dict[str, Any],
    name: dict[str, Any],
) -> dict[str, Any]:
    return {
        "provider": "Atlas of Living Australia",
        "dataset": name.get("infoSourceName") or "ALA species index",
        "source_url": name.get("infoSourceURL") or profile["request_url"],
        "source_version": "sha256:" + snapshot_sha256,
        "source_response_sha256": profile["response_sha256"],
        "retrieved_at": snapshot["retrieved_at"],
    }
def base_assertion(
    taxon: dict[str, Any],
    name: str,
    name_type: str,
    source: dict[str, Any],
    trust_tier: str,
    provider_status: str | None,
    nomenclatural_status: str | None,
    provider_name_id: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": NAME_SCHEMA_VERSION,
        "assertion_id": None,
        "butterflylens_key": taxon["butterflylens_key"],
        "accepted_scientific_name": taxon["accepted_scientific_name"],
        "taxon_rank": taxon["rank"],
        "name": name,
        "normalized_name": normalized_name(name),
        "name_type": name_type,
        "language": {
            "code": "zxx",
            "label": "No linguistic content (scientific name)",
        },
        "region": {"code": "AU", "label": "Australia", "scope": "pack"},
        "source": source,
        "trust_tier": trust_tier,
        "query_eligibility": {"eligible": True, "reason": "pending_collision_check"},
        "homonym_risk": "pending_collision_check",
        "review_state": "source_assertion_unreviewed",
        "provider_status": provider_status,
        "nomenclatural_status": nomenclatural_status,
        "provider_name_id": provider_name_id,
        "retrieval_date": source["retrieved_at"][:10],
    }


def finalize_query_safety(assertions: list[dict[str, Any]]) -> None:
    keys_by_name: dict[str, set[str]] = defaultdict(set)
    for assertion in assertions:
        keys_by_name[assertion["normalized_name"]].add(assertion["butterflylens_key"])
    for assertion in assertions:
        collision = len(keys_by_name[assertion["normalized_name"]]) > 1
        if collision:
            risk = "cross_taxon_collision"
            eligible = False
            reason = "excluded_cross_taxon_collision"
        elif assertion["name_type"] == "english_vernacular":
            lexical_tokens = re.findall(r"[A-Za-z]+", assertion["name"])
            if len(lexical_tokens) < 2:
                risk = "single_token_vernacular"
                eligible = False
                reason = "excluded_single_token_vernacular"
            else:
                risk = "none_detected_in_pack"
                eligible = True
                reason = "trusted_english_name_unique_in_pack"
        else:
            risk = "none_detected_in_pack"
            eligible = True
            reason = "trusted_scientific_name_unique_in_pack"
        assertion["homonym_risk"] = risk
        assertion["query_eligibility"] = {"eligible": eligible, "reason": reason}
        assertion["assertion_id"] = assertion_identifier(assertion)


def validate_profile_snapshot(snapshot: dict[str, Any], crosswalk_sha: str) -> None:
    if snapshot.get("schema_version") != PROFILE_SCHEMA_VERSION:
        raise NamePackError("unsupported ALA species-profile snapshot")
    if snapshot.get("input_crosswalk_sha256") != crosswalk_sha:
        raise NamePackError("ALA species-profile snapshot targets another crosswalk")
    profiles = snapshot.get("profiles", [])
    if snapshot.get("profile_count") != len(profiles):
        raise NamePackError("ALA profile count does not match payload")
    keys = [profile.get("butterflylens_key") for profile in profiles]
    if len(keys) != len(set(keys)):
        raise NamePackError("ALA profile keys are not unique")


def build_scientific_names(
    taxa_path: Path,
    crosswalk_path: Path,
    profiles_path: Path,
    output_dir: Path,
    generated_at: str | None,
) -> None:
    taxa = [
        json.loads(line)
        for line in taxa_path.read_text(encoding="utf-8").splitlines()
    ]
    crosswalk_sha = sha256_file(crosswalk_path)
    snapshot = json.loads(profiles_path.read_text(encoding="utf-8"))
    validate_profile_snapshot(snapshot, crosswalk_sha)
    taxon_by_key = {taxon["butterflylens_key"]: taxon for taxon in taxa}
    taxon_order = {
        taxon["butterflylens_key"]: index for index, taxon in enumerate(taxa)
    }
    profile_snapshot_sha256 = sha256_file(profiles_path)
    assertions: list[dict[str, Any]] = []
    for taxon in taxa:
        assertions.append(
            base_assertion(
                taxon,
                taxon["accepted_scientific_name"],
                "accepted_scientific",
                source_for_accepted(taxon),
                "accepted_authority",
                taxon["taxonomic_status"],
                None,
                None,
            )
        )
    for profile in snapshot["profiles"]:
        taxon = taxon_by_key.get(profile["butterflylens_key"])
        if taxon is None:
            raise NamePackError("ALA profile references a taxon outside the pack")
        for synonym in profile["profile"].get("synonyms") or []:
            name = synonym.get("nameString") or synonym.get("scientificName")
            if not name or normalized_name(name) == normalized_name(
                taxon["accepted_scientific_name"]
            ):
                continue
            assertions.append(
                base_assertion(
                    taxon,
                    name,
                    "scientific_synonym",
                    source_for_profile_name(
                        snapshot, profile_snapshot_sha256, profile, synonym
                    ),
                    "provider_linked_synonym",
                    synonym.get("taxonomicStatus") or synonym.get("status"),
                    synonym.get("nomenclaturalStatus"),
                    synonym.get("nameGuid") or synonym.get("identifier"),
                )
            )
    assertions.sort(
        key=lambda assertion: (
            taxon_order[assertion["butterflylens_key"]],
            assertion["name_type"] != "accepted_scientific",
            assertion["normalized_name"],
        )
    )
    finalize_query_safety(assertions)
    identifiers = [assertion["assertion_id"] for assertion in assertions]
    if len(identifiers) != len(set(identifiers)):
        raise NamePackError("name assertion IDs are not unique")
    output_dir.mkdir(parents=True, exist_ok=True)
    assertions_path = output_dir / "name_assertions.jsonl"
    assertions_path.write_bytes(
        b"".join(canonical_json(assertion) for assertion in assertions)
    )
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    type_counts = Counter(assertion["name_type"] for assertion in assertions)
    eligible_count = sum(
        assertion["query_eligibility"]["eligible"] for assertion in assertions
    )
    manifest["artifacts"]["sources/ala_species_profiles.json"] = {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "physical_sha256": sha256_file(profiles_path),
        "row_count": snapshot["profile_count"],
    }
    manifest["artifacts"]["name_assertions.jsonl"] = {
        "schema_version": NAME_SCHEMA_VERSION,
        "physical_sha256": sha256_file(assertions_path),
        "row_count": len(assertions),
        "type_counts": dict(sorted(type_counts.items())),
        "query_eligible_count": eligible_count,
    }
    manifest["name_state"] = {
        "status": "partially_built",
        "generated_at": generated_at or utc_now(),
        "scientific_names": "built",
        "english_vernacular_names": "not_built",
        "first_nations_names": "not_built",
    }
    manifest_path.write_bytes(canonical_json(manifest))


def common_name_identifier(common_name: dict[str, Any]) -> str:
    identity = {
        "name": common_name.get("nameString"),
        "language": common_name.get("language"),
        "country_code": common_name.get("countryCode"),
        "locality": common_name.get("locality"),
        "source_name": common_name.get("infoSourceName"),
        "source_url": common_name.get("infoSourceURL"),
        "dataset_url": common_name.get("datasetURL"),
    }
    return "ala-common:v1:" + sha256_bytes(canonical_json(identity))[:24]


def vernacular_assertion(
    taxon: dict[str, Any],
    snapshot: dict[str, Any],
    snapshot_sha256: str,
    profile: dict[str, Any],
    common_name: dict[str, Any],
) -> dict[str, Any]:
    name = common_name.get("nameString")
    if not isinstance(name, str) or not name.strip():
        raise NamePackError("ALA common-name assertion has no name")
    if common_name.get("language") != "en":
        raise NamePackError("build-vernacular accepts only explicit English names")
    if common_name.get("countryCode") != "AU":
        raise NamePackError("build-vernacular accepts only Australia-scoped names")
    source_name = common_name.get("infoSourceName")
    if source_name == "AFD":
        trust_tier = "authority_vernacular"
    elif source_name == "ALA Preferred Vernacular Names":
        trust_tier = "provider_curated_vernacular"
    else:
        trust_tier = "provider_vernacular"
    source = source_for_profile_name(
        snapshot, snapshot_sha256, profile, common_name
    )
    return {
        "schema_version": NAME_SCHEMA_VERSION,
        "assertion_id": None,
        "butterflylens_key": taxon["butterflylens_key"],
        "accepted_scientific_name": taxon["accepted_scientific_name"],
        "taxon_rank": taxon["rank"],
        "name": name.strip(),
        "normalized_name": normalized_name(name),
        "name_type": "english_vernacular",
        "language": {"code": "en", "label": "English"},
        "region": {
            "code": common_name["countryCode"],
            "label": common_name.get("locality") or "Australia",
            "scope": "assertion",
        },
        "source": source,
        "trust_tier": trust_tier,
        "query_eligibility": {"eligible": False, "reason": "pending_collision_check"},
        "homonym_risk": "pending_collision_check",
        "review_state": "source_assertion_unreviewed",
        "provider_status": common_name.get("status"),
        "nomenclatural_status": None,
        "provider_name_id": common_name_identifier(common_name),
        "retrieval_date": snapshot["retrieved_at"][:10],
    }


def build_vernacular_names(
    taxa_path: Path,
    profiles_path: Path,
    assertions_path: Path,
    output_dir: Path,
    generated_at: str | None,
) -> None:
    taxa = [
        json.loads(line)
        for line in taxa_path.read_text(encoding="utf-8").splitlines()
    ]
    taxon_by_key = {taxon["butterflylens_key"]: taxon for taxon in taxa}
    taxon_order = {
        taxon["butterflylens_key"]: index for index, taxon in enumerate(taxa)
    }
    assertions = [
        json.loads(line)
        for line in assertions_path.read_text(encoding="utf-8").splitlines()
    ]
    assertions = [
        assertion
        for assertion in assertions
        if assertion.get("name_type")
        in {"accepted_scientific", "scientific_synonym"}
    ]
    snapshot = json.loads(profiles_path.read_text(encoding="utf-8"))
    snapshot_sha256 = sha256_file(profiles_path)
    for profile in snapshot["profiles"]:
        taxon = taxon_by_key.get(profile["butterflylens_key"])
        if taxon is None:
            raise NamePackError("ALA profile references a taxon outside the pack")
        for common_name in profile["profile"].get("commonNames") or []:
            assertions.append(
                vernacular_assertion(
                    taxon, snapshot, snapshot_sha256, profile, common_name
                )
            )
    type_order = {
        "accepted_scientific": 0,
        "scientific_synonym": 1,
        "english_vernacular": 2,
    }
    assertions.sort(
        key=lambda assertion: (
            taxon_order[assertion["butterflylens_key"]],
            type_order[assertion["name_type"]],
            assertion["normalized_name"],
            assertion.get("provider_name_id") or "",
        )
    )
    finalize_query_safety(assertions)
    identifiers = [assertion["assertion_id"] for assertion in assertions]
    if len(identifiers) != len(set(identifiers)):
        raise NamePackError("name assertion IDs are not unique")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "name_assertions.jsonl"
    output_path.write_bytes(
        b"".join(canonical_json(assertion) for assertion in assertions)
    )
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    type_counts = Counter(assertion["name_type"] for assertion in assertions)
    manifest["artifacts"]["name_assertions.jsonl"] = {
        "schema_version": NAME_SCHEMA_VERSION,
        "physical_sha256": sha256_file(output_path),
        "row_count": len(assertions),
        "type_counts": dict(sorted(type_counts.items())),
        "query_eligible_count": sum(
            assertion["query_eligibility"]["eligible"] for assertion in assertions
        ),
    }
    state = manifest["name_state"]
    state.update(
        {
            "status": "partially_built",
            "generated_at": generated_at or utc_now(),
            "scientific_names": "built",
            "english_vernacular_names": "built",
            "first_nations_names": "not_built",
        }
    )
    manifest_path.write_bytes(canonical_json(manifest))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    acquire = commands.add_parser("acquire-ala-profiles")
    acquire.add_argument("--crosswalk", type=Path, required=True)
    acquire.add_argument("--output", type=Path, required=True)
    acquire.add_argument("--workers", type=int, default=4)
    acquire.add_argument("--retrieved-at")
    scientific = commands.add_parser("build-scientific")
    scientific.add_argument("--taxa", type=Path, required=True)
    scientific.add_argument("--crosswalk", type=Path, required=True)
    scientific.add_argument("--profiles", type=Path, required=True)
    scientific.add_argument("--output-dir", type=Path, required=True)
    scientific.add_argument("--generated-at")
    vernacular = commands.add_parser("build-vernacular")
    vernacular.add_argument("--taxa", type=Path, required=True)
    vernacular.add_argument("--profiles", type=Path, required=True)
    vernacular.add_argument("--assertions", type=Path, required=True)
    vernacular.add_argument("--output-dir", type=Path, required=True)
    vernacular.add_argument("--generated-at")
    return root


def main() -> None:
    arguments = parser().parse_args()
    if arguments.command == "acquire-ala-profiles":
        acquire_ala_profiles(
            arguments.crosswalk,
            arguments.output,
            arguments.workers,
            arguments.retrieved_at,
        )
    elif arguments.command == "build-scientific":
        build_scientific_names(
            arguments.taxa,
            arguments.crosswalk,
            arguments.profiles,
            arguments.output_dir,
            arguments.generated_at,
        )
    elif arguments.command == "build-vernacular":
        build_vernacular_names(
            arguments.taxa,
            arguments.profiles,
            arguments.assertions,
            arguments.output_dir,
            arguments.generated_at,
        )
    else:
        raise AssertionError("unreachable")


if __name__ == "__main__":
    main()
