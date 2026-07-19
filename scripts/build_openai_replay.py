#!/usr/bin/env python3
"""Generate the strict credential-free Ask ButterflyLens replay catalogue."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from jsonschema import Draft202012Validator
import rfc8785


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "packages" / "openai" / "python"
OUTPUT = ROOT / "packages" / "openai" / "submitted-replays.v1.json"
SCHEMA_OUTPUT = ROOT / "packages" / "openai" / "replay-catalog.schema.json"
IMPLEMENTATION_COMMIT = "609433e0e765cc3ba7d1b894db44e3cd2c4381f0"
RECORDED_AT = "2026-07-18T17:55:33Z"
sys.path.insert(0, str(PACKAGE_ROOT))

from butterflylens_openai import EvidenceToolbox, TOOL_ORDER  # noqa: E402
from butterflylens_openai.catalog import input_schema, output_schema  # noqa: E402


def strict_object(
    properties: dict[str, Any],
    *,
    required: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required if required is not None else list(properties),
        "properties": properties,
    }


def replay_schema() -> dict[str, Any]:
    identifier = {
        "type": "string",
        "minLength": 1,
        "maxLength": 180,
        "pattern": r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$",
    }
    citation = strict_object(
        {
            "artifact_id": deepcopy(identifier),
            "repository": {"const": "karikris/ButterflyLens"},
            "commit": {"type": "string", "pattern": r"^[0-9a-f]{40}$"},
            "path": {"type": "string", "minLength": 1, "maxLength": 300},
            "fingerprint": {
                "type": "string",
                "pattern": r"^sha256:[0-9a-f]{64}$",
            },
        }
    )
    claim = strict_object(
        {
            "claim_id": {
                "type": "string",
                "pattern": r"^claim_[1-9][0-9]{0,2}$",
            },
            "statement": {"type": "string", "minLength": 1, "maxLength": 800},
            "evidence_state": {
                "type": "string",
                "enum": ["direct", "inference", "unavailable", "conflict"],
            },
            "citation_ids": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "uniqueItems": True,
                "items": deepcopy(identifier),
            },
        }
    )
    trace_variants = []
    for name in TOOL_ORDER:
        trace_variants.append(
            strict_object(
                {
                    "sequence": {"type": "integer", "minimum": 1, "maximum": 8},
                    "call_id": deepcopy(identifier),
                    "name": {"const": name},
                    "arguments": input_schema(name),
                    "output": output_schema(name),
                }
            )
        )
    replay_metadata = strict_object(
        {
            "replay_id": deepcopy(identifier),
            "recorded_at": {"type": "string", "format": "date-time"},
            "source_commit": {"type": "string", "pattern": r"^[0-9a-f]{40}$"},
            "model_invoked": {"const": False},
            "response_calls": {"const": 0},
            "tool_calls": {"type": "integer", "minimum": 1, "maximum": 8},
            "trace_fingerprint": {
                "type": "string",
                "pattern": r"^sha256:[0-9a-f]{64}$",
            },
        }
    )
    response = strict_object(
        {
            "schema_version": {
                "const": "butterflylens-analyst-replay-response:v1.0.0"
            },
            "mode": {"const": "replayed"},
            "response_state": {
                "type": "string",
                "enum": ["completed", "incomplete"],
            },
            "summary": {"type": "string", "minLength": 1, "maxLength": 800},
            "claims": {
                "type": "array",
                "minItems": 1,
                "maxItems": 12,
                "items": claim,
            },
            "citations": {
                "type": "array",
                "minItems": 1,
                "maxItems": 16,
                "items": citation,
            },
            "limitations": {
                "type": "array",
                "minItems": 1,
                "maxItems": 12,
                "uniqueItems": True,
                "items": {"type": "string", "minLength": 1, "maxLength": 600},
            },
            "tools_used": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "uniqueItems": True,
                "items": {"type": "string", "enum": list(TOOL_ORDER)},
            },
            "replay": replay_metadata,
        }
    )
    replay_case = strict_object(
        {
            "replay_id": deepcopy(identifier),
            "accepted_questions": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "uniqueItems": True,
                "items": {"type": "string", "minLength": 1, "maxLength": 1200},
            },
            "tool_trace": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "items": {"oneOf": trace_variants},
            },
            "response": response,
        }
    )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://butterflylens.app/schemas/openai/replay-catalog-v1.json",
        "title": "ButterflyLens credential-free analyst replay catalogue",
        **strict_object(
            {
                "schema_version": {
                    "const": "butterflylens-analyst-replay-catalog:v1.0.0"
                },
                "mode": {"const": "replayed"},
                "source": strict_object(
                    {
                        "repository": {"const": "karikris/ButterflyLens"},
                        "implementation_commit": {
                            "type": "string",
                            "pattern": r"^[0-9a-f]{40}$",
                        },
                        "tool_artifact_commit": {
                            "type": "string",
                            "pattern": r"^[0-9a-f]{40}$",
                        },
                        "recorded_at": {"type": "string", "format": "date-time"},
                        "model_invoked": {"const": False},
                        "network_calls": {"const": 0},
                    }
                ),
                "cases": {
                    "type": "array",
                    "minItems": 3,
                    "maxItems": 12,
                    "items": replay_case,
                },
                "catalog_fingerprint": {
                    "type": "string",
                    "pattern": r"^sha256:[0-9a-f]{64}$",
                },
            }
        ),
    }


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def trace(
    toolbox: EvidenceToolbox,
    replay_id: str,
    name: str,
    arguments: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "sequence": 1,
            "call_id": f"{replay_id}:call:1",
            "name": name,
            "arguments": arguments,
            "output": toolbox.invoke(name, arguments),
        }
    ]


def response(
    replay_id: str,
    stored_trace: list[dict[str, Any]],
    *,
    summary: str,
    claims: list[dict[str, Any]],
    limitations: list[str],
) -> dict[str, Any]:
    citations: dict[str, dict[str, Any]] = {}
    for item in stored_trace:
        for citation in item["output"]["citations"]:
            citations.setdefault(citation["artifact_id"], citation)
    citation_rows = list(citations.values())
    citation_ids = set(citations)
    for claim in claims:
        if not set(claim["citation_ids"]).issubset(citation_ids):
            raise ValueError(f"{replay_id} claim cites outside its stored trace")
    trace_fingerprint = fingerprint(stored_trace)
    return {
        "schema_version": "butterflylens-analyst-replay-response:v1.0.0",
        "mode": "replayed",
        "response_state": "completed",
        "summary": summary,
        "claims": claims,
        "citations": citation_rows,
        "limitations": limitations,
        "tools_used": list(dict.fromkeys(item["name"] for item in stored_trace)),
        "replay": {
            "replay_id": replay_id,
            "recorded_at": RECORDED_AT,
            "source_commit": IMPLEMENTATION_COMMIT,
            "model_invoked": False,
            "response_calls": 0,
            "tool_calls": len(stored_trace),
            "trace_fingerprint": trace_fingerprint,
        },
    }


def build_catalog() -> dict[str, Any]:
    toolbox = EvidenceToolbox(ROOT)
    species_id = "replay:species-acraea-andromacha"
    species_trace = trace(
        toolbox,
        species_id,
        "inspect_species",
        {"species_key": None, "scientific_name": "Acraea andromacha"},
    )
    species_output = species_trace[0]["output"]
    species_record = species_output["records"][0]
    species_facts = {fact["name"]: fact["value"] for fact in species_record["facts"]}
    if species_facts["accepted_scientific_name"] != "Acraea andromacha":
        raise ValueError("stored species replay resolved the wrong accepted species")
    if species_facts["human_verified_media"] != 0:
        raise ValueError("stored species replay unexpectedly claims human verification")
    species_citations = [citation["artifact_id"] for citation in species_output["citations"]]

    comparison_id = "replay:ala-flickr-comparison"
    comparison_trace = trace(
        toolbox,
        comparison_id,
        "compare_ala_and_flickr",
        {"scope_type": "national", "scope_id": None, "species_key": None},
    )
    comparison_output = comparison_trace[0]["output"]
    comparison_facts = {
        fact["name"]: (fact["state"], fact["value"])
        for fact in comparison_output["facts"]
    }
    if comparison_facts["ala_occurrence_count"] != ("observed", 213_310):
        raise ValueError("stored comparison lost the rights-screened ALA count")
    if comparison_facts["flickr_candidate_count"] != ("unavailable", None):
        raise ValueError("stored comparison unexpectedly has Flickr counts")
    comparison_citations = [
        citation["artifact_id"] for citation in comparison_output["citations"]
    ]

    priority_id = "replay:next-reference-review"
    priority_trace = trace(
        toolbox,
        priority_id,
        "recommend_next_species",
        {"criterion": "reference_gap", "limit": 3},
    )
    priority_output = priority_trace[0]["output"]
    priority_names = [
        next(
            fact["value"]
            for fact in record["facts"]
            if fact["name"] == "accepted_scientific_name"
        )
        for record in priority_output["records"]
    ]
    if priority_names != [
        "Hypochrysops sandrae",
        "Lacturnea lacturnus",
        "Charaxes andrewsi",
    ]:
        raise ValueError("stored reference-gap replay order changed")
    priority_citations = [citation["artifact_id"] for citation in priority_output["citations"]]

    cases = [
        {
            "replay_id": species_id,
            "accepted_questions": [
                "What evidence is available for Acraea andromacha?"
            ],
            "tool_trace": species_trace,
            "response": response(
                species_id,
                species_trace,
                summary=(
                    "This stored replay shows submitted evidence for Acraea "
                    "andromacha; it does not identify a photo or release an occurrence."
                ),
                claims=[
                    {
                        "claim_id": "claim_1",
                        "statement": (
                            "Acraea andromacha is an accepted species in the "
                            "authoritative rebuilt ButterflyLens catalogue."
                        ),
                        "evidence_state": "direct",
                        "citation_ids": [species_citations[0], species_citations[1]],
                    },
                    {
                        "claim_id": "claim_2",
                        "statement": (
                            "The submitted reference diagnostics report 20 selected "
                            "valid decodes and zero human-verified media; release remains "
                            "blocked by unfinished models and human review."
                        ),
                        "evidence_state": "direct",
                        "citation_ids": species_citations,
                    },
                ],
                limitations=[
                    "No Bounded model or other model was invoked to generate or display this replay.",
                    "Accepted taxonomy and provisional references do not identify a photograph or establish an occurrence.",
                ],
            ),
        },
        {
            "replay_id": comparison_id,
            "accepted_questions": ["Can ALA and Flickr counts be compared yet?"],
            "tool_trace": comparison_trace,
            "response": response(
                comparison_id,
                comparison_trace,
                summary=(
                    "The stored submitted evidence has a rights-screened national "
                    "ALA count, but no immutable Flickr count or two-source difference."
                ),
                claims=[
                    {
                        "claim_id": "claim_1",
                        "statement": (
                            "The submitted public map contains 213,310 spatially "
                            "eligible ALA baseline occurrence-evidence rows after "
                            "its conservative dataset-rights screen."
                        ),
                        "evidence_state": "direct",
                        "citation_ids": [comparison_citations[1], comparison_citations[3]],
                    },
                    {
                        "claim_id": "claim_2",
                        "statement": (
                            "No completed immutable national Flickr candidate count is "
                            "present in the stored submitted evidence."
                        ),
                        "evidence_state": "unavailable",
                        "citation_ids": [comparison_citations[2]],
                    },
                    {
                        "claim_id": "claim_3",
                        "statement": (
                            "The count difference is unavailable; missing evidence is "
                            "not a zero or evidence of biological absence."
                        ),
                        "evidence_state": "unavailable",
                        "citation_ids": comparison_citations,
                    },
                ],
                limitations=[
                    "No Bounded model or other model was invoked to generate or display this replay.",
                    "The replay does not inspect the active Flickr fetch or any partial BioMiner output.",
                ],
            ),
        },
        {
            "replay_id": priority_id,
            "accepted_questions": [
                "Which species should receive the next reference review?"
            ],
            "tool_trace": priority_trace,
            "response": response(
                priority_id,
                priority_trace,
                summary=(
                    "The stored deterministic reference-gap queue returns three "
                    "species-level workflow priorities."
                ),
                claims=[
                    {
                        "claim_id": "claim_1",
                        "statement": (
                            "The stored queue orders Hypochrysops sandrae, Lacturnea "
                            "lacturnus, then Charaxes andrewsi for targeted reference-gap review."
                        ),
                        "evidence_state": "direct",
                        "citation_ids": priority_citations,
                    },
                    {
                        "claim_id": "claim_2",
                        "statement": (
                            "All three have zero selected reference media and zero "
                            "human-verified media in this stored trace."
                        ),
                        "evidence_state": "direct",
                        "citation_ids": priority_citations,
                    },
                    {
                        "claim_id": "claim_3",
                        "statement": (
                            "This is targeted workflow order, not a ranking of rarity, "
                            "presence, conservation importance, or dataset quality."
                        ),
                        "evidence_state": "direct",
                        "citation_ids": priority_citations,
                    },
                ],
                limitations=[
                    "No Bounded model or other model was invoked to generate or display this replay.",
                    "Reference-gap priorities are provisional diagnostics and cannot establish photo identity or occurrence.",
                ],
            ),
        },
    ]
    tool_commits = {
        citation["commit"]
        for case in cases
        for trace_item in case["tool_trace"]
        for citation in trace_item["output"]["citations"]
    }
    if len(tool_commits) != 1:
        raise ValueError("stored replay citations do not share one tool artifact commit")
    catalogue: dict[str, Any] = {
        "schema_version": "butterflylens-analyst-replay-catalog:v1.0.0",
        "mode": "replayed",
        "source": {
            "repository": "karikris/ButterflyLens",
            "implementation_commit": IMPLEMENTATION_COMMIT,
            "tool_artifact_commit": next(iter(tool_commits)),
            "recorded_at": RECORDED_AT,
            "model_invoked": False,
            "network_calls": 0,
        },
        "cases": cases,
    }
    catalogue["catalog_fingerprint"] = fingerprint(catalogue)
    return catalogue


def main() -> None:
    schema = replay_schema()
    catalogue = build_catalog()
    errors = sorted(
        Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).iter_errors(catalogue),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        path = ".".join(str(part) for part in error.absolute_path) or "catalogue"
        raise ValueError(f"replay catalogue invalid at {path}: {error.message}")
    SCHEMA_OUTPUT.write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    OUTPUT.write_text(
        json.dumps(catalogue, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {SCHEMA_OUTPUT.relative_to(ROOT)}")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
