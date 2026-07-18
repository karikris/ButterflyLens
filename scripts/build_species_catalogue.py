#!/usr/bin/env python3
"""Build the public species catalogue from fingerprinted local evidence only."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACK = ROOT / "data/packs/australian_butterflies/v1"
DEFAULT_RIGHTS = ROOT / "provenance/data_rights_manifest.json"
DEFAULT_OUTPUT = ROOT / "apps/web/src/species/submittedSpeciesCatalogue.json"

CATALOGUE_SCHEMA_VERSION = "butterflylens-public-species-catalogue:v1.0.0"
TAXON_SCHEMA_VERSION = "butterflylens-taxonomy/v1"
SPECIES_KEY_PATTERN = re.compile(r"^bltx:v1:[0-9a-f]{24}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
UTC_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
PROVIDERS = (
    ("ala", "Atlas of Living Australia", "ala_taxon_id"),
    ("gbif", "GBIF", "gbif_taxon_key"),
    ("inaturalist", "iNaturalist", "inaturalist_taxon_id"),
)


class SpeciesCatalogueError(RuntimeError):
    """Raised when a public catalogue source fails closed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SpeciesCatalogueError(f"{path} must contain a JSON object")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        value = json.loads(line)
        if not isinstance(value, dict):
            raise SpeciesCatalogueError(f"{path}:{line_number} must contain an object")
        rows.append(value)
    return rows


def verified_artifact(pack: Path, manifest: dict[str, Any], name: str) -> Path:
    artifact = manifest.get("artifacts", {}).get(name)
    if not isinstance(artifact, dict):
        raise SpeciesCatalogueError(f"pack manifest is missing {name}")
    expected = artifact.get("physical_sha256")
    path = pack / name
    actual = sha256_file(path)
    if expected != actual:
        raise SpeciesCatalogueError(f"{name} checksum mismatch")
    return path


def require_public_rights(
    rights: dict[str, Any], relative_path: str, expected_sha256: str
) -> dict[str, Any]:
    artifact = next(
        (
            row
            for row in rights.get("artifacts", [])
            if isinstance(row, dict) and row.get("path") == relative_path
        ),
        None,
    )
    if artifact is None:
        raise SpeciesCatalogueError(f"rights record missing for {relative_path}")
    if artifact.get("display_allowed") is not True:
        raise SpeciesCatalogueError(f"public display is not allowed for {relative_path}")
    if artifact.get("redistribution_allowed") is not True:
        raise SpeciesCatalogueError(f"redistribution is not allowed for {relative_path}")
    if artifact.get("removal_state") != "active":
        raise SpeciesCatalogueError(f"rights record is not active for {relative_path}")
    if artifact.get("fingerprint") != f"sha256:{expected_sha256}":
        raise SpeciesCatalogueError(f"rights fingerprint mismatch for {relative_path}")
    return artifact


def public_source(
    rights: dict[str, Any], relative_path: str, physical_sha256: str
) -> dict[str, Any]:
    row = require_public_rights(rights, relative_path, physical_sha256)
    return {
        "path": relative_path,
        "physicalSha256": physical_sha256,
        "licence": row["licence"],
        "attribution": row["attribution"],
    }


