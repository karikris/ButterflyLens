#!/usr/bin/env python3
"""Build the deterministic, rights-screened submitted ALA public map."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any
import urllib.parse


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))

from butterflylens.contracts import canonicalize_json  # noqa: E402


ALA_DIR = ROOT / "data/packs/australian_butterflies/v1/ala"
DEFAULT_MAP_DIR = ROOT / "data/packs/australian_butterflies/v1/map"
DEFAULT_WEB_OUTPUT = ROOT / "apps/web/src/map/submittedMapSnapshot.json"

MAP_SCHEMA_VERSION = "butterflylens-submitted-ala-map/v1"
SUMMARY_SCHEMA_VERSION = "butterflylens-geographic-impact-summary/v1"
CELL_SCHEMA_VERSION = "butterflylens-geographic-impact-cell:v1.0.0"
SNAPSHOT_SCHEMA_VERSION = "butterflylens-geographic-impact-snapshot:v1.0.0"
QUERY_SCHEMA_VERSION = "butterflylens-geographic-impact-query:v1.0.0"
BROWSER_SCHEMA_VERSION = "butterflylens-submitted-map-browser-snapshot/v1"
GENERATED_AT = "2026-07-19T00:00:00Z"
PROJECT_ID = "project:australian-butterflies"
RUN_ID = "run:submitted-ala-public-map-20260719"
MAP_SNAPSHOT_ID = "snapshot:submitted-ala-public-map-20260719"
ROOT_TAXON_KEY = "bltx:v1:846e98d50678dffa38d43103"
EXPECTED_BLOCKED_DATASETS = ("dr1097", "dr30019", "dr635")
H3_RESOLUTIONS = {"coarse": 3, "regional": 5, "local": 7}
ELIGIBLE_ALL = "eligible_all_configured_resolutions"
ELIGIBLE_COARSE = "eligible_generalised_coarse_only"
HEX64 = re.compile(r"^[0-9a-f]{64}$")

UNAVAILABLE_REASONS = {
    "flickr_candidate": (
        "BioMiner is still fetching Flickr metadata; no complete immutable "
        "Flickr evidence snapshot is attached."
    ),
    "yoloe_butterfly": "YOLOE was not run by operator direction.",
    "bioclip_species_candidate": "BioCLIP was not run by operator direction.",
    "community_reviewed": "No completed review projection is attached to this map.",
    "human_supported": "No completed human-support consensus is attached to this map.",
    "release_ready": "No release-ready occurrence projection is attached to this map.",
}


class PublicMapError(RuntimeError):
    """Raised when the public projection cannot be built safely."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(value: object) -> str:
    return sha256_bytes(canonicalize_json(value))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonicalize_json(value))


def encoded_scope_id(prefix: str, label: str) -> str:
    return f"{prefix}:{urllib.parse.quote(label, safe='').lower()}"


def contextual_scope_metadata(scope_type: str, label: str) -> dict[str, Any]:
    definitions = {
        "australia": {
            "scope_order": 0,
            "scope_id": "country:au",
            "scope_resolution_class": "national",
            "contextual_source": "ALA selected country filter: Australia",
        },
        "state_territory": {
            "scope_order": 1,
            "scope_id": encoded_scope_id("ala:state-territory", label),
            "scope_resolution_class": "coarse",
            "contextual_source": "ALA stateProvince provider assertion",
        },
        "ibra_region": {
            "scope_order": 2,
            "scope_id": encoded_scope_id("ala:ibra-v7", label),
            "scope_resolution_class": "regional",
            "contextual_source": "ALA cl11185 IBRA v7 contextual assertion",
        },
        "lga_2023_statistical_approximation": {
            "scope_order": 3,
            "scope_id": encoded_scope_id("ala:lga-2023-approx", label),
            "scope_resolution_class": "local",
            "contextual_source": (
                "ALA cl11170 LGA 2023 Mesh Block statistical approximation; "
                "not a legal boundary"
            ),
        },
    }
    if scope_type not in definitions:
        raise PublicMapError(f"unknown contextual scope {scope_type!r}")
    return {
        "scope_type": scope_type,
        "scope_label": label,
        "h3_resolution": None,
        "h3_cell_id": None,
        "parent_h3_cell_id": None,
        "cell_center_latitude": None,
        "cell_center_longitude": None,
        **definitions[scope_type],
    }


def h3_scope_metadata(h3: Any, resolution_class: str, cell_id: str) -> dict[str, Any]:
    resolution = H3_RESOLUTIONS[resolution_class]
    parent_resolution = {"coarse": None, "regional": 3, "local": 5}[
        resolution_class
    ]
    latitude, longitude = h3.cell_to_latlng(cell_id)
    return {
        "scope_type": f"h3_{resolution_class}",
        "scope_order": {"coarse": 4, "regional": 5, "local": 6}[
            resolution_class
        ],
        "scope_id": f"h3:{resolution}:{cell_id}",
        "scope_label": cell_id,
        "scope_resolution_class": resolution_class,
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
        "cell_center_latitude": float(latitude),
        "cell_center_longitude": float(longitude),
    }


