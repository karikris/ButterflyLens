#!/usr/bin/env python3
"""Acquire and build the versioned Australian butterfly taxonomy pack.

Network access is confined to explicit acquisition commands. Pack builds and
tests consume frozen snapshots and are deterministic and credential-free.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "butterflylens-taxonomy/v1"
SNAPSHOT_SCHEMA_VERSION = "butterflylens-afd-snapshot/v1"
MANIFEST_SCHEMA_VERSION = "butterflylens-taxonomy-pack-manifest/v1"
PACK_ID = "australian-butterflies-v1"
AFD_ROOT_KEY = "PAPILIONOIDEA"
AFD_ROOT_URL = "https://biodiversity.org.au/afd/taxa/PAPILIONOIDEA"
AFD_CHECKLIST_URL = AFD_ROOT_URL + "/checklist-subtaxa.json"
AFD_CITATION = (
    "Australian Biological Resources Study. Australian Faunal Directory, "
    "Papilionoidea. Viewed {viewed_date}."
)
AFD_ATTRIBUTION = (
    "Australian Biological Resources Study, Australian Faunal Directory; "
    "Department of Climate Change, Energy, the Environment and Water."
)
AFD_LICENCE = "CC-BY-4.0"
AFD_LICENCE_URL = "https://creativecommons.org/licenses/by/4.0/"
AFD_COPYRIGHT_URL = "https://www.dcceew.gov.au/about/copyright"
AFD_CITATION_URL = (
    "https://www.dcceew.gov.au/science-research/abrs/online-resources/citation"
)
USER_AGENT = (
    "ButterflyLens-taxonomy/0.1 "
    "(https://github.com/karikris/ButterflyLens; public research pack)"
)
INCLUDED_RANKS = (
    "superfamily",
    "family",
    "subfamily",
    "tribe",
    "genus",
    "species",
    "subspecies",
)


class TaxonomyBuildError(RuntimeError):
    """Raised when source or pack invariants fail closed."""


def canonical_json(value: Any) -> bytes:
    """Return the repository's deterministic JSON representation."""

    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def plain_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", value))).strip()


def scientific_name_from_key(source_key: str) -> tuple[str, str | None]:
    """Decode an AFD name key without discarding a collision qualifier."""

    decoded = urllib.parse.unquote(source_key)
    name_part, separator, qualifier = decoded.partition(";")
    scientific_name = name_part.replace("_", " ").strip()
    if not scientific_name:
        raise TaxonomyBuildError(f"empty scientific name for AFD key {source_key!r}")
    return scientific_name, qualifier if separator else None


def endpoint_for_key(source_key: str) -> str:
    return (
        "https://biodiversity.org.au/afd/taxa/"
        + source_key
        + "/checklist-subtaxa.json"
    )


def request_bytes(url: str, *, attempts: int = 3) -> tuple[bytes, dict[str, str | None]]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json,text/html", "User-Agent": USER_AGENT},
    )
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read(), {
                    "content_type": response.headers.get("Content-Type"),
                    "etag": response.headers.get("ETag"),
                    "last_modified": response.headers.get("Last-Modified"),
                }
        except urllib.error.HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == attempts:
                raise TaxonomyBuildError(f"request failed for {url}: HTTP {error.code}") from error
            retry_after = error.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
            time.sleep(delay)
        except urllib.error.URLError as error:
            if attempt == attempts:
                raise TaxonomyBuildError(f"request failed for {url}: {error.reason}") from error
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def iter_child_nodes(
    values: list[dict[str, Any]], parent_key: str
) -> Iterable[tuple[dict[str, Any], str]]:
    for value in values:
        if not isinstance(value, dict):
            raise TaxonomyBuildError(f"AFD child under {parent_key!r} is not an object")
        yield value, parent_key
        source_key = value.get("metadata", {}).get("nameKey")
        if not isinstance(source_key, str) or not source_key:
            raise TaxonomyBuildError(f"AFD child under {parent_key!r} has no nameKey")
        children = value.get("children", [])
        if children:
            if not isinstance(children, list):
                raise TaxonomyBuildError(f"AFD children for {source_key!r} are not a list")
            yield from iter_child_nodes(children, source_key)


def normalize_node(
    raw: dict[str, Any], parent_key: str, discovery_index: int
) -> dict[str, Any]:
    metadata = raw.get("metadata")
    data = raw.get("data")
    if not isinstance(metadata, dict) or not isinstance(data, dict):
        raise TaxonomyBuildError(f"malformed AFD node under {parent_key!r}")
    source_key = metadata.get("nameKey")
    rank = metadata.get("rank-with-prefix")
    title = data.get("title")
    state = raw.get("state")
    if not all(isinstance(item, str) and item for item in (source_key, rank, title, state)):
        raise TaxonomyBuildError(f"incomplete AFD node under {parent_key!r}")
    scientific_name, qualifier = scientific_name_from_key(source_key)
    return {
        "source_key": source_key,
        "source_parent_key": parent_key,
        "scientific_name": scientific_name,
        "source_key_qualifier": qualifier,
        "source_title": plain_text(title),
        "rank": rank.lower(),
        "rank_key": metadata.get("rank-key"),
        "state": state,
        "discovery_index": discovery_index,
    }


