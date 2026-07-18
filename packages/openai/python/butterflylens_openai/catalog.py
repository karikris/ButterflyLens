"""Strict model-facing contracts for the ButterflyLens evidence tools."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


CONTRACT_SCHEMA_VERSION = "butterflylens-openai-tool-contracts:v1.0.0"
RESULT_SCHEMA_VERSION = "butterflylens-openai-tool-result:v1.0.0"

TOOL_ORDER = (
    "inspect_map_scope",
    "compare_ala_and_flickr",
    "inspect_species",
    "inspect_flickr_candidate",
    "trace_record_evidence",
    "explain_classification",
    "inspect_review_consensus",
    "inspect_reviewer_quality",
    "inspect_pipeline_status",
    "inspect_worker_status",
    "recommend_next_review_batch",
    "recommend_next_species",
    "explain_geographic_contribution",
    "prepare_impact_report",
)

_DESCRIPTIONS = {
    "inspect_map_scope": (
        "Inspect the governed submitted map scope and its ALA/Flickr evidence "
        "availability. Missing counts are unavailable, never biological absence."
    ),
    "compare_ala_and_flickr": (
        "Compare admitted ALA baseline and Flickr candidate counts only when both "
        "exist for the same exact scope and optional accepted species."
    ),
    "inspect_species": (
        "Inspect one accepted ButterflyLens species by stable key or exact accepted "
        "scientific name, including sourced names, conflicts, and evidence maturity."
    ),
    "inspect_flickr_candidate": (
        "Inspect one governed Flickr candidate by immutable candidate ID; never "
        "fetch Flickr or infer a species from imagery or metadata."
    ),
    "trace_record_evidence": (
        "Trace the stored artifact lineage for one record without inventing missing "
        "steps or treating source assertions as verification."
    ),
    "explain_classification": (
        "Explain one stored classification and its evidence maturity. Raw scores are "
        "not probabilities and no classification is made by this tool."
    ),
    "inspect_review_consensus": (
        "Inspect one stored review consensus without exposing reviewer identities, "
        "private controls, or treating vote count alone as accuracy."
    ),
    "inspect_reviewer_quality": (
        "Inspect the authenticated reviewer's own governed quality snapshot. Model "
        "arguments cannot select another reviewer or grant access."
    ),
    "inspect_pipeline_status": (
        "Inspect committed submitted pipeline stages and explicit unfinished or "
        "unavailable live lanes; never inspect an active provider run."
    ),
    "inspect_worker_status": (
        "Inspect a committed governed worker heartbeat. No heartbeat means unavailable, "
        "not silently online or offline."
    ),
    "recommend_next_review_batch": (
        "Recommend a bounded deterministic species-level reference-review batch from "
        "committed diagnostics; it is targeted work, not a quality or species ranking."
    ),
    "recommend_next_species": (
        "Recommend bounded accepted-species priorities using one explicit committed "
        "workflow criterion; never infer rarity, presence, or scientific importance."
    ),
    "explain_geographic_contribution": (
        "Explain the authenticated contributor's governed aggregate contribution for "
        "one public scope; potential contribution is not a new occurrence."
    ),
    "prepare_impact_report": (
        "Prepare the authenticated contributor's evidence-based self report without "
        "rankings, speed metrics, private controls, or scientific authority."
    ),
}


def _object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


_IDENTIFIER = {
    "type": "string",
    "minLength": 1,
    "maxLength": 180,
    "pattern": r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$",
}
_NULLABLE_IDENTIFIER = {
    "type": ["string", "null"],
    "minLength": 1,
    "maxLength": 180,
    "pattern": r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$",
}
_NULLABLE_TEXT = {"type": ["string", "null"], "minLength": 1, "maxLength": 240}
_SCOPE_TYPE = {"type": "string", "enum": ["national", "state", "ibra", "lga", "h3"]}
_LIMIT = {"type": "integer", "minimum": 1, "maximum": 20}

_SCOPE_PROPERTIES = {
    "scope_type": deepcopy(_SCOPE_TYPE),
    "scope_id": deepcopy(_NULLABLE_IDENTIFIER),
}

_INPUT_SCHEMAS = {
    "inspect_map_scope": _object(deepcopy(_SCOPE_PROPERTIES)),
    "compare_ala_and_flickr": _object(
        {
            **deepcopy(_SCOPE_PROPERTIES),
            "species_key": deepcopy(_NULLABLE_IDENTIFIER),
        }
    ),
    "inspect_species": _object(
        {
            "species_key": deepcopy(_NULLABLE_IDENTIFIER),
            "scientific_name": deepcopy(_NULLABLE_TEXT),
        }
    ),
    "inspect_flickr_candidate": _object({"candidate_id": deepcopy(_IDENTIFIER)}),
    "trace_record_evidence": _object(
        {
            "record_type": {
                "type": "string",
                "enum": [
                    "species",
                    "ala_occurrence",
                    "flickr_candidate",
                    "classification",
                    "review_consensus",
                    "worker",
                    "contribution",
                ],
            },
            "record_id": deepcopy(_IDENTIFIER),
        }
    ),
    "explain_classification": _object(
        {"classification_id": deepcopy(_IDENTIFIER)}
    ),
    "inspect_review_consensus": _object({"item_id": deepcopy(_IDENTIFIER)}),
    "inspect_reviewer_quality": _object(
        {
            "subject": {"type": "string", "enum": ["self"]},
            "domain_key": deepcopy(_NULLABLE_IDENTIFIER),
        }
    ),
    "inspect_pipeline_status": _object(
        {"pipeline_id": deepcopy(_NULLABLE_IDENTIFIER)}
    ),
    "inspect_worker_status": _object({"worker_id": deepcopy(_NULLABLE_IDENTIFIER)}),
    "recommend_next_review_batch": _object(
        {
            **deepcopy(_SCOPE_PROPERTIES),
            "species_key": deepcopy(_NULLABLE_IDENTIFIER),
            "limit": deepcopy(_LIMIT),
        }
    ),
    "recommend_next_species": _object(
        {
            "criterion": {
                "type": "string",
                "enum": ["reference_gap", "open_conflicts", "reviewable_reference"],
            },
            "limit": deepcopy(_LIMIT),
        }
    ),
    "explain_geographic_contribution": _object(deepcopy(_SCOPE_PROPERTIES)),
    "prepare_impact_report": _object(
        {"report_scope": {"type": "string", "enum": ["self"]}}
    ),
}

_SEMANTIC_RULES = {
    "scope": (
        "scope_id must be null for national scope and non-null for state, IBRA, "
        "LGA, and H3 scopes"
    ),
    "inspect_species": (
        "exactly one of species_key and scientific_name must be non-null; "
        "scientific_name is an exact accepted-name lookup"
    ),
    "private_tools": (
        "reviewer quality, geographic contribution, and impact report are bound to "
        "server authorization context; arguments cannot name or authorize another person"
    ),
}

_CITATION_SCHEMA = _object(
    {
        "artifact_id": deepcopy(_IDENTIFIER),
        "repository": {"type": "string", "const": "karikris/ButterflyLens"},
        "commit": {"type": "string", "pattern": r"^[0-9a-f]{40}$"},
        "path": {"type": "string", "minLength": 1, "maxLength": 300},
        "fingerprint": {"type": "string", "pattern": r"^sha256:[0-9a-f]{64}$"},
    }
)

_FACT_SCHEMA = _object(
    {
        "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100,
            "pattern": r"^[a-z][a-z0-9_]*$",
        },
        "state": {
            "type": "string",
            "enum": [
                "observed",
                "derived",
                "unavailable",
                "withheld",
                "unfinished",
                "conflict",
                "not_applicable",
            ],
        },
        "value": {"type": ["string", "integer", "number", "boolean", "null"]},
        "unit": {"type": ["string", "null"], "maxLength": 80},
        "interpretation": {"type": "string", "minLength": 1, "maxLength": 600},
        "citation_ids": {
            "type": "array",
            "items": {"type": "string", "minLength": 1, "maxLength": 180},
            "maxItems": 12,
            "uniqueItems": True,
        },
    }
)

_RECORD_SCHEMA = _object(
    {
        "record_id": deepcopy(_IDENTIFIER),
        "record_type": {
            "type": "string",
            "minLength": 1,
            "maxLength": 80,
            "pattern": r"^[a-z][a-z0-9_]*$",
        },
        "facts": {"type": "array", "items": _FACT_SCHEMA, "maxItems": 30},
        "citation_ids": {
            "type": "array",
            "items": {"type": "string", "minLength": 1, "maxLength": 180},
            "maxItems": 12,
            "uniqueItems": True,
        },
    }
)

OUTPUT_SCHEMA = _object(
    {
        "schema_version": {"type": "string", "const": RESULT_SCHEMA_VERSION},
        "tool_name": {"type": "string", "enum": list(TOOL_ORDER)},
        "status": {
            "type": "string",
            "enum": ["available", "partial", "unavailable", "not_found", "forbidden"],
        },
        "summary": {"type": "string", "minLength": 1, "maxLength": 600},
        "query": {"type": "array", "items": _FACT_SCHEMA, "maxItems": 12},
        "facts": {"type": "array", "items": _FACT_SCHEMA, "maxItems": 40},
        "records": {"type": "array", "items": _RECORD_SCHEMA, "maxItems": 20},
        "citations": {
            "type": "array",
            "items": _CITATION_SCHEMA,
            "minItems": 1,
            "maxItems": 12,
        },
        "limitations": {
            "type": "array",
            "items": {"type": "string", "minLength": 1, "maxLength": 600},
            "maxItems": 12,
        },
        "result_fingerprint": {
            "type": "string",
            "pattern": r"^sha256:[0-9a-f]{64}$",
        },
    }
)


def tool_definitions() -> list[dict[str, Any]]:
    """Return Responses API function definitions in deterministic order."""

    return [
        {
            "type": "function",
            "name": name,
            "description": _DESCRIPTIONS[name],
            "strict": True,
            "parameters": deepcopy(_INPUT_SCHEMAS[name]),
        }
        for name in TOOL_ORDER
    ]


def input_schema(name: str) -> dict[str, Any]:
    """Return a defensive copy of one strict input schema."""

    return deepcopy(_INPUT_SCHEMAS[name])


def output_schema(name: str) -> dict[str, Any]:
    """Return the common bounded result schema narrowed to one tool name."""

    schema = deepcopy(OUTPUT_SCHEMA)
    schema["properties"]["tool_name"] = {"type": "string", "const": name}
    return schema


def contract_document() -> dict[str, Any]:
    """Return the versioned generated contract document."""

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "transport": "openai_responses_function_tools",
        "strict": True,
        "deterministic": True,
        "read_only": True,
        "tool_count": len(TOOL_ORDER),
        "tools": tool_definitions(),
        "output_schema": deepcopy(OUTPUT_SCHEMA),
        "semantic_rules": deepcopy(_SEMANTIC_RULES),
    }
