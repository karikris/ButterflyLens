#!/usr/bin/env python3
"""Fail closed when ButterflyLens software/model licence evidence is incomplete."""

from __future__ import annotations

import json
import re
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

    web_manifest_path = "apps/web/package.json"
    if web_manifest_path in tracked:
        required_web_files = {
            "apps/web/package-lock.json",
            "apps/web/dependency-licenses.json",
            "apps/web/public/THIRD_PARTY_LICENSES.txt",
        }
        missing_web_files = sorted(required_web_files - tracked)
        if missing_web_files:
            raise VerificationError(
                f"web dependency evidence is incomplete: {missing_web_files}"
            )

        web_manifest = require_json_object(
            web_manifest_path, ("dependencies", "devDependencies")
        )
        direct_web_dependencies = {
            **web_manifest["dependencies"],
            **web_manifest["devDependencies"],
        }
        non_exact = {
            name: version
            for name, version in direct_web_dependencies.items()
            if not isinstance(version, str)
            or re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", version) is None
        }
        if non_exact:
            raise VerificationError(
                f"web dependencies must use exact versions: {non_exact}"
            )

        web_lock = require_json_object(
            "apps/web/package-lock.json", ("lockfileVersion", "packages")
        )
        locked_root = web_lock["packages"].get("", {})
        for section in ("dependencies", "devDependencies"):
            if locked_root.get(section) != web_manifest[section]:
                raise VerificationError(
                    f"web lock root {section} does not match package.json"
                )

        web_licenses = require_json_object(
            "apps/web/dependency-licenses.json",
            ("schema_version", "lockfile", "allowed_licenses", "packages"),
        )
        packages = web_licenses["packages"]
        if not isinstance(packages, list) or not packages:
            raise VerificationError("web dependency licence report is empty")
        allowed = set(web_licenses["allowed_licenses"])
        invalid_packages = [
            package.get("name", "<unknown>")
            if isinstance(package, dict)
            else "<invalid>"
            for package in packages
            if not isinstance(package, dict)
            or package.get("license") not in allowed
            or not package.get("version")
        ]
        if invalid_packages:
            raise VerificationError(
                f"web dependency licence report has invalid rows: {invalid_packages}"
            )

        require_text(
            "apps/web/public/THIRD_PARTY_LICENSES.txt",
            ("react 19.2.7", "react-dom 19.2.7", "scheduler 0.27.0", "MIT License"),
        )

    deno_config_path = "supabase/functions/deno.json"
    if deno_config_path in tracked:
        required_deno_files = {
            "supabase/functions/deno.lock",
            "supabase/functions/dependency-licenses.json",
        }
        missing_deno_files = sorted(required_deno_files - tracked)
        if missing_deno_files:
            raise VerificationError(
                f"Edge Function dependency evidence is incomplete: {missing_deno_files}"
            )

        deno_config = require_json_object(deno_config_path, ("imports", "lock"))
        expected_imports = {
            "@supabase/server": "npm:@supabase/server@1.4.0",
        }
        if deno_config["imports"] != expected_imports:
            raise VerificationError("Edge Function imports are not the audited exact pins")
        if deno_config["lock"] != "./deno.lock":
            raise VerificationError("Edge Function must use its committed frozen lock")

        deno_lock = require_json_object(
            "supabase/functions/deno.lock", ("version", "specifiers", "npm")
        )
        expected_specifiers = {
            "npm:@supabase/server@1.4.0": (
                "1.4.0_@supabase+supabase-js@2.110.7"
            ),
        }
        if deno_lock["version"] != "5" or deno_lock["specifiers"] != expected_specifiers:
            raise VerificationError("Edge Function lock specifiers changed from audited pins")
        locked_packages = deno_lock["npm"]
        if not isinstance(locked_packages, dict) or not locked_packages:
            raise VerificationError("Edge Function npm lock tree is empty")

        deno_licenses = require_json_object(
            "supabase/functions/dependency-licenses.json",
            ("schema_version", "lockfile", "allowed_licenses", "packages"),
        )
        if deno_licenses["lockfile"] != "supabase/functions/deno.lock":
            raise VerificationError("Edge Function licence report names the wrong lock")
        allowed_deno_licenses = set(deno_licenses["allowed_licenses"])
        report_rows = deno_licenses["packages"]
        if not isinstance(report_rows, list) or not report_rows:
            raise VerificationError("Edge Function dependency licence report is empty")
        report_by_key = {
            row.get("lock_key"): row
            for row in report_rows
            if isinstance(row, dict) and isinstance(row.get("lock_key"), str)
        }
        if len(report_by_key) != len(report_rows) or set(report_by_key) != set(
            locked_packages
        ):
            raise VerificationError(
                "Edge Function licence report does not exactly cover the npm lock tree"
            )
        invalid_deno_rows = [
            lock_key
            for lock_key, locked in locked_packages.items()
            if not isinstance(locked, dict)
            or report_by_key[lock_key].get("integrity") != locked.get("integrity")
            or report_by_key[lock_key].get("license") not in allowed_deno_licenses
            or report_by_key[lock_key].get("scope") not in {"direct", "transitive"}
            or not report_by_key[lock_key].get("name")
            or not report_by_key[lock_key].get("version")
        ]
        if invalid_deno_rows:
            raise VerificationError(
                "Edge Function dependency licence rows are invalid: "
                f"{invalid_deno_rows}"
            )
        direct_deno = {
            row.get("name")
            for row in report_rows
            if isinstance(row, dict) and row.get("scope") == "direct"
        }
        if direct_deno != {"@supabase/server"}:
            raise VerificationError(
                f"Edge Function direct dependency set changed: {sorted(direct_deno)}"
            )

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
