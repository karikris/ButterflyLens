"""Deterministic Australia geo/time partitions and complete page checkpoints."""

from __future__ import annotations

from copy import deepcopy
from math import ceil
import hashlib
import re
from typing import Iterable, Mapping

from butterflylens.contracts.fingerprint import canonicalize_json

from .query_plan import FLICKR_REST_ENDPOINT, FLICKR_SEARCH_METHOD


AUSTRALIA_PARTITION_SCHEMA_VERSION = "butterflylens-flickr-australia-partition:v1.0.0"
PARTITION_COUNT_CHECKPOINT_SCHEMA_VERSION = (
    "butterflylens-flickr-partition-count-checkpoint:v1.0.0"
)
PARTITION_PAGE_CHECKPOINT_SCHEMA_VERSION = (
    "butterflylens-flickr-partition-page-checkpoint:v1.0.0"
)
PARTITION_COMPLETION_SCHEMA_VERSION = (
    "butterflylens-flickr-partition-completion:v1.0.0"
)
FLICKR_GEO_RESULTS_PER_PAGE = 250
FLICKR_ACCESSIBLE_RESULT_LIMIT = 4000
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_RESERVED_PARTITION_PARAMETERS = frozenset(
    {"bbox", "has_geo", "min_upload_date", "max_upload_date", "page", "per_page"}
)


class PartitionError(ValueError):
    """Raised when a partition or checkpoint would be ambiguous or incomplete."""


def validate_australia_partition_scope(scope: Mapping[str, object]) -> None:
    """Validate the frozen ABS-derived national and state envelope inventory."""

    if scope.get("schema_version") != "butterflylens-australia-partition-scopes:v1.0.0":
        raise PartitionError("unsupported Australia partition scope version")
    national = _validate_bbox(scope.get("national_bbox"), "national_bbox")
    partitions = scope.get("partitions")
    if not isinstance(partitions, list) or len(partitions) != 9:
        raise PartitionError("Australia scope must contain nine state/territory partitions")
    source = scope.get("source")
    if not isinstance(source, dict) or _SHA256.fullmatch(str(source.get("physical_sha256"))) is None:
        raise PartitionError("Australia scope source checksum is invalid")
    codes: set[str] = set()
    bboxes: set[tuple[float, float, float, float]] = set()
    for partition in partitions:
        if not isinstance(partition, dict):
            raise PartitionError("state/territory partition must be an object")
        code = partition.get("state_code")
        name = partition.get("state_name")
        if not isinstance(code, str) or code in codes or not isinstance(name, str) or not name:
            raise PartitionError("state/territory code and name must be unique")
        codes.add(code)
        bbox = _validate_bbox(partition.get("bbox"), f"partition {code} bbox")
        if bbox in bboxes:
            raise PartitionError("duplicate state/territory physical envelope")
        bboxes.add(bbox)
        if not _bbox_within(bbox, national):
            raise PartitionError("state/territory envelope exceeds Australia scope")
    if codes != set("123456789"):
        raise PartitionError("state/territory code inventory is incomplete")


def seed_australia_state_partitions(
    physical_request: Mapping[str, object],
    scope: Mapping[str, object],
    *,
    min_upload_date: int,
    max_upload_date: int,
) -> tuple[dict[str, object], ...]:
    """Create one unsent full-time seed for each ABS state/territory envelope."""

    validate_australia_partition_scope(scope)
    _validate_base_request(physical_request)
    _validate_time_range(min_upload_date, max_upload_date)
    partitions = tuple(
        _make_partition(
            physical_request=physical_request,
            state_code=str(state["state_code"]),
            state_name=str(state["state_name"]),
            bbox=_validate_bbox(state["bbox"], "state bbox"),
            min_upload_date=min_upload_date,
            max_upload_date=max_upload_date,
            parent_partition_id=None,
            split_reason="state_seed",
            split_depth=0,
        )
        for state in scope["partitions"]
    )
    _assert_unique_physical_partitions(partitions)
    return tuple(sorted(partitions, key=lambda row: str(row["state_code"])))