def species_slug(scientific_name: str, key: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", scientific_name.casefold()).strip("-")
    return f"{base}-{key.rsplit(':', 1)[-1][:8]}"


def build_catalogue(
    *,
    pack: Path = DEFAULT_PACK,
    manifest_path: Path | None = None,
    rights_path: Path = DEFAULT_RIGHTS,
    generated_at: str,
) -> dict[str, Any]:
    if not UTC_PATTERN.fullmatch(generated_at):
        raise SpeciesCatalogueError("generated_at must be an RFC 3339 UTC second timestamp")

    manifest_path = manifest_path or pack / "manifest.json"
    manifest = load_json(manifest_path)
    rights = load_json(rights_path)
    if manifest.get("pack_id") != "australian-butterflies-v1":
        raise SpeciesCatalogueError("unexpected taxonomy pack")
    if rights.get("schema_version") != "butterflylens-data-rights/v1":
        raise SpeciesCatalogueError("unexpected data-rights manifest")

    taxa_path = verified_artifact(pack, manifest, "taxa.jsonl")
    crosswalk_path = verified_artifact(pack, manifest, "crosswalk.jsonl")
    names_path = verified_artifact(pack, manifest, "name_assertions.jsonl")
    conflicts_path = verified_artifact(pack, manifest, "conflicts.jsonl")
    first_nations_path = verified_artifact(
        pack, manifest, "first_nations_name_review_manifest.json"
    )

    quality_manifest_path = pack / "references/v1/reference_quality_manifest.json"
    quality_manifest = load_json(quality_manifest_path)
    quality_path = pack / quality_manifest["artifact"]["path"].split(
        "data/packs/australian_butterflies/v1/", 1
    )[-1]
    quality_sha256 = sha256_file(quality_path)
    if quality_manifest["artifact"]["physical_sha256"] != quality_sha256:
        raise SpeciesCatalogueError("reference quality checksum mismatch")

    ala_manifest_path = pack / "ala/ala_snapshot_manifest.json"
    ala_manifest = load_json(ala_manifest_path)
    expected_ala_sha256 = manifest["ala_state"]["snapshot_manifest_sha256"]
    if sha256_file(ala_manifest_path) != expected_ala_sha256:
        raise SpeciesCatalogueError("ALA snapshot manifest checksum mismatch")
    release_state = ala_manifest["rights"]["downstream_public_product_release_state"]
    if release_state != "blocked_pending_dataset_rights_resolution":
        raise SpeciesCatalogueError("ALA public-product release state changed; review required")
    blocked_uids = ala_manifest["rights"][
        "citation_restrictive_rights_review_required_uids"
    ]
    if not blocked_uids:
        raise SpeciesCatalogueError("ALA rights block lacks dataset identifiers")

    first_nations = load_json(first_nations_path)
    if first_nations.get("status") != "empty_no_authorized_source" or any(
        first_nations.get("counts", {}).values()
    ):
        raise SpeciesCatalogueError("First Nations language-name gate is not empty")

    source_paths = {
        "taxa": taxa_path,
        "crosswalk": crosswalk_path,
        "names": names_path,
        "conflicts": conflicts_path,
        "firstNationsReview": first_nations_path,
        "referenceQuality": quality_path,
        "referenceQualityManifest": quality_manifest_path,
        "alaSnapshotManifest": ala_manifest_path,
    }
    sources = []
    for path in source_paths.values():
        relative = path.relative_to(ROOT).as_posix()
        sources.append(public_source(rights, relative, sha256_file(path)))

    taxa = load_jsonl(taxa_path)
    crosswalk = load_jsonl(crosswalk_path)
    names = load_jsonl(names_path)
    conflicts = load_jsonl(conflicts_path)

    try:
        import pyarrow.parquet as pq
    except ImportError as error:
        raise SpeciesCatalogueError("PyArrow is required for quality projection") from error
    quality_rows = pq.read_table(quality_path).to_pylist()

    species = [row for row in taxa if row.get("rank") == "species"]
    if len(species) != manifest["artifacts"]["taxa.jsonl"]["rank_counts"]["species"]:
        raise SpeciesCatalogueError("species count does not reconcile with the pack")
    species_keys = {row["butterflylens_key"] for row in species}
    if len(species_keys) != len(species) or not all(
        SPECIES_KEY_PATTERN.fullmatch(key) for key in species_keys
    ):
        raise SpeciesCatalogueError("species keys are invalid or duplicated")

    crosswalk_by_key = {
        row["butterflylens_key"]: row
        for row in crosswalk
        if row.get("rank") == "species"
    }
    quality_by_key = {row["butterflylens_taxon_key"]: row for row in quality_rows}
    if set(crosswalk_by_key) != species_keys or set(quality_by_key) != species_keys:
        raise SpeciesCatalogueError("species sources do not have identical key coverage")

    names_by_key: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in names:
        if row.get("butterflylens_key") in species_keys:
            names_by_key[row["butterflylens_key"]].append(row)
    conflicts_by_key: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in conflicts:
        if row.get("butterflylens_key") in species_keys:
            conflicts_by_key[row["butterflylens_key"]].append(row)

    projected_species = []
    for taxon in sorted(species, key=lambda row: row["accepted_scientific_name"].casefold()):
        key = taxon["butterflylens_key"]
        if taxon.get("schema_version") != TAXON_SCHEMA_VERSION:
            raise SpeciesCatalogueError(f"unexpected taxonomy schema for {key}")
        cross = crosswalk_by_key[key]
        diagnostic = quality_by_key[key]
        if diagnostic["accepted_scientific_name"] != taxon["accepted_scientific_name"]:
            raise SpeciesCatalogueError(f"reference name mismatch for {key}")
        if diagnostic["human_verified_count"] != 0:
            raise SpeciesCatalogueError(f"unexpected human-verified reference for {key}")
        if diagnostic["yoloe_routed_count"] != 0:
            raise SpeciesCatalogueError(f"unexpected YOLOE evidence for {key}")
        if diagnostic["bioclip_embedding_count"] != 0:
            raise SpeciesCatalogueError(f"unexpected BioCLIP evidence for {key}")

        hierarchy = {
            row["rank"]: {
                "key": row["butterflylens_key"],
                "acceptedScientificName": row["accepted_scientific_name"],
            }
            for row in taxon["parent_path"]
        }
        if "family" not in hierarchy or "genus" not in hierarchy:
            raise SpeciesCatalogueError(f"species hierarchy is incomplete for {key}")

        assertions = names_by_key[key]
        accepted = [row for row in assertions if row["name_type"] == "accepted_scientific"]
        if len(accepted) != 1 or accepted[0]["name"] != taxon["accepted_scientific_name"]:
            raise SpeciesCatalogueError(f"accepted-name assertion mismatch for {key}")

        english_names = sorted(
            (
                {
                    "name": row["name"],
                    "assertionId": row["assertion_id"],
                    "trustTier": row["trust_tier"],
                    "reviewState": row["review_state"],
                    "sourceProvider": row["source"]["provider"],
                    "sourceDataset": row["source"]["dataset"],
                    "queryEligible": row["query_eligibility"]["eligible"],
                    "homonymRisk": row["homonym_risk"],
                }
                for row in assertions
                if row["name_type"] == "english_vernacular"
            ),
            key=lambda row: (row["name"].casefold(), row["assertionId"]),
        )
        synonyms = sorted(
            (
                {
                    "name": row["name"],
                    "assertionId": row["assertion_id"],
                    "reviewState": row["review_state"],
                    "sourceProvider": row["source"]["provider"],
                    "providerNameId": row["provider_name_id"],
                }
                for row in assertions
                if row["name_type"] == "scientific_synonym"
            ),
            key=lambda row: (row["name"].casefold(), row["assertionId"]),
        )
        if any(row["reviewState"] != "source_assertion_unreviewed" for row in english_names):
            raise SpeciesCatalogueError(f"unexpected reviewed English name for {key}")

        provider_matches = []
        for provider_id, label, identifier_field in PROVIDERS:
            match = cross["provider_matches"][provider_id]
            state = match["state"]
            identifier = cross[identifier_field]
            if (identifier is not None) != (state == "matched"):
                raise SpeciesCatalogueError(
                    f"provider identifier/state mismatch for {key}:{provider_id}"
                )
            provider_matches.append(
                {
                    "provider": provider_id,
                    "label": label,
                    "state": state,
                    "identifier": str(identifier) if identifier is not None else None,
                    "matchedName": match.get("matched_name"),
                    "matchedRank": match.get("matched_rank"),
                    "reasons": match.get("reasons", []),
                }
            )

        open_conflicts = sorted(
            (
                {
                    "conflictId": row["conflict_id"],
                    "provider": row["provider"],
                    "conflictType": row["conflict_type"],
                    "reasons": row["reasons"],
                    "resolutionStatus": row["resolution"]["status"],
                }
                for row in conflicts_by_key[key]
                if row["resolution"]["status"] == "open"
            ),
            key=lambda row: (row["provider"], row["conflictId"]),
        )

        projected_species.append(
            {
                "key": key,
                "slug": species_slug(taxon["accepted_scientific_name"], key),
                "acceptedScientificName": taxon["accepted_scientific_name"],
                "queryScientificName": cross["provider_query_name"],
                "sourceTitle": taxon["source"]["source_title"],
                "sourceUrl": taxon["source"]["source_url"],
                "sourceRetrievedAt": taxon["source"]["retrieved_at"],
                "hierarchy": hierarchy,
                "englishNames": english_names,
                "scientificSynonyms": synonyms,
                "crosswalk": {
                    "status": cross["crosswalk_status"],
                    "queryNameNormalization": cross["query_name_normalization"],
                    "providers": provider_matches,
                    "openConflicts": open_conflicts,
                },
                "referenceCoverage": {
                    "status": diagnostic["coverage_status"],
                    "candidateMediaCount": diagnostic["candidate_media_count"],
                    "automatedGateEligibleCount": diagnostic[
                        "automated_gate_eligible_count"
                    ],
                    "selectedCount": diagnostic["selected_count"],
                    "validDecodeCount": diagnostic["valid_decode_count"],
                    "humanVerifiedCount": diagnostic["human_verified_count"],
                    "releaseStatus": diagnostic["release_status"],
                    "qualityFlags": diagnostic["quality_flags"],
                    "evidenceFingerprint": diagnostic["evidence_fingerprint"],
                },
            }
        )

    catalogue: dict[str, Any] = {
        "schemaVersion": CATALOGUE_SCHEMA_VERSION,
        "catalogueId": "australian-butterflies-v1/submitted-species-catalogue-v1",
        "generatedAt": generated_at,
        "speciesCount": len(projected_species),
        "authoritativeBaseline": "ButterflyLens rebuilt baseline",
        "states": {
            "taxonomy": "accepted_authority_snapshot",
            "englishNames": "source_assertions_unreviewed",
            "firstNationsNames": "empty_no_authorized_source",
            "alaOccurrenceEvidence": "withheld_pending_dataset_rights_resolution",
            "referenceEvidence": quality_manifest["status"],
            "humanReview": "absent",
            "yoloe": "unfinished",
            "bioclip": "unfinished",
            "scientificClaimAllowed": False,
        },
        "alaOccurrenceBoundary": {
            "snapshotId": ala_manifest["snapshot_id"],
            "snapshotFingerprint": manifest["ala_state"]["snapshot_fingerprint"],
            "releaseState": release_state,
            "rightsReviewRequiredDatasetUids": sorted(blocked_uids),
            "displayedOccurrenceCount": None,
            "absenceInferencePermitted": False,
            "reason": (
                "Species-level ALA occurrence counts are withheld while exact "
                "dataset citation rights remain unresolved; a missing displayed "
                "count is not evidence of biological absence."
            ),
        },
        "firstNationsNameBoundary": {
            "approvedCount": 0,
            "pendingCount": 0,
            "reason": (
                "No language-name assertion has an authorized public source in "
                "this pack; this is not evidence that no First Nations names exist."
            ),
        },
        "referenceBoundary": {
            "status": quality_manifest["status"],
            "humanVerifiedCount": quality_manifest["counts"]["human_verified"],
            "yoloeState": quality_manifest["upstream_states"]["yoloe"],
            "bioclipState": quality_manifest["upstream_states"]["bioclip"],
            "qualityScoreComputed": quality_manifest["policy"]["quality_score_computed"],
            "releaseReady": quality_manifest["policy"]["release_ready"],
            "reason": (
                "Reference counts are provider-asserted workflow diagnostics, "
                "not verified identities, model votes, or a quality estimate."
            ),
        },
        "sources": sorted(sources, key=lambda row: row["path"]),
        "sourceFingerprints": {
            name: sha256_file(path) for name, path in sorted(source_paths.items())
        }
        | {
            "packManifest": sha256_file(manifest_path),
            "dataRightsManifest": sha256_file(rights_path),
        },
        "species": projected_species,
    }
    catalogue["catalogueFingerprint"] = "sha256:" + hashlib.sha256(
        canonical_json(catalogue)
    ).hexdigest()
    return catalogue


def write_catalogue(catalogue: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(catalogue, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--rights", type=Path, default=DEFAULT_RIGHTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--generated-at", required=True)
    args = parser.parse_args()
    catalogue = build_catalogue(
        pack=args.pack,
        manifest_path=args.manifest,
        rights_path=args.rights,
        generated_at=args.generated_at,
    )
    write_catalogue(catalogue, args.output)
    print(
        "species catalogue built "
        f"(species={catalogue['speciesCount']}, "
        f"fingerprint={catalogue['catalogueFingerprint']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
