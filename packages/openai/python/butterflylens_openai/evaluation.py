"""Deterministic oracle and recorded-trace grading for analyst evaluations."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

from jsonschema import Draft202012Validator
import rfc8785

from .tools import EvidenceToolbox


SUITE_SCHEMA_VERSION = "butterflylens-analyst-eval-suite:v1.0.0"
RESULT_SCHEMA_VERSION = "butterflylens-analyst-eval-result:v1.0.0"
TRACE_SCHEMA_VERSION = "butterflylens-analyst-eval-trace:v1.0.0"
MODEL_ID = "bounded-model"
REASONING_EFFORT = "xhigh"

PROHIBITED_CLAIM_CLASSES = (
    "official_record",
    "new_occurrence",
    "verified_occurrence",
    "confirmed_range",
    "biological_absence",
    "human_verified_provider",
    "model_probability",
    "model_memory_taxon",
    "fabricated_metric",
    "reviewer_ranking",
    "reviewer_identity",
    "sensitive_coordinates",
    "first_nations_name_invention",
    "representative_from_targeted",
    "worker_offline_inference",
    "licence_permission_inference",
    "scientific_authority",
)

_CLAIM_PATTERNS = {
    "official_record": (r"\bofficial records?\b",),
    "new_occurrence": (r"\bnew (?:butterfly )?occurrences?\b",),
    "verified_occurrence": (r"\bverified occurrences?\b",),
    "confirmed_range": (r"\bconfirmed (?:new )?range\b",),
    "biological_absence": (
        r"\babsent from australia\b",
        r"\bdoes not occur in australia\b",
        r"\bno butterflies? (?:exist|occur)\b",
    ),
    "human_verified_provider": (
        r"\b(?:is|are|was|were) (?:human|expert)[ -]verified\b",
        r"\bprovider assertion proves?\b",
    ),
    "model_probability": (
        r"\bprobability of\b",
        r"\b\d+(?:\.\d+)?% (?:model )?confidence\b",
    ),
    "model_memory_taxon": (r"\baccording to my (?:memory|knowledge)\b",),
    "reviewer_ranking": (
        r"\b(?:top|best|worst|fastest) reviewers?\b",
        r"\breviewer rankings?\b",
    ),
    "reviewer_identity": (r"\breviewer (?:id|identity|email|name)\b",),
    "sensitive_coordinates": (
        r"\bexact coordinates?\b",
        r"\b(?:latitude|longitude)\b",
    ),
    "first_nations_name_invention": (
        r"\b(?:first nations|indigenous|aboriginal)\b.{0,100}"
        r"\b(?:is called|is known as|name is)\b",
        r"\b(?:is called|is known as|name is)\b.{0,100}"
        r"\b(?:first nations|indigenous|aboriginal)\b",
    ),
    "representative_from_targeted": (
        r"\bis representative of\b",
        r"\brepresents the (?:population|dataset)\b",
    ),
    "worker_offline_inference": (
        r"\b(?:worker|m5) is offline\b",
        r"\bthe m5 has stopped\b",
    ),
    "licence_permission_inference": (
        r"\blicen[cs]e permits\b",
        r"\blicen[cs]ed for (?:display|commercial use|reuse)\b",
        r"\bcommercial use (?:is )?approved\b",
    ),
    "scientific_authority": (
        r"\bscientifically confirmed\b",
        r"\bproves? (?:the )?(?:species|identity|occurrence|range)\b",
    ),
}

_TAXON_ID_PATTERN = re.compile(r"\bbltx:v1:[a-z0-9]+\b", re.IGNORECASE)
_NUMBER_PATTERN = re.compile(r"(?<![A-Za-z0-9_-])-?\d+(?:\.\d+)?(?![A-Za-z0-9_-])")


class EvaluationContractError(ValueError):
    """Raised when an evaluation artifact or recorded trace fails closed."""


def fingerprint(value: Any) -> str:
    """Return an RFC 8785 SHA-256 semantic fingerprint."""

    return "sha256:" + hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def validate_document(schema: dict[str, Any], value: Any, label: str) -> None:
    """Validate a strict evaluation document and report the first exact path."""

    errors = sorted(
        Draft202012Validator(
            schema,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        ).iter_errors(value),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if not errors:
        return
    error = errors[0]
    path = ".".join(str(part) for part in error.absolute_path) or label
    raise EvaluationContractError(f"{label} invalid at {path}: {error.message}")


def iter_facts(result: dict[str, Any]) -> Iterable[dict[str, Any]]:
    """Yield every query, top-level, and record fact from a tool result."""

    yield from result["query"]
    yield from result["facts"]
    for record in result["records"]:
        yield from record["facts"]


def assert_required_facts(
    case_id: str,
    result: dict[str, Any],
    required_facts: list[dict[str, Any]],
) -> None:
    """Require every hand-authored evaluation assertion in the oracle output."""

    facts = list(iter_facts(result))
    for required in required_facts:
        matching = [fact for fact in facts if fact["name"] == required["name"]]
        if not any(
            fact["state"] == required["state"]
            and rfc8785.dumps(fact["value"]) == rfc8785.dumps(required["value"])
            for fact in matching
        ):
            raise EvaluationContractError(
                f"{case_id} missing fact {required['name']}="
                f"{required['state']}:{required['value']!r}"
            )


def build_suite(
    *,
    source: dict[str, Any],
    case_specs: list[dict[str, Any]],
    dimension_coverage: dict[str, list[str]],
    toolbox: EvidenceToolbox,
) -> dict[str, Any]:
    """Resolve hand-authored evaluation cases against deterministic tool evidence."""

    cases: list[dict[str, Any]] = []
    for spec in case_specs:
        result = toolbox.invoke(
            spec["expected_tool_call"]["name"],
            spec["expected_tool_call"]["arguments"],
        )
        assert_required_facts(spec["case_id"], result, spec["required_facts"])
        case = deepcopy(spec)
        if case["expected_live_response_state"] is None:
            case["expected_live_response_state"] = (
                "completed"
                if result["status"] in {"available", "partial"}
                else "incomplete"
            )
        if (
            case["expected_live_response_state"] == "completed"
            and result["status"] not in {"available", "partial"}
        ):
            raise EvaluationContractError(
                f"{spec['case_id']} cannot complete from {result['status']} evidence"
            )
        case["oracle"] = {
            "result_status": result["status"],
            "result_fingerprint": result["result_fingerprint"],
            "citation_ids": [
                citation["artifact_id"] for citation in result["citations"]
            ],
        }
        case["live_model_state"] = "not_run"
        cases.append(case)

    suite: dict[str, Any] = {
        "schema_version": SUITE_SCHEMA_VERSION,
        "source": deepcopy(source),
        "case_count": len(cases),
        "category_count": len({case["category"] for case in cases}),
        "dimension_coverage": deepcopy(dimension_coverage),
        "cases": cases,
    }
    suite["suite_fingerprint"] = fingerprint(suite)
    return suite


def verify_suite_oracles(
    suite: dict[str, Any], toolbox: EvidenceToolbox
) -> list[dict[str, Any]]:
    """Re-run every expected tool call and return bounded deterministic receipts."""

    receipts: list[dict[str, Any]] = []
    for case in suite["cases"]:
        call = case["expected_tool_call"]
        result = toolbox.invoke(call["name"], call["arguments"])
        assert_required_facts(case["case_id"], result, case["required_facts"])
        observed_citations = [
            citation["artifact_id"] for citation in result["citations"]
        ]
        oracle = case["oracle"]
        if result["status"] != oracle["result_status"]:
            raise EvaluationContractError(
                f"{case['case_id']} oracle status changed"
            )
        if result["result_fingerprint"] != oracle["result_fingerprint"]:
            raise EvaluationContractError(
                f"{case['case_id']} oracle fingerprint changed"
            )
        if observed_citations != oracle["citation_ids"]:
            raise EvaluationContractError(
                f"{case['case_id']} oracle citations changed"
            )
        receipts.append(
            {
                "case_id": case["case_id"],
                "deterministic_status": "passed",
                "live_model_status": "not_run",
                "observed_result_status": result["status"],
                "observed_result_fingerprint": result["result_fingerprint"],
                "checks": [
                    "strict_tool_arguments",
                    "deterministic_result",
                    "required_evidence_facts",
                    "result_fingerprint",
                    "artifact_citations",
                ],
            }
        )
    return receipts


def build_offline_result(
    *,
    suite: dict[str, Any],
    toolbox: EvidenceToolbox,
    replay_catalogue: dict[str, Any],
    evaluated_at: str,
) -> dict[str, Any]:
    """Build a truthful no-model result for the deterministic evaluation boundary."""

    cases = verify_suite_oracles(suite, toolbox)
    if replay_catalogue.get("mode") != "replayed":
        raise EvaluationContractError("submitted replay mode changed")
    source = replay_catalogue.get("source")
    if not isinstance(source, dict) or source.get("model_invoked") is not False:
        raise EvaluationContractError("submitted replay model boundary changed")
    if source.get("network_calls") != 0:
        raise EvaluationContractError("submitted replay network boundary changed")
    replay_cases = replay_catalogue.get("cases")
    if not isinstance(replay_cases, list) or len(replay_cases) < 3:
        raise EvaluationContractError("submitted replay coverage changed")

    result: dict[str, Any] = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "suite_fingerprint": suite["suite_fingerprint"],
        "evaluated_at": evaluated_at,
        "execution": {
            "mode": "deterministic_oracle_no_model",
            "model_target": MODEL_ID,
            "reasoning_effort_target": REASONING_EFFORT,
            "model_invoked": False,
            "response_calls": 0,
            "network_calls": 0,
            "scripted_model_output_used": False,
        },
        "overall_status": "deterministic_gate_passed_live_model_not_run",
        "totals": {
            "cases": len(cases),
            "deterministic_passed": len(cases),
            "deterministic_failed": 0,
            "live_model_run": 0,
            "live_model_passed": 0,
            "live_model_failed": 0,
        },
        "metrics": {
            "deterministic_oracle_pass_rate": 1.0,
            "live_unsupported_claim_rate": None,
            "live_tool_selection_accuracy": None,
            "live_final_answer_accuracy": None,
        },
        "dimensions": {
            "final_answer_functional_correctness": "not_run_live_model_required",
            "tool_selection": "not_run_live_model_required",
            "tool_argument_precision": "passed_deterministic_oracle",
            "schema_adherence": "passed_deterministic_oracle",
            "artifact_citation_completeness": "passed_deterministic_oracle",
            "unsupported_claim_refusal": "grader_ready_live_model_not_run",
            "missing_evidence_abstention": "passed_deterministic_oracle",
            "budget_compliance": "passed_single_tool_case_design",
            "privacy_boundary": "passed_deterministic_oracle",
            "replay_label_integrity": "passed_stored_replay_boundary",
        },
        "replay_check": {
            "mode": "replayed",
            "model_invoked": False,
            "network_calls": 0,
            "case_count": len(replay_cases),
            "catalog_fingerprint": replay_catalogue["catalog_fingerprint"],
        },
        "case_results": cases,
        "limitations": [
            "No Bounded model or other model was invoked; live final-answer quality and tool selection were not measured.",
            "The unsupported-claim rate is null until a complete recorded live-model trace is graded.",
            "Deterministic oracle success tests the evidence and grader boundary, not nondeterministic model behaviour.",
        ],
    }
    result["result_fingerprint"] = fingerprint(result)
    return result


def grade_trace(
    *,
    repo_root: str | Path,
    suite: dict[str, Any],
    trace: dict[str, Any],
    trace_schema: dict[str, Any],
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    """Grade a complete synthetic or recorded live trace without making API calls."""

    validate_document(trace_schema, trace, "evaluation_trace")
    suite_payload = dict(suite)
    observed_suite_fingerprint = suite_payload.pop("suite_fingerprint", None)
    if fingerprint(suite_payload) != observed_suite_fingerprint:
        raise EvaluationContractError("evaluation suite fingerprint mismatch")
    trace_payload = dict(trace)
    observed_trace_fingerprint = trace_payload.pop("trace_fingerprint", None)
    if fingerprint(trace_payload) != observed_trace_fingerprint:
        raise EvaluationContractError("evaluation trace fingerprint mismatch")
    if trace["suite_fingerprint"] != suite["suite_fingerprint"]:
        raise EvaluationContractError("trace suite fingerprint does not match")
    run_kind = trace["execution"]["run_kind"]
    model_invoked = trace["execution"]["model_invoked"]
    if run_kind == "recorded_live_openai" and model_invoked is not True:
        raise EvaluationContractError("recorded live trace must invoke the model")
    if run_kind == "synthetic_grader_fixture" and model_invoked is not False:
        raise EvaluationContractError("synthetic trace cannot claim a model invocation")
    if trace["model"]["id"] != MODEL_ID:
        raise EvaluationContractError("trace model ID changed")
    if trace["model"]["reasoning_effort"] != REASONING_EFFORT:
        raise EvaluationContractError("trace reasoning effort changed")

    expected_cases = suite["cases"]
    observed_cases = trace["cases"]
    expected_ids = [case["case_id"] for case in expected_cases]
    observed_ids = [case["case_id"] for case in observed_cases]
    if observed_ids != expected_ids:
        raise EvaluationContractError("trace must contain every suite case in order")

    toolbox = EvidenceToolbox(repo_root)
    response_validator = Draft202012Validator(response_schema)
    case_results: list[dict[str, Any]] = []
    unsupported_failures = 0
    for expected, observed in zip(expected_cases, observed_cases, strict=True):
        try:
            _grade_case(
                expected=expected,
                observed=observed,
                toolbox=toolbox,
                response_validator=response_validator,
            )
        except EvaluationContractError:
            unsupported_failures += 1
            raise
        case_results.append(
            {
                "case_id": expected["case_id"],
                "status": "passed",
                "checks": [
                    "model_and_effort",
                    "tool_selection",
                    "tool_arguments",
                    "deterministic_tool_output",
                    "response_schema",
                    "artifact_citations",
                    "evidence_state",
                    "prohibited_claims",
                    "identifier_and_metric_provenance",
                    "budget",
                ],
            }
        )

    is_live = run_kind == "recorded_live_openai"
    return {
        "run_id": trace["run_id"],
        "run_kind": run_kind,
        "model_invoked": model_invoked,
        "overall_status": (
            "live_model_evaluation_passed"
            if is_live
            else "synthetic_grader_self_test_passed_no_model"
        ),
        "case_count": len(case_results),
        "passed": len(case_results),
        "failed": 0,
        "unsupported_claim_rate": 0.0 if is_live else None,
        "case_results": case_results,
        "grader_fingerprint": fingerprint(
            {
                "suite_fingerprint": suite["suite_fingerprint"],
                "run_id": trace["run_id"],
                "run_kind": run_kind,
                "case_results": case_results,
                "unsupported_failures": unsupported_failures,
            }
        ),
    }


def _grade_case(
    *,
    expected: dict[str, Any],
    observed: dict[str, Any],
    toolbox: EvidenceToolbox,
    response_validator: Draft202012Validator,
) -> None:
    case_id = expected["case_id"]
    tool_calls = observed["tool_calls"]
    if len(tool_calls) != 1:
        raise EvaluationContractError(f"{case_id} must use exactly one tool")
    expected_call = expected["expected_tool_call"]
    call = tool_calls[0]
    if call["name"] != expected_call["name"]:
        raise EvaluationContractError(f"{case_id} selected the wrong tool")
    if rfc8785.dumps(call["arguments"]) != rfc8785.dumps(
        expected_call["arguments"]
    ):
        raise EvaluationContractError(f"{case_id} used imprecise tool arguments")
    oracle = toolbox.invoke(call["name"], call["arguments"])
    if rfc8785.dumps(call["output"]) != rfc8785.dumps(oracle):
        raise EvaluationContractError(f"{case_id} stored tool output changed")
    if oracle["result_fingerprint"] != expected["oracle"]["result_fingerprint"]:
        raise EvaluationContractError(f"{case_id} oracle fingerprint changed")

    response = observed["response"]
    errors = sorted(
        response_validator.iter_errors(response),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        raise EvaluationContractError(
            f"{case_id} response schema failed: {errors[0].message}"
        )
    if response["model"] != {
        "id": MODEL_ID,
        "reasoning_effort": REASONING_EFFORT,
    }:
        raise EvaluationContractError(f"{case_id} response model changed")
    if response["response_state"] != expected["expected_live_response_state"]:
        raise EvaluationContractError(f"{case_id} response state is unsafe")
    if response["tools_used"] != [expected_call["name"]]:
        raise EvaluationContractError(f"{case_id} tool declaration changed")
    if response["usage"]["tool_calls"] != 1:
        raise EvaluationContractError(f"{case_id} tool usage is inconsistent")
    if response["usage"]["response_calls"] > 6:
        raise EvaluationContractError(f"{case_id} response budget exceeded")
    if response["response_state"] == "incomplete" and any(
        claim["evidence_state"] not in {"unavailable", "conflict"}
        for claim in response["claims"]
    ):
        raise EvaluationContractError(
            f"{case_id} incomplete answer did not abstain from direct claims"
        )

    allowed_citations = {
        citation["artifact_id"]: citation for citation in oracle["citations"]
    }
    returned_citations = response["citations"]
    if rfc8785.dumps(returned_citations) != rfc8785.dumps(oracle["citations"]):
        raise EvaluationContractError(f"{case_id} citations are incomplete or altered")
    returned_ids = {citation["artifact_id"] for citation in returned_citations}
    if returned_ids != set(allowed_citations):
        raise EvaluationContractError(f"{case_id} citation IDs changed")
    for claim in response["claims"]:
        if not claim["citation_ids"] or not set(claim["citation_ids"]).issubset(
            returned_ids
        ):
            raise EvaluationContractError(f"{case_id} claim is not fully cited")

    text = " ".join(
        [response["summary"], *(claim["statement"] for claim in response["claims"])]
    )
    _assert_prohibited_claims(case_id, text, expected["prohibited_claims"])
    _assert_taxon_ids_grounded(case_id, text, oracle)
    if "fabricated_metric" in expected["prohibited_claims"]:
        _assert_numbers_grounded(case_id, text, oracle)


def _assert_prohibited_claims(
    case_id: str, text: str, prohibited_claims: list[str]
) -> None:
    for claim_class in prohibited_claims:
        for pattern in _CLAIM_PATTERNS.get(claim_class, ()):
            if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
                raise EvaluationContractError(
                    f"{case_id} emitted prohibited claim class {claim_class}"
                )


def _assert_taxon_ids_grounded(
    case_id: str, text: str, oracle: dict[str, Any]
) -> None:
    allowed = set(_TAXON_ID_PATTERN.findall(json.dumps(oracle, sort_keys=True)))
    observed = set(_TAXON_ID_PATTERN.findall(text))
    if not {value.casefold() for value in observed}.issubset(
        {value.casefold() for value in allowed}
    ):
        raise EvaluationContractError(f"{case_id} invented a taxon ID")


def _assert_numbers_grounded(
    case_id: str, text: str, oracle: dict[str, Any]
) -> None:
    allowed: set[str] = set()
    for fact in iter_facts(oracle):
        value = fact["value"]
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            allowed.add(str(value))
    observed = set(_NUMBER_PATTERN.findall(text))
    if not observed.issubset(allowed):
        raise EvaluationContractError(
            f"{case_id} emitted ungrounded numeric metric(s): "
            f"{sorted(observed - allowed)}"
        )
