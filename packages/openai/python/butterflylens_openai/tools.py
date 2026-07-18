"""Bounded deterministic ButterflyLens analyst tool implementations."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import math
from pathlib import Path
from typing import Any, Callable, Iterable, Literal

from jsonschema import Draft202012Validator
import rfc8785

from .catalog import (
    RESULT_SCHEMA_VERSION,
    TOOL_ORDER,
    input_schema,
    output_schema,
    tool_definitions,
)
from .repository import SubmittedEvidenceRepository


ToolStatus = Literal["available", "partial", "unavailable", "not_found", "forbidden"]
FactState = Literal[
    "observed",
    "derived",
    "unavailable",
    "withheld",
    "unfinished",
    "conflict",
    "not_applicable",
]

_MAX_RESULT_BYTES = 65_536
_TARGET_REFERENCE_SUPPORT = 20


class ToolInputError(ValueError):
    """Raised when model-provided arguments fail strict or semantic validation."""


class ToolContractError(RuntimeError):
    """Raised when an implementation attempts to return an invalid tool result."""


def _fact(
    name: str,
    value: str | int | float | bool | None,
    *,
    state: FactState,
    interpretation: str,
    citation_ids: Iterable[str] = (),
    unit: str | None = None,
) -> dict[str, Any]:
    if isinstance(value, float) and not math.isfinite(value):
        raise ToolContractError(f"fact {name} is not finite")
    return {
        "name": name,
        "state": state,
        "value": value,
        "unit": unit,
        "interpretation": interpretation,
        "citation_ids": list(dict.fromkeys(citation_ids)),
    }


def _record(
    record_id: str,
    record_type: str,
    facts: Iterable[dict[str, Any]],
    citation_ids: Iterable[str],
) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "record_type": record_type,
        "facts": list(facts),
        "citation_ids": list(dict.fromkeys(citation_ids)),
    }


class EvidenceToolbox:
    """Invoke fourteen read-only tools over the checksum-pinned submitted snapshot."""

    def __init__(
        self,
        repo_root: str | Path,
        *,
        repository: SubmittedEvidenceRepository | None = None,
    ) -> None:
        self.repository = repository or SubmittedEvidenceRepository(repo_root)
        self._input_validators = {
            name: Draft202012Validator(input_schema(name)) for name in TOOL_ORDER
        }
        self._output_validators = {
            name: Draft202012Validator(output_schema(name)) for name in TOOL_ORDER
        }
        self._dispatch: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            name: getattr(self, f"_{name}") for name in TOOL_ORDER
        }

    @property
    def definitions(self) -> list[dict[str, Any]]:
        return tool_definitions()

    def invoke(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Validate, execute, fingerprint, and validate one deterministic tool call."""

        if name not in self._dispatch:
            raise ToolInputError(f"unknown ButterflyLens tool: {name}")
        if not isinstance(arguments, dict):
            raise ToolInputError("tool arguments must be an object")
        errors = sorted(
            self._input_validators[name].iter_errors(arguments),
            key=lambda error: tuple(str(part) for part in error.absolute_path),
        )
        if errors:
            error = errors[0]
            path = ".".join(str(part) for part in error.absolute_path) or "arguments"
            raise ToolInputError(f"{name} invalid {path}: {error.message}")
        self._validate_semantics(name, arguments)
        result = self._dispatch[name](deepcopy(arguments))
        self._validate_result(name, result)
        return result

    @staticmethod
    def _validate_semantics(name: str, arguments: dict[str, Any]) -> None:
        if "scope_type" in arguments:
            national = arguments["scope_type"] == "national"
            scope_id = arguments["scope_id"]
            if national and scope_id is not None:
                raise ToolInputError("national scope requires scope_id null")
            if not national and scope_id is None:
                raise ToolInputError("non-national scope requires a scope_id")
        if name == "inspect_species":
            provided = sum(
                arguments[field] is not None
                for field in ("species_key", "scientific_name")
            )
            if provided != 1:
                raise ToolInputError(
                    "inspect_species requires exactly one of species_key and scientific_name"
                )

    def _validate_result(self, name: str, result: dict[str, Any]) -> None:
        errors = sorted(
            self._output_validators[name].iter_errors(result),
            key=lambda error: tuple(str(part) for part in error.absolute_path),
        )
        if errors:
            error = errors[0]
            path = ".".join(str(part) for part in error.absolute_path) or "result"
            raise ToolContractError(f"{name} invalid {path}: {error.message}")
        citations = result["citations"]
        citation_ids = [citation["artifact_id"] for citation in citations]
        if len(citation_ids) != len(set(citation_ids)):
            raise ToolContractError(f"{name} returned duplicate citations")
        allowed = set(citation_ids)
        for section in (result["query"], result["facts"]):
            for fact in section:
                self._validate_fact_citations(name, fact, allowed)
        for record in result["records"]:
            if not set(record["citation_ids"]).issubset(allowed):
                raise ToolContractError(f"{name} record cites an unreturned artifact")
            for fact in record["facts"]:
                self._validate_fact_citations(name, fact, allowed)
        fingerprint = result["result_fingerprint"]
        without_fingerprint = dict(result)
        without_fingerprint.pop("result_fingerprint")
        expected = "sha256:" + hashlib.sha256(
            rfc8785.dumps(without_fingerprint)
        ).hexdigest()
        if fingerprint != expected:
            raise ToolContractError(f"{name} result fingerprint mismatch")
        if len(rfc8785.dumps(result)) > _MAX_RESULT_BYTES:
            raise ToolContractError(f"{name} result exceeds bounded output size")

    @staticmethod
    def _validate_fact_citations(
        name: str, fact: dict[str, Any], allowed: set[str]
    ) -> None:
        ids = fact["citation_ids"]
        if not ids:
            raise ToolContractError(f"{name} evidence fact has no citation")
        if not set(ids).issubset(allowed):
            raise ToolContractError(f"{name} fact cites an unreturned artifact")

    def _finish(
        self,
        *,
        tool_name: str,
        status: ToolStatus,
        summary: str,
        query: Iterable[dict[str, Any]],
        facts: Iterable[dict[str, Any]],
        records: Iterable[dict[str, Any]],
        artifact_keys: Iterable[str],
        limitations: Iterable[str],
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": RESULT_SCHEMA_VERSION,
            "tool_name": tool_name,
            "status": status,
            "summary": summary,
            "query": list(query),
            "facts": list(facts),
            "records": list(records),
            "citations": self.repository.citations(artifact_keys),
            "limitations": list(limitations),
        }
        result["result_fingerprint"] = "sha256:" + hashlib.sha256(
            rfc8785.dumps(result)
        ).hexdigest()
        return result

    def _citation_ids(self, *keys: str) -> tuple[str, ...]:
        return tuple(self.repository.artifact(key).artifact_id for key in keys)

    def _scope_query(self, arguments: dict[str, Any], citation_ids: Iterable[str]) -> list[dict[str, Any]]:
        return [
            _fact(
                "scope_type",
                arguments["scope_type"],
                state="observed",
                interpretation="Validated requested geographic scope type.",
                citation_ids=citation_ids,
            ),
            _fact(
                "scope_id",
                arguments["scope_id"],
                state="not_applicable" if arguments["scope_id"] is None else "observed",
                interpretation=(
                    "National scope has no subordinate scope ID."
                    if arguments["scope_id"] is None
                    else "Validated requested public scope identifier."
                ),
                citation_ids=citation_ids,
            ),
        ]

    @staticmethod
    def _required_map_integer(payload: dict[str, Any], field: str) -> int:
        value = payload.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ToolContractError(f"submitted map {field} is not a count")
        return value

    def _map_scope_count(
        self,
        snapshot: dict[str, Any],
        scope_type: str,
        scope: dict[str, Any],
    ) -> int:
        if scope_type == "national":
            return self._required_map_integer(snapshot["counts"], "mapEligible")
        return self._required_map_integer(scope, "count")

    def _map_scope_record(
        self,
        scope: dict[str, Any],
        citation_ids: Iterable[str],
    ) -> dict[str, Any]:
        fingerprint = scope.get("summaryFingerprint")
        if not isinstance(fingerprint, str) or len(fingerprint) != 64:
            raise ToolContractError("submitted map scope has no summary fingerprint")
        evidence_fingerprint = scope.get("evidenceFingerprint")
        if not isinstance(evidence_fingerprint, str) or len(evidence_fingerprint) != 64:
            raise ToolContractError("submitted map scope has no evidence fingerprint")
        latest_year = scope.get("latestEventYear")
        if latest_year is not None and not isinstance(latest_year, int):
            raise ToolContractError("submitted map scope latest year is invalid")
        return _record(
            f"map-scope:{fingerprint}",
            "submitted_ala_map_scope",
            (
                _fact(
                    "scope_id",
                    scope.get("scopeId"),
                    state="observed",
                    interpretation="Exact public aggregate scope identifier.",
                    citation_ids=citation_ids,
                ),
                _fact(
                    "scope_label",
                    scope.get("label"),
                    state="observed",
                    interpretation="Public aggregate scope label.",
                    citation_ids=citation_ids,
                ),
                _fact(
                    "ala_occurrence_count",
                    self._required_map_integer(scope, "count"),
                    state="observed",
                    unit="occurrences",
                    interpretation="Rights-screened ALA baseline occurrence-evidence rows in this exact aggregate scope.",
                    citation_ids=citation_ids,
                ),
                _fact(
                    "unique_taxon_count",
                    self._required_map_integer(scope, "uniqueTaxonCount"),
                    state="observed",
                    unit="taxa",
                    interpretation="Distinct normalized taxon assertions represented in the aggregate; this is not a completeness claim.",
                    citation_ids=citation_ids,
                ),
                _fact(
                    "latest_event_year",
                    latest_year,
                    state="observed" if latest_year is not None else "unavailable",
                    unit="year",
                    interpretation=(
                        "Latest retained provider event year in the aggregate."
                        if latest_year is not None
                        else "No retained provider event year is available for this aggregate."
                    ),
                    citation_ids=citation_ids,
                ),
                _fact(
                    "publicly_generalised_count",
                    self._required_map_integer(scope, "publiclyGeneralisedCount"),
                    state="observed",
                    unit="occurrences",
                    interpretation="Rows marked publicly generalized by the source projection.",
                    citation_ids=citation_ids,
                ),
                _fact(
                    "evidence_fingerprint",
                    f"sha256:{evidence_fingerprint}",
                    state="observed",
                    interpretation="Fingerprint of the aggregate's evidence membership.",
                    citation_ids=citation_ids,
                ),
                _fact(
                    "summary_fingerprint",
                    f"sha256:{fingerprint}",
                    state="observed",
                    interpretation="Fingerprint of the exact aggregate summary row.",
                    citation_ids=citation_ids,
                ),
            ),
            citation_ids,
        )

    def _inspect_map_scope(self, arguments: dict[str, Any]) -> dict[str, Any]:
        keys = (
            "species_catalogue",
            "submitted_map",
            "flickr_global_status",
            "rights_manifest",
        )
        ids = self._citation_ids(*keys)
        catalogue = self.repository.species_catalogue()
        snapshot = self.repository.submitted_map()
        scope = self.repository.find_map_scope(
            scope_type=arguments["scope_type"],
            scope_id=arguments["scope_id"],
        )
        if scope is None:
            return self._finish(
                tool_name="inspect_map_scope",
                status="not_found",
                summary="The requested exact scope is not in the submitted public ALA map.",
                query=self._scope_query(arguments, ids),
                facts=(
                    _fact(
                        "scope_found",
                        False,
                        state="unavailable",
                        interpretation="No exact scope identifier matched; the tool does not guess or broaden geography.",
                        citation_ids=ids,
                    ),
                ),
                records=(),
                artifact_keys=keys,
                limitations=("No approximate geographic match was attempted.",),
            )
        is_national = arguments["scope_type"] == "national"
        count = self._map_scope_count(snapshot, arguments["scope_type"], scope)
        map_cells = self._required_map_integer(snapshot["counts"], "mapCells")
        facts = [
            _fact(
                "accepted_species",
                catalogue["speciesCount"] if is_national else None,
                state="observed" if is_national else "unavailable",
                unit="species",
                interpretation=(
                    "Accepted species in the authoritative national checklist."
                    if is_national
                    else "No committed lower-scope species aggregate exists in the submitted snapshot."
                ),
                citation_ids=ids,
            ),
            _fact(
                "ala_occurrence_count",
                count,
                state="observed",
                unit="occurrences",
                interpretation=(
                    "Rights-screened ALA baseline occurrence-evidence rows in the national public map projection."
                    if is_national
                    else "Rights-screened ALA baseline occurrence-evidence rows in the exact requested aggregate scope."
                ),
                citation_ids=ids,
            ),
            _fact(
                "flickr_candidate_count",
                None,
                state="unavailable",
                unit="candidates",
                interpretation="No completed immutable Flickr candidate snapshot is committed for this scope.",
                citation_ids=ids,
            ),
            _fact(
                "map_cell_count",
                map_cells if is_national else (1 if arguments["scope_type"] == "h3" else None),
                state=(
                    "observed"
                    if is_national or arguments["scope_type"] == "h3"
                    else "unavailable"
                ),
                unit="cells",
                interpretation=(
                    "H3 resolution-3 aggregate cells in the submitted national heatmap."
                    if is_national
                    else (
                        "The requested H3 aggregate is one map cell."
                        if arguments["scope_type"] == "h3"
                        else "A count of intersecting national heatmap cells is not materialized for this administrative scope."
                    )
                ),
                citation_ids=ids,
            ),
            _fact(
                "rights_excluded_selected",
                self._required_map_integer(snapshot["counts"], "rightsExcludedSelected")
                if is_national
                else None,
                state="observed" if is_national else "unavailable",
                unit="occurrences",
                interpretation=(
                    "Selected rows conservatively excluded from the national public projection; exclusion is not a legal conclusion."
                    if is_national
                    else "The submitted map does not publish excluded-source counts by lower scope."
                ),
                citation_ids=ids,
            ),
            _fact(
                "absence_inference_permitted",
                False,
                state="observed",
                interpretation="Withheld or unavailable map evidence cannot establish biological absence.",
                citation_ids=ids,
            ),
        ]
        return self._finish(
            tool_name="inspect_map_scope",
            status="partial",
            summary="Rights-screened ALA aggregate evidence is available for this submitted map scope; Flickr evidence remains unavailable.",
            query=self._scope_query(arguments, ids),
            facts=facts,
            records=() if is_national else (self._map_scope_record(scope, ids),),
            artifact_keys=keys,
            limitations=(
                "The complete ALA baseline remains authoritative; this is a conservative public aggregate projection with three flagged datasets excluded.",
                "The active Flickr run is not a committed artifact and was not inspected.",
                "Provider labels are assertions, and missing evidence is not biological absence.",
            ),
        )

    def _compare_ala_and_flickr(self, arguments: dict[str, Any]) -> dict[str, Any]:
        keys = (
            "species_catalogue",
            "submitted_map",
            "flickr_global_status",
            "rights_manifest",
        )
        ids = self._citation_ids(*keys)
        query = self._scope_query(arguments, ids)
        snapshot = self.repository.submitted_map()
        scope = self.repository.find_map_scope(
            scope_type=arguments["scope_type"],
            scope_id=arguments["scope_id"],
        )
        if scope is None:
            return self._finish(
                tool_name="compare_ala_and_flickr",
                status="not_found",
                summary="The requested exact scope is not in the submitted public ALA map.",
                query=query,
                facts=(
                    _fact(
                        "comparison_allowed",
                        False,
                        state="unavailable",
                        interpretation="No exact public scope matched; geography is not guessed or broadened.",
                        citation_ids=ids,
                    ),
                ),
                records=(),
                artifact_keys=keys,
                limitations=("No approximate geographic match was attempted.",),
            )
        species_key = arguments["species_key"]
        if species_key is not None:
            species = self.repository.find_species(
                species_key=species_key, scientific_name=None
            )
            query.append(
                _fact(
                    "species_key",
                    species_key,
                    state="observed",
                    interpretation="Requested accepted species key.",
                    citation_ids=ids,
                )
            )
            if species is None:
                return self._finish(
                    tool_name="compare_ala_and_flickr",
                    status="not_found",
                    summary="The requested species key is not in the authoritative submitted catalogue.",
                    query=query,
                    facts=(
                        _fact(
                            "comparison_allowed",
                            False,
                            state="unavailable",
                            interpretation="A comparison cannot be made for an unknown accepted species key.",
                            citation_ids=ids,
                        ),
                    ),
                    records=(),
                    artifact_keys=keys,
                    limitations=("No provider or model lookup was attempted.",),
                )
        species_scoped = species_key is not None
        ala_count = (
            None
            if species_scoped
            else self._map_scope_count(snapshot, arguments["scope_type"], scope)
        )
        facts = [
            _fact(
                "ala_occurrence_count",
                ala_count,
                state="unavailable" if species_scoped else "observed",
                unit="occurrences",
                interpretation=(
                    "The submitted public map is not species-granular, so it cannot supply an ALA count for this species selector."
                    if species_scoped
                    else "Rights-screened ALA baseline occurrence-evidence rows in the exact requested aggregate scope."
                ),
                citation_ids=ids,
            ),
            _fact(
                "flickr_candidate_count",
                None,
                state="unavailable",
                unit="candidates",
                interpretation="No completed immutable Flickr candidate snapshot exists for the requested scope.",
                citation_ids=ids,
            ),
            _fact(
                "count_difference",
                None,
                state="unavailable",
                unit="records",
                interpretation="A difference is not calculated unless both comparable counts are admitted.",
                citation_ids=ids,
            ),
            _fact(
                "comparison_allowed",
                False,
                state="observed",
                interpretation="The submitted evidence does not satisfy the same-scope two-source comparison gate.",
                citation_ids=ids,
            ),
        ]
        return self._finish(
            tool_name="compare_ala_and_flickr",
            status="unavailable" if species_scoped else "partial",
            summary=(
                "The submitted map has no species-granular ALA count and no immutable Flickr count for this selector."
                if species_scoped
                else "The rights-screened ALA aggregate count is available, but Flickr and the two-source difference remain unavailable."
            ),
            query=query,
            facts=facts,
            records=(),
            artifact_keys=keys,
            limitations=(
                "Unavailable is not zero and does not imply absence.",
                "The complete ALA baseline remains authoritative; the displayed count is the conservative public projection.",
                "No active Flickr or BioMiner output was inspected.",
            ),
        )

    def _inspect_species(self, arguments: dict[str, Any]) -> dict[str, Any]:
        keys = ("species_catalogue", "taxonomy_pack", "reference_quality")
        ids = self._citation_ids(*keys)
        species = self.repository.find_species(
            species_key=arguments["species_key"],
            scientific_name=arguments["scientific_name"],
        )
        query = [
            _fact(
                "species_key",
                arguments["species_key"],
                state="not_applicable" if arguments["species_key"] is None else "observed",
                interpretation="Stable species key selector when supplied.",
                citation_ids=ids,
            ),
            _fact(
                "scientific_name",
                arguments["scientific_name"],
                state="not_applicable" if arguments["scientific_name"] is None else "observed",
                interpretation="Exact accepted scientific-name selector when supplied.",
                citation_ids=ids,
            ),
        ]
        if species is None:
            return self._finish(
                tool_name="inspect_species",
                status="not_found",
                summary="No accepted species matches the exact submitted catalogue selector.",
                query=query,
                facts=(
                    _fact(
                        "model_memory_lookup_permitted",
                        False,
                        state="observed",
                        interpretation="The tool does not guess a taxon or provider identifier from model memory.",
                        citation_ids=ids,
                    ),
                ),
                records=(),
                artifact_keys=keys,
                limitations=("Only exact accepted keys or names are supported.",),
            )
        return self._finish(
            tool_name="inspect_species",
            status="available",
            summary=f"Accepted species evidence is available for {species['acceptedScientificName']}.",
            query=query,
            facts=(
                _fact(
                    "authoritative_baseline",
                    self.repository.species_catalogue()["authoritativeBaseline"],
                    state="observed",
                    interpretation="The rebuilt ButterflyLens baseline is authoritative for this goal.",
                    citation_ids=ids,
                ),
                _fact(
                    "scientific_claim_allowed",
                    False,
                    state="observed",
                    interpretation="This evidence view does not itself verify a photo identity or occurrence.",
                    citation_ids=ids,
                ),
            ),
            records=(self._species_record(species, ids),),
            artifact_keys=keys,
            limitations=(
                "English names remain sourced unreviewed assertions.",
                "Reference counts are provisional workflow diagnostics, not verified identities or quality estimates.",
                "YOLOE, BioCLIP, and human reference review are unfinished or absent.",
            ),
        )

    def _species_record(
        self, species: dict[str, Any], citation_ids: Iterable[str]
    ) -> dict[str, Any]:
        hierarchy = species.get("hierarchy", {})
        crosswalk = species.get("crosswalk", {})
        reference = species.get("referenceCoverage", {})
        english_names = species.get("englishNames", [])
        names = [
            row.get("name")
            for row in english_names[:8]
            if isinstance(row, dict) and isinstance(row.get("name"), str)
        ]
        facts = [
            _fact("species_key", species["key"], state="observed", interpretation="Stable ButterflyLens accepted-species key.", citation_ids=citation_ids),
            _fact("accepted_scientific_name", species["acceptedScientificName"], state="observed", interpretation="Accepted scientific name in the frozen authority snapshot.", citation_ids=citation_ids),
            _fact("slug", species["slug"], state="derived", interpretation="Deterministic public route slug.", citation_ids=citation_ids),
            _fact("family", self._hierarchy_name(hierarchy, "family"), state="observed", interpretation="Accepted family in the submitted hierarchy.", citation_ids=citation_ids),
            _fact("genus", self._hierarchy_name(hierarchy, "genus"), state="observed", interpretation="Accepted genus in the submitted hierarchy.", citation_ids=citation_ids),
            _fact("english_names", "; ".join(names) if names else None, state="observed" if names else "unavailable", interpretation="Sourced English-name assertions; they remain unreviewed.", citation_ids=citation_ids),
            _fact("crosswalk_status", crosswalk.get("status"), state="observed", interpretation="Conservative provider crosswalk state.", citation_ids=citation_ids),
            _fact("open_conflict_count", len(crosswalk.get("openConflicts", [])), state="conflict" if crosswalk.get("openConflicts") else "observed", unit="conflicts", interpretation="Unresolved provider-concept conflicts retained without automatic resolution.", citation_ids=citation_ids),
            _fact("reference_status", reference.get("status"), state="unfinished", interpretation="Provider-asserted provisional reference workflow state.", citation_ids=citation_ids),
            _fact("reference_candidate_media", reference.get("candidateMediaCount"), state="observed", unit="media", interpretation="Candidate metadata count, not verified identity evidence.", citation_ids=citation_ids),
            _fact("reference_selected_media", reference.get("selectedCount"), state="observed", unit="media", interpretation="Selected decode workflow count, not a release count.", citation_ids=citation_ids),
            _fact("reference_valid_decodes", reference.get("validDecodeCount"), state="observed", unit="media", interpretation="Valid decode count, not a quality estimate.", citation_ids=citation_ids),
            _fact("human_verified_media", reference.get("humanVerifiedCount"), state="unfinished", unit="media", interpretation="Human reference verification is absent in the submitted pack.", citation_ids=citation_ids),
            _fact("release_status", reference.get("releaseStatus"), state="unfinished", interpretation="Reference evidence remains blocked from scientific release.", citation_ids=citation_ids),
            _fact("source_url", species.get("sourceUrl"), state="observed", interpretation="Source authority concept URL recorded by the catalogue.", citation_ids=citation_ids),
        ]
        return _record(species["key"], "species", facts, citation_ids)

    @staticmethod
    def _hierarchy_name(hierarchy: Any, rank: str) -> str | None:
        value = hierarchy.get(rank) if isinstance(hierarchy, dict) else None
        return value.get("acceptedScientificName") if isinstance(value, dict) else None

    def _inspect_flickr_candidate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        keys = ("flickr_global_status", "rights_manifest", "species_catalogue")
        ids = self._citation_ids(*keys)
        return self._finish(
            tool_name="inspect_flickr_candidate",
            status="unavailable",
            summary="No completed immutable Flickr candidate snapshot is available to inspect.",
            query=(
                _fact("candidate_id", arguments["candidate_id"], state="observed", interpretation="Requested immutable candidate identifier.", citation_ids=ids),
            ),
            facts=(
                _fact("candidate_state", None, state="unavailable", interpretation="The submitted snapshot contains no admitted Flickr candidate record.", citation_ids=ids),
                _fact("flickr_api_call_made", False, state="observed", interpretation="This tool is local and did not call Flickr.", citation_ids=ids),
                _fact("species_identity_inferred", False, state="observed", interpretation="No species identity is inferred from identifier, metadata, or model memory.", citation_ids=ids),
            ),
            records=(),
            artifact_keys=keys,
            limitations=(
                "The user-reported active Flickr run is incomplete and was not inspected.",
                "Unavailable is not evidence that the candidate does not exist upstream.",
            ),
        )

    def _trace_record_evidence(self, arguments: dict[str, Any]) -> dict[str, Any]:
        record_type = arguments["record_type"]
        record_id = arguments["record_id"]
        key_map = {
            "species": ("species_catalogue", "taxonomy_pack", "reference_quality"),
            "ala_occurrence": ("ala_snapshot", "rights_manifest"),
            "flickr_candidate": ("flickr_global_status", "rights_manifest"),
            "classification": ("classification_contract", "reference_quality"),
            "review_consensus": ("consensus_contract", "quality_projection"),
            "worker": ("worker_contract", "worker_policy"),
            "contribution": ("contributor_projection", "geographic_impact_contract", "geographic_impact_policy"),
        }
        keys = key_map[record_type]
        ids = self._citation_ids(*keys)
        query = (
            _fact("record_type", record_type, state="observed", interpretation="Requested governed record type.", citation_ids=ids),
            _fact("record_id", record_id, state="observed", interpretation="Requested immutable record identifier.", citation_ids=ids),
        )
        if record_type == "species":
            species = self.repository.find_species(species_key=record_id, scientific_name=None)
            if species is not None:
                records = (
                    _record(
                        f"{record_id}:authority",
                        "lineage_step",
                        (
                            _fact("step_order", 1, state="observed", interpretation="Authority taxonomy source is the identity root.", citation_ids=ids),
                            _fact("relationship", "accepted_taxon_source", state="observed", interpretation="The accepted key is derived from the frozen taxonomy authority snapshot.", citation_ids=ids),
                        ),
                        ids,
                    ),
                    _record(
                        f"{record_id}:catalogue",
                        "lineage_step",
                        (
                            _fact("step_order", 2, state="derived", interpretation="Deterministic public catalogue projection step.", citation_ids=ids),
                            _fact("relationship", "checksum_verified_projection", state="derived", interpretation="Names, crosswalk state, and reference maturity are projected without automatic conflict resolution.", citation_ids=ids),
                        ),
                        ids,
                    ),
                )
                return self._finish(
                    tool_name="trace_record_evidence",
                    status="available",
                    summary=f"Stored evidence lineage is available for {species['acceptedScientificName']}.",
                    query=query,
                    facts=(
                        _fact("lineage_complete_for_claim", True, state="derived", interpretation="The cited artifacts support the returned catalogue facts, not photo identity or occurrence claims.", citation_ids=ids),
                    ),
                    records=records,
                    artifact_keys=keys,
                    limitations=("This lineage does not create human verification or occurrence evidence.",),
                )
        state: FactState = "withheld" if record_type == "ala_occurrence" else "unavailable"
        return self._finish(
            tool_name="trace_record_evidence",
            status="unavailable",
            summary="No governed submitted record lineage is available for that exact record selector.",
            query=query,
            facts=(
                _fact("lineage_state", None, state=state, interpretation="The exact record is absent from the analyst's committed readable snapshot or is behind a rights/privacy boundary.", citation_ids=ids),
            ),
            records=(),
            artifact_keys=keys,
            limitations=("The tool does not search providers, active workstores, private tables, or model memory.",),
        )

    def _explain_classification(self, arguments: dict[str, Any]) -> dict[str, Any]:
        keys = ("classification_contract", "reference_quality", "species_catalogue")
        ids = self._citation_ids(*keys)
        return self._finish(
            tool_name="explain_classification",
            status="unavailable",
            summary="No stored classification exists in the submitted snapshot; YOLOE and BioCLIP are unfinished.",
            query=(
                _fact("classification_id", arguments["classification_id"], state="observed", interpretation="Requested stored classification identifier.", citation_ids=ids),
            ),
            facts=(
                _fact("classification_state", None, state="unavailable", interpretation="No governed classification record is committed for analyst use.", citation_ids=ids),
                _fact("yoloe_state", "unfinished", state="unfinished", interpretation="YOLOE was explicitly skipped for this goal and supplied no route evidence.", citation_ids=ids),
                _fact("bioclip_state", "unfinished", state="unfinished", interpretation="BioCLIP was explicitly skipped for this goal and supplied no embedding or score evidence.", citation_ids=ids),
                _fact("probability_available", False, state="observed", interpretation="No raw model score is converted into a probability.", citation_ids=ids),
            ),
            records=(),
            artifact_keys=keys,
            limitations=("The tool never identifies a species from the model's memory.",),
        )

    def _inspect_review_consensus(self, arguments: dict[str, Any]) -> dict[str, Any]:
        keys = ("consensus_contract", "quality_projection")
        ids = self._citation_ids(*keys)
        return self._finish(
            tool_name="inspect_review_consensus",
            status="unavailable",
            summary="No completed fingerprinted review consensus is stored in the submitted replay.",
            query=(
                _fact("item_id", arguments["item_id"], state="observed", interpretation="Requested review item identifier.", citation_ids=ids),
            ),
            facts=(
                _fact("consensus_status", None, state="unavailable", interpretation="No governed consensus record is available for the requested item.", citation_ids=ids),
                _fact("review_count", None, state="unavailable", unit="reviews", interpretation="A missing review snapshot is not a zero-review assertion about live storage.", citation_ids=ids),
                _fact("majority_is_accuracy", False, state="observed", interpretation="Vote count alone cannot establish accuracy or representative quality.", citation_ids=ids),
            ),
            records=(),
            artifact_keys=keys,
            limitations=("Reviewer identities and private control evidence are never returned.",),
        )

    def _inspect_reviewer_quality(self, arguments: dict[str, Any]) -> dict[str, Any]:
        keys = ("reviewer_quality_contract", "quality_projection")
        ids = self._citation_ids(*keys)
        return self._finish(
            tool_name="inspect_reviewer_quality",
            status="unavailable",
            summary="No authenticated fingerprinted self-quality snapshot is present in the submitted replay.",
            query=(
                _fact("subject", arguments["subject"], state="observed", interpretation="The model-facing contract is self-only.", citation_ids=ids),
                _fact("domain_key", arguments["domain_key"], state="not_applicable" if arguments["domain_key"] is None else "observed", interpretation="Optional governed reviewer-quality domain selector.", citation_ids=ids),
            ),
            facts=(
                _fact("quality_estimate", None, state="unavailable", interpretation="Minimum independent evidence is not available in this replay.", citation_ids=ids),
                _fact("applied_weight", None, state="unavailable", interpretation="No reliability weight is exposed or applied by this result.", citation_ids=ids),
                _fact("visibility", "self_only", state="observed", interpretation="Reviewer quality is private to an authorized viewer and is not a public ranking.", citation_ids=ids),
                _fact("public_ranking_allowed", False, state="observed", interpretation="Reviewer comparison and ranking are prohibited.", citation_ids=ids),
            ),
            records=(),
            artifact_keys=keys,
            limitations=(
                "Model arguments cannot grant access to another reviewer.",
                "Control identities, expected answers, and person-to-person comparisons remain private.",
            ),
        )

    def _inspect_pipeline_status(self, arguments: dict[str, Any]) -> dict[str, Any]:
        keys = (
            "taxonomy_pack",
            "ala_snapshot",
            "reference_bank",
            "reference_quality",
            "quality_projection",
            "flickr_global_status",
        )
        ids = self._citation_ids(*keys)
        pipeline_id = arguments["pipeline_id"]
        query = (
            _fact("pipeline_id", pipeline_id, state="not_applicable" if pipeline_id is None else "observed", interpretation="Null selects the committed submitted pipeline; the only available ID is submitted.", citation_ids=ids),
        )
        if pipeline_id not in (None, "submitted"):
            return self._finish(
                tool_name="inspect_pipeline_status",
                status="not_found",
                summary="Only the committed submitted pipeline is available; no live pipeline lookup was attempted.",
                query=query,
                facts=(
                    _fact("pipeline_state", None, state="unavailable", interpretation="The requested pipeline ID is not in the committed snapshot.", citation_ids=ids),
                ),
                records=(),
                artifact_keys=keys,
                limitations=("Active BioMiner and Flickr workstores were not inspected.",),
            )
        stage_rows = (
            ("taxonomy", "complete", "The rebuilt accepted AFD taxonomy pack is committed."),
            ("ala_baseline", "rights_review_required", "The ALA baseline is built but occurrence publication remains rights-blocked."),
            ("reference_metadata", "provisional", "Automated metadata/decode gates are complete with provider-asserted provisional support."),
            ("yoloe", "unfinished", "YOLOE is explicitly unfinished for this goal."),
            ("bioclip", "unfinished", "BioCLIP is explicitly unfinished for this goal."),
            ("human_reference_review", "absent", "No human-verified reference media is stored in the submitted pack."),
            ("scientific_release", "blocked", "Release gates are not satisfied."),
            ("flickr_live_fetch", "unavailable", "The active external fetch is not a committed artifact and was not inspected."),
        )
        records = [
            _record(
                f"pipeline:{stage}",
                "pipeline_stage",
                (
                    _fact("stage", stage, state="observed", interpretation="Deterministic pipeline stage identifier.", citation_ids=ids),
                    _fact("stage_state", state, state="unfinished" if state in {"unfinished", "absent", "blocked"} else ("unavailable" if state == "unavailable" else "observed"), interpretation=meaning, citation_ids=ids),
                ),
                ids,
            )
            for stage, state, meaning in stage_rows
        ]
        return self._finish(
            tool_name="inspect_pipeline_status",
            status="partial",
            summary="The submitted taxonomy and provisional reference stages are committed; live, model, review, and release lanes remain unavailable or unfinished.",
            query=query,
            facts=(
                _fact("snapshot_mode", "submitted", state="observed", interpretation="This is an immutable submitted snapshot, not live operations.", citation_ids=ids),
                _fact("release_ready", False, state="observed", interpretation="Scientific release gates are not satisfied.", citation_ids=ids),
                _fact("live_state_claimed", False, state="observed", interpretation="No active workstore or provider process state is claimed.", citation_ids=ids),
            ),
            records=records,
            artifact_keys=keys,
            limitations=(
                "The user-reported Flickr run and active BioMiner work remain outside the committed snapshot.",
                "YOLOE and BioCLIP remain unfinished and were not run.",
            ),
        )

    def _inspect_worker_status(self, arguments: dict[str, Any]) -> dict[str, Any]:
        keys = ("worker_contract", "worker_policy", "quality_projection")
        ids = self._citation_ids(*keys)
        return self._finish(
            tool_name="inspect_worker_status",
            status="unavailable",
            summary="No committed governed worker heartbeat is present in the submitted snapshot.",
            query=(
                _fact("worker_id", arguments["worker_id"], state="not_applicable" if arguments["worker_id"] is None else "observed", interpretation="Optional immutable worker selector; null requests the submitted default worker state.", citation_ids=ids),
            ),
            facts=(
                _fact("worker_state", None, state="unavailable", interpretation="Without a committed heartbeat, the tool does not guess online or offline state.", citation_ids=ids),
                _fact("last_heartbeat", None, state="unavailable", interpretation="No governed heartbeat timestamp is available.", citation_ids=ids),
                _fact("m5_dependency_for_submitted_map", False, state="observed", interpretation="The submitted public snapshot remains usable without the M5 worker.", citation_ids=ids),
            ),
            records=(),
            artifact_keys=keys,
            limitations=("No local process table, PID, workstore, or active BioMiner log was inspected.",),
        )

    def _recommend_next_review_batch(self, arguments: dict[str, Any]) -> dict[str, Any]:
        keys = ("species_catalogue", "reference_quality", "taxonomy_pack")
        ids = self._citation_ids(*keys)
        query = self._scope_query(arguments, ids)
        query.extend(
            (
                _fact("species_key", arguments["species_key"], state="not_applicable" if arguments["species_key"] is None else "observed", interpretation="Optional accepted-species constraint.", citation_ids=ids),
                _fact("limit", arguments["limit"], state="observed", unit="species", interpretation="Maximum bounded recommendation count.", citation_ids=ids),
            )
        )
        if arguments["scope_type"] != "national":
            return self._finish(
                tool_name="recommend_next_review_batch",
                status="unavailable",
                summary="Lower-scope review recommendations require a committed governed map snapshot.",
                query=query,
                facts=(
                    _fact("batch_state", None, state="unavailable", interpretation="No lower-scope candidate frame is committed.", citation_ids=ids),
                ),
                records=(),
                artifact_keys=keys,
                limitations=("Geographic missingness is not biological absence.",),
            )
        species_rows = list(self.repository.species())
        requested_key = arguments["species_key"]
        if requested_key is not None:
            selected = self.repository.find_species(species_key=requested_key, scientific_name=None)
            if selected is None:
                return self._not_found_recommendation(
                    "recommend_next_review_batch", query, keys, ids
                )
            species_rows = [selected]
        reviewable = [
            row
            for row in species_rows
            if int(row.get("referenceCoverage", {}).get("selectedCount", 0)) > 0
        ]
        reviewable.sort(key=self._review_batch_sort_key)
        selected_rows = reviewable[: arguments["limit"]]
        records = [
            self._priority_record(row, index + 1, "targeted_reference_review", ids)
            for index, row in enumerate(selected_rows)
        ]
        status: ToolStatus = "available" if records else "unavailable"
        return self._finish(
            tool_name="recommend_next_review_batch",
            status=status,
            summary=(
                f"Prepared {len(records)} deterministic species-level targeted reference-review priorities."
                if records
                else "No committed selected reference media exists for the requested species constraint."
            ),
            query=query,
            facts=(
                _fact("batch_kind", "targeted_failure_discovery", state="derived", interpretation="This queue targets known evidence gaps and is not representative sampling.", citation_ids=ids),
                _fact("representative", False, state="derived", interpretation="The recommendation cannot estimate population quality.", citation_ids=ids),
                _fact("ranking_of_people_or_species", False, state="observed", interpretation="Priority order is a workflow decision, not scientific importance or contributor performance.", citation_ids=ids),
                _fact("recommended_species", len(records), state="derived", unit="species", interpretation="Bounded count returned from committed reference diagnostics.", citation_ids=ids),
            ),
            records=records,
            artifact_keys=keys,
            limitations=(
                "Recommendations identify review workflow priorities, not verified identities or occurrences.",
                "No Flickr candidate IDs are returned because no completed Flickr snapshot is committed.",
            ),
        )

    def _not_found_recommendation(
        self,
        tool_name: str,
        query: Iterable[dict[str, Any]],
        keys: Iterable[str],
        ids: Iterable[str],
    ) -> dict[str, Any]:
        return self._finish(
            tool_name=tool_name,
            status="not_found",
            summary="The requested species key is not in the authoritative submitted catalogue.",
            query=query,
            facts=(
                _fact("recommendation_available", False, state="unavailable", interpretation="Unknown taxa are not guessed from provider search or model memory.", citation_ids=ids),
            ),
            records=(),
            artifact_keys=keys,
            limitations=("Only accepted ButterflyLens species keys are eligible.",),
        )

    @staticmethod
    def _review_batch_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
        reference = row.get("referenceCoverage", {})
        conflict_count = len(row.get("crosswalk", {}).get("openConflicts", []))
        selected = int(reference.get("selectedCount", 0))
        valid = int(reference.get("validDecodeCount", 0))
        return (-conflict_count, selected, valid, row["acceptedScientificName"], row["key"])

    def _recommend_next_species(self, arguments: dict[str, Any]) -> dict[str, Any]:
        keys = ("species_catalogue", "reference_quality", "taxonomy_pack")
        ids = self._citation_ids(*keys)
        criterion = arguments["criterion"]
        rows = list(self.repository.species())
        if criterion == "open_conflicts":
            rows = [row for row in rows if self._conflict_count(row) > 0]
            rows.sort(key=lambda row: (-self._conflict_count(row), row["acceptedScientificName"], row["key"]))
            reason = "open_provider_conflicts"
        elif criterion == "reviewable_reference":
            rows = [row for row in rows if self._selected_count(row) > 0]
            rows.sort(key=self._review_batch_sort_key)
            reason = "selected_provisional_reference_media"
        else:
            rows.sort(
                key=lambda row: (
                    self._selected_count(row),
                    int(row.get("referenceCoverage", {}).get("candidateMediaCount", 0)),
                    -self._conflict_count(row),
                    row["acceptedScientificName"],
                    row["key"],
                )
            )
            reason = "reference_support_gap"
        selected_rows = rows[: arguments["limit"]]
        records = [
            self._priority_record(row, index + 1, reason, ids)
            for index, row in enumerate(selected_rows)
        ]
        return self._finish(
            tool_name="recommend_next_species",
            status="available" if records else "unavailable",
            summary=f"Prepared {len(records)} deterministic workflow priorities using criterion {criterion}.",
            query=(
                _fact("criterion", criterion, state="observed", interpretation="Explicit workflow criterion selected by the caller.", citation_ids=ids),
                _fact("limit", arguments["limit"], state="observed", unit="species", interpretation="Maximum bounded recommendation count.", citation_ids=ids),
            ),
            facts=(
                _fact("priority_basis", criterion, state="derived", interpretation="Priority derives only from committed catalogue/reference diagnostics.", citation_ids=ids),
                _fact("scientific_importance_rank", False, state="observed", interpretation="Workflow order is not rarity, presence, conservation, or scientific importance.", citation_ids=ids),
                _fact("recommended_species", len(records), state="derived", unit="species", interpretation="Bounded number of accepted species returned.", citation_ids=ids),
            ),
            records=records,
            artifact_keys=keys,
            limitations=(
                "Reference counts are provisional workflow diagnostics.",
                "No geographic absence, occurrence, probability, or model score is inferred.",
            ),
        )

    @staticmethod
    def _selected_count(row: dict[str, Any]) -> int:
        return int(row.get("referenceCoverage", {}).get("selectedCount", 0))

    @staticmethod
    def _conflict_count(row: dict[str, Any]) -> int:
        return len(row.get("crosswalk", {}).get("openConflicts", []))

    def _priority_record(
        self,
        row: dict[str, Any],
        order: int,
        reason: str,
        citation_ids: Iterable[str],
    ) -> dict[str, Any]:
        reference = row.get("referenceCoverage", {})
        selected = int(reference.get("selectedCount", 0))
        gap = max(0, _TARGET_REFERENCE_SUPPORT - selected)
        return _record(
            row["key"],
            "species_workflow_priority",
            (
                _fact("priority_order", order, state="derived", interpretation="Deterministic order within this bounded tool result only.", citation_ids=citation_ids),
                _fact("species_key", row["key"], state="observed", interpretation="Stable accepted-species key.", citation_ids=citation_ids),
                _fact("accepted_scientific_name", row["acceptedScientificName"], state="observed", interpretation="Accepted name in the authoritative submitted baseline.", citation_ids=citation_ids),
                _fact("workflow_reason", reason, state="derived", interpretation="Explicit non-scientific workflow prioritization reason.", citation_ids=citation_ids),
                _fact("selected_reference_media", selected, state="observed", unit="media", interpretation="Provisional selected decode count, not verified identity.", citation_ids=citation_ids),
                _fact("target_support_gap", gap, state="derived", unit="media", interpretation="Arithmetic gap to the configured workflow target of 20; not biological absence.", citation_ids=citation_ids),
                _fact("open_conflict_count", self._conflict_count(row), state="conflict" if self._conflict_count(row) else "observed", unit="conflicts", interpretation="Retained provider-concept conflict count.", citation_ids=citation_ids),
                _fact("human_verified_media", int(reference.get("humanVerifiedCount", 0)), state="unfinished", unit="media", interpretation="No submitted reference media has human verification.", citation_ids=citation_ids),
            ),
            citation_ids,
        )

    def _explain_geographic_contribution(self, arguments: dict[str, Any]) -> dict[str, Any]:
        keys = ("contributor_projection", "geographic_impact_contract", "geographic_impact_policy", "species_catalogue")
        ids = self._citation_ids(*keys)
        projection = self.repository.read_json("contributor_projection")
        return self._finish(
            tool_name="explain_geographic_contribution",
            status="unavailable",
            summary="No authenticated fingerprinted geographic contribution snapshot is included in the submitted replay.",
            query=self._scope_query(arguments, ids),
            facts=(
                _fact("visibility", projection["visibility"], state="observed", interpretation="Contributor impact is self-only by default.", citation_ids=ids),
                _fact("regions_helped", None, state="unavailable", unit="regions", interpretation="Generalised public-region lineage is unavailable, not zero.", citation_ids=ids),
                _fact("potential_contribution_is_occurrence", False, state="observed", interpretation="Community evidence potential is never called a new biological occurrence.", citation_ids=ids),
                _fact("exact_sensitive_region_returned", False, state="observed", interpretation="Exact sensitive locations are not exposed.", citation_ids=ids),
            ),
            records=(),
            artifact_keys=keys,
            limitations=(
                "Model arguments cannot select another contributor or grant authorization.",
                "Unavailable contribution evidence is not a zero contribution claim.",
            ),
        )

    def _prepare_impact_report(self, arguments: dict[str, Any]) -> dict[str, Any]:
        keys = ("contributor_projection", "geographic_impact_contract", "geographic_impact_policy", "quality_projection")
        ids = self._citation_ids(*keys)
        projection = self.repository.read_json("contributor_projection")
        metric_names = (
            ("reviewed_images", "reviewedImages"),
            ("resolved_conflicts", "resolvedConflicts"),
            ("species_helped", "speciesHelped"),
            ("regions_helped", "regionsHelped"),
            ("control_coverage", "controlCoverage"),
            ("expert_contribution", "expertContribution"),
        )
        facts = [
            _fact(
                output_name,
                projection["metrics"][source_name]["value"],
                state="unavailable",
                interpretation=projection["metrics"][source_name]["reason"],
                citation_ids=ids,
            )
            for output_name, source_name in metric_names
        ]
        facts.extend(
            (
                _fact("visibility", projection["visibility"], state="observed", interpretation="The report is private to the authenticated contributor.", citation_ids=ids),
                _fact("ranking_permitted", projection["rankingPermitted"], state="observed", interpretation="Contributor rankings are prohibited.", citation_ids=ids),
                _fact("speed_metric_permitted", projection["speedMetricPermitted"], state="observed", interpretation="Speed and throughput are not contribution quality.", citation_ids=ids),
                _fact("scientific_claim_allowed", projection["scientificClaimAllowed"], state="observed", interpretation="Contribution recognition does not create scientific authority.", citation_ids=ids),
            )
        )
        return self._finish(
            tool_name="prepare_impact_report",
            status="unavailable",
            summary="The self-impact report structure is available, but every submitted metric is explicitly unavailable.",
            query=(
                _fact("report_scope", arguments["report_scope"], state="observed", interpretation="The model-facing report scope is self-only.", citation_ids=ids),
            ),
            facts=facts,
            records=(),
            artifact_keys=keys,
            limitations=(
                "Unavailable metrics remain null rather than fabricated zeroes.",
                "No speed, rank, control identity, exact sensitive region, or reviewer weight is returned.",
            ),
        )
