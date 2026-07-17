"""Persist every logical association behind a deduplicated Flickr request."""

from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Iterable, Mapping, Protocol

from butterflylens.contracts.fingerprint import canonicalize_json

from .execution import SEARCH_PAGE_EXECUTION_SCHEMA_VERSION
from .query_plan import (
    validate_logical_query_association,
    validate_query_request_link,
)


LOGICAL_ASSOCIATION_LEDGER_SCHEMA_VERSION = (
    "butterflylens-flickr-logical-association-ledger:v1.0.0"
)


class LogicalAssociationLedgerError(ValueError):
    """Raised when physical execution would lose or alter logical query meaning."""


class LogicalAssociationLedgerStore(Protocol):
    """Atomic service-side adapter for public.api_request_associations."""

    def insert_api_request_associations(
        self, records: tuple[Mapping[str, object], ...]
    ) -> Iterable[Mapping[str, object]]: ...


def persist_logical_associations(
    execution: Mapping[str, object],
    request_hash_receipt: Mapping[str, object],
    logical_associations: Iterable[Mapping[str, object]],
    request_links: Iterable[Mapping[str, object]],
    *,
    api_request_pk: int,
    association_pk_by_id: Mapping[str, int],
    store: LogicalAssociationLedgerStore,
) -> dict[str, object]:
    """Atomically persist all logical associations for one executed page."""

    _validate_positive_key(api_request_pk, "api_request_pk")
    _validate_execution_receipt(execution, request_hash_receipt)
    associations = [deepcopy(dict(item)) for item in logical_associations]
    links = [deepcopy(dict(item)) for item in request_links]
    if not associations or len(associations) != len(links):
        raise LogicalAssociationLedgerError(
            "logical associations and request links must be non-empty and complete"
        )
    associations_by_id: dict[str, dict[str, object]] = {}
    for association in associations:
        validate_logical_query_association(association)
        association_id = str(association["logical_query_association_id"])
        if association_id in associations_by_id:
            raise LogicalAssociationLedgerError("duplicate logical association")
        associations_by_id[association_id] = association
    if set(association_pk_by_id) != set(associations_by_id):
        raise LogicalAssociationLedgerError(
            "database association key mapping is incomplete or contains extras"
        )
    database_keys = list(association_pk_by_id.values())
    for key in database_keys:
        _validate_positive_key(key, "query_association_pk")
    if len(database_keys) != len(set(database_keys)):
        raise LogicalAssociationLedgerError("database association keys are duplicated")

    root_request_id = execution["root_physical_query_request_id"]
    root_request_fingerprint = execution["root_request_fingerprint"]
    links_by_association: dict[str, dict[str, object]] = {}
    for link in links:
        validate_query_request_link(link)
        association_id = str(link["logical_query_association_id"])
        association = associations_by_id.get(association_id)
        if association is None or link["association_fingerprint"] != association[
            "association_fingerprint"
        ]:
            raise LogicalAssociationLedgerError(
                "request link does not bind a retained logical association"
            )
        if (
            link["physical_query_request_id"] != root_request_id
            or link["request_fingerprint"] != root_request_fingerprint
        ):
            raise LogicalAssociationLedgerError(
                "request link does not bind the executed page root"
            )
        if association_id in links_by_association:
            raise LogicalAssociationLedgerError(
                "logical association has duplicate request links"
            )
        links_by_association[association_id] = link
    if set(links_by_association) != set(associations_by_id):
        raise LogicalAssociationLedgerError("logical request links are incomplete")

    records: list[dict[str, object]] = []
    for association_id in sorted(associations_by_id):
        link = links_by_association[association_id]
        preimage = {
            "api_request_id": request_hash_receipt["api_request_id"],
            "page_request_fingerprint": execution["page_request_fingerprint"],
            "query_request_link_id": link["query_request_link_id"],
            "query_request_link_fingerprint": link["link_fingerprint"],
        }
        fingerprint = _digest(preimage)
        records.append(
            {
                "api_request_association_id": f"blra:v1:{fingerprint[:24]}",
                "api_request_pk": api_request_pk,
                "query_association_pk": association_pk_by_id[association_id],
                "query_request_link_id": link["query_request_link_id"],
                "link_fingerprint": fingerprint,
            }
        )
    immutable_records = tuple(records)
    acknowledgement = tuple(
        deepcopy(dict(item))
        for item in store.insert_api_request_associations(
            tuple(deepcopy(record) for record in immutable_records)
        )
    )
    _validate_acknowledgement(acknowledgement, immutable_records)
    row_fingerprints = sorted(str(row["link_fingerprint"]) for row in records)
    receipt_preimage = {
        "api_request_id": request_hash_receipt["api_request_id"],
        "api_request_pk": api_request_pk,
        "association_count": len(records),
        "link_fingerprints": row_fingerprints,
    }
    receipt_fingerprint = _digest(receipt_preimage)
    return {
        "schema_version": LOGICAL_ASSOCIATION_LEDGER_SCHEMA_VERSION,
        "logical_ledger_id": f"blla:v1:{receipt_fingerprint[:24]}",
        **receipt_preimage,
        "records": immutable_records,
        "query_term_is_taxon_label": False,
        "storage_table": "public.api_request_associations",
        "storage_state": "persisted",
        "receipt_fingerprint": receipt_fingerprint,
    }