@dataclass
class SummaryAccumulator:
    metadata: dict[str, Any]
    record_count: int = 0
    matched_taxon_record_count: int = 0
    unmatched_taxon_assertion_count: int = 0
    taxon_keys: set[str] = field(default_factory=set)
    data_resources: set[str] = field(default_factory=set)
    earliest_event_year: int | None = None
    latest_event_year: int | None = None
    publicly_generalised_record_count: int = 0
    source_record_digest: Any = field(default_factory=hashlib.sha256)

    def add(self, row: dict[str, Any]) -> None:
        self.record_count += 1
        taxon_key = row["butterflylens_taxon_key"]
        if taxon_key is None:
            self.unmatched_taxon_assertion_count += 1
        else:
            self.matched_taxon_record_count += 1
            self.taxon_keys.add(taxon_key)
        self.data_resources.add(row["data_resource_uid"])
        year = row["event_year"]
        if year is not None and row["temporal_evidence_band"] != (
            "outside_declared_valid_year_range"
        ):
            self.earliest_event_year = (
                year
                if self.earliest_event_year is None
                else min(self.earliest_event_year, year)
            )
            self.latest_event_year = (
                year
                if self.latest_event_year is None
                else max(self.latest_event_year, year)
            )
        if row["coordinates_publicly_generalised"]:
            self.publicly_generalised_record_count += 1
        self.source_record_digest.update(
            row["normalized_occurrence_fingerprint"].encode("ascii")
        )
        self.source_record_digest.update(b"\n")

    def finish(self, snapshot: dict[str, str]) -> dict[str, Any]:
        row = {
            "schema_version": SUMMARY_SCHEMA_VERSION,
            "source_snapshot_id": snapshot["snapshot_id"],
            "source_snapshot_fingerprint": snapshot["snapshot_fingerprint"],
            **self.metadata,
            "ala_baseline_count": self.record_count,
            "matched_taxon_record_count": self.matched_taxon_record_count,
            "unmatched_taxon_assertion_count": self.unmatched_taxon_assertion_count,
            "unique_butterflylens_taxon_count": len(self.taxon_keys),
            "unique_data_resource_count": len(self.data_resources),
            "earliest_event_year": self.earliest_event_year,
            "latest_event_year": self.latest_event_year,
            "publicly_generalised_record_count": self.publicly_generalised_record_count,
            "source_record_fingerprint_digest": self.source_record_digest.hexdigest(),
            "scientific_claim_allowed": False,
        }
        row["summary_fingerprint"] = fingerprint(row)
        return row


def add_membership(
    groups: dict[tuple[str, str], SummaryAccumulator],
    metadata: dict[str, Any],
    row: dict[str, Any],
) -> None:
    key = (metadata["scope_type"], metadata["scope_id"])
    accumulator = groups.get(key)
    if accumulator is None:
        accumulator = SummaryAccumulator(metadata)
        groups[key] = accumulator
    accumulator.add(row)


def public_sample(row: dict[str, Any]) -> dict[str, Any]:
    source_reference = row["source_reference"]
    if not source_reference or not str(source_reference).startswith(("http://", "https://")):
        source_reference = (
            "https://biocache.ala.org.au/occurrences/" + row["ala_record_id"]
        )
    return {
        "recordId": row["ala_record_id"],
        "recordFingerprint": row["normalized_occurrence_fingerprint"],
        "taxonKey": row["butterflylens_taxon_key"],
        "providerScientificName": row["provider_scientific_name"],
        "dataResourceUid": row["data_resource_uid"],
        "dataResourceName": row["data_resource_name"],
        "basisOfRecord": row["basis_of_record"],
        "eventYear": row["event_year"],
        "publiclyGeneralised": row["coordinates_publicly_generalised"],
        "sourceReference": source_reference,
        "evidenceLabel": "ALA provider occurrence assertion; not human verification",
    }


def unavailable_count(reason: str) -> dict[str, Any]:
    return {"status": "unavailable", "value": None, "reason": reason}


def impact_unavailable(reason: str) -> dict[str, Any]:
    return {"status": "unavailable", "value": None, "reason": reason}


