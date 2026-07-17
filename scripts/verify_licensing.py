#!/usr/bin/env python3
"""Fail closed when ButterflyLens software/model licence evidence is incomplete."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class VerificationError(RuntimeError):
    """Raised when a release-blocking licence condition is not met."""


def require_text(path: str, terms: tuple[str, ...]) -> None:
    target = ROOT / path
    if not target.is_file():
        raise VerificationError(f"missing required file: {path}")
    text = target.read_text(encoding="utf-8")
    missing = [term for term in terms if term not in text]
    if missing:
        raise VerificationError(f"{path} is missing required evidence: {missing}")


def tracked_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return {value.decode("utf-8") for value in result.stdout.split(b"\0") if value}


def require_json_object(path: str, required_keys: tuple[str, ...]) -> dict[str, object]:
    target = ROOT / path
    if not target.is_file():
        raise VerificationError(f"missing required manifest: {path}")
    value = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise VerificationError(f"{path} must contain a JSON object")
    missing = [key for key in required_keys if key not in value]
    if missing:
        raise VerificationError(f"{path} is missing keys: {missing}")
    return value


def verify() -> None:
    require_text(
        "LICENSE",
        ("GNU AFFERO GENERAL PUBLIC LICENSE", "Version 3, 19 November 2007"),
    )
    require_text(
        "LICENSE_DECISION.md",
        (
            "Decision: PASS",
            "`AGPL-3.0-only`",
            "No Ultralytics Enterprise licence",
            "corresponding source",
            "python3 scripts/verify_rights.py",
        ),
    )
    require_text(
        "THIRD_PARTY_LICENSES.md",
        (
            "BioMiner",
            "TaxaLens",
            "bioclip-2.5-vith14",
            "THU-MIG YOLOE",
            "Ultralytics",
            "MapLibre GL JS",
            "H3",
            "Supabase",
        ),
    )
    require_text("DATA_RIGHTS.md", ("Unknown is a blocking value", "removal graph"))
    require_text(".gitignore", ("AGENTS.md",))

    tracked = tracked_files()
    if "AGENTS.md" in tracked:
        raise VerificationError("AGENTS.md must remain untracked by explicit user decision")

    dependency_manifests = {
        path for path in tracked if path.endswith(("package.json", "pyproject.toml"))
    }
    if dependency_manifests:
        manifest = require_json_object(
            "provenance/dependency_licenses.json",
            ("schema_version", "generated_at", "direct", "transitive"),
        )
        if not manifest.get("direct"):
            raise VerificationError("dependency licence manifest has no direct dependencies")

    model_files = {
        path
        for path in tracked
        if Path(path).suffix.lower() in {".onnx", ".pt", ".pth", ".safetensors"}
    }
    if model_files:
        manifest = require_json_object(
            "provenance/model_licenses.json",
            ("schema_version", "generated_at", "models"),
        )
        if not manifest.get("models"):
            raise VerificationError("tracked model files exist without model licence records")

    print(
        "licence verification: PASS "
        f"(tracked_files={len(tracked)}, dependency_manifests={len(dependency_manifests)}, "
        f"model_files={len(model_files)})"
    )


if __name__ == "__main__":
    try:
        verify()
    except (VerificationError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"licence verification: FAIL: {error}", file=sys.stderr)
        raise SystemExit(1) from error