def _validate_execution_receipt(
    execution: Mapping[str, object], receipt: Mapping[str, object]
) -> None:
    if execution.get("schema_version") != SEARCH_PAGE_EXECUTION_SCHEMA_VERSION:
        raise LogicalAssociationLedgerError("search-page execution version is unsupported")
    if execution.get("execution_state") != "checkpointed":
        raise LogicalAssociationLedgerError("search-page execution is not checkpointed")
    if receipt.get("storage_state") != "persisted" or receipt.get(
        "storage_table"
    ) != "public.api_requests":
        raise LogicalAssociationLedgerError("request hash receipt is not persisted")
    record = receipt.get("record")
    if not isinstance(record, dict):
        raise LogicalAssociationLedgerError("request hash receipt record is invalid")
    if (
        receipt.get("api_request_id") != execution.get("budget_request_id")
        or record.get("api_request_id") != execution.get("budget_request_id")
        or receipt.get("request_fingerprint")
        != execution.get("page_request_fingerprint")
        or record.get("request_fingerprint")
        != execution.get("page_request_fingerprint")
    ):
        raise LogicalAssociationLedgerError(
            "request hash receipt does not identify the executed page"
        )


def _validate_acknowledgement(
    acknowledgement: tuple[Mapping[str, object], ...],
    records: tuple[Mapping[str, object], ...],
) -> None:
    if len(acknowledgement) != len(records):
        raise LogicalAssociationLedgerError(
            "logical association store acknowledgement is incomplete"
        )
    expected = {
        str(record["api_request_association_id"]): record for record in records
    }
    observed: dict[str, Mapping[str, object]] = {}
    for row in acknowledgement:
        row_id = str(row.get("api_request_association_id"))
        if row_id in observed or row_id not in expected:
            raise LogicalAssociationLedgerError(
                "logical association store acknowledgement has unknown or duplicate rows"
            )
        for field in (
            "api_request_association_id",
            "api_request_pk",
            "query_association_pk",
            "query_request_link_id",
            "link_fingerprint",
        ):
            if row.get(field) != expected[row_id][field]:
                raise LogicalAssociationLedgerError(
                    f"logical association store acknowledgement changed {field}"
                )
        observed[row_id] = row


def _validate_positive_key(value: int, field: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise LogicalAssociationLedgerError(f"{field} must be a positive database key")


def _digest(value: object) -> str:
    return hashlib.sha256(canonicalize_json(value)).hexdigest()