def build_cell(summary: dict[str, Any], snapshot_fingerprint: str, h3_version: str) -> dict[str, Any]:
    evidence = sorted(
        {snapshot_fingerprint, summary["source_record_fingerprint_digest"]}
    )
    row = {
        "schema_version": CELL_SCHEMA_VERSION,
        "cell_id": summary["h3_cell_id"],
        "grid": "H3",
        "h3_version": h3_version,
        "h3_resolution": 3,
        "project_id": PROJECT_ID,
        "run_id": RUN_ID,
        "snapshot_mode": "submitted",
        "accepted_taxon_key": ROOT_TAXON_KEY,
        "ala_snapshot_fingerprint": snapshot_fingerprint,
        "flickr_snapshot_fingerprint": None,
        "provider_union_fingerprint": None,
        "review_projection_fingerprint": None,
        "quality_snapshot_fingerprint": None,
        "counts": {
            "ala_baseline": {
                "status": "available",
                "value": summary["ala_baseline_count"],
                "reason": None,
            },
            **{
                name: unavailable_count(reason)
                for name, reason in UNAVAILABLE_REASONS.items()
            },
        },
        "impact": {
            "potential_coverage_gap": impact_unavailable(
                "Coverage-gap comparison requires an admitted Flickr candidate snapshot."
            ),
            "human_supported_additional": impact_unavailable(
                "No completed human-support consensus is attached to this map."
            ),
            "release_ready_additional": impact_unavailable(
                "No release-ready occurrence projection is attached to this map."
            ),
        },
        "nearest_ala_evidence_distance": {
            "status": "not_applicable",
            "metres": None,
            "reason": "This H3 cell already contains ALA baseline evidence.",
        },
        "latest_ala_event_date": None,
        "latest_flickr_event_date": None,
        "data_deficiency_state": "baseline_present",
        "public_geometry": {
            "status": "generalized",
            "source_precision_metres": None,
            "published_h3_resolution": 3,
            "reason": (
                "Published geometry is an H3 resolution 3 aggregate derived from "
                "public ALA processed coordinates; it is not an occurrence coordinate."
            ),
        },
        "evidence_fingerprints": evidence,
        "cell_fingerprint": "",
        "scientific_claim_allowed": False,
    }
    fingerprint_input = dict(row)
    del fingerprint_input["cell_fingerprint"]
    row["cell_fingerprint"] = fingerprint(fingerprint_input)
    return row


def summary_arrow_schema(pa: Any, snapshot: dict[str, str], h3_version: str) -> Any:
    metadata = {
        b"schema_version": SUMMARY_SCHEMA_VERSION.encode(),
        b"snapshot_id": snapshot["snapshot_id"].encode(),
        b"snapshot_fingerprint": snapshot["snapshot_fingerprint"].encode(),
        b"h3_version": h3_version.encode(),
        b"rights_projection": b"excludes frozen citation-rights review datasets",
    }
    return pa.schema(
        [
            pa.field("schema_version", pa.string(), nullable=False),
            pa.field("source_snapshot_id", pa.string(), nullable=False),
            pa.field("source_snapshot_fingerprint", pa.string(), nullable=False),
            pa.field("scope_type", pa.string(), nullable=False),
            pa.field("scope_order", pa.int32(), nullable=False),
            pa.field("scope_id", pa.string(), nullable=False),
            pa.field("scope_label", pa.string(), nullable=False),
            pa.field("scope_resolution_class", pa.string(), nullable=False),
            pa.field("contextual_source", pa.string(), nullable=False),
            pa.field("h3_resolution", pa.int32(), nullable=True),
            pa.field("h3_cell_id", pa.string(), nullable=True),
            pa.field("parent_h3_cell_id", pa.string(), nullable=True),
            pa.field("cell_center_latitude", pa.float64(), nullable=True),
            pa.field("cell_center_longitude", pa.float64(), nullable=True),
            pa.field("ala_baseline_count", pa.int64(), nullable=False),
            pa.field("matched_taxon_record_count", pa.int64(), nullable=False),
            pa.field("unmatched_taxon_assertion_count", pa.int64(), nullable=False),
            pa.field("unique_butterflylens_taxon_count", pa.int64(), nullable=False),
            pa.field("unique_data_resource_count", pa.int64(), nullable=False),
            pa.field("earliest_event_year", pa.int32(), nullable=True),
            pa.field("latest_event_year", pa.int32(), nullable=True),
            pa.field("publicly_generalised_record_count", pa.int64(), nullable=False),
            pa.field("source_record_fingerprint_digest", pa.string(), nullable=False),
            pa.field("scientific_claim_allowed", pa.bool_(), nullable=False),
            pa.field("summary_fingerprint", pa.string(), nullable=False),
        ],
        metadata=metadata,
    )


