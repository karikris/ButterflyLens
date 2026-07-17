"""Build authoritative query lanes without executing provider requests."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import re
from typing import Iterable, Mapping

from butterflylens.contracts.fingerprint import canonicalize_json

from .query_compiler import (
    QueryCompilationError,
    compile_global_out_of_range_assertion,
    compile_name_assertions,
)
from .query_plan import build_logical_query_association, plan_physical_query_requests


AUSTRALIA_KNOWN_LANE_SCHEMA_VERSION = "butterflylens-flickr-australia-known-lane:v1.0.0"
AUSTRALIA_KNOWN_LANE_ID = "australia_known"
GLOBAL_OUT_OF_RANGE_LANE_SCHEMA_VERSION = (
    "butterflylens-flickr-global-out-of-range-lane:v1.0.0"
)
GLOBAL_OUT_OF_RANGE_LANE_ID = "global_out_of_range"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SUPPORTED_RANKS = frozenset({"species", "genus", "family", "order", "superfamily"})
_RELATIONSHIP_BY_SPECIES_NAME_TYPE = {
    "accepted_scientific": "accepted_name",
    "scientific_synonym": "synonym",
    "english_vernacular": "english_vernacular",
    "trusted_vernacular": "trusted_vernacular",
    "first_nations_language": "authorized_first_nations_name",
}


class QueryLaneError(ValueError):
    """Raised when a lane cannot be derived truthfully from its source pack."""


def build_australia_known_lane(
    taxa: Iterable[Mapping[str, object]],
    name_assertions: Iterable[Mapping[str, object]],
    *,
    source_pack_id: str,
    source_taxa_sha256: str,
    source_name_assertions_sha256: str,
) -> dict[str, object]:
    """Expand eligible Australian taxon terms to explicit species associations."""

    if not source_pack_id or not isinstance(source_pack_id, str):
        raise QueryLaneError("source_pack_id is required")
    for value in (source_taxa_sha256, source_name_assertions_sha256):
        if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
            raise QueryLaneError("source artifact checksums must be lowercase SHA-256")

    copied_taxa = [deepcopy(dict(taxon)) for taxon in taxa]
    taxa_by_key = _validate_taxa(copied_taxa)
    species = {
        key: taxon for key, taxon in taxa_by_key.items() if taxon["rank"] == "species"
    }
    if not species:
        raise QueryLaneError("authoritative pack contains no accepted species")

    eligible_assertions: list[Mapping[str, object]] = []
    for assertion in name_assertions:
        rank = assertion.get("taxon_rank")
        eligibility = assertion.get("query_eligibility")
        if rank not in _SUPPORTED_RANKS:
            continue
        if not isinstance(eligibility, dict) or eligibility.get("eligible") is not True:
            continue
        taxon_key = assertion.get("butterflylens_key")
        taxon = taxa_by_key.get(taxon_key) if isinstance(taxon_key, str) else None
        if taxon is None or taxon["rank"] != rank:
            raise QueryLaneError("eligible assertion does not resolve to its declared taxon")
        eligible_assertions.append(assertion)
    try:
        definitions = compile_name_assertions(eligible_assertions)
    except QueryCompilationError as error:
        raise QueryLaneError(f"authoritative assertion failed compilation: {error}") from error

    species_ancestors = {
        key: {
            ancestor["butterflylens_key"]
            for ancestor in taxon["parent_path"]
            if isinstance(ancestor, dict) and isinstance(ancestor.get("butterflylens_key"), str)
        }
        for key, taxon in species.items()
    }
    associations: list[dict[str, object]] = []
    for definition in definitions:
        source_taxon_key = str(definition["source_taxon_key"])
        rank = str(definition["taxon_rank"])
        targets = _species_targets(
            source_taxon_key=source_taxon_key,
            rank=rank,
            species=species,
            species_ancestors=species_ancestors,
        )
        relationship = _relationship(definition)
        for target_key in targets:
            associations.append(
                build_logical_query_association(
                    definition,
                    associated_taxon_key=target_key,
                    relationship=relationship,
                    query_lane=AUSTRALIA_KNOWN_LANE_ID,
                    association_reason=(
                        f"eligible {rank} assertion linked through the authoritative "
                        "Australian taxon hierarchy"
                    ),
                )
            )

    plan = plan_physical_query_requests(
        definitions,
        associations,
        fixed_parameters={"content_type": 1, "media": "photos", "safe_search": 1},
    )
    tier_definition_counts = _tier_counts(definitions)
    tier_association_counts = _tier_counts(plan["logical_associations"])
    lane_preimage = {
        "lane_id": AUSTRALIA_KNOWN_LANE_ID,
        "source_pack_id": source_pack_id,
        "source_taxa_sha256": source_taxa_sha256,
        "source_name_assertions_sha256": source_name_assertions_sha256,
        "definition_fingerprints": sorted(
            str(row["compiler_fingerprint"]) for row in definitions
        ),
        "association_fingerprints": sorted(
            str(row["association_fingerprint"])
            for row in plan["logical_associations"]
        ),
        "request_fingerprints": sorted(
            str(row["request_fingerprint"]) for row in plan["physical_requests"]
        ),
    }
    lane_fingerprint = hashlib.sha256(canonicalize_json(lane_preimage)).hexdigest()
    return {
        "schema_version": AUSTRALIA_KNOWN_LANE_SCHEMA_VERSION,
        "lane_id": AUSTRALIA_KNOWN_LANE_ID,
        "source_pack": {
            "pack_id": source_pack_id,
            "taxa_sha256": source_taxa_sha256,
            "name_assertions_sha256": source_name_assertions_sha256,
        },
        "scope": {
            "region_code": "AU",
            "meaning": "taxa_authoritatively_known_from_australia",
            "photo_location_filter_implied": False,
            "absence_inference_permitted": False,
        },
        "execution_state": "planned_not_sent",
        "counts": {
            "accepted_species": len(species),
            "query_definitions": len(definitions),
            "logical_associations": len(plan["logical_associations"]),
            "physical_requests": len(plan["physical_requests"]),
            "request_links": len(plan["request_links"]),
            "definitions_by_tier": tier_definition_counts,
            "associations_by_tier": tier_association_counts,
        },
        "query_definitions": definitions,
        **plan,
        "lane_fingerprint": lane_fingerprint,
    }


def build_global_out_of_range_lane(
    global_name_assertions: Iterable[Mapping[str, object]],
    australia_name_assertions: Iterable[Mapping[str, object]],
    *,
    source_snapshot_id: str,
    source_snapshot_sha256: str,
    australia_pack_id: str,
    australia_taxa_sha256: str,
) -> dict[str, object]:
    """Build tier 5 only from admitted checklist-complement species assertions."""

    if not all(
        isinstance(value, str) and value
        for value in (source_snapshot_id, australia_pack_id)
    ):
        raise QueryLaneError("global source and Australian comparison IDs are required")
    for value in (source_snapshot_sha256, australia_taxa_sha256):
        if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
            raise QueryLaneError("lane source checksums must be lowercase SHA-256")

    known_australian_scientific_names = {
        str(assertion["normalized_name"])
        for assertion in australia_name_assertions
        if assertion.get("taxon_rank") == "species"
        and assertion.get("name_type") in {"accepted_scientific", "scientific_synonym"}
    }
    definitions: list[dict[str, object]] = []
    for assertion in global_name_assertions:
        eligibility = assertion.get("query_eligibility")
        scope = assertion.get("australia_scope")
        if not isinstance(eligibility, dict) or eligibility.get("eligible") is not True:
            continue
        if not isinstance(scope, dict) or scope.get("status") != "not_currently_known":
            continue
        normalized_name = assertion.get("normalized_name")
        if normalized_name in known_australian_scientific_names:
            raise QueryLaneError(
                "claimed out-of-range species collides with an Australian scientific name"
            )
        if scope.get("comparison_pack_id") != australia_pack_id:
            raise QueryLaneError("global assertion compares against the wrong Australian pack")
        if scope.get("comparison_taxa_sha256") != australia_taxa_sha256:
            raise QueryLaneError("global assertion comparison checksum is stale")
        try:
            definitions.append(compile_global_out_of_range_assertion(assertion))
        except QueryCompilationError as error:
            raise QueryLaneError(f"global assertion failed compilation: {error}") from error
    definitions.sort(
        key=lambda row: (
            str(row["normalized_query_text"]),
            str(row["source_taxon_key"]),
            str(row["source_assertion_id"]),
        )
    )
    if len({row["query_definition_id"] for row in definitions}) != len(definitions):
        raise QueryLaneError("global query definition ID collision")

    associations = [
        build_logical_query_association(
            definition,
            associated_taxon_key=str(definition["source_taxon_key"]),
            relationship="global_out_of_range",
            query_lane=GLOBAL_OUT_OF_RANGE_LANE_ID,
            association_reason=(
                "accepted global species is outside the current authoritative "
                "Australian checklist comparison"
            ),
        )
        for definition in definitions
    ]
    plan = plan_physical_query_requests(
        definitions,
        associations,
        fixed_parameters={"content_type": 1, "media": "photos", "safe_search": 1},
    )
    lane_preimage = {
        "lane_id": GLOBAL_OUT_OF_RANGE_LANE_ID,
        "source_snapshot_id": source_snapshot_id,
        "source_snapshot_sha256": source_snapshot_sha256,
        "australia_pack_id": australia_pack_id,
        "australia_taxa_sha256": australia_taxa_sha256,
        "definition_fingerprints": [
            str(row["compiler_fingerprint"]) for row in definitions
        ],
        "association_fingerprints": sorted(
            str(row["association_fingerprint"])
            for row in plan["logical_associations"]
        ),
        "request_fingerprints": sorted(
            str(row["request_fingerprint"]) for row in plan["physical_requests"]
        ),
    }
    lane_fingerprint = hashlib.sha256(canonicalize_json(lane_preimage)).hexdigest()
    return {
        "schema_version": GLOBAL_OUT_OF_RANGE_LANE_SCHEMA_VERSION,
        "lane_id": GLOBAL_OUT_OF_RANGE_LANE_ID,
        "source_snapshot": {
            "snapshot_id": source_snapshot_id,
            "snapshot_sha256": source_snapshot_sha256,
        },
        "australia_comparison": {
            "pack_id": australia_pack_id,
            "taxa_sha256": australia_taxa_sha256,
        },
        "scope": {
            "meaning": "species_not_in_current_authoritative_australian_checklist",
            "biological_absence_claimed": False,
            "photo_location_filter_implied": False,
        },
        "execution_state": "planned_not_sent",
        "counts": {
            "query_definitions": len(definitions),
            "logical_associations": len(plan["logical_associations"]),
            "physical_requests": len(plan["physical_requests"]),
            "request_links": len(plan["request_links"]),
            "definitions_by_tier": _tier_counts(definitions),
        },
        "query_definitions": tuple(definitions),
        **plan,
        "lane_fingerprint": lane_fingerprint,
    }


def _validate_taxa(taxa: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    taxa_by_key: dict[str, dict[str, object]] = {}
    for taxon in taxa:
        key = taxon.get("butterflylens_key")
        if not isinstance(key, str) or key in taxa_by_key:
            raise QueryLaneError("taxon keys must be present and unique")
        if taxon.get("taxonomic_status") != "accepted":
            raise QueryLaneError("Australia-known lane accepts only authoritative taxa")
        if not isinstance(taxon.get("parent_path"), list):
            raise QueryLaneError("taxon parent_path must be an array")
        taxa_by_key[key] = taxon
    for taxon in taxa:
        parent_key = taxon.get("parent_key")
        if parent_key is not None and parent_key not in taxa_by_key:
            raise QueryLaneError("taxon parent is absent from the authoritative pack")
        for ancestor in taxon["parent_path"]:
            if (
                not isinstance(ancestor, dict)
                or ancestor.get("butterflylens_key") not in taxa_by_key
            ):
                raise QueryLaneError("taxon ancestor is absent from the authoritative pack")
    return taxa_by_key


def _species_targets(
    *,
    source_taxon_key: str,
    rank: str,
    species: Mapping[str, Mapping[str, object]],
    species_ancestors: Mapping[str, set[str]],
) -> tuple[str, ...]:
    if rank == "species":
        if source_taxon_key not in species:
            raise QueryLaneError("species definition does not target an accepted species")
        return (source_taxon_key,)
    targets = tuple(
        sorted(
            species_key
            for species_key in species
            if source_taxon_key in species_ancestors[species_key]
        )
    )
    if not targets:
        raise QueryLaneError("broader query definition has no accepted species descendants")
    return targets


def _relationship(definition: Mapping[str, object]) -> str:
    rank = definition["taxon_rank"]
    if rank == "species":
        try:
            return _RELATIONSHIP_BY_SPECIES_NAME_TYPE[str(definition["name_type"])]
        except KeyError as error:
            raise QueryLaneError("species name type has no logical relationship") from error
    if rank in {"genus", "family", "order"}:
        return str(rank)
    if rank == "superfamily":
        return "broad_butterfly"
    raise QueryLaneError("query rank has no logical relationship")


def _tier_counts(rows: Iterable[Mapping[str, object]]) -> dict[str, int]:
    counts = {str(tier): 0 for tier in range(1, 6)}
    for row in rows:
        counts[str(row["tier"])] += 1
    return counts
