"""Compile trusted name assertions into non-label Flickr discovery terms."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import re
from typing import Mapping
import unicodedata

import rfc8785


QUERY_DEFINITION_SCHEMA_VERSION = "butterflylens-flickr-query-definition:v1.0.0"
GLOBAL_QUERY_DEFINITION_SCHEMA_VERSION = (
    "butterflylens-flickr-global-query-definition:v1.0.0"
)
_STABLE_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,159}$")
_SUPPORTED_NAME_TYPES = {
    "accepted_scientific",
    "scientific_synonym",
    "english_vernacular",
    "trusted_vernacular",
    "first_nations_language",
}
_TRUST_BY_NAME_TYPE = {
    "accepted_scientific": {"accepted_authority", "accepted_global_authority"},
    "scientific_synonym": {"provider_linked_synonym"},
    "english_vernacular": {
        "authority_vernacular",
        "provider_curated_vernacular",
    },
    "trusted_vernacular": {"trusted_vernacular_authority"},
    "first_nations_language": {"authorized_first_nations_name"},
}
_RANK_TIERS = {"species": 1, "genus": 2, "family": 3, "order": 4, "superfamily": 4}


class QueryCompilationError(ValueError):
    """Raised when a source assertion cannot become a truthful query definition."""


def compile_name_assertion(assertion: Mapping[str, object]) -> dict[str, object]:
    """Compile one eligible local name assertion without executing a request."""

    required = {
        "assertion_id",
        "butterflylens_key",
        "name",
        "normalized_name",
        "name_type",
        "taxon_rank",
        "language",
        "region",
        "trust_tier",
        "homonym_risk",
        "query_eligibility",
        "source",
    }
    missing = sorted(required - set(assertion))
    if missing:
        raise QueryCompilationError(f"name assertion missing fields: {', '.join(missing)}")
    assertion_id = assertion["assertion_id"]
    taxon_key = assertion["butterflylens_key"]
    if not isinstance(assertion_id, str) or _STABLE_ID.fullmatch(assertion_id) is None:
        raise QueryCompilationError("invalid assertion_id")
    if not isinstance(taxon_key, str) or _STABLE_ID.fullmatch(taxon_key) is None:
        raise QueryCompilationError("invalid butterflylens_key")
    name = assertion["name"]
    normalized = assertion["normalized_name"]
    if not isinstance(name, str) or not name.strip() or len(name) > 200:
        raise QueryCompilationError("query name is invalid")
    if not isinstance(normalized, str) or not normalized.strip() or len(normalized) > 200:
        raise QueryCompilationError("normalized query name is invalid")
    if normalized != _normalize_query_name(name):
        raise QueryCompilationError("normalized query name does not match query text")
    name_type = assertion["name_type"]
    if name_type not in _SUPPORTED_NAME_TYPES:
        raise QueryCompilationError("name type is not supported by the compiler")
    rank = assertion["taxon_rank"]
    if rank not in _RANK_TIERS:
        raise QueryCompilationError("taxon rank has no declared query tier")
    eligibility = assertion["query_eligibility"]
    if not isinstance(eligibility, dict) or eligibility.get("eligible") is not True:
        reason = eligibility.get("reason") if isinstance(eligibility, dict) else "missing"
        raise QueryCompilationError(f"name assertion is not query eligible: {reason}")
    eligibility_reason = eligibility.get("reason")
    if (
        not isinstance(eligibility_reason, str)
        or not eligibility_reason
        or eligibility_reason.startswith("excluded_")
        or "pending" in eligibility_reason
    ):
        raise QueryCompilationError("query eligibility reason is contradictory or incomplete")
    homonym_risk = assertion["homonym_risk"]
    if not isinstance(homonym_risk, str) or not homonym_risk.startswith("none_detected"):
        raise QueryCompilationError("name assertion has unresolved homonym risk")
    language = assertion["language"]
    region = assertion["region"]
    source = assertion["source"]
    if not all(isinstance(value, dict) for value in (language, region, source)):
        raise QueryCompilationError("language, region, and source must be objects")
    language_code = language.get("code")
    if not isinstance(language_code, str) or not language_code:
        raise QueryCompilationError("language code is required")
    if name_type in {"accepted_scientific", "scientific_synonym"} and language_code != "zxx":
        raise QueryCompilationError("scientific name language must be zxx")
    if name_type == "english_vernacular" and language_code != "en":
        raise QueryCompilationError("English vernacular language must be en")
    if name_type == "first_nations_language":
        raise QueryCompilationError(
            "First Nations query terms require an authorized scoped decision adapter"
        )
    trust_tier = assertion["trust_tier"]
    if trust_tier not in _TRUST_BY_NAME_TYPE[name_type]:
        raise QueryCompilationError("name assertion trust is insufficient for its type")
    provider = source.get("provider")
    if not isinstance(provider, str) or not provider:
        raise QueryCompilationError("query source provider is required")
    preimage = {
        "source_assertion_id": assertion_id,
        "source_taxon_key": taxon_key,
        "query_text": name,
        "normalized_query_text": normalized,
        "language_code": language_code,
        "name_type": name_type,
        "taxon_rank": rank,
        "trust_tier": trust_tier,
        "tier": _RANK_TIERS[rank],
        "source": deepcopy(source),
    }
    digest = hashlib.sha256(rfc8785.dumps(preimage)).hexdigest()
    return {
        "schema_version": QUERY_DEFINITION_SCHEMA_VERSION,
        "query_definition_id": f"blfq:v1:{digest[:24]}",
        **preimage,
        "region": deepcopy(region),
        "homonym_risk": homonym_risk,
        "eligibility_reason": eligibility_reason,
        "term_semantics": "discovery_term_only_not_a_taxon_label",
        "compiler_fingerprint": digest,
    }


def compile_name_assertions(
    assertions: list[Mapping[str, object]],
) -> tuple[dict[str, object], ...]:
    """Compile a deterministic set while retaining every logical assertion."""

    compiled = [compile_name_assertion(assertion) for assertion in assertions]
    compiled.sort(
        key=lambda item: (
            item["tier"],
            item["normalized_query_text"],
            item["source_taxon_key"],
            item["source_assertion_id"],
        )
    )
    identities = [item["query_definition_id"] for item in compiled]
    if len(identities) != len(set(identities)):
        raise QueryCompilationError("query definition ID collision")
    taxon_keys_by_term: dict[str, set[str]] = {}
    for item in compiled:
        term = str(item["normalized_query_text"])
        taxon_keys_by_term.setdefault(term, set()).add(str(item["source_taxon_key"]))
    collisions = sorted(
        term for term, taxon_keys in taxon_keys_by_term.items() if len(taxon_keys) > 1
    )
    if collisions:
        raise QueryCompilationError(
            "eligible normalized query term maps to multiple taxa: " + ", ".join(collisions)
        )
    return tuple(compiled)


def compile_global_out_of_range_assertion(
    assertion: Mapping[str, object],
) -> dict[str, object]:
    """Compile one authoritative global species assertion into tier 5."""

    base = compile_name_assertion(assertion)
    if base["taxon_rank"] != "species":
        raise QueryCompilationError("global out-of-range terms must be species rank")
    if base["name_type"] != "accepted_scientific":
        raise QueryCompilationError(
            "global out-of-range terms must be accepted scientific names"
        )
    if base["trust_tier"] != "accepted_global_authority":
        raise QueryCompilationError("global out-of-range trust is not authoritative")
    homonym_risk = base["homonym_risk"]
    if not isinstance(homonym_risk, str) or not homonym_risk.startswith("none_detected"):
        raise QueryCompilationError("global out-of-range term has homonym risk")
    scope = assertion.get("australia_scope")
    required_scope = {
        "status",
        "basis",
        "comparison_pack_id",
        "comparison_taxa_sha256",
    }
    if not isinstance(scope, dict) or set(scope) != required_scope:
        raise QueryCompilationError("global assertion has incomplete Australia scope evidence")
    if scope["status"] != "not_currently_known":
        raise QueryCompilationError("global assertion is not out of Australian range")
    if scope["basis"] != "authoritative_checklist_complement":
        raise QueryCompilationError("global assertion range basis is not authoritative")
    if (
        not isinstance(scope["comparison_taxa_sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", scope["comparison_taxa_sha256"]) is None
    ):
        raise QueryCompilationError("global assertion comparison checksum is invalid")
    preimage = {
        key: deepcopy(base[key])
        for key in (
            "source_assertion_id",
            "source_taxon_key",
            "query_text",
            "normalized_query_text",
            "language_code",
            "name_type",
            "taxon_rank",
            "trust_tier",
            "source",
        )
    }
    preimage["tier"] = 5
    preimage["scope_evidence"] = deepcopy(scope)
    digest = hashlib.sha256(rfc8785.dumps(preimage)).hexdigest()
    return {
        **base,
        "schema_version": GLOBAL_QUERY_DEFINITION_SCHEMA_VERSION,
        "query_definition_id": f"blfq:v1:{digest[:24]}",
        "tier": 5,
        "scope_evidence": deepcopy(scope),
        "compiler_fingerprint": digest,
    }


def _normalize_query_name(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())