def cell_arrow_schema(pa: Any, snapshot: dict[str, str], h3_version: str) -> Any:
    count = pa.struct(
        [
            pa.field("status", pa.string(), nullable=False),
            pa.field("value", pa.int64(), nullable=True),
            pa.field("reason", pa.string(), nullable=True),
        ]
    )
    flag = pa.struct(
        [
            pa.field("status", pa.string(), nullable=False),
            pa.field("value", pa.bool_(), nullable=True),
            pa.field("reason", pa.string(), nullable=True),
        ]
    )
    metadata = {
        b"schema_version": CELL_SCHEMA_VERSION.encode(),
        b"snapshot_id": snapshot["snapshot_id"].encode(),
        b"snapshot_fingerprint": snapshot["snapshot_fingerprint"].encode(),
        b"h3_version": h3_version.encode(),
        b"rights_projection": b"excludes frozen citation-rights review datasets",
    }
    return pa.schema(
        [
            pa.field("schema_version", pa.string(), nullable=False),
            pa.field("cell_id", pa.string(), nullable=False),
            pa.field("grid", pa.string(), nullable=False),
            pa.field("h3_version", pa.string(), nullable=False),
            pa.field("h3_resolution", pa.int32(), nullable=False),
            pa.field("project_id", pa.string(), nullable=False),
            pa.field("run_id", pa.string(), nullable=False),
            pa.field("snapshot_mode", pa.string(), nullable=False),
            pa.field("accepted_taxon_key", pa.string(), nullable=False),
            pa.field("ala_snapshot_fingerprint", pa.string(), nullable=True),
            pa.field("flickr_snapshot_fingerprint", pa.string(), nullable=True),
            pa.field("provider_union_fingerprint", pa.string(), nullable=True),
            pa.field("review_projection_fingerprint", pa.string(), nullable=True),
            pa.field("quality_snapshot_fingerprint", pa.string(), nullable=True),
            pa.field(
                "counts",
                pa.struct(
                    [pa.field(name, count, nullable=False) for name in (
                        "ala_baseline",
                        "flickr_candidate",
                        "yoloe_butterfly",
                        "bioclip_species_candidate",
                        "community_reviewed",
                        "human_supported",
                        "release_ready",
                    )]
                ),
                nullable=False,
            ),
            pa.field(
                "impact",
                pa.struct(
                    [pa.field(name, flag, nullable=False) for name in (
                        "potential_coverage_gap",
                        "human_supported_additional",
                        "release_ready_additional",
                    )]
                ),
                nullable=False,
            ),
            pa.field(
                "nearest_ala_evidence_distance",
                pa.struct(
                    [
                        pa.field("status", pa.string(), nullable=False),
                        pa.field("metres", pa.float64(), nullable=True),
                        pa.field("reason", pa.string(), nullable=True),
                    ]
                ),
                nullable=False,
            ),
            pa.field("latest_ala_event_date", pa.string(), nullable=True),
            pa.field("latest_flickr_event_date", pa.string(), nullable=True),
            pa.field("data_deficiency_state", pa.string(), nullable=False),
            pa.field(
                "public_geometry",
                pa.struct(
                    [
                        pa.field("status", pa.string(), nullable=False),
                        pa.field("source_precision_metres", pa.float64(), nullable=True),
                        pa.field("published_h3_resolution", pa.int32(), nullable=True),
                        pa.field("reason", pa.string(), nullable=True),
                    ]
                ),
                nullable=False,
            ),
            pa.field("evidence_fingerprints", pa.list_(pa.string()), nullable=False),
            pa.field("cell_fingerprint", pa.string(), nullable=False),
            pa.field("scientific_claim_allowed", pa.bool_(), nullable=False),
        ],
        metadata=metadata,
    )