def checkpoint_partition_count(
    partition: Mapping[str, object],
    *,
    total: int,
    source_response_fingerprint: str,
) -> dict[str, object]:
    """Record one count response and either split or enumerate every page."""

    _validate_partition(partition)
    if not isinstance(total, int) or isinstance(total, bool) or total < 0:
        raise PartitionError("partition total must be a non-negative integer")
    _validate_sha256(source_response_fingerprint, "source response fingerprint")
    split_required = total >= FLICKR_ACCESSIBLE_RESULT_LIMIT
    expected_pages = 0 if split_required else ceil(total / FLICKR_GEO_RESULTS_PER_PAGE)
    preimage = {
        "partition_fingerprint": partition["partition_fingerprint"],
        "total": total,
        "source_response_fingerprint": source_response_fingerprint,
        "split_required": split_required,
        "expected_pages": expected_pages,
    }
    digest = _digest(preimage)
    return {
        "schema_version": PARTITION_COUNT_CHECKPOINT_SCHEMA_VERSION,
        "count_checkpoint_id": f"blfc:v1:{digest[:24]}",
        "partition_id": partition["partition_id"],
        **preimage,
        "status": "split_required" if split_required else "page_plan_ready",
        "checkpoint_fingerprint": digest,
    }


def split_saturated_partition(
    partition: Mapping[str, object],
    count_checkpoint: Mapping[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    """Bisect time first, then the longest bbox axis at one-second saturation."""

    _validate_count_checkpoint(partition, count_checkpoint)
    if count_checkpoint["split_required"] is not True:
        raise PartitionError("partition has not reached the 4,000-result split boundary")
    minimum = int(partition["min_upload_date"])
    maximum = int(partition["max_upload_date"])
    bbox = _validate_bbox(partition["bbox"], "partition bbox")
    if minimum < maximum:
        midpoint = minimum + (maximum - minimum) // 2
        child_specs = (
            (bbox, minimum, midpoint),
            (bbox, midpoint + 1, maximum),
        )
        split_reason = "time_bisection"
    else:
        min_lon, min_lat, max_lon, max_lat = bbox
        longitude_span = max_lon - min_lon
        latitude_span = max_lat - min_lat
        if max(longitude_span, latitude_span) <= 0.000001:
            raise PartitionError("saturated partition reached minimum time and bbox precision")
        if longitude_span >= latitude_span:
            midpoint = (min_lon + max_lon) / 2
            boxes = (
                (min_lon, min_lat, midpoint, max_lat),
                (midpoint, min_lat, max_lon, max_lat),
            )
        else:
            midpoint = (min_lat + max_lat) / 2
            boxes = (
                (min_lon, min_lat, max_lon, midpoint),
                (min_lon, midpoint, max_lon, max_lat),
            )
        child_specs = tuple((box, minimum, maximum) for box in boxes)
        split_reason = "bbox_bisection"
    base_request = {
        "physical_query_request_id": partition["root_physical_query_request_id"],
        "request_fingerprint": partition["root_request_fingerprint"],
        "provider": "flickr",
        "method": FLICKR_SEARCH_METHOD,
        "endpoint": FLICKR_REST_ENDPOINT,
        "normalized_parameters": deepcopy(partition["base_parameters"]),
        "execution_state": "planned_not_sent",
    }
    children = tuple(
        _make_partition(
            physical_request=base_request,
            state_code=str(partition["state_code"]),
            state_name=str(partition["state_name"]),
            bbox=box,
            min_upload_date=child_minimum,
            max_upload_date=child_maximum,
            parent_partition_id=str(partition["partition_id"]),
            split_reason=split_reason,
            split_depth=int(partition["split_depth"]) + 1,
        )
        for box, child_minimum, child_maximum in child_specs
    )
    _assert_unique_physical_partitions(children)
    return children  # type: ignore[return-value]


def plan_partition_pages(
    partition: Mapping[str, object],
    count_checkpoint: Mapping[str, object],
) -> tuple[dict[str, object], ...]:
    """Create an exact, gap-free page checkpoint inventory below saturation."""

    _validate_count_checkpoint(partition, count_checkpoint)
    if count_checkpoint["split_required"] is True:
        raise PartitionError("saturated partition must split before paging")
    pages: list[dict[str, object]] = []
    for page in range(1, int(count_checkpoint["expected_pages"]) + 1):
        parameters = {**deepcopy(partition["normalized_parameters"]), "page": page}
        request_preimage = {
            "provider": "flickr",
            "method": FLICKR_SEARCH_METHOD,
            "endpoint": FLICKR_REST_ENDPOINT,
            "normalized_parameters": parameters,
        }
        request_fingerprint = _digest(request_preimage)
        checkpoint_preimage = {
            "partition_fingerprint": partition["partition_fingerprint"],
            "count_checkpoint_fingerprint": count_checkpoint["checkpoint_fingerprint"],
            "page": page,
            "cursor": None,
            "page_request_fingerprint": request_fingerprint,
        }
        checkpoint_fingerprint = _digest(checkpoint_preimage)
        pages.append(
            {
                "schema_version": PARTITION_PAGE_CHECKPOINT_SCHEMA_VERSION,
                "page_checkpoint_id": f"blfp:v1:{checkpoint_fingerprint[:24]}",
                "partition_id": partition["partition_id"],
                "count_checkpoint_id": count_checkpoint["count_checkpoint_id"],
                **checkpoint_preimage,
                "normalized_parameters": parameters,
                "pagination_mode": "page",
                "status": "pending",
                "source_response_fingerprint": None,
                "observed_total": None,
                "returned_count": None,
                "checkpoint_fingerprint": checkpoint_fingerprint,
            }
        )
    if len({row["page_request_fingerprint"] for row in pages}) != len(pages):
        raise PartitionError("duplicate physical page partition")
    return tuple(pages)


def complete_page_checkpoint(
    checkpoint: Mapping[str, object],
    *,
    source_response_fingerprint: str,
    observed_total: int,
    returned_count: int,
) -> dict[str, object]:
    """Complete one planned page without allowing total drift or oversize pages."""

    _validate_page_checkpoint(checkpoint)
    if checkpoint.get("status") != "pending":
        raise PartitionError("page checkpoint is not pending")
    _validate_sha256(source_response_fingerprint, "page response fingerprint")
    if (
        not isinstance(observed_total, int)
        or isinstance(observed_total, bool)
        or observed_total < 0
    ):
        raise PartitionError("observed page total is invalid")
    if (
        not isinstance(returned_count, int)
        or isinstance(returned_count, bool)
        or returned_count < 0
        or returned_count > FLICKR_GEO_RESULTS_PER_PAGE
    ):
        raise PartitionError("returned page count exceeds geo page size")
    completed = deepcopy(dict(checkpoint))
    completed.update(
        {
            "status": "succeeded",
            "source_response_fingerprint": source_response_fingerprint,
            "observed_total": observed_total,
            "returned_count": returned_count,
        }
    )
    return completed


def validate_partition_completion(
    partition: Mapping[str, object],
    count_checkpoint: Mapping[str, object],
    page_checkpoints: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    """Require every expected page, stable totals, and exact returned-row coverage."""

    _validate_count_checkpoint(partition, count_checkpoint)
    if count_checkpoint["split_required"] is True:
        raise PartitionError("saturated parent cannot be marked complete")
    pages = [deepcopy(dict(page)) for page in page_checkpoints]
    for page in pages:
        _validate_page_checkpoint(page)
        if page.get("partition_id") != partition.get("partition_id"):
            raise PartitionError("page checkpoint references another partition")
        if page.get("count_checkpoint_id") != count_checkpoint.get("count_checkpoint_id"):
            raise PartitionError("page checkpoint references another count checkpoint")
    expected_page_numbers = list(range(1, int(count_checkpoint["expected_pages"]) + 1))
    if sorted(page.get("page") for page in pages if isinstance(page.get("page"), int)) != expected_page_numbers:
        raise PartitionError("page checkpoint inventory has a gap or duplicate")
    pages.sort(key=lambda row: int(row["page"]))
    if any(page.get("status") != "succeeded" for page in pages):
        raise PartitionError("page checkpoint inventory is incomplete")
    expected_total = int(count_checkpoint["total"])
    if any(page.get("observed_total") != expected_total for page in pages):
        raise PartitionError("partition total drifted during page retrieval")
    if sum(int(page["returned_count"]) for page in pages) != expected_total:
        raise PartitionError("completed page row counts do not reconcile to total")
    response_fingerprints = [page.get("source_response_fingerprint") for page in pages]
    if any(not isinstance(value, str) or _SHA256.fullmatch(value) is None for value in response_fingerprints):
        raise PartitionError("completed page response fingerprint is invalid")
    preimage = {
        "partition_fingerprint": partition["partition_fingerprint"],
        "count_checkpoint_fingerprint": count_checkpoint["checkpoint_fingerprint"],
        "page_checkpoint_fingerprints": [
            page["checkpoint_fingerprint"] for page in pages
        ],
        "source_response_fingerprints": response_fingerprints,
        "total": expected_total,
    }
    digest = _digest(preimage)
    return {
        "schema_version": PARTITION_COMPLETION_SCHEMA_VERSION,
        "partition_completion_id": f"blpc:v1:{digest[:24]}",
        "partition_id": partition["partition_id"],
        **preimage,
        "status": "complete",
        "completion_fingerprint": digest,
    }


def _make_partition(
    *,
    physical_request: Mapping[str, object],
    state_code: str,
    state_name: str,
    bbox: tuple[float, float, float, float],
    min_upload_date: int,
    max_upload_date: int,
    parent_partition_id: str | None,
    split_reason: str,
    split_depth: int,
) -> dict[str, object]:
    base_parameters = deepcopy(dict(physical_request["normalized_parameters"]))
    if _RESERVED_PARTITION_PARAMETERS & set(base_parameters):
        raise PartitionError("base request already contains partition parameters")
    parameters = {
        **base_parameters,
        "bbox": _bbox_parameter(bbox),
        "has_geo": 1,
        "max_upload_date": max_upload_date,
        "min_upload_date": min_upload_date,
        "per_page": FLICKR_GEO_RESULTS_PER_PAGE,
    }
    physical_preimage = {
        "provider": "flickr",
        "method": FLICKR_SEARCH_METHOD,
        "endpoint": FLICKR_REST_ENDPOINT,
        "normalized_parameters": parameters,
    }
    fingerprint = _digest(physical_preimage)
    return {
        "schema_version": AUSTRALIA_PARTITION_SCHEMA_VERSION,
        "partition_id": f"blap:v1:{fingerprint[:24]}",
        "root_physical_query_request_id": physical_request["physical_query_request_id"],
        "root_request_fingerprint": physical_request["request_fingerprint"],
        "parent_partition_id": parent_partition_id,
        "state_code": state_code,
        "state_name": state_name,
        "bbox": list(bbox),
        "min_upload_date": min_upload_date,
        "max_upload_date": max_upload_date,
        "split_reason": split_reason,
        "split_depth": split_depth,
        "base_parameters": base_parameters,
        **physical_preimage,
        "partition_fingerprint": fingerprint,
        "pagination": {
            "mode": "page",
            "results_per_page": FLICKR_GEO_RESULTS_PER_PAGE,
            "accessible_result_limit": FLICKR_ACCESSIBLE_RESULT_LIMIT,
        },
        "execution_state": "planned_not_sent",
    }


def _validate_base_request(request: Mapping[str, object]) -> None:
    required = {
        "physical_query_request_id",
        "request_fingerprint",
        "provider",
        "method",
        "endpoint",
        "normalized_parameters",
        "execution_state",
    }
    if required - set(request):
        raise PartitionError("physical request is incomplete")
    if request["provider"] != "flickr" or request["method"] != FLICKR_SEARCH_METHOD:
        raise PartitionError("partition source is not Flickr photo search")
    if request["endpoint"] != FLICKR_REST_ENDPOINT:
        raise PartitionError("partition source endpoint is unsupported")
    if request["execution_state"] != "planned_not_sent":
        raise PartitionError("only unsent physical requests may be partitioned")
    _validate_sha256(str(request["request_fingerprint"]), "root request fingerprint")
    if not isinstance(request["normalized_parameters"], dict):
        raise PartitionError("root request parameters must be an object")
    expected = _digest(
        {
            "provider": request["provider"],
            "method": request["method"],
            "endpoint": request["endpoint"],
            "normalized_parameters": request["normalized_parameters"],
        }
    )
    if request["request_fingerprint"] != expected:
        raise PartitionError("root request fingerprint mismatch")


def _validate_partition(partition: Mapping[str, object]) -> None:
    if partition.get("schema_version") != AUSTRALIA_PARTITION_SCHEMA_VERSION:
        raise PartitionError("unsupported partition version")
    _validate_sha256(str(partition.get("partition_fingerprint")), "partition fingerprint")
    _validate_bbox(partition.get("bbox"), "partition bbox")
    _validate_time_range(partition.get("min_upload_date"), partition.get("max_upload_date"))
    if partition.get("execution_state") != "planned_not_sent":
        raise PartitionError("partition is not in planned-not-sent state")
    base_parameters = partition.get("base_parameters")
    normalized_parameters = partition.get("normalized_parameters")
    if not isinstance(base_parameters, dict) or not isinstance(normalized_parameters, dict):
        raise PartitionError("partition parameters must be objects")
    expected_parameters = {
        **base_parameters,
        "bbox": _bbox_parameter(_validate_bbox(partition["bbox"], "partition bbox")),
        "has_geo": 1,
        "max_upload_date": partition["max_upload_date"],
        "min_upload_date": partition["min_upload_date"],
        "per_page": FLICKR_GEO_RESULTS_PER_PAGE,
    }
    if normalized_parameters != expected_parameters:
        raise PartitionError("partition parameters do not match its declared scope")
    expected_fingerprint = _digest(
        {
            "provider": "flickr",
            "method": FLICKR_SEARCH_METHOD,
            "endpoint": FLICKR_REST_ENDPOINT,
            "normalized_parameters": normalized_parameters,
        }
    )
    if partition["partition_fingerprint"] != expected_fingerprint:
        raise PartitionError("partition fingerprint mismatch")
    if partition.get("partition_id") != f"blap:v1:{expected_fingerprint[:24]}":
        raise PartitionError("partition ID mismatch")


def _validate_count_checkpoint(
    partition: Mapping[str, object], checkpoint: Mapping[str, object]
) -> None:
    _validate_partition(partition)
    if checkpoint.get("schema_version") != PARTITION_COUNT_CHECKPOINT_SCHEMA_VERSION:
        raise PartitionError("unsupported count checkpoint version")
    if checkpoint.get("partition_id") != partition.get("partition_id"):
        raise PartitionError("count checkpoint references another partition")
    if checkpoint.get("partition_fingerprint") != partition.get("partition_fingerprint"):
        raise PartitionError("count checkpoint partition fingerprint mismatch")
    total = checkpoint.get("total")
    if not isinstance(total, int) or isinstance(total, bool) or total < 0:
        raise PartitionError("count checkpoint total is invalid")
    split_required = total >= FLICKR_ACCESSIBLE_RESULT_LIMIT
    expected_pages = 0 if split_required else ceil(total / FLICKR_GEO_RESULTS_PER_PAGE)
    if (
        checkpoint.get("split_required") is not split_required
        or checkpoint.get("expected_pages") != expected_pages
        or checkpoint.get("status")
        != ("split_required" if split_required else "page_plan_ready")
    ):
        raise PartitionError("count checkpoint decision is inconsistent")
    response_fingerprint = checkpoint.get("source_response_fingerprint")
    if not isinstance(response_fingerprint, str):
        raise PartitionError("count checkpoint response fingerprint is invalid")
    _validate_sha256(response_fingerprint, "count checkpoint response fingerprint")
    preimage = {
        "partition_fingerprint": partition["partition_fingerprint"],
        "total": total,
        "source_response_fingerprint": response_fingerprint,
        "split_required": split_required,
        "expected_pages": expected_pages,
    }
    expected_fingerprint = _digest(preimage)
    if checkpoint.get("checkpoint_fingerprint") != expected_fingerprint:
        raise PartitionError("count checkpoint fingerprint mismatch")
    if checkpoint.get("count_checkpoint_id") != f"blfc:v1:{expected_fingerprint[:24]}":
        raise PartitionError("count checkpoint ID mismatch")


def _validate_page_checkpoint(checkpoint: Mapping[str, object]) -> None:
    if checkpoint.get("schema_version") != PARTITION_PAGE_CHECKPOINT_SCHEMA_VERSION:
        raise PartitionError("unsupported page checkpoint version")
    page = checkpoint.get("page")
    if not isinstance(page, int) or isinstance(page, bool) or page < 1:
        raise PartitionError("page checkpoint page is invalid")
    if checkpoint.get("cursor") is not None or checkpoint.get("pagination_mode") != "page":
        raise PartitionError("photo search checkpoint must use page pagination")
    parameters = checkpoint.get("normalized_parameters")
    if not isinstance(parameters, dict) or parameters.get("page") != page:
        raise PartitionError("page checkpoint parameters are inconsistent")
    request_fingerprint = _digest(
        {
            "provider": "flickr",
            "method": FLICKR_SEARCH_METHOD,
            "endpoint": FLICKR_REST_ENDPOINT,
            "normalized_parameters": parameters,
        }
    )
    if checkpoint.get("page_request_fingerprint") != request_fingerprint:
        raise PartitionError("page request fingerprint mismatch")
    preimage = {
        "partition_fingerprint": checkpoint.get("partition_fingerprint"),
        "count_checkpoint_fingerprint": checkpoint.get("count_checkpoint_fingerprint"),
        "page": page,
        "cursor": None,
        "page_request_fingerprint": request_fingerprint,
    }
    expected = _digest(preimage)
    if checkpoint.get("checkpoint_fingerprint") != expected:
        raise PartitionError("page checkpoint fingerprint mismatch")
    if checkpoint.get("page_checkpoint_id") != f"blfp:v1:{expected[:24]}":
        raise PartitionError("page checkpoint ID mismatch")


def _validate_bbox(value: object, label: str) -> tuple[float, float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise PartitionError(f"{label} must contain four coordinates")
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value):
        raise PartitionError(f"{label} coordinates must be numeric")
    min_lon, min_lat, max_lon, max_lat = (float(item) for item in value)
    if not (-180 <= min_lon < max_lon <= 180 and -90 <= min_lat < max_lat <= 90):
        raise PartitionError(f"{label} coordinate order or range is invalid")
    return min_lon, min_lat, max_lon, max_lat


def _bbox_within(
    child: tuple[float, float, float, float], parent: tuple[float, float, float, float]
) -> bool:
    return (
        parent[0] <= child[0]
        and parent[1] <= child[1]
        and child[2] <= parent[2]
        and child[3] <= parent[3]
    )


def _bbox_parameter(bbox: tuple[float, float, float, float]) -> str:
    return ",".join(format(value, ".8f").rstrip("0").rstrip(".") for value in bbox)


def _validate_time_range(minimum: object, maximum: object) -> None:
    if (
        not isinstance(minimum, int)
        or isinstance(minimum, bool)
        or not isinstance(maximum, int)
        or isinstance(maximum, bool)
        or minimum < 0
        or minimum > maximum
    ):
        raise PartitionError("upload-date range must be ordered non-negative Unix seconds")


def _validate_sha256(value: str, label: str) -> None:
    if _SHA256.fullmatch(value) is None:
        raise PartitionError(f"{label} must be lowercase SHA-256")


def _assert_unique_physical_partitions(partitions: Iterable[Mapping[str, object]]) -> None:
    fingerprints = [str(partition["partition_fingerprint"]) for partition in partitions]
    if len(fingerprints) != len(set(fingerprints)):
        raise PartitionError("duplicate physical partition")


def _digest(value: object) -> str:
    return hashlib.sha256(canonicalize_json(value)).hexdigest()
