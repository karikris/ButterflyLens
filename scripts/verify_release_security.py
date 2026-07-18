#!/usr/bin/env python3
"""Verify the credential-free ButterflyLens release-security boundary."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import subprocess
import tomllib


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "supabase" / "migrations"

SECRET_PATTERNS = {
    "aws_access_key": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "jwt": re.compile(
        rb"\beyJ[A-Za-z0-9_-]{30,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
    ),
    "openai_secret": re.compile(rb"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}\b"),
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "supabase_secret": re.compile(rb"\bsb_secret_[A-Za-z0-9_-]{20,}\b"),
}

EXPECTED_PYTHON_NETWORK_FILES = {
    "scripts/build_ala_baseline.py",
    "scripts/build_butterfly_names.py",
    "scripts/build_butterfly_taxonomy.py",
    "scripts/crosswalk_butterfly_taxonomy.py",
}
EXPECTED_BROWSER_NETWORK_FILES = {
    "apps/web/src/analyst/analystModel.ts",
    "apps/web/src/operations/monitoringTransport.ts",
}
EXPECTED_EDGE_SUPABASE_FILES = {
    "supabase/functions/ask-butterflylens/index.ts",
    "supabase/functions/control-butterflylens/index.ts",
    "supabase/functions/operations-status/index.ts",
    "supabase/functions/sign-b2-object/index.ts",
}
EXPECTED_OPENAI_FILES = {"supabase/functions/ask-butterflylens/index.ts"}


class SecurityVerificationError(RuntimeError):
    """Raised when a release-security invariant is not satisfied."""


@dataclass(frozen=True)
class SecurityAudit:
    public_rls_tables: int
    security_definer_functions: int
    security_invoker_views: int
    tracked_files_scanned_for_secrets: int
    external_network_boundary_files: int
    privacy_status: str
    community_writes_enabled: bool
    live_analyst_enabled: bool
    release_ready: bool
    release_blockers: tuple[str, ...]


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def migration_documents() -> list[tuple[Path, str]]:
    return [
        (path, path.read_text(encoding="utf-8"))
        for path in sorted(MIGRATIONS.glob("*.sql"))
    ]


def verify_rls(documents: list[tuple[Path, str]]) -> tuple[int, int, int]:
    combined = "\n".join(text for _, text in documents)
    public_tables = set(
        re.findall(
            r"create\s+table(?:\s+if\s+not\s+exists)?\s+public\.([a-z0-9_]+)",
            combined,
            flags=re.IGNORECASE,
        )
    )
    rls_tables = set(
        re.findall(
            r"alter\s+table\s+public\.([a-z0-9_]+)\s+enable\s+row\s+level\s+security",
            combined,
            flags=re.IGNORECASE,
        )
    )
    missing_rls = sorted(public_tables - rls_tables)
    if missing_rls:
        raise SecurityVerificationError(f"public tables without RLS: {missing_rls}")

    views = 0
    for path, text in documents:
        for match in re.finditer(
            r"create\s+(?:or\s+replace\s+)?view\s+public\.([a-z0-9_]+)",
            text,
            flags=re.IGNORECASE,
        ):
            views += 1
            header = text[match.start() : match.start() + 240].lower()
            if "security_invoker = true" not in header:
                raise SecurityVerificationError(
                    f"public view is not security invoker: {relative(path)}:{match.group(1)}"
                )

    if re.search(r"\bauth\.role\s*\(", combined, flags=re.IGNORECASE):
        raise SecurityVerificationError("deprecated auth.role() appears in migrations")
    if re.search(r"\b(?:raw_)?user_meta_data\b", combined, flags=re.IGNORECASE):
        raise SecurityVerificationError("user-editable auth metadata appears in authorization SQL")

    function_starts = list(
        re.finditer(
            r"create\s+(?:or\s+replace\s+)?function\s+([a-z0-9_]+)\.([a-z0-9_]+)\s*\(",
            combined,
            flags=re.IGNORECASE,
        )
    )
    revoke_blocks = re.findall(
        r"revoke\s+all\s+on\s+function\s+(.*?);",
        combined,
        flags=re.IGNORECASE | re.DOTALL,
    )
    security_definers = 0
    for index, match in enumerate(function_starts):
        end = function_starts[index + 1].start() if index + 1 < len(function_starts) else len(combined)
        block = combined[match.start() : end]
        if not re.search(r"\bsecurity\s+definer\b", block, flags=re.IGNORECASE):
            continue
        security_definers += 1
        if not re.search(r"set\s+search_path\s*=\s*''", block, flags=re.IGNORECASE):
            raise SecurityVerificationError(
                f"security definer lacks an empty search path: {match.group(1)}.{match.group(2)}"
            )
        public_function = re.compile(
            rf"\bpublic\.{re.escape(match.group(2))}\b", flags=re.IGNORECASE
        )
        if match.group(1).lower() == "public" and not any(
            public_function.search(block) for block in revoke_blocks
        ):
            raise SecurityVerificationError(
                f"public security definer lacks an explicit default revoke: {match.group(2)}"
            )
    return len(public_tables), security_definers, views


def tracked_paths() -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    paths = [ROOT / item.decode("utf-8") for item in completed.stdout.split(b"\0") if item]
    current_script = Path(__file__).resolve()
    if current_script not in paths:
        paths.append(current_script)
    return sorted(set(paths))


def verify_no_secrets(paths: list[Path]) -> int:
    scanned = 0
    for path in paths:
        if not path.is_file():
            continue
        data = path.read_bytes()
        if b"\0" in data:
            continue
        scanned += 1
        for pattern_name, pattern in SECRET_PATTERNS.items():
            if pattern.search(data):
                raise SecurityVerificationError(
                    f"{pattern_name} pattern in tracked text: {relative(path)}"
                )
    return scanned


def source_files(directory: Path, suffixes: tuple[str, ...]) -> list[Path]:
    return [
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix in suffixes and "node_modules" not in path.parts
    ]


def verify_external_network_inventory() -> int:
    python_network: set[str] = set()
    for directory in (ROOT / "scripts", ROOT / "packages", ROOT / "services"):
        for path in source_files(directory, (".py",)):
            text = path.read_text(encoding="utf-8")
            if re.search(
                r"(?:import\s+urllib\.request|from\s+urllib\.request\s+import|"
                r"import\s+(?:requests|httpx|aiohttp|boto3)\b)",
                text,
            ):
                python_network.add(relative(path))
    if python_network != EXPECTED_PYTHON_NETWORK_FILES:
        raise SecurityVerificationError(
            f"Python external-network inventory changed: {sorted(python_network)}"
        )

    browser_network: set[str] = set()
    for path in source_files(ROOT / "apps" / "web" / "src", (".ts", ".tsx")):
        if ".test." in path.name or ".e2e." in path.name:
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"(?:\?\?\s*fetch\b|=\s*fetch\s*[,;)])", text):
            browser_network.add(relative(path))
    if browser_network != EXPECTED_BROWSER_NETWORK_FILES:
        raise SecurityVerificationError(
            f"browser external-network inventory changed: {sorted(browser_network)}"
        )

    edge_supabase: set[str] = set()
    openai_clients: set[str] = set()
    for path in source_files(ROOT / "supabase" / "functions", (".ts",)):
        if "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if "withSupabase" in text:
            edge_supabase.add(relative(path))
        if "new OpenAI(" in text:
            openai_clients.add(relative(path))
    if edge_supabase != EXPECTED_EDGE_SUPABASE_FILES:
        raise SecurityVerificationError(
            f"Edge Supabase boundary inventory changed: {sorted(edge_supabase)}"
        )
    if openai_clients != EXPECTED_OPENAI_FILES:
        raise SecurityVerificationError(
            f"OpenAI boundary inventory changed: {sorted(openai_clients)}"
        )

    flickr_source = ROOT / "packages" / "contracts" / "python" / "butterflylens" / "flickr"
    for path in source_files(flickr_source, (".py",)):
        text = path.read_text(encoding="utf-8")
        if re.search(
            r"(?:import\s+urllib\.request|from\s+urllib\.request\s+import|"
            r"import\s+(?:requests|httpx|aiohttp)\b)",
            text,
        ):
            raise SecurityVerificationError(
                f"Flickr contract gained a built-in transport: {relative(path)}"
            )
    return len(python_network | browser_network | edge_supabase | openai_clients)


def verify_privacy_and_release_blocks() -> tuple[str, bool, bool, tuple[str, ...]]:
    policy = json.loads(
        (ROOT / "policies" / "community-privacy-policy.v1.json").read_text(
            encoding="utf-8"
        )
    )
    config = tomllib.loads((ROOT / "supabase" / "config.toml").read_text(encoding="utf-8"))
    auth = config["auth"]
    email = auth["email"]
    if policy["status"] != "prelaunch_blocked":
        raise SecurityVerificationError("privacy policy no longer fails closed")
    if policy["community_write_access"] or policy["live_analyst_enabled"]:
        raise SecurityVerificationError("privacy-blocked features are marked enabled")
    if auth["enable_signup"] or email["enable_signup"] or auth["enable_anonymous_sign_ins"]:
        raise SecurityVerificationError("local Auth permits a prelaunch account path")
    if (
        auth["minimum_password_length"] < 12
        or auth["password_requirements"] != "lower_upper_letters_digits_symbols"
        or not email["enable_confirmations"]
        or not email["secure_password_change"]
    ):
        raise SecurityVerificationError("local Auth hardening does not meet the release policy")

    ala = json.loads(
        (
            ROOT
            / "data/packs/australian_butterflies/v1/ala/ala_snapshot_manifest.json"
        ).read_text(encoding="utf-8")
    )
    yoloe = json.loads(
        (
            ROOT
            / "data/packs/australian_butterflies/v1/references/v1/"
            "reference_yoloe_readiness_manifest.json"
        ).read_text(encoding="utf-8")
    )
    bioclip = json.loads(
        (
            ROOT
            / "data/packs/australian_butterflies/v1/references/v1/"
            "reference_bioclip_status.json"
        ).read_text(encoding="utf-8")
    )
    rights_uids = ala["rights"]["citation_restrictive_rights_review_required_uids"]
    blockers = [f"community_privacy:{item}" for item in policy["launch_blockers"]]
    blockers.extend(f"ala_dataset_rights:{uid}" for uid in rights_uids)
    if yoloe["status"] != "blocked_not_executed":
        raise SecurityVerificationError("YOLOE is not in the required unfinished state")
    blockers.append("yoloe:blocked_not_executed")
    if bioclip["status"] != "skipped_unfinished_by_goal_instruction":
        raise SecurityVerificationError("BioCLIP is not in the required unfinished state")
    blockers.append("bioclip:skipped_unfinished_by_goal_instruction")
    return (
        policy["status"],
        bool(policy["community_write_access"]),
        bool(policy["live_analyst_enabled"]),
        tuple(sorted(blockers)),
    )


def run_audit() -> SecurityAudit:
    public_tables, security_definers, views = verify_rls(migration_documents())
    scanned_files = verify_no_secrets(tracked_paths())
    network_files = verify_external_network_inventory()
    privacy_status, writes_enabled, analyst_enabled, blockers = (
        verify_privacy_and_release_blocks()
    )
    return SecurityAudit(
        public_rls_tables=public_tables,
        security_definer_functions=security_definers,
        security_invoker_views=views,
        tracked_files_scanned_for_secrets=scanned_files,
        external_network_boundary_files=network_files,
        privacy_status=privacy_status,
        community_writes_enabled=writes_enabled,
        live_analyst_enabled=analyst_enabled,
        release_ready=False,
        release_blockers=blockers,
    )


def main() -> None:
    audit = run_audit()
    print(json.dumps(asdict(audit), sort_keys=True, separators=(",", ":")))
    print(
        "release security verification: PASS "
        f"(public_rls_tables={audit.public_rls_tables}, "
        f"security_invoker_views={audit.security_invoker_views}, "
        f"security_definers={audit.security_definer_functions}, "
        f"tracked_text_files={audit.tracked_files_scanned_for_secrets}, "
        f"network_boundary_files={audit.external_network_boundary_files}, "
        "release_ready=false)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, KeyError, ValueError, SecurityVerificationError, subprocess.SubprocessError) as error:
        raise SystemExit(f"release security verification: FAIL: {error}") from error