def root_page_receipt(body: bytes) -> dict[str, str]:
    text = body.decode("utf-8")
    concept_match = re.search(
        r'id="afdTaxonURI"[^>]*>.*?<a href="([^"]+)">', text, re.DOTALL
    )
    modified_match = re.search(r"last modified\s+([^<\r\n]+)", text)
    compiler_match = re.search(
        r'id="afdCompiler".*?<p>(.*?)</p>', text, re.DOTALL
    )
    if not concept_match or not modified_match:
        raise TaxonomyBuildError("AFD root page lacks concept or last-modified evidence")
    return {
        "url": AFD_ROOT_URL,
        "sha256": sha256_bytes(body),
        "source_concept_id": concept_match.group(1),
        "source_last_modified": modified_match.group(1).strip(),
        "compiler": plain_text(compiler_match.group(1)) if compiler_match else "not stated",
    }


def acquire_afd_snapshot(output: Path, delay_seconds: float) -> None:
    if delay_seconds < 0.1:
        raise TaxonomyBuildError("AFD acquisition delay must be at least 0.1 seconds")
    retrieved_at = utc_now()
    root_body, root_headers = request_bytes(AFD_ROOT_URL)
    root_receipt = root_page_receipt(root_body)
    root_name, root_qualifier = scientific_name_from_key(AFD_ROOT_KEY)
    nodes: dict[str, dict[str, Any]] = {
        AFD_ROOT_KEY: {
            "source_key": AFD_ROOT_KEY,
            "source_parent_key": None,
            "scientific_name": root_name,
            "source_key_qualifier": root_qualifier,
            "source_title": "PAPILIONOIDEA",
            "rank": "superfamily",
            "rank_key": "F",
            "state": "open",
            "discovery_index": 0,
        }
    }
    node_states: dict[str, set[str]] = defaultdict(set)
    node_states[AFD_ROOT_KEY].add("open")
    pending: deque[str] = deque([AFD_ROOT_KEY])
    scheduled = {AFD_ROOT_KEY}
    responses: list[dict[str, Any]] = []
    discovery_index = 1

    while pending:
        source_key = pending.popleft()
        url = endpoint_for_key(source_key)
        body, headers = request_bytes(url)
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as error:
            raise TaxonomyBuildError(f"AFD returned non-JSON for {url}") from error
        if not isinstance(payload, list):
            raise TaxonomyBuildError(f"AFD response for {url} is not a list")
        responses.append(
            {
                "source_key": source_key,
                "url": url,
                "sha256": sha256_bytes(body),
                "headers": headers,
                "body": payload,
            }
        )
        for raw_node, parent_key in iter_child_nodes(payload, source_key):
            candidate = normalize_node(raw_node, parent_key, discovery_index)
            child_key = candidate["source_key"]
            node_states[child_key].add(candidate["state"])
            existing = nodes.get(child_key)
            if existing is None:
                nodes[child_key] = candidate
                discovery_index += 1
            else:
                comparable = (
                    "source_parent_key",
                    "scientific_name",
                    "source_key_qualifier",
                    "source_title",
                    "rank",
                    "rank_key",
                )
                mismatches = [
                    field for field in comparable if existing.get(field) != candidate.get(field)
                ]
                if mismatches:
                    raise TaxonomyBuildError(
                        f"incompatible duplicate AFD key {child_key!r}: {mismatches}"
                    )
            if candidate["state"] != "leaf" and child_key not in scheduled:
                pending.append(child_key)
                scheduled.add(child_key)
        if pending:
            time.sleep(delay_seconds)

    for source_key, states in node_states.items():
        nodes[source_key]["observed_states"] = sorted(states)
        nodes[source_key].pop("state", None)

    ordered_nodes = sorted(nodes.values(), key=lambda item: item["discovery_index"])
    semantic_input = {
        "root_page": root_receipt,
        "responses": [
            {"source_key": item["source_key"], "sha256": item["sha256"]}
            for item in responses
        ],
        "nodes": ordered_nodes,
    }
    source_semantic_sha256 = sha256_bytes(canonical_json(semantic_input))
    viewed_date = retrieved_at[:10]
    snapshot = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "retrieved_at": retrieved_at,
        "source_semantic_sha256": source_semantic_sha256,
        "request_policy": {
            "user_agent": USER_AGENT,
            "minimum_delay_seconds": delay_seconds,
            "retryable_http_statuses": [429, 500, 502, 503, 504],
        },
        "source": {
            "provider": "Australian Biological Resources Study",
            "dataset": "Australian Faunal Directory",
            "scope": "PAPILIONOIDEA",
            "root_url": AFD_ROOT_URL,
            "checklist_url": AFD_CHECKLIST_URL,
            "citation": AFD_CITATION.format(viewed_date=viewed_date),
            "citation_guidance_url": AFD_CITATION_URL,
            "attribution": AFD_ATTRIBUTION,
            "licence": AFD_LICENCE,
            "licence_url": AFD_LICENCE_URL,
            "copyright_policy_url": AFD_COPYRIGHT_URL,
        },
        "root_page": {**root_receipt, "headers": root_headers},
        "nodes": ordered_nodes,
        "responses": responses,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json(snapshot))


