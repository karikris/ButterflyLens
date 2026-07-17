#!/usr/bin/env python3
"""Publish a fail-closed YOLOE routing-readiness ledger.

The ledger never substitutes a synthetic detector result for a live YOLOE
route. It records every selected reference outcome and the exact reasons why
the pinned BioMiner router cannot currently execute it.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


SCHEMA_VERSION = "butterflylens-reference-yoloe-readiness/v1"
MANIFEST_SCHEMA_VERSION = "butterflylens-reference-yoloe-readiness-manifest/v1"
PINNED_BIOMINER_SHA = "d71bceabf75748a25df39d0025e8da907f295f8c"
OBSERVED_BIOMINER_SHA = "c7eaa9bf3696a25a0c8229837819dccec4fb9d66"
OBSERVED_BIOMINER_REPORT_SHA256 = (
    "309def915f77fcbb707cecb8a102a4cc0dceb4bdd716c596362d9bc053a0f917"
)
UPSTREAM_ROUTE_SCHEMA_VERSION = "reference-yoloe-routing-v1.0.0"


class RoutingReadinessError(RuntimeError):
    """Raised when frozen reference inputs do not reconcile."""


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(value: Any) -> str:
    payload = canonical_json(value).rstrip(b"\n")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_json(value))
    temporary.replace(path)


def write_parquet(path: Path, rows: list[dict[str, Any]]) -> None:
    schema = pa.schema(
        [
            ("schema_version", pa.string()),
            ("reference_media_id", pa.string()),
            ("reference_observation_id", pa.string()),
            ("source", pa.string()),
            ("source_record_hash", pa.string()),
            ("content_sha256", pa.string()),
            ("source_object_uri", pa.string()),
            ("decode_status", pa.string()),
            ("upstream_router_source_supported", pa.bool_()),
            ("detector_runtime_status", pa.string()),
            ("detector_checkpoint_status", pa.string()),
            ("routing_status", pa.string()),
            ("blocking_reasons", pa.list_(pa.string())),
            ("human_verification_status", pa.string()),
            ("readiness_fingerprint", pa.string()),
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(
        table,
        path,
        compression="zstd",
        compression_level=9,
        use_dictionary=True,
        write_statistics=True,
        version="2.6",
        data_page_version="1.0",
        row_group_size=65_536,
    )


def artifact(
    path: Path, rows: int | None = None, manifest_path: str | None = None
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "path": manifest_path or path.as_posix(),
        "physical_bytes": path.stat().st_size,
        "physical_sha256": sha256_file(path),
    }
    if rows is not None:
        value["row_count"] = rows
    return value


def build(args: argparse.Namespace) -> None:
    selections = pq.read_table(args.selections).to_pylist()
    observations = pq.read_table(args.observations).to_pylist()
    objects = pq.read_table(args.media_objects).to_pylist()
    admission = json.loads(args.admission_manifest.read_text())
    observation_by_id = {
        row["reference_observation_id"]: row for row in observations
    }
    object_by_id = {row["reference_media_id"]: row for row in objects}
    selection_ids = {row["reference_media_id"] for row in selections}
    if len(selection_ids) != len(selections):
        raise RoutingReadinessError("download selections contain duplicate media IDs")
    if set(object_by_id) != selection_ids:
        raise RoutingReadinessError("media-object outcomes do not cover selections")
    if admission["counts"]["selected_for_download"] != len(selections):
        raise RoutingReadinessError("admission manifest does not cover selections")

    rows: list[dict[str, Any]] = []
    for selection in selections:
        media_id = selection["reference_media_id"]
        observation = observation_by_id[selection["reference_observation_id"]]
        media_object = object_by_id[media_id]
        source = str(selection["source"])
        reasons: list[str] = []
        upstream_supported = source.casefold() == "gbif"
        if not upstream_supported:
            reasons.append("pinned_reference_router_accepts_gbif_only")
        if media_object["decode_status"] != "valid":
            reasons.append(
                "media_object_not_decoded:" + str(media_object["decode_status"])
            )
        reasons.extend(
            [
                "audited_yoloe_runtime_unavailable",
                "verified_yoloe_checkpoint_unavailable",
            ]
        )
        payload = {
            "reference_media_id": media_id,
            "reference_observation_id": selection["reference_observation_id"],
            "source": source,
            "source_record_hash": observation["source_record_hash"],
            "content_sha256": media_object["sha256"],
            "source_object_uri": media_object["source_object_uri"],
            "decode_status": media_object["decode_status"],
            "upstream_router_source_supported": upstream_supported,
            "detector_runtime_status": "unavailable_not_installed",
            "detector_checkpoint_status": "unavailable_not_downloaded",
            "routing_status": "blocked_not_executed",
            "blocking_reasons": sorted(reasons),
            "human_verification_status": "unreviewed",
        }
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                **payload,
                "readiness_fingerprint": fingerprint(payload),
            }
        )
    rows.sort(key=lambda row: row["reference_media_id"])
    write_parquet(args.output, rows)
    reason_counts = Counter(
        reason for row in rows for reason in row["blocking_reasons"]
    )
    decode_counts = Counter(row["decode_status"] for row in rows)
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "generated_at": args.generated_at,
        "status": "blocked_not_executed",
        "candidate_semantics": (
            "provider-asserted provisional support; no YOLOE or species decision"
        ),
        "counts": {
            "selected_reference_outcomes": len(rows),
            "decoded_objects": decode_counts["valid"],
            "download_or_decode_failures": len(rows) - decode_counts["valid"],
            "upstream_router_source_supported": sum(
                row["upstream_router_source_supported"] for row in rows
            ),
            "images_routed": 0,
            "human_verified_media": 0,
        },
        "decode_status_counts": dict(sorted(decode_counts.items())),
        "blocking_reason_counts": dict(sorted(reason_counts.items())),
        "runtime": {
            "execution_attempted": False,
            "torch_status": "unavailable_not_installed",
            "ultralytics_status": "unavailable_not_installed",
            "checkpoint_status": "unavailable_not_downloaded",
            "checkpoint_sha256": None,
            "model_revision": None,
            "routes_or_detections_published": False,
        },
        "upstream": {
            "pinned_biominer_sha": PINNED_BIOMINER_SHA,
            "pinned_route_schema_version": UPSTREAM_ROUTE_SCHEMA_VERSION,
            "pinned_router_source_scope": ["GBIF"],
            "observed_biominer_sha": OBSERVED_BIOMINER_SHA,
            "observed_final_report_sha256": OBSERVED_BIOMINER_REPORT_SHA256,
            "observed_goal_status": (
                "implementation_complete_with_live_scientific_work_pending"
            ),
            "live_gbif_support_bank_status": "pending_not_available_to_copy",
            "live_artifact_copied": False,
            "active_build_process_observed": False,
        },
        "artifact": artifact(
            args.output,
            rows=len(rows),
            manifest_path="gated/reference_yoloe_readiness.parquet",
        ),
        "inputs": {
            "selections_sha256": sha256_file(args.selections),
            "observations_sha256": sha256_file(args.observations),
            "media_objects_sha256": sha256_file(args.media_objects),
            "admission_manifest_sha256": sha256_file(args.admission_manifest),
        },
        "limitations": [
            "no YOLOE runtime, checkpoint, detection, route, or model claim exists",
            "the pinned BioMiner reference router rejects non-GBIF source rows",
            "the observed upstream final report says live GBIF acquisition is pending",
            "source objects remain in ignored local cache pending durable storage",
        ],
    }
    write_json(args.manifest_output, manifest)
    pack = json.loads(args.pack_manifest.read_text())
    pack["reference_state"].update(
        {
            "yoloe_status": manifest["status"],
            "yoloe_readiness_manifest_path": (
                "references/v1/reference_yoloe_readiness_manifest.json"
            ),
            "yoloe_readiness_manifest_sha256": sha256_file(args.manifest_output),
            "images_pending_yoloe": decode_counts["valid"],
            "images_routed": 0,
            "human_verified_media": 0,
        }
    )
    write_json(args.pack_manifest, pack)
    print(json.dumps(manifest["counts"], sort_keys=True))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--selections", type=Path, required=True)
    result.add_argument("--observations", type=Path, required=True)
    result.add_argument("--media-objects", type=Path, required=True)
    result.add_argument("--admission-manifest", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--manifest-output", type=Path, required=True)
    result.add_argument("--pack-manifest", type=Path, required=True)
    result.add_argument("--generated-at", required=True)
    return result


def main() -> int:
    try:
        build(parser().parse_args())
    except (KeyError, OSError, ValueError, RoutingReadinessError) as error:
        print(f"reference YOLOE readiness failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