def summary_schema_contract() -> dict[str, Any]:
    fields = [
        ("schema_version", "string", False),
        ("source_snapshot_id", "string", False),
        ("source_snapshot_fingerprint", "string", False),
        ("scope_type", "string", False),
        ("scope_order", "int32", False),
        ("scope_id", "string", False),
        ("scope_label", "string", False),
        ("scope_resolution_class", "string", False),
        ("contextual_source", "string", False),
        ("h3_resolution", "int32", True),
        ("h3_cell_id", "string", True),
        ("parent_h3_cell_id", "string", True),
        ("cell_center_latitude", "float64", True),
        ("cell_center_longitude", "float64", True),
        ("ala_baseline_count", "int64", False),
        ("matched_taxon_record_count", "int64", False),
        ("unmatched_taxon_assertion_count", "int64", False),
        ("unique_butterflylens_taxon_count", "int64", False),
        ("unique_data_resource_count", "int64", False),
        ("earliest_event_year", "int32", True),
        ("latest_event_year", "int32", True),
        ("publicly_generalised_record_count", "int64", False),
        ("source_record_fingerprint_digest", "string", False),
        ("scientific_claim_allowed", "bool", False),
        ("summary_fingerprint", "string", False),
    ]
    return {
        "schema_version": "butterflylens-parquet-schema/v1",
        "artifact_schema_version": SUMMARY_SCHEMA_VERSION,
        "format": "parquet",
        "closed": True,
        "fields": [
            {"name": name, "type": kind, "nullable": nullable}
            for name, kind, nullable in fields
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
        "invariants": [
            "rows are sorted by scope_order then scope_id",
            "the Australia count equals the sum of geographic-impact H3 cell counts",
            "rights-screened datasets are absent from every aggregate",
            "publicly generalised rows contribute only to national, state, and H3 resolution 3 scopes",
            "IBRA and LGA values remain contextual assertions and no boundary geometry is copied",
            "provider occurrence assertions are not human verification",
        ],
    }


def write_parquet(path: Path, rows: list[dict[str, Any]], schema: Any, pq: Any, pa: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(
        table,
        path,
        compression="zstd",
        use_dictionary=True,
        row_group_size=65_536,
        write_statistics=True,
    )


def artifact_receipt(path: Path, row_count: int, logical_fingerprint: str) -> dict[str, Any]:
    return {
        "path": path.name,
        "row_count": row_count,
        "physical_bytes": path.stat().st_size,
        "physical_sha256": sha256_file(path),
        "logical_fingerprint_sha256": logical_fingerprint,
        "compression": "zstd" if path.suffix == ".parquet" else None,
    }


def load_inputs(occurrence_path: Path, dataset_path: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    normalization = json.loads(
        (ALA_DIR / "ala_normalization_manifest.json").read_text(encoding="utf-8")
    )
    snapshot = json.loads(
        (ALA_DIR / "ala_snapshot_manifest.json").read_text(encoding="utf-8")
    )
    if sha256_file(occurrence_path) != normalization["artifact"]["physical_sha256"]:
        raise PublicMapError("ALA occurrence checksum does not match its manifest")
    blocked = tuple(snapshot["rights"]["citation_restrictive_rights_review_required_uids"])
    if blocked != EXPECTED_BLOCKED_DATASETS:
        raise PublicMapError("frozen citation-rights review dataset set changed")
    import pyarrow.parquet as pq

    datasets = pq.read_table(dataset_path).to_pylist()
    selected = [row for row in datasets if row["data_resource_uid"] in blocked]
    if tuple(sorted(row["data_resource_uid"] for row in selected)) != blocked:
        raise PublicMapError("rights-screened dataset manifest rows are incomplete")
    if any(
        row["public_product_rights_review_state"]
        != "blocked_pending_citation_rights_resolution"
        for row in selected
    ):
        raise PublicMapError("rights-screened dataset state is no longer blocked")
    return normalization, snapshot, sorted(selected, key=lambda row: row["data_resource_uid"])


def build(args: argparse.Namespace) -> dict[str, Any]:
    try:
        import h3
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as error:
        raise PublicMapError(
            "public map build requires locked h3 and PyArrow dependencies"
        ) from error
    if h3.__version__ != "4.5.0":
        raise PublicMapError(f"unexpected h3 version {h3.__version__!r}")
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_commit):
        raise PublicMapError("source commit must be a full lowercase Git SHA")

    normalization, snapshot_manifest, blocked_datasets = load_inputs(
        args.occurrences, args.dataset_manifest
    )
    snapshot = {
        "snapshot_id": normalization["snapshot_id"],
        "snapshot_fingerprint": normalization["snapshot_fingerprint"],
    }
    blocked_uids = {row["data_resource_uid"] for row in blocked_datasets}
    columns = [
        "ala_record_id",
        "normalized_occurrence_fingerprint",
        "butterflylens_taxon_key",
        "provider_scientific_name",
        "data_resource_uid",
        "data_resource_name",
        "decimal_latitude",
        "decimal_longitude",
        "coordinates_publicly_generalised",
        "spatial_aggregation_eligibility",
        "event_year",
        "temporal_evidence_band",
        "basis_of_record",
        "state_territory",
        "ibra_region",
        "lga_name",
        "source_reference",
    ]
    table = pq.read_table(args.occurrences, columns=columns)
    if table.num_rows != normalization["artifact"]["row_count"]:
        raise PublicMapError("ALA occurrence row count does not match its manifest")

    groups: dict[tuple[str, str], SummaryAccumulator] = {}
    samples: dict[str, list[dict[str, Any]]] = {}
    selected_counts = Counter()
    spatial_counts = Counter()
    eligibility_counts = Counter()
    previous_record_id: str | None = None

    for batch in table.to_batches(max_chunksize=65_536):
        for row in batch.to_pylist():
            record_id = row["ala_record_id"]
            if previous_record_id is not None and record_id <= previous_record_id:
                raise PublicMapError("normalized occurrence rows are not uniquely sorted")
            previous_record_id = record_id
            uid = row["data_resource_uid"]
            bucket = "excluded" if uid in blocked_uids else "included"
            selected_counts[bucket] += 1
            eligibility = row["spatial_aggregation_eligibility"]
            eligibility_counts[(bucket, eligibility)] += 1
            if uid in blocked_uids:
                if eligibility in {ELIGIBLE_ALL, ELIGIBLE_COARSE}:
                    spatial_counts[uid] += 1
                    spatial_counts["excluded"] += 1
                continue
            if eligibility not in {ELIGIBLE_ALL, ELIGIBLE_COARSE}:
                continue
            spatial_counts["included"] += 1
            if row["decimal_latitude"] is None or row["decimal_longitude"] is None:
                raise PublicMapError("spatially eligible row lacks public coordinates")
            all_resolution = eligibility == ELIGIBLE_ALL
            if not all_resolution and not row["coordinates_publicly_generalised"]:
                raise PublicMapError("coarse-only row lacks generalisation evidence")

            add_membership(
                groups,
                contextual_scope_metadata("australia", "Australia"),
                row,
            )
            if row["state_territory"]:
                add_membership(
                    groups,
                    contextual_scope_metadata(
                        "state_territory", row["state_territory"]
                    ),
                    row,
                )
            if all_resolution and row["ibra_region"]:
                add_membership(
                    groups,
                    contextual_scope_metadata("ibra_region", row["ibra_region"]),
                    row,
                )
            if all_resolution and row["lga_name"]:
                add_membership(
                    groups,
                    contextual_scope_metadata(
                        "lga_2023_statistical_approximation", row["lga_name"]
                    ),
                    row,
                )

            resolution_classes = (
                ("coarse", "regional", "local")
                if all_resolution
                else ("coarse",)
            )
            for resolution_class in resolution_classes:
                resolution = H3_RESOLUTIONS[resolution_class]
                cell_id = h3.latlng_to_cell(
                    row["decimal_latitude"], row["decimal_longitude"], resolution
                )
                add_membership(
                    groups,
                    h3_scope_metadata(h3, resolution_class, cell_id),
                    row,
                )
                if resolution_class == "coarse" and len(samples.setdefault(cell_id, [])) < 2:
                    samples[cell_id].append(public_sample(row))

    if selected_counts["included"] + selected_counts["excluded"] != table.num_rows:
        raise PublicMapError("selected record counts do not reconcile")
    if selected_counts["excluded"] != sum(
        row["selected_record_count"] for row in blocked_datasets
    ):
        raise PublicMapError("excluded selected counts do not reconcile")

    summary_rows = sorted(
        (accumulator.finish(snapshot) for accumulator in groups.values()),
        key=lambda row: (row["scope_order"], row["scope_id"]),
    )
    national = [row for row in summary_rows if row["scope_type"] == "australia"]
    if len(national) != 1 or national[0]["ala_baseline_count"] != spatial_counts["included"]:
        raise PublicMapError("national spatial count does not reconcile")
    coarse_summaries = [
        row for row in summary_rows if row["scope_type"] == "h3_coarse"
    ]
    cells = [
        build_cell(row, snapshot["snapshot_fingerprint"], h3.__version__)
        for row in coarse_summaries
    ]
    if sum(row["counts"]["ala_baseline"]["value"] for row in cells) != (
        spatial_counts["included"]
    ):
        raise PublicMapError("H3 cell counts do not reconcile")

    map_dir = args.output_dir
    cells_path = map_dir / "geographic_impact_cells.parquet"
    summary_path = map_dir / "geographic_impact_summary.parquet"
    manifest_path = map_dir / "map_manifest.json"
    summary_schema_path = map_dir / "schemas/geographic_impact_summary.schema.json"
    write_parquet(
        cells_path,
        cells,
        cell_arrow_schema(pa, snapshot, h3.__version__),
        pq,
        pa,
    )
    write_parquet(
        summary_path,
        summary_rows,
        summary_arrow_schema(pa, snapshot, h3.__version__),
        pq,
        pa,
    )
    write_json(summary_schema_path, summary_schema_contract())

    browser_cells = []
    for cell, summary in zip(cells, coarse_summaries, strict=True):
        boundary = [
            [round(longitude, 6), round(latitude, 6)]
            for latitude, longitude in h3.cell_to_boundary(cell["cell_id"])
        ]
        browser_cells.append(
            {
                "cellId": cell["cell_id"],
                "count": cell["counts"]["ala_baseline"]["value"],
                "center": [
                    round(summary["cell_center_longitude"], 6),
                    round(summary["cell_center_latitude"], 6),
                ],
                "polygon": boundary,
                "latestEventYear": summary["latest_event_year"],
                "publiclyGeneralisedCount": summary[
                    "publicly_generalised_record_count"
                ],
                "evidenceFingerprint": summary[
                    "source_record_fingerprint_digest"
                ],
                "cellFingerprint": cell["cell_fingerprint"],
                "records": samples.get(cell["cell_id"], []),
            }
        )
    browser_scopes: dict[str, list[dict[str, Any]]] = {}
    scope_map = {
        "state": "state_territory",
        "ibra": "ibra_region",
        "lga": "lga_2023_statistical_approximation",
        "h3": "h3_coarse",
    }
    for browser_name, scope_type in scope_map.items():
        browser_scopes[browser_name] = [
            {
                "scopeId": row["scope_id"],
                "label": row["scope_label"],
                "count": row["ala_baseline_count"],
                "matchedTaxonCount": row["matched_taxon_record_count"],
                "unmatchedTaxonAssertionCount": row[
                    "unmatched_taxon_assertion_count"
                ],
                "uniqueTaxonCount": row["unique_butterflylens_taxon_count"],
                "latestEventYear": row["latest_event_year"],
                "publiclyGeneralisedCount": row[
                    "publicly_generalised_record_count"
                ],
                "evidenceFingerprint": row[
                    "source_record_fingerprint_digest"
                ],
                "summaryFingerprint": row["summary_fingerprint"],
            }
            for row in summary_rows
            if row["scope_type"] == scope_type
        ]

    excluded_rows = []
    for row in blocked_datasets:
        excluded_rows.append(
            {
                "dataResourceUid": row["data_resource_uid"],
                "dataResourceName": row["data_resource_name"],
                "selectedRecordCount": row["selected_record_count"],
                "spatiallyEligibleRecordCount": spatial_counts[
                    row["data_resource_uid"]
                ],
                "reviewState": row["public_product_rights_review_state"],
                "datasetFingerprint": row["dataset_manifest_fingerprint"],
            }
        )

    browser_snapshot = {
        "schemaVersion": BROWSER_SCHEMA_VERSION,
        "snapshotId": MAP_SNAPSHOT_ID,
        "mode": "submitted",
        "generatedAt": GENERATED_AT,
        "sourceCommit": args.source_commit,
        "projectId": PROJECT_ID,
        "runId": RUN_ID,
        "acceptedTaxonKey": ROOT_TAXON_KEY,
        "source": {
            "provider": "Atlas of Living Australia",
            "snapshotId": snapshot["snapshot_id"],
            "snapshotFingerprint": snapshot["snapshot_fingerprint"],
            "attribution": (
                "Atlas of Living Australia occurrence data and each contributing "
                "provider retained in the rights-screened projection."
            ),
            "notice": (
                "ALA baseline occurrence evidence is a selected snapshot; provider "
                "taxon labels are assertions, not human verification."
            ),
        },
        "counts": {
            "authoritativeBaselineSelected": table.num_rows,
            "rightsScreenedSelected": selected_counts["included"],
            "rightsExcludedSelected": selected_counts["excluded"],
            "mapEligible": spatial_counts["included"],
            "rightsExcludedMapEligible": spatial_counts["excluded"],
            "mapCells": len(cells),
        },
        "layers": {
            "alaBaseline": {
                "status": "available",
                "label": "ALA baseline",
                "visualEncoding": "blue filled H3 polygon",
                "reason": None,
            },
            "flickrCandidate": {
                "status": "unavailable",
                "label": "Flickr candidate",
                "visualEncoding": "amber outlined diamond",
                "reason": UNAVAILABLE_REASONS["flickr_candidate"],
            },
            "communityReviewed": {
                "status": "unavailable",
                "label": "Community reviewed",
                "visualEncoding": "ring marker",
                "reason": UNAVAILABLE_REASONS["community_reviewed"],
            },
            "releaseReady": {
                "status": "unavailable",
                "label": "Release ready",
                "visualEncoding": "star marker",
                "reason": UNAVAILABLE_REASONS["release_ready"],
            },
        },
        "rights": {
            "state": "public_projection_available_with_flagged_datasets_excluded",
            "legalConclusion": False,
            "excludedDatasets": excluded_rows,
        },
        "policies": {
            "occurrenceCoordinatesPublished": False,
            "boundaryGeometryCopied": False,
            "absenceInferencePermitted": False,
            "scientificClaimAllowed": False,
            "lgaQualification": (
                "ALA contextual LGA 2023 Mesh Block statistical approximation; "
                "not a legal boundary."
            ),
        },
        "cells": browser_cells,
        "scopes": browser_scopes,
    }
    browser_snapshot["snapshotFingerprint"] = fingerprint(browser_snapshot)
    write_json(args.web_output, browser_snapshot)

    cell_logical_fingerprint = fingerprint(cells)
    summary_logical_fingerprint = fingerprint(summary_rows)
    browser_logical_fingerprint = browser_snapshot["snapshotFingerprint"]
    cells_receipt = artifact_receipt(
        cells_path, len(cells), cell_logical_fingerprint
    )
    summary_receipt = artifact_receipt(
        summary_path, len(summary_rows), summary_logical_fingerprint
    )
    browser_receipt = {
        "path": str(args.web_output.relative_to(ROOT)),
        "physical_bytes": args.web_output.stat().st_size,
        "physical_sha256": sha256_file(args.web_output),
        "logical_fingerprint_sha256": browser_logical_fingerprint,
    }

    query_without_fingerprint = {
        "schema_version": QUERY_SCHEMA_VERSION,
        "project_id": PROJECT_ID,
        "accepted_taxon_keys": [ROOT_TAXON_KEY],
        "snapshot_mode": "submitted",
        "h3_resolution": 3,
        "scope": {"kind": "national", "scope_id": "country:au"},
        "event_date_from": None,
        "event_date_to": None,
        "evidence_maturity": ["ala_baseline"],
        "ala_basis_of_record": [],
        "review_states": [],
        "page_size": 1000,
    }
    query = {
        **query_without_fingerprint,
        "query_fingerprint": fingerprint(query_without_fingerprint),
    }
    projection_fingerprint = fingerprint(
        {
            "summary_fingerprint": summary_logical_fingerprint,
            "browser_fingerprint": browser_logical_fingerprint,
            "excluded_dataset_fingerprints": [
                row["dataset_manifest_fingerprint"] for row in blocked_datasets
            ],
        }
    )
    snapshot_contract = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": MAP_SNAPSHOT_ID,
        "project_id": PROJECT_ID,
        "run_id": RUN_ID,
        "mode": "submitted",
        "country_code": "AU",
        "status": "available",
        "generated_at": GENERATED_AT,
        "last_updated_at": GENERATED_AT,
        "submitted_source_commit": args.source_commit,
        "worker_heartbeat_fingerprint": None,
        "cell_schema_version": CELL_SCHEMA_VERSION,
        "cell_count": len(cells),
        "cell_artifact_checksum": cells_receipt["physical_sha256"],
        "cell_artifact_fingerprint": cell_logical_fingerprint,
        "query_fingerprint": query["query_fingerprint"],
        "map_projection_fingerprint": projection_fingerprint,
        "blockers": [
            "flickr_snapshot_unavailable",
            "yoloe_unfinished_not_run",
            "bioclip_unfinished_not_run",
            "review_projection_unavailable",
            "release_projection_unavailable",
        ],
        "append_only_revision": 1,
    }
    manifest = {
        "schema_version": MAP_SCHEMA_VERSION,
        "generated_at": GENERATED_AT,
        "source_commit": args.source_commit,
        "snapshot": snapshot_contract,
        "query": query,
        "input": {
            "authoritative_baseline": True,
            "occurrence_path": str(args.occurrences.relative_to(ROOT)),
            "occurrence_sha256": sha256_file(args.occurrences),
            "dataset_manifest_path": str(args.dataset_manifest.relative_to(ROOT)),
            "dataset_manifest_sha256": sha256_file(args.dataset_manifest),
            "ala_snapshot_id": snapshot["snapshot_id"],
            "ala_snapshot_fingerprint": snapshot["snapshot_fingerprint"],
            "gbif_relationship": "complementary_not_merged",
        },
        "counts": {
            "authoritative_baseline_selected": table.num_rows,
            "rights_screened_selected": selected_counts["included"],
            "rights_excluded_selected": selected_counts["excluded"],
            "map_eligible": spatial_counts["included"],
            "rights_excluded_map_eligible": spatial_counts["excluded"],
            "source_spatial_eligibility": {
                key: int(value)
                for (bucket, key), value in sorted(eligibility_counts.items())
                if bucket == "included"
            },
            "summary_scope_rows": dict(
                sorted(Counter(row["scope_type"] for row in summary_rows).items())
            ),
        },
        "rights_screen": {
            "state": "public_projection_available_with_flagged_datasets_excluded",
            "screening_semantics": snapshot_manifest["rights"][
                "citation_restrictive_rights_screening"
            ],
            "legal_conclusion": False,
            "full_baseline_preserved": True,
            "excluded_datasets": [
                {
                    "data_resource_uid": row["data_resource_uid"],
                    "data_resource_name": row["data_resource_name"],
                    "selected_record_count": row["selected_record_count"],
                    "spatially_eligible_record_count": spatial_counts[
                        row["data_resource_uid"]
                    ],
                    "review_state": row["public_product_rights_review_state"],
                    "dataset_manifest_fingerprint": row[
                        "dataset_manifest_fingerprint"
                    ],
                }
                for row in blocked_datasets
            ],
        },
        "availability": {
            "ala_baseline": {"status": "available", "reason": None},
            **{
                name: {"status": "unavailable", "reason": reason}
                for name, reason in UNAVAILABLE_REASONS.items()
            },
        },
        "policies": {
            "occurrence_coordinates_published": False,
            "boundary_geometry_copied": False,
            "h3_geometry_is_aggregate_not_occurrence": True,
            "absence_inference_permitted": False,
            "provider_assertions_are_human_verification": False,
            "scientific_claim_allowed": False,
            "publicly_generalised_membership": (
                "national, state/territory, and H3 resolution 3 only"
            ),
        },
        "attribution": {
            "path": "../ala/ala_attribution.json",
            "physical_sha256": sha256_file(ALA_DIR / "ala_attribution.json"),
            "required_notice": (
                "ALA baseline occurrence evidence is a selected snapshot, not "
                "complete truth; provider taxon labels are provider assertions, "
                "not human verification."
            ),
        },
        "artifacts": {
            "geographic_impact_cells": cells_receipt,
            "geographic_impact_summary": summary_receipt,
            "browser_snapshot": browser_receipt,
            "summary_schema": {
                "path": "schemas/geographic_impact_summary.schema.json",
                "physical_sha256": sha256_file(summary_schema_path),
            },
        },
        "build": {
            "python": sys.version.split()[0],
            "pyarrow": pa.__version__,
            "h3": h3.__version__,
            "network_calls": 0,
            "flickr_api_calls": 0,
            "model_invocations": 0,
        },
    }
    manifest["manifest_fingerprint"] = fingerprint(manifest)
    write_json(manifest_path, manifest)
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--occurrences",
        type=Path,
        default=ALA_DIR / "ala_baseline_occurrences.parquet",
    )
    parser.add_argument(
        "--dataset-manifest",
        type=Path,
        default=ALA_DIR / "ala_dataset_manifest.parquet",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_MAP_DIR)
    parser.add_argument("--web-output", type=Path, default=DEFAULT_WEB_OUTPUT)
    parser.add_argument("--source-commit", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    manifest = build(parse_args(argv))
    print(
        json.dumps(
            {
                "snapshot_id": manifest["snapshot"]["snapshot_id"],
                "cell_count": manifest["snapshot"]["cell_count"],
                "map_eligible": manifest["counts"]["map_eligible"],
                "rights_excluded_selected": manifest["counts"][
                    "rights_excluded_selected"
                ],
                "manifest_fingerprint": manifest["manifest_fingerprint"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
