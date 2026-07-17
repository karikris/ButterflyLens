#!/usr/bin/env python3
"""Validate JSON Schema, Python, and TypeScript contract parity."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parents[1]
SCHEMAS = PACKAGE / "schemas"
FIXTURES = PACKAGE / "tests" / "fixtures" / "parity-cases.json"
TYPESCRIPT_VALIDATOR = PACKAGE / "tests" / "typescript" / "schema-validator.ts"
TYPESCRIPT_RUNNER = PACKAGE / "tests" / "typescript" / "run-parity.cjs"


class ParityFailure(RuntimeError):
    """Raised when one contract representation diverges."""


def load_schemas() -> tuple[dict[str, dict[str, Any]], Registry[Any]]:
    schemas: dict[str, dict[str, Any]] = {}
    registry: Registry[Any] = Registry()
    for path in sorted(SCHEMAS.glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        schema_id = schema.get("$id")
        if not isinstance(schema_id, str) or schema_id in schemas:
            raise ParityFailure(f"invalid or duplicate $id in {path}")
        schemas[schema_id] = schema
        registry = registry.with_resource(schema_id, Resource.from_contents(schema))
    return schemas, registry


def expand(value: Any) -> Any:
    if isinstance(value, list):
        return [expand(item) for item in value]
    if isinstance(value, dict):
        return {key: expand(item) for key, item in value.items()}
    return {
        "{{sha256}}": "a" * 64,
        "{{sha256_b}}": "b" * 64,
        "{{git_sha}}": "c" * 40,
        "{{now}}": "2026-07-17T14:43:29Z",
        "{{later}}": "2026-07-17T14:48:29Z",
    }.get(value, value)


def apply_change(document: dict[str, Any], change: dict[str, Any]) -> None:
    parts = [part.replace("~1", "/").replace("~0", "~") for part in change["path"].split("/")[1:]]
    parent: dict[str, Any] = document
    for part in parts[:-1]:
        child = parent.get(part)
        if not isinstance(child, dict):
            raise ParityFailure(f"fixture mutation has non-object parent: {change}")
        parent = child
    key = parts[-1]
    if change["op"] == "delete":
        parent.pop(key, None)
    elif change["op"] == "set":
        parent[key] = expand(change.get("value"))
    else:
        raise ParityFailure(f"unsupported fixture mutation: {change['op']}")


def validate_python_cases(
    fixtures: dict[str, Any],
    schemas: dict[str, dict[str, Any]],
    registry: Registry[Any],
) -> dict[str, bool]:
    format_checker = FormatChecker()
    valid_documents: dict[str, dict[str, Any]] = {}
    results: dict[str, bool] = {}
    for case in fixtures["valid_documents"]:
        document = expand(case["document"])
        valid_documents[case["case_id"]] = document
        validator = Draft202012Validator(
            schemas[case["schema_id"]],
            registry=registry,
            format_checker=format_checker,
        )
        errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
        if errors:
            raise ParityFailure(
                f"Python rejected valid case {case['case_id']}: "
                + "; ".join(error.message for error in errors)
            )
        results[case["case_id"]] = True

    for case in fixtures["invalid_cases"]:
        document = deepcopy(valid_documents[case["base_case_id"]])
        for change in case["changes"]:
            apply_change(document, change)
        validator = Draft202012Validator(
            schemas[case["schema_id"]],
            registry=registry,
            format_checker=format_checker,
        )
        errors = list(validator.iter_errors(document))
        if not errors:
            raise ParityFailure(f"Python accepted invalid case {case['case_id']}")
        results[case["case_id"]] = False
    return results


def find_typescript_compiler() -> str:
    configured = os.environ.get("BUTTERFLYLENS_TSC")
    candidates = [
        configured,
        str(ROOT / "node_modules" / ".bin" / "tsc"),
        str(PACKAGE / "node_modules" / ".bin" / "tsc"),
        shutil.which("tsc"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise ParityFailure(
        "TypeScript compiler unavailable; set BUTTERFLYLENS_TSC or install the "
        "pinned workspace development dependency"
    )


def run_typescript(fixtures: dict[str, Any]) -> tuple[dict[str, bool], dict[str, Any], str]:
    compiler = find_typescript_compiler()
    node = shutil.which("node")
    if node is None:
        raise ParityFailure("Node.js is unavailable")
    sources = [str(path) for path in sorted((PACKAGE / "src").glob("*.ts"))]
    sources.append(str(TYPESCRIPT_VALIDATOR))
    version = subprocess.run(
        [compiler, "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="butterflylens-contract-parity-") as temporary:
        output = Path(temporary)
        subprocess.run(
            [
                compiler,
                "--target", "ES2022",
                "--lib", "ES2022",
                "--module", "NodeNext",
                "--moduleResolution", "NodeNext",
                "--strict",
                "--skipLibCheck",
                "--rootDir", str(PACKAGE),
                "--outDir", str(output),
                *sources,
            ],
            check=True,
            cwd=ROOT,
        )
        completed = subprocess.run(
            [
                node,
                str(TYPESCRIPT_RUNNER),
                str(SCHEMAS),
                str(FIXTURES),
                str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
    report = json.loads(completed.stdout)
    results = {item["case_id"]: bool(item["valid"]) for item in report["results"]}
    return results, report["constants"], version


def pointer(value: Any, path: str) -> Any:
    current = value
    for raw_part in path.split("/")[1:]:
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or part not in current:
            raise ParityFailure(f"unresolved fixture pointer {path}")
        current = current[part]
    return current


def validate_declaration_parity(
    fixtures: dict[str, Any],
    schemas: dict[str, dict[str, Any]],
    typescript_constants: dict[str, Any],
) -> None:
    sys.path.insert(0, str(PACKAGE / "python"))
    import butterflylens.contracts as python_contracts  # noqa: PLC0415

    for check in [*fixtures["schema_version_checks"], *fixtures["vocabulary_checks"]]:
        expected = pointer(schemas[check["schema_id"]], check["pointer"])
        python_value = getattr(python_contracts, check["constant"], None)
        if isinstance(python_value, tuple):
            python_value = list(python_value)
        typescript_value = typescript_constants.get(check["constant"])
        if python_value != expected:
            raise ParityFailure(
                f"Python {check['constant']} diverges: {python_value!r} != {expected!r}"
            )
        if typescript_value != expected:
            raise ParityFailure(
                f"TypeScript {check['constant']} diverges: "
                f"{typescript_value!r} != {expected!r}"
            )


def main() -> None:
    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
    if fixtures.get("schema_version") != "butterflylens-contract-parity-fixtures:v1.0.0":
        raise ParityFailure("unsupported parity fixture version")
    schemas, registry = load_schemas()
    python_results = validate_python_cases(fixtures, schemas, registry)
    typescript_results, constants, compiler_version = run_typescript(fixtures)
    expected = {
        **{case["case_id"]: True for case in fixtures["valid_documents"]},
        **{case["case_id"]: False for case in fixtures["invalid_cases"]},
    }
    if python_results != expected:
        raise ParityFailure("Python case results diverge from fixture expectations")
    if typescript_results != expected:
        mismatches = {
            key: (expected[key], typescript_results.get(key))
            for key in expected
            if typescript_results.get(key) != expected[key]
        }
        raise ParityFailure(f"TypeScript case results diverge: {mismatches}")
    validate_declaration_parity(fixtures, schemas, constants)
    print(
        "contract parity: PASS "
        f"(schemas={len(schemas)}, valid={len(fixtures['valid_documents'])}, "
        f"invalid={len(fixtures['invalid_cases'])}, "
        f"versions={len(fixtures['schema_version_checks'])}, "
        f"vocabularies={len(fixtures['vocabulary_checks'])}, "
        f"typescript={compiler_version})"
    )


if __name__ == "__main__":
    try:
        main()
    except (ParityFailure, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"contract parity: FAIL: {error}", file=sys.stderr)
        raise SystemExit(1) from error
