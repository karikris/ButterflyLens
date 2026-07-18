#!/usr/bin/env python3
"""Grade one complete ButterflyLens analyst trace without calling OpenAI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "packages" / "openai" / "python"
sys.path.insert(0, str(PACKAGE_ROOT))

from butterflylens_openai import EvaluationContractError, grade_trace  # noqa: E402


OPENAI_ROOT = ROOT / "packages" / "openai"
SUITE_PATH = OPENAI_ROOT / "analyst-eval-cases.v1.json"
TRACE_SCHEMA_PATH = OPENAI_ROOT / "analyst-live-eval-trace.schema.json"
RESPONSE_SCHEMA_PATH = OPENAI_ROOT / "analyst-response.schema.json"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=(
            "Grade a complete recorded or explicitly synthetic ButterflyLens "
            "analyst trace. This command makes no network or model call."
        )
    )
    result.add_argument("trace", type=Path, help="JSON trace to grade")
    result.add_argument(
        "--output",
        type=Path,
        help="optional JSON result path; stdout is used when omitted",
    )
    return result


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise EvaluationContractError(f"{path} must contain a JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        report = grade_trace(
            repo_root=ROOT,
            suite=load_json(SUITE_PATH),
            trace=load_json(arguments.trace),
            trace_schema=load_json(TRACE_SCHEMA_PATH),
            response_schema=load_json(RESPONSE_SCHEMA_PATH),
        )
    except (EvaluationContractError, json.JSONDecodeError, OSError) as error:
        print(f"evaluation trace rejected: {error}", file=sys.stderr)
        return 1
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if arguments.output is None:
        print(output, end="")
    else:
        arguments.output.write_text(output, encoding="utf-8")
        print(f"wrote {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