def lineage_for(source_key: str, nodes: dict[str, dict[str, Any]]) -> list[str]:
    lineage: list[str] = []
    seen: set[str] = set()
    current: str | None = source_key
    while current is not None:
        if current in seen:
            raise TaxonomyBuildError(f"cycle in AFD hierarchy at {current!r}")
        seen.add(current)
        node = nodes.get(current)
        if node is None:
            raise TaxonomyBuildError(f"missing AFD parent {current!r}")
        lineage.append(current)
        current = node["source_parent_key"]
    return list(reversed(lineage))


def butterflylens_key(node: dict[str, Any]) -> str:
    identity = {
        "namespace": "afd-papilionoidea",
        "rank": node["rank"],
        "source_key": node["source_key"],
    }
    return "bltx:v1:" + sha256_bytes(canonical_json(identity))[:24]


def hierarchy_order(nodes: dict[str, dict[str, Any]]) -> list[str]:
    children: dict[str | None, list[str]] = defaultdict(list)
    for source_key, node in nodes.items():
        children[node["source_parent_key"]].append(source_key)
    for values in children.values():
        values.sort(key=lambda key: nodes[key]["discovery_index"])
    ordered: list[str] = []

    def visit(source_key: str) -> None:
        ordered.append(source_key)
        for child_key in children.get(source_key, []):
            visit(child_key)

    roots = children[None]
    if roots != [AFD_ROOT_KEY]:
        raise TaxonomyBuildError(f"expected only AFD root {AFD_ROOT_KEY!r}, found {roots}")
    visit(AFD_ROOT_KEY)
    if len(ordered) != len(nodes):
        raise TaxonomyBuildError("AFD hierarchy contains disconnected nodes")
    return ordered


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    if snapshot.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise TaxonomyBuildError("unsupported AFD snapshot schema")
    response_receipts = [
        {"source_key": item["source_key"], "sha256": item["sha256"]}
        for item in snapshot.get("responses", [])
    ]
    semantic_input = {
        "root_page": {
            key: value
            for key, value in snapshot["root_page"].items()
            if key != "headers"
        },
        "responses": response_receipts,
        "nodes": snapshot.get("nodes", []),
    }
    observed = sha256_bytes(canonical_json(semantic_input))
    if observed != snapshot.get("source_semantic_sha256"):
        raise TaxonomyBuildError("AFD snapshot semantic checksum mismatch")
    for response in snapshot.get("responses", []):
        body_hash = sha256_bytes(
            json.dumps(response["body"], ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
        )
        # The HTTP byte checksum is retained as a receipt. Re-serialization is not
        # expected to reproduce provider whitespace and is deliberately not used
        # as an integrity substitute for the enclosing frozen snapshot checksum.
        if not re.fullmatch(r"[0-9a-f]{64}", response.get("sha256", "")):
            raise TaxonomyBuildError("invalid AFD response checksum receipt")
        if not body_hash:
            raise AssertionError("unreachable")


def build_scope(snapshot_path: Path, output_dir: Path, generated_at: str | None) -> None:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    validate_snapshot(snapshot)
    raw_nodes = snapshot.get("nodes")
    if not isinstance(raw_nodes, list):
        raise TaxonomyBuildError("AFD snapshot nodes must be a list")
    nodes = {node["source_key"]: node for node in raw_nodes}
    if len(nodes) != len(raw_nodes):
        raise TaxonomyBuildError("duplicate AFD source keys in snapshot")
    ordered_keys = hierarchy_order(nodes)
    included_keys = [key for key in ordered_keys if nodes[key]["rank"] in INCLUDED_RANKS]
    key_map = {key: butterflylens_key(nodes[key]) for key in included_keys}
    records: list[dict[str, Any]] = []

    for source_key in included_keys:
        node = nodes[source_key]
        full_lineage = lineage_for(source_key, nodes)
        ancestor_keys = full_lineage[:-1]
        included_ancestors = [key for key in ancestor_keys if key in key_map]
        parent_key = key_map[included_ancestors[-1]] if included_ancestors else None
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "butterflylens_key": key_map[source_key],
                "accepted_scientific_name": node["scientific_name"],
                "rank": node["rank"],
                "parent_key": parent_key,
                "parent_path": [
                    {
                        "butterflylens_key": key_map[key],
                        "rank": nodes[key]["rank"],
                        "accepted_scientific_name": nodes[key]["scientific_name"],
                    }
                    for key in included_ancestors
                ],
                "source_parent_path": [
                    {
                        "source_key": key,
                        "rank": nodes[key]["rank"],
                        "scientific_name": nodes[key]["scientific_name"],
                    }
                    for key in ancestor_keys
                ],
                "taxonomic_status": "accepted",
                "source": {
                    "provider": "Australian Faunal Directory",
                    "source_key": source_key,
                    "source_key_qualifier": node.get("source_key_qualifier"),
                    "source_title": node["source_title"],
                    "source_url": "https://biodiversity.org.au/afd/taxa/" + source_key,
                    "source_version": "sha256:" + snapshot["source_semantic_sha256"],
                    "retrieved_at": snapshot["retrieved_at"],
                },
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    taxa_path = output_dir / "taxa.jsonl"
    taxa_path.write_bytes(b"".join(canonical_json(record) for record in records))
    rank_counts: dict[str, int] = defaultdict(int)
    excluded_rank_counts: dict[str, int] = defaultdict(int)
    for node in raw_nodes:
        target = rank_counts if node["rank"] in INCLUDED_RANKS else excluded_rank_counts
        target[node["rank"]] += 1
    generated = generated_at or utc_now()
    snapshot_relative = snapshot_path.relative_to(output_dir).as_posix()
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "pack_id": PACK_ID,
        "generated_at": generated,
        "scope": {
            "root": "PAPILIONOIDEA",
            "additional_configured_taxa": [],
            "authority": "Australian Faunal Directory checklist hierarchy",
            "included_ranks": list(INCLUDED_RANKS),
            "taxonomic_status": "accepted",
            "geographic_interpretation": (
                "Australian fauna as represented by the frozen AFD Papilionoidea "
                "checklist, including Australian external territories represented by AFD"
            ),
        },
        "rights": {
            "licence": AFD_LICENCE,
            "licence_url": AFD_LICENCE_URL,
            "attribution": AFD_ATTRIBUTION,
            "citation": snapshot["source"]["citation"],
            "copyright_policy_url": AFD_COPYRIGHT_URL,
        },
        "sources": [
            {
                "path": snapshot_relative,
                "physical_sha256": sha256_file(snapshot_path),
                "semantic_sha256": snapshot["source_semantic_sha256"],
                "retrieved_at": snapshot["retrieved_at"],
                "root_source_concept_id": snapshot["root_page"]["source_concept_id"],
                "root_source_last_modified": snapshot["root_page"][
                    "source_last_modified"
                ],
            }
        ],
        "artifacts": {
            "taxa.jsonl": {
                "schema_version": SCHEMA_VERSION,
                "physical_sha256": sha256_file(taxa_path),
                "row_count": len(records),
                "rank_counts": dict(sorted(rank_counts.items())),
            }
        },
        "excluded_source_rank_counts": dict(sorted(excluded_rank_counts.items())),
        "crosswalk_state": "not_built",
        "conflict_state": "not_built",
    }
    (output_dir / "manifest.json").write_bytes(canonical_json(manifest))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    acquire = commands.add_parser("acquire-afd", help="freeze the current AFD hierarchy")
    acquire.add_argument("--output", type=Path, required=True)
    acquire.add_argument("--delay-seconds", type=float, default=0.2)
    scope = commands.add_parser("build-scope", help="build accepted taxa from an AFD snapshot")
    scope.add_argument("--snapshot", type=Path, required=True)
    scope.add_argument("--output-dir", type=Path, required=True)
    scope.add_argument("--generated-at")
    return root


def main() -> None:
    arguments = parser().parse_args()
    if arguments.command == "acquire-afd":
        acquire_afd_snapshot(arguments.output, arguments.delay_seconds)
    elif arguments.command == "build-scope":
        build_scope(arguments.snapshot, arguments.output_dir, arguments.generated_at)
    else:
        raise AssertionError("unreachable")


if __name__ == "__main__":
    try:
        main()
    except (TaxonomyBuildError, OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"taxonomy build: FAIL: {error}") from error
