"""Compile trusted name assertions into non-label Flickr discovery terms."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import re
from typing import Mapping

import rfc8785


QUERY_DEFINITION_SCHEMA_VERSION = "butterflylens-flickr-query-definition:v1.0.0"
_STABLE_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,159}$")
_SUPPORTED_NAME_TYPES = {
    "accepted_scientific",
    "scientific_synonym",
    "english_vernacular",
    "trusted_vernacular",
    "first_nations_language",
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
    language = assertion["language"]
    region = assertion["region"]
    source = assertion["source"]
    if not all(isinstance(value, dict) for value in (language, region, source)):
        raise QueryCompilationError("language, region, and source must be objects")
    language_code = language.get("code")
    if not isinstance(language_code, str) or not language_code:
        raise QueryCompilationError("language code is required")
    if name_type == "first_nations_language":
        raise QueryCompilationError(
            "First Nations query terms require an authorized scoped decision adapter"
        )
    preimage = {
        "source_assertion_id": assertion_id,
        "source_taxon_key": taxon_key,
        "query_text": name,
        "normalized_query_text": normalized,
        "language_code": language_code,
        "name_type": name_type,
        "taxon_rank": rank,
        "trust_tier": assertion["trust_tier"],
        "tier": _RANK_TIERS[rank],
        "source": deepcopy(source),
    }
    digest = hashlib.sha256(rfc8785.dumps(preimage)).hexdigest()
    return {
        "schema_version": QUERY_DEFINITION_SCHEMA_VERSION,
        "query_definition_id": f"blfq:v1:{digest[:24]}",
        **preimage,
        "region": deepcopy(region),
        "homonym_risk": assertion["homonym_risk"],
        "eligibility_reason": eligibility["reason"],
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
    return tuple(compiled)
