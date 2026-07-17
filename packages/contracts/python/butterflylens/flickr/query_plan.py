"""Retain logical query meaning while deduplicating physical Flickr requests."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import re
from typing import Iterable, Mapping

from butterflylens.contracts.fingerprint import canonicalize_json


LOGICAL_QUERY_ASSOCIATION_SCHEMA_VERSION = (
    "butterflylens-logical-query-association:v1.0.0"
)
PHYSICAL_QUERY_REQUEST_SCHEMA_VERSION = (
    "butterflylens-physical-query-request:v1.0.0"
)
QUERY_REQUEST_LINK_SCHEMA_VERSION = "butterflylens-query-request-link:v1.0.0"
FLICKR_SEARCH_METHOD = "flickr.photos.search"
FLICKR_REST_ENDPOINT = "https://www.flickr.com/services/rest/"

_STABLE_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,159}$")
_SECRET_PARAMETER_NAMES = frozenset(
    {"api_key", "api_sig", "auth_token", "oauth_token", "password", "secret", "token"}
)
_RELATIONSHIPS = frozenset(
    {
        "accepted_name",
        "synonym",
        "english_vernacular",
        "trusted_vernacular",
        "authorized_first_nations_name",
        "genus",
        "family",
        "order",
        "broad_butterfly",
        "global_out_of_range",
    }
)


class QueryPlanError(ValueError):
    """Raised when logical meaning or physical request identity is ambiguous."""


def build_logical_query_association(
    definition: Mapping[str, object],
    *,
    associated_taxon_key: str,
    relationship: str,
    query_lane: str,
    association_reason: str,
) -> dict[str, object]:
    """Bind one query definition to one taxon without asserting an image label."""

    _validate_definition(definition)
    if _STABLE_ID.fullmatch(associated_taxon_key) is None:
        raise QueryPlanError("associated_taxon_key is invalid")
    if relationship not in _RELATIONSHIPS:
        raise QueryPlanError("logical relationship is outside the closed vocabulary")
    if _STABLE_ID.fullmatch(query_lane) is None:
        raise QueryPlanError("query_lane is invalid")
    if not isinstance(association_reason, str) or not association_reason.strip():
        raise QueryPlanError("association_reason is required")
    preimage = {
        "query_definition_id": definition["query_definition_id"],
        "query_definition_fingerprint": definition["compiler_fingerprint"],
        "associated_taxon_key": associated_taxon_key,
        "source_assertion_id": definition["source_assertion_id"],
        "relationship": relationship,
        "query_lane": query_lane,
        "tier": definition["tier"],
        "association_reason": association_reason,
        "query_term_is_taxon_label": False,
    }
    digest = _digest(preimage)
    return {
        "schema_version": LOGICAL_QUERY_ASSOCIATION_SCHEMA_VERSION,
        "logical_query_association_id": f"blqa:v1:{digest[:24]}",
        **preimage,
        "association_fingerprint": digest,
    }


def plan_physical_query_requests(
    definitions: Iterable[Mapping[str, object]],
    associations: Iterable[Mapping[str, object]],
    *,
    fixed_parameters: Mapping[str, object] | None = None,
) -> dict[str, tuple[dict[str, object], ...]]:
    """Deduplicate request semantics and retain every logical association link."""

    definitions_by_id: dict[str, Mapping[str, object]] = {}
    for definition in definitions:
        _validate_definition(definition)
        definition_id = str(definition["query_definition_id"])
        if definition_id in definitions_by_id:
            raise QueryPlanError("duplicate query definition ID")
        definitions_by_id[definition_id] = definition

    common = _normalize_parameters(fixed_parameters or {})
    if "text" in common or "method" in common:
        raise QueryPlanError("fixed parameters cannot override text or method")

    requests_by_fingerprint: dict[str, dict[str, object]] = {}
    retained_associations: list[dict[str, object]] = []
    links: list[dict[str, object]] = []
    association_ids: set[str] = set()
    link_ids: set[str] = set()
    for association in associations:
        association_copy = deepcopy(dict(association))
        _validate_association(association_copy)
        association_id = str(association_copy["logical_query_association_id"])
        if association_id in association_ids:
            raise QueryPlanError("duplicate logical query association ID")
        association_ids.add(association_id)
        definition_id = str(association_copy["query_definition_id"])
        definition = definitions_by_id.get(definition_id)
        if definition is None:
            raise QueryPlanError("logical association references an unknown definition")
        if association_copy["query_definition_fingerprint"] != definition["compiler_fingerprint"]:
            raise QueryPlanError("logical association definition fingerprint mismatch")

        parameters = {**common, "text": definition["normalized_query_text"]}
        request_preimage = {
            "provider": "flickr",
            "method": FLICKR_SEARCH_METHOD,
            "endpoint": FLICKR_REST_ENDPOINT,
            "normalized_parameters": parameters,
        }
        request_fingerprint = _digest(request_preimage)
        request = requests_by_fingerprint.get(request_fingerprint)
        if request is None:
            request = {
                "schema_version": PHYSICAL_QUERY_REQUEST_SCHEMA_VERSION,
                "physical_query_request_id": f"blpr:v1:{request_fingerprint[:24]}",
                **request_preimage,
                "request_fingerprint": request_fingerprint,
                "execution_state": "planned_not_sent",
            }
            requests_by_fingerprint[request_fingerprint] = request

        link_preimage = {
            "physical_query_request_id": request["physical_query_request_id"],
            "request_fingerprint": request_fingerprint,
            "logical_query_association_id": association_id,
            "association_fingerprint": association_copy["association_fingerprint"],
        }
        link_fingerprint = _digest(link_preimage)
        link_id = f"blql:v1:{link_fingerprint[:24]}"
        if link_id in link_ids:
            raise QueryPlanError("duplicate physical/logical request link")
        link_ids.add(link_id)
        links.append(
            {
                "schema_version": QUERY_REQUEST_LINK_SCHEMA_VERSION,
                "query_request_link_id": link_id,
                **link_preimage,
                "link_fingerprint": link_fingerprint,
            }
        )
        retained_associations.append(association_copy)

    requests = tuple(
        deepcopy(requests_by_fingerprint[key]) for key in sorted(requests_by_fingerprint)
    )
    retained_associations.sort(key=lambda item: str(item["logical_query_association_id"]))
    links.sort(
        key=lambda item: (
            str(item["physical_query_request_id"]),
            str(item["logical_query_association_id"]),
        )
    )
    return {
        "logical_associations": tuple(retained_associations),
        "physical_requests": requests,
        "request_links": tuple(links),
    }


def _validate_definition(definition: Mapping[str, object]) -> None:
    required = {
        "query_definition_id",
        "compiler_fingerprint",
        "source_assertion_id",
        "normalized_query_text",
        "tier",
        "term_semantics",
    }
    if required - set(definition):
        raise QueryPlanError("query definition is incomplete")
    if definition["term_semantics"] != "discovery_term_only_not_a_taxon_label":
        raise QueryPlanError("query definition does not preserve non-label semantics")
    if not isinstance(definition["normalized_query_text"], str) or not definition[
        "normalized_query_text"
    ]:
        raise QueryPlanError("normalized query text is invalid")
    fingerprint = definition["compiler_fingerprint"]
    if not isinstance(fingerprint, str) or re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None:
        raise QueryPlanError("query definition fingerprint is invalid")


def _validate_association(association: Mapping[str, object]) -> None:
    required = {
        "schema_version",
        "logical_query_association_id",
        "query_definition_id",
        "query_definition_fingerprint",
        "associated_taxon_key",
        "source_assertion_id",
        "relationship",
        "query_lane",
        "tier",
        "association_reason",
        "query_term_is_taxon_label",
        "association_fingerprint",
    }
    if set(association) != required:
        raise QueryPlanError("logical query association fields are not exact")
    if association["schema_version"] != LOGICAL_QUERY_ASSOCIATION_SCHEMA_VERSION:
        raise QueryPlanError("logical query association version is unsupported")
    if association["query_term_is_taxon_label"] is not False:
        raise QueryPlanError("query terms may never be taxon labels")
    preimage = {
        key: association[key]
        for key in required
        if key not in {"schema_version", "logical_query_association_id", "association_fingerprint"}
    }
    expected = _digest(preimage)
    if association["association_fingerprint"] != expected:
        raise QueryPlanError("logical query association fingerprint mismatch")
    if association["logical_query_association_id"] != f"blqa:v1:{expected[:24]}":
        raise QueryPlanError("logical query association ID mismatch")


def _normalize_parameters(parameters: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(parameters, Mapping):
        raise QueryPlanError("fixed parameters must be an object")
    normalized: dict[str, object] = {}
    for raw_key, raw_value in parameters.items():
        if not isinstance(raw_key, str) or not raw_key:
            raise QueryPlanError("parameter names must be non-empty strings")
        key = raw_key.strip().lower()
        if key in _SECRET_PARAMETER_NAMES:
            raise QueryPlanError("credentials and secrets are forbidden in query plans")
        if not isinstance(raw_value, (str, int, bool)):
            raise QueryPlanError("query parameters must be scalar JSON values")
        value = raw_value.strip() if isinstance(raw_value, str) else raw_value
        if isinstance(value, str) and not value:
            raise QueryPlanError("query parameter values cannot be empty")
        if key in normalized:
            raise QueryPlanError("parameter names collide after normalization")
        normalized[key] = value
    return {key: normalized[key] for key in sorted(normalized)}


def _digest(value: object) -> str:
    return hashlib.sha256(canonicalize_json(value)).hexdigest()
