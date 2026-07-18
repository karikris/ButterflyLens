import toolContractsJson from "../../../packages/openai/tool_contracts.json" with {
  type: "json",
};
import artifactRegistryJson from "../../../packages/openai/submitted-artifacts.v1.json" with {
  type: "json",
};
import speciesCatalogueJson from "../../../apps/web/src/species/submittedSpeciesCatalogue.json" with {
  type: "json",
};
import submittedMapSnapshotJson from "../../../apps/web/src/map/submittedMapSnapshot.json" with {
  type: "json",
};
import contributorProjectionJson from "../../../apps/web/src/community/submittedContributorImpact.json" with {
  type: "json",
};

import {
  assertJsonSchema,
  canonicalJson,
  isJsonObject,
  type JsonObject,
  type JsonPrimitive,
  type JsonSchema,
  type JsonValue,
  SchemaValidationError,
  sha256Fingerprint,
} from "./schema.ts";

export const TOOL_NAMES = [
  "inspect_map_scope",
  "compare_ala_and_flickr",
  "inspect_species",
  "inspect_flickr_candidate",
  "trace_record_evidence",
  "explain_classification",
  "inspect_review_consensus",
  "inspect_reviewer_quality",
  "inspect_pipeline_status",
  "inspect_worker_status",
  "recommend_next_review_batch",
  "recommend_next_species",
  "explain_geographic_contribution",
  "prepare_impact_report",
] as const;

export type ToolName = (typeof TOOL_NAMES)[number];

type EvidenceState =
  | "observed"
  | "derived"
  | "unavailable"
  | "withheld"
  | "unfinished"
  | "conflict"
  | "not_applicable";

type ToolStatus =
  | "available"
  | "partial"
  | "unavailable"
  | "not_found"
  | "forbidden";

type Citation = {
  artifact_id: string;
  repository: "karikris/ButterflyLens";
  commit: string;
  path: string;
  fingerprint: string;
};

type Fact = {
  name: string;
  state: EvidenceState;
  value: JsonPrimitive;
  unit: string | null;
  interpretation: string;
  citation_ids: string[];
};

type EvidenceRecord = {
  record_id: string;
  record_type: string;
  facts: Fact[];
  citation_ids: string[];
};

export type ToolResult = {
  schema_version: "butterflylens-openai-tool-result:v1.0.0";
  tool_name: ToolName;
  status: ToolStatus;
  summary: string;
  query: Fact[];
  facts: Fact[];
  records: EvidenceRecord[];
  citations: Citation[];
  limitations: string[];
  result_fingerprint: string;
};

type ArtifactRow = {
  key: string;
  artifact_id: string;
  path: string;
  sha256: string;
};

const toolContracts = toolContractsJson as unknown as {
  output_schema: JsonSchema;
  tools: Array<{ name: string; parameters: JsonSchema }>;
};
const artifactRegistry = artifactRegistryJson as unknown as {
  repository: "karikris/ButterflyLens";
  commit: string;
  artifacts: ArtifactRow[];
};
const speciesCatalogue = speciesCatalogueJson as unknown as JsonObject;
const submittedMapSnapshot = submittedMapSnapshotJson as unknown as JsonObject;
const contributorProjection =
  contributorProjectionJson as unknown as JsonObject;
const artifacts = new Map(
  artifactRegistry.artifacts.map((artifact) => [artifact.key, artifact]),
);

export const OPENAI_TOOL_DEFINITIONS = toolContractsJson
  .tools as unknown as Array<{
    type: "function";
    name: ToolName;
    description: string;
    strict: true;
    parameters: JsonSchema;
  }>;

export class SubmittedToolError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SubmittedToolError";
  }
}

export async function executeSubmittedTool(
  name: string,
  argumentsValue: unknown,
): Promise<ToolResult> {
  if (!TOOL_NAMES.includes(name as ToolName)) {
    throw new SubmittedToolError(`unknown ButterflyLens tool: ${name}`);
  }
  const definition = toolContracts.tools.find((tool) => tool.name === name);
  if (!definition) {
    throw new SubmittedToolError(`missing tool contract: ${name}`);
  }
  try {
    assertJsonSchema(
      definition.parameters,
      argumentsValue,
      `${name}.arguments`,
    );
  } catch (error) {
    if (error instanceof SchemaValidationError) {
      throw new SubmittedToolError(error.message);
    }
    throw error;
  }
  if (!isJsonObject(argumentsValue)) {
    throw new SubmittedToolError(`${name}.arguments must be an object`);
  }
  validateSemantics(name as ToolName, argumentsValue);

  switch (name as ToolName) {
    case "inspect_map_scope":
      return inspectMapScope(argumentsValue);
    case "compare_ala_and_flickr":
      return compareAlaAndFlickr(argumentsValue);
    case "inspect_species":
      return inspectSpecies(argumentsValue);
    case "inspect_flickr_candidate":
      return inspectFlickrCandidate(argumentsValue);
    case "trace_record_evidence":
      return traceRecordEvidence(argumentsValue);
    case "explain_classification":
      return explainClassification(argumentsValue);
    case "inspect_review_consensus":
      return inspectReviewConsensus(argumentsValue);
    case "inspect_reviewer_quality":
      return inspectReviewerQuality(argumentsValue);
    case "inspect_pipeline_status":
      return inspectPipelineStatus(argumentsValue);
    case "inspect_worker_status":
      return inspectWorkerStatus(argumentsValue);
    case "recommend_next_review_batch":
      return recommendNextReviewBatch(argumentsValue);
    case "recommend_next_species":
      return recommendNextSpecies(argumentsValue);
    case "explain_geographic_contribution":
      return explainGeographicContribution(argumentsValue);
    case "prepare_impact_report":
      return prepareImpactReport(argumentsValue);
  }
}

function validateSemantics(name: ToolName, args: JsonObject): void {
  if ("scope_type" in args) {
    const national = args.scope_type === "national";
    if (national && args.scope_id !== null) {
      throw new SubmittedToolError("national scope requires scope_id null");
    }
    if (!national && args.scope_id === null) {
      throw new SubmittedToolError("non-national scope requires a scope_id");
    }
  }
  if (name === "inspect_species") {
    const provided = Number(args.species_key !== null) +
      Number(args.scientific_name !== null);
    if (provided !== 1) {
      throw new SubmittedToolError(
        "inspect_species requires exactly one of species_key and scientific_name",
      );
    }
  }
}

function fact(
  name: string,
  value: JsonPrimitive,
  state: EvidenceState,
  interpretation: string,
  citationIds: readonly string[],
  unit: string | null = null,
): Fact {
  return {
    name,
    state,
    value,
    unit,
    interpretation,
    citation_ids: [...new Set(citationIds)],
  };
}

function evidenceRecord(
  recordId: string,
  recordType: string,
  facts: Fact[],
  citationIds: readonly string[],
): EvidenceRecord {
  return {
    record_id: recordId,
    record_type: recordType,
    facts,
    citation_ids: [...new Set(citationIds)],
  };
}

function citations(keys: readonly string[]): Citation[] {
  return [...new Set(keys)].map((key) => {
    const artifact = artifacts.get(key);
    if (!artifact) throw new SubmittedToolError(`unknown artifact key: ${key}`);
    return {
      artifact_id: artifact.artifact_id,
      repository: artifactRegistry.repository,
      commit: artifactRegistry.commit,
      path: artifact.path,
      fingerprint: `sha256:${artifact.sha256}`,
    };
  });
}

function citationIds(keys: readonly string[]): string[] {
  return citations(keys).map((citation) => citation.artifact_id);
}

async function finish(input: {
  tool_name: ToolName;
  status: ToolStatus;
  summary: string;
  query: Fact[];
  facts: Fact[];
  records?: EvidenceRecord[];
  artifact_keys: string[];
  limitations: string[];
}): Promise<ToolResult> {
  const withoutFingerprint = {
    schema_version: "butterflylens-openai-tool-result:v1.0.0",
    tool_name: input.tool_name,
    status: input.status,
    summary: input.summary,
    query: input.query,
    facts: input.facts,
    records: input.records ?? [],
    citations: citations(input.artifact_keys),
    limitations: input.limitations,
  };
  const result = {
    ...withoutFingerprint,
    result_fingerprint: await sha256Fingerprint(
      withoutFingerprint as JsonValue,
    ),
  } as ToolResult;
  assertJsonSchema(
    toolContracts.output_schema,
    result,
    `${input.tool_name}.result`,
  );
  validateCitationMembership(result);
  if (
    new TextEncoder().encode(canonicalJson(result as unknown as JsonValue))
      .length > 65_536
  ) {
    throw new SubmittedToolError(
      `${input.tool_name} result exceeds 65536 bytes`,
    );
  }
  return result;
}

function validateCitationMembership(result: ToolResult): void {
  const allowed = new Set(
    result.citations.map((citation) => citation.artifact_id),
  );
  const checkFacts = (facts: readonly Fact[]) => {
    for (const row of facts) {
      if (
        row.citation_ids.length === 0 ||
        row.citation_ids.some((id) => !allowed.has(id))
      ) {
        throw new SubmittedToolError(
          `${result.tool_name} returned an invalid fact citation`,
        );
      }
    }
  };
  checkFacts(result.query);
  checkFacts(result.facts);
  for (const row of result.records) {
    if (row.citation_ids.some((id) => !allowed.has(id))) {
      throw new SubmittedToolError(
        `${result.tool_name} returned an invalid record citation`,
      );
    }
    checkFacts(row.facts);
  }
}

function scopeQuery(args: JsonObject, ids: readonly string[]): Fact[] {
  return [
    fact(
      "scope_type",
      args.scope_type as JsonPrimitive,
      "observed",
      "Validated geographic scope type.",
      ids,
    ),
    fact(
      "scope_id",
      args.scope_id as JsonPrimitive,
      args.scope_id === null ? "not_applicable" : "observed",
      args.scope_id === null
        ? "National scope has no subordinate ID."
        : "Validated public scope ID.",
      ids,
    ),
  ];
}

function speciesRows(): JsonObject[] {
  const rows = speciesCatalogue.species;
  if (!Array.isArray(rows) || !rows.every(isJsonObject)) {
    throw new SubmittedToolError("submitted species catalogue is malformed");
  }
  return rows;
}

function findSpecies(key: JsonValue, name: JsonValue): JsonObject | null {
  return (
    speciesRows().find((row) =>
      key !== null ? row.key === key : typeof name === "string" &&
        typeof row.acceptedScientificName === "string" &&
        row.acceptedScientificName.toLocaleLowerCase("en-AU") ===
          name.toLocaleLowerCase("en-AU")
    ) ?? null
  );
}

function objectField(value: JsonValue | undefined): JsonObject {
  return isJsonObject(value) ? value : {};
}

function numberField(value: JsonValue | undefined): number {
  return typeof value === "number" && Number.isInteger(value) ? value : 0;
}

function stringField(value: JsonValue | undefined): string | null {
  return typeof value === "string" ? value : null;
}

function arrayField(value: JsonValue | undefined): JsonValue[] {
  return Array.isArray(value) ? value : [];
}

function requiredMapInteger(payload: JsonObject, field: string): number {
  const value = payload[field];
  if (!Number.isInteger(value) || (value as number) < 0) {
    throw new SubmittedToolError(`submitted map ${field} is not a count`);
  }
  return value as number;
}

function findMapScope(args: JsonObject): JsonObject | null {
  if (args.scope_type === "national") {
    return args.scope_id === null
      ? { scopeId: "AU", label: "Australia" }
      : null;
  }
  const scopes = objectField(submittedMapSnapshot.scopes);
  const rows = arrayField(scopes[args.scope_type as string]);
  return (rows.find((row) =>
    isJsonObject(row) && row.scopeId === args.scope_id
  ) as JsonObject | undefined) ?? null;
}

function mapScopeCount(
  scopeType: JsonValue,
  scope: JsonObject,
): number {
  return scopeType === "national"
    ? requiredMapInteger(
      objectField(submittedMapSnapshot.counts),
      "mapEligible",
    )
    : requiredMapInteger(scope, "count");
}

function mapScopeRecord(
  scope: JsonObject,
  ids: readonly string[],
): EvidenceRecord {
  const fingerprint = stringField(scope.summaryFingerprint);
  const evidenceFingerprint = stringField(scope.evidenceFingerprint);
  if (!fingerprint || fingerprint.length !== 64) {
    throw new SubmittedToolError(
      "submitted map scope has no summary fingerprint",
    );
  }
  if (!evidenceFingerprint || evidenceFingerprint.length !== 64) {
    throw new SubmittedToolError(
      "submitted map scope has no evidence fingerprint",
    );
  }
  const latestYear = scope.latestEventYear;
  if (latestYear !== null && !Number.isInteger(latestYear)) {
    throw new SubmittedToolError(
      "submitted map scope latest year is invalid",
    );
  }
  return evidenceRecord(
    `map-scope:${fingerprint}`,
    "submitted_ala_map_scope",
    [
      fact(
        "scope_id",
        scope.scopeId as JsonPrimitive,
        "observed",
        "Exact public aggregate scope identifier.",
        ids,
      ),
      fact(
        "scope_label",
        scope.label as JsonPrimitive,
        "observed",
        "Public aggregate scope label.",
        ids,
      ),
      fact(
        "ala_occurrence_count",
        requiredMapInteger(scope, "count"),
        "observed",
        "Rights-screened ALA baseline occurrence-evidence rows in this exact aggregate scope.",
        ids,
        "occurrences",
      ),
      fact(
        "unique_taxon_count",
        requiredMapInteger(scope, "uniqueTaxonCount"),
        "observed",
        "Distinct normalized taxon assertions represented in the aggregate; this is not a completeness claim.",
        ids,
        "taxa",
      ),
      fact(
        "latest_event_year",
        latestYear as JsonPrimitive,
        latestYear === null ? "unavailable" : "observed",
        latestYear === null
          ? "No retained provider event year is available for this aggregate."
          : "Latest retained provider event year in the aggregate.",
        ids,
        "year",
      ),
      fact(
        "publicly_generalised_count",
        requiredMapInteger(scope, "publiclyGeneralisedCount"),
        "observed",
        "Rows marked publicly generalized by the source projection.",
        ids,
        "occurrences",
      ),
      fact(
        "evidence_fingerprint",
        `sha256:${evidenceFingerprint}`,
        "observed",
        "Fingerprint of the aggregate's evidence membership.",
        ids,
      ),
      fact(
        "summary_fingerprint",
        `sha256:${fingerprint}`,
        "observed",
        "Fingerprint of the exact aggregate summary row.",
        ids,
      ),
    ],
    ids,
  );
}

async function inspectMapScope(args: JsonObject): Promise<ToolResult> {
  const keys = [
    "species_catalogue",
    "submitted_map",
    "flickr_global_status",
    "rights_manifest",
  ];
  const ids = citationIds(keys);
  const national = args.scope_type === "national";
  const scope = findMapScope(args);
  if (!scope) {
    return finish({
      tool_name: "inspect_map_scope",
      status: "not_found",
      summary:
        "The requested exact scope is not in the submitted public ALA map.",
      query: scopeQuery(args, ids),
      facts: [
        fact(
          "scope_found",
          false,
          "unavailable",
          "No exact scope identifier matched; the tool does not guess or broaden geography.",
          ids,
        ),
      ],
      artifact_keys: keys,
      limitations: ["No approximate geographic match was attempted."],
    });
  }
  const counts = objectField(submittedMapSnapshot.counts);
  const count = mapScopeCount(args.scope_type, scope);
  const mapCells = requiredMapInteger(counts, "mapCells");
  return finish({
    tool_name: "inspect_map_scope",
    status: "partial",
    summary:
      "Rights-screened ALA aggregate evidence is available for this submitted map scope; Flickr evidence remains unavailable.",
    query: scopeQuery(args, ids),
    facts: [
      fact(
        "accepted_species",
        national ? speciesCatalogue.speciesCount as JsonPrimitive : null,
        national ? "observed" : "unavailable",
        national
          ? "Accepted species in the authoritative national checklist."
          : "No committed lower-scope accepted-species aggregate exists in the submitted snapshot.",
        ids,
        "species",
      ),
      fact(
        "ala_occurrence_count",
        count,
        "observed",
        national
          ? "Rights-screened ALA baseline occurrence-evidence rows in the national public map projection."
          : "Rights-screened ALA baseline occurrence-evidence rows in the exact requested aggregate scope.",
        ids,
        "occurrences",
      ),
      fact(
        "flickr_candidate_count",
        null,
        "unavailable",
        "No completed immutable Flickr candidate snapshot is committed.",
        ids,
        "candidates",
      ),
      fact(
        "map_cell_count",
        national ? mapCells : args.scope_type === "h3" ? 1 : null,
        national || args.scope_type === "h3" ? "observed" : "unavailable",
        national
          ? "H3 resolution-3 aggregate cells in the submitted national heatmap."
          : args.scope_type === "h3"
          ? "The requested H3 aggregate is one map cell."
          : "A count of intersecting national heatmap cells is not materialized for this administrative scope.",
        ids,
        "cells",
      ),
      fact(
        "rights_excluded_selected",
        national ? requiredMapInteger(counts, "rightsExcludedSelected") : null,
        national ? "observed" : "unavailable",
        national
          ? "Selected rows conservatively excluded from the national public projection; exclusion is not a legal conclusion."
          : "The submitted map does not publish excluded-source counts by lower scope.",
        ids,
        "occurrences",
      ),
      fact(
        "absence_inference_permitted",
        false,
        "observed",
        "Withheld or unavailable evidence cannot establish biological absence.",
        ids,
      ),
    ],
    records: national ? [] : [mapScopeRecord(scope, ids)],
    artifact_keys: keys,
    limitations: [
      "The complete ALA baseline remains authoritative; this is a conservative public aggregate projection with three flagged datasets excluded.",
      "The active Flickr run is not a committed artifact and was not inspected.",
      "Provider labels are assertions, and missing evidence is not biological absence.",
    ],
  });
}

async function compareAlaAndFlickr(args: JsonObject): Promise<ToolResult> {
  const keys = [
    "species_catalogue",
    "submitted_map",
    "flickr_global_status",
    "rights_manifest",
  ];
  const ids = citationIds(keys);
  const query = scopeQuery(args, ids);
  const scope = findMapScope(args);
  if (!scope) {
    return finish({
      tool_name: "compare_ala_and_flickr",
      status: "not_found",
      summary:
        "The requested exact scope is not in the submitted public ALA map.",
      query,
      facts: [
        fact(
          "comparison_allowed",
          false,
          "unavailable",
          "No exact public scope matched; geography is not guessed or broadened.",
          ids,
        ),
      ],
      artifact_keys: keys,
      limitations: ["No approximate geographic match was attempted."],
    });
  }
  if (args.species_key !== null) {
    query.push(
      fact(
        "species_key",
        args.species_key as JsonPrimitive,
        "observed",
        "Requested accepted species key.",
        ids,
      ),
    );
    if (!findSpecies(args.species_key, null)) {
      return finish({
        tool_name: "compare_ala_and_flickr",
        status: "not_found",
        summary:
          "The requested species key is not in the authoritative catalogue.",
        query,
        facts: [
          fact(
            "comparison_allowed",
            false,
            "unavailable",
            "Unknown taxa are never guessed.",
            ids,
          ),
        ],
        artifact_keys: keys,
        limitations: ["No provider or model lookup was attempted."],
      });
    }
  }
  const speciesScoped = args.species_key !== null;
  const alaCount = speciesScoped ? null : mapScopeCount(args.scope_type, scope);
  return finish({
    tool_name: "compare_ala_and_flickr",
    status: speciesScoped ? "unavailable" : "partial",
    summary: speciesScoped
      ? "The submitted map has no species-granular ALA count and no immutable Flickr count for this selector."
      : "The rights-screened ALA aggregate count is available, but Flickr and the two-source difference remain unavailable.",
    query,
    facts: [
      fact(
        "ala_occurrence_count",
        alaCount,
        speciesScoped ? "unavailable" : "observed",
        speciesScoped
          ? "The submitted public map is not species-granular, so it cannot supply an ALA count for this species selector."
          : "Rights-screened ALA baseline occurrence-evidence rows in the exact requested aggregate scope.",
        ids,
        "occurrences",
      ),
      fact(
        "flickr_candidate_count",
        null,
        "unavailable",
        "No completed immutable Flickr snapshot exists.",
        ids,
        "candidates",
      ),
      fact(
        "count_difference",
        null,
        "unavailable",
        "No difference is calculated unless both comparable counts are admitted.",
        ids,
        "records",
      ),
      fact(
        "comparison_allowed",
        false,
        "observed",
        "The same-scope two-source comparison gate is not satisfied.",
        ids,
      ),
    ],
    artifact_keys: keys,
    limitations: [
      "Unavailable is not zero and does not imply absence.",
      "The complete ALA baseline remains authoritative; the displayed count is the conservative public projection.",
      "No active Flickr or BioMiner output was inspected.",
    ],
  });
}

async function inspectSpecies(args: JsonObject): Promise<ToolResult> {
  const keys = ["species_catalogue", "taxonomy_pack", "reference_quality"];
  const ids = citationIds(keys);
  const row = findSpecies(args.species_key, args.scientific_name);
  const query = [
    fact(
      "species_key",
      args.species_key as JsonPrimitive,
      args.species_key === null ? "not_applicable" : "observed",
      "Stable accepted-species selector.",
      ids,
    ),
    fact(
      "scientific_name",
      args.scientific_name as JsonPrimitive,
      args.scientific_name === null ? "not_applicable" : "observed",
      "Exact accepted-name selector.",
      ids,
    ),
  ];
  if (!row) {
    return finish({
      tool_name: "inspect_species",
      status: "not_found",
      summary:
        "No accepted species matches the exact submitted catalogue selector.",
      query,
      facts: [
        fact(
          "model_memory_lookup_permitted",
          false,
          "observed",
          "Taxa and provider IDs are never guessed from model memory.",
          ids,
        ),
      ],
      artifact_keys: keys,
      limitations: ["Only exact accepted keys or names are supported."],
    });
  }
  const hierarchy = objectField(row.hierarchy);
  const family = objectField(hierarchy.family);
  const genus = objectField(hierarchy.genus);
  const crosswalk = objectField(row.crosswalk);
  const reference = objectField(row.referenceCoverage);
  const conflicts = arrayField(crosswalk.openConflicts);
  return finish({
    tool_name: "inspect_species",
    status: "available",
    summary: `Accepted species evidence is available for ${
      String(row.acceptedScientificName)
    }.`,
    query,
    facts: [
      fact(
        "authoritative_baseline",
        speciesCatalogue.authoritativeBaseline as JsonPrimitive,
        "observed",
        "The rebuilt ButterflyLens baseline is authoritative for this goal.",
        ids,
      ),
      fact(
        "scientific_claim_allowed",
        false,
        "observed",
        "This view does not verify a photo identity or occurrence.",
        ids,
      ),
    ],
    records: [evidenceRecord(String(row.key), "species", [
      fact(
        "species_key",
        row.key as JsonPrimitive,
        "observed",
        "Stable ButterflyLens accepted-species key.",
        ids,
      ),
      fact(
        "accepted_scientific_name",
        row.acceptedScientificName as JsonPrimitive,
        "observed",
        "Accepted name in the frozen authority snapshot.",
        ids,
      ),
      fact(
        "family",
        stringField(family.acceptedScientificName),
        "observed",
        "Accepted family.",
        ids,
      ),
      fact(
        "genus",
        stringField(genus.acceptedScientificName),
        "observed",
        "Accepted genus.",
        ids,
      ),
      fact(
        "crosswalk_status",
        stringField(crosswalk.status),
        "observed",
        "Conservative provider crosswalk state.",
        ids,
      ),
      fact(
        "open_conflict_count",
        conflicts.length,
        conflicts.length ? "conflict" : "observed",
        "Unresolved provider concept conflicts.",
        ids,
        "conflicts",
      ),
      fact(
        "reference_status",
        stringField(reference.status),
        "unfinished",
        "Provider-asserted provisional workflow state.",
        ids,
      ),
      fact(
        "reference_selected_media",
        numberField(reference.selectedCount),
        "observed",
        "Selected decode workflow count, not verified identity.",
        ids,
        "media",
      ),
      fact(
        "reference_valid_decodes",
        numberField(reference.validDecodeCount),
        "observed",
        "Valid decode count, not a quality estimate.",
        ids,
        "media",
      ),
      fact(
        "human_verified_media",
        numberField(reference.humanVerifiedCount),
        "unfinished",
        "Human reference verification is absent.",
        ids,
        "media",
      ),
      fact(
        "release_status",
        stringField(reference.releaseStatus),
        "unfinished",
        "Reference evidence remains blocked from scientific release.",
        ids,
      ),
    ], ids)],
    artifact_keys: keys,
    limitations: [
      "Names and reference counts retain their source and maturity boundaries.",
      "YOLOE, BioCLIP, and human reference review are unfinished or absent.",
    ],
  });
}

async function inspectFlickrCandidate(args: JsonObject): Promise<ToolResult> {
  const keys = ["flickr_global_status", "rights_manifest", "species_catalogue"];
  const ids = citationIds(keys);
  return finish({
    tool_name: "inspect_flickr_candidate",
    status: "unavailable",
    summary:
      "No completed immutable Flickr candidate snapshot is available to inspect.",
    query: [
      fact(
        "candidate_id",
        args.candidate_id as JsonPrimitive,
        "observed",
        "Requested immutable candidate identifier.",
        ids,
      ),
    ],
    facts: [
      fact(
        "candidate_state",
        null,
        "unavailable",
        "No admitted Flickr candidate record exists in the submitted snapshot.",
        ids,
      ),
      fact(
        "flickr_api_call_made",
        false,
        "observed",
        "This local tool did not call Flickr.",
        ids,
      ),
      fact(
        "species_identity_inferred",
        false,
        "observed",
        "No identity is inferred from metadata or memory.",
        ids,
      ),
    ],
    artifact_keys: keys,
    limitations: [
      "The active Flickr run was not inspected.",
      "Unavailable does not mean absent upstream.",
    ],
  });
}

async function traceRecordEvidence(args: JsonObject): Promise<ToolResult> {
  const recordType = String(args.record_type);
  const keyMap: Record<string, string[]> = {
    species: ["species_catalogue", "taxonomy_pack", "reference_quality"],
    ala_occurrence: ["ala_snapshot", "rights_manifest"],
    flickr_candidate: ["flickr_global_status", "rights_manifest"],
    classification: ["classification_contract", "reference_quality"],
    review_consensus: ["consensus_contract", "quality_projection"],
    worker: ["worker_contract", "worker_policy"],
    contribution: [
      "contributor_projection",
      "geographic_impact_contract",
      "geographic_impact_policy",
    ],
  };
  const keys = keyMap[recordType];
  const ids = citationIds(keys);
  const query = [
    fact(
      "record_type",
      args.record_type as JsonPrimitive,
      "observed",
      "Requested governed record type.",
      ids,
    ),
    fact(
      "record_id",
      args.record_id as JsonPrimitive,
      "observed",
      "Requested immutable record identifier.",
      ids,
    ),
  ];
  const row = recordType === "species"
    ? findSpecies(args.record_id, null)
    : null;
  if (row) {
    return finish({
      tool_name: "trace_record_evidence",
      status: "available",
      summary: `Stored evidence lineage is available for ${
        String(row.acceptedScientificName)
      }.`,
      query,
      facts: [
        fact(
          "lineage_complete_for_claim",
          true,
          "derived",
          "Citations support catalogue facts, not photo identity or occurrence.",
          ids,
        ),
      ],
      records: [
        evidenceRecord(`${String(args.record_id)}:authority`, "lineage_step", [
          fact(
            "step_order",
            1,
            "observed",
            "Authority taxonomy is the identity root.",
            ids,
          ),
          fact(
            "relationship",
            "accepted_taxon_source",
            "observed",
            "The accepted key derives from the frozen authority snapshot.",
            ids,
          ),
        ], ids),
        evidenceRecord(`${String(args.record_id)}:catalogue`, "lineage_step", [
          fact(
            "step_order",
            2,
            "derived",
            "Deterministic public catalogue projection.",
            ids,
          ),
          fact(
            "relationship",
            "checksum_verified_projection",
            "derived",
            "Conflicts and evidence maturity are retained.",
            ids,
          ),
        ], ids),
      ],
      artifact_keys: keys,
      limitations: [
        "This lineage does not create human verification or occurrence evidence.",
      ],
    });
  }
  return finish({
    tool_name: "trace_record_evidence",
    status: "unavailable",
    summary:
      "No governed submitted record lineage is available for that selector.",
    query,
    facts: [
      fact(
        "lineage_state",
        null,
        recordType === "ala_occurrence" ? "withheld" : "unavailable",
        "The exact record is absent from the readable snapshot or behind a governed boundary.",
        ids,
      ),
    ],
    artifact_keys: keys,
    limitations: [
      "No provider, active workstore, private table, or model-memory search occurred.",
    ],
  });
}

async function explainClassification(args: JsonObject): Promise<ToolResult> {
  const keys = [
    "classification_contract",
    "reference_quality",
    "species_catalogue",
  ];
  const ids = citationIds(keys);
  return finish({
    tool_name: "explain_classification",
    status: "unavailable",
    summary:
      "No stored classification exists; YOLOE and BioCLIP are unfinished.",
    query: [
      fact(
        "classification_id",
        args.classification_id as JsonPrimitive,
        "observed",
        "Requested stored classification identifier.",
        ids,
      ),
    ],
    facts: [
      fact(
        "classification_state",
        null,
        "unavailable",
        "No governed classification record is committed.",
        ids,
      ),
      fact(
        "yoloe_state",
        "unfinished",
        "unfinished",
        "YOLOE supplied no route evidence.",
        ids,
      ),
      fact(
        "bioclip_state",
        "unfinished",
        "unfinished",
        "BioCLIP supplied no embedding or score evidence.",
        ids,
      ),
      fact(
        "probability_available",
        false,
        "observed",
        "No raw score is converted into a probability.",
        ids,
      ),
    ],
    artifact_keys: keys,
    limitations: ["The tool never identifies a species from model memory."],
  });
}

async function inspectReviewConsensus(args: JsonObject): Promise<ToolResult> {
  const keys = ["consensus_contract", "quality_projection"];
  const ids = citationIds(keys);
  return finish({
    tool_name: "inspect_review_consensus",
    status: "unavailable",
    summary:
      "No completed fingerprinted review consensus is stored in the submitted replay.",
    query: [
      fact(
        "item_id",
        args.item_id as JsonPrimitive,
        "observed",
        "Requested review item identifier.",
        ids,
      ),
    ],
    facts: [
      fact(
        "consensus_status",
        null,
        "unavailable",
        "No governed consensus record is available.",
        ids,
      ),
      fact(
        "review_count",
        null,
        "unavailable",
        "Missing replay evidence is not a zero-review live claim.",
        ids,
        "reviews",
      ),
      fact(
        "majority_is_accuracy",
        false,
        "observed",
        "Vote count alone cannot establish accuracy.",
        ids,
      ),
    ],
    artifact_keys: keys,
    limitations: ["Reviewer identities and private controls are not returned."],
  });
}

async function inspectReviewerQuality(args: JsonObject): Promise<ToolResult> {
  const keys = ["reviewer_quality_contract", "quality_projection"];
  const ids = citationIds(keys);
  return finish({
    tool_name: "inspect_reviewer_quality",
    status: "unavailable",
    summary:
      "No authenticated fingerprinted self-quality snapshot is present in the submitted replay.",
    query: [
      fact(
        "subject",
        args.subject as JsonPrimitive,
        "observed",
        "The model-facing contract is self-only.",
        ids,
      ),
      fact(
        "domain_key",
        args.domain_key as JsonPrimitive,
        args.domain_key === null ? "not_applicable" : "observed",
        "Optional governed quality domain.",
        ids,
      ),
    ],
    facts: [
      fact(
        "quality_estimate",
        null,
        "unavailable",
        "Minimum independent evidence is unavailable.",
        ids,
      ),
      fact(
        "applied_weight",
        null,
        "unavailable",
        "No reliability weight is exposed.",
        ids,
      ),
      fact(
        "visibility",
        "self_only",
        "observed",
        "Reviewer quality is private and unranked.",
        ids,
      ),
      fact(
        "public_ranking_allowed",
        false,
        "observed",
        "Person-to-person ranking is prohibited.",
        ids,
      ),
    ],
    artifact_keys: keys,
    limitations: [
      "Model arguments cannot grant access to another reviewer.",
      "Control identities and expected answers remain private.",
    ],
  });
}

async function inspectPipelineStatus(args: JsonObject): Promise<ToolResult> {
  const keys = [
    "taxonomy_pack",
    "ala_snapshot",
    "reference_bank",
    "reference_quality",
    "quality_projection",
    "flickr_global_status",
  ];
  const ids = citationIds(keys);
  const query = [
    fact(
      "pipeline_id",
      args.pipeline_id as JsonPrimitive,
      args.pipeline_id === null ? "not_applicable" : "observed",
      "Null selects the committed submitted pipeline.",
      ids,
    ),
  ];
  if (args.pipeline_id !== null && args.pipeline_id !== "submitted") {
    return finish({
      tool_name: "inspect_pipeline_status",
      status: "not_found",
      summary: "Only the committed submitted pipeline is available.",
      query,
      facts: [
        fact(
          "pipeline_state",
          null,
          "unavailable",
          "The requested pipeline ID is not committed.",
          ids,
        ),
      ],
      artifact_keys: keys,
      limitations: ["Active workstores were not inspected."],
    });
  }
  const stages: Array<[string, string, EvidenceState, string]> = [
    [
      "taxonomy",
      "complete",
      "observed",
      "The rebuilt taxonomy pack is committed.",
    ],
    [
      "ala_baseline",
      "rights_review_required",
      "withheld",
      "Occurrence publication remains rights-blocked.",
    ],
    [
      "reference_metadata",
      "provisional",
      "observed",
      "Automated gates retain provider-asserted provisional support.",
    ],
    ["yoloe", "unfinished", "unfinished", "YOLOE is unfinished."],
    ["bioclip", "unfinished", "unfinished", "BioCLIP is unfinished."],
    [
      "human_reference_review",
      "absent",
      "unfinished",
      "No human-verified reference media is stored.",
    ],
    [
      "scientific_release",
      "blocked",
      "unfinished",
      "Release gates are not satisfied.",
    ],
    [
      "flickr_live_fetch",
      "unavailable",
      "unavailable",
      "The active fetch is not a committed artifact.",
    ],
  ];
  return finish({
    tool_name: "inspect_pipeline_status",
    status: "partial",
    summary:
      "Submitted taxonomy and provisional reference stages are committed; live, model, review, and release lanes remain unavailable or unfinished.",
    query,
    facts: [
      fact(
        "snapshot_mode",
        "submitted",
        "observed",
        "This is not live operations.",
        ids,
      ),
      fact(
        "release_ready",
        false,
        "observed",
        "Scientific release gates are not satisfied.",
        ids,
      ),
      fact(
        "live_state_claimed",
        false,
        "observed",
        "No active process state is claimed.",
        ids,
      ),
    ],
    records: stages.map(([stage, state, evidenceState, meaning]) =>
      evidenceRecord(`pipeline:${stage}`, "pipeline_stage", [
        fact(
          "stage",
          stage,
          "observed",
          "Deterministic stage identifier.",
          ids,
        ),
        fact("stage_state", state, evidenceState, meaning, ids),
      ], ids)
    ),
    artifact_keys: keys,
    limitations: [
      "Active BioMiner and Flickr work remain outside this snapshot.",
      "YOLOE and BioCLIP were not run.",
    ],
  });
}

async function inspectWorkerStatus(args: JsonObject): Promise<ToolResult> {
  const keys = ["worker_contract", "worker_policy", "quality_projection"];
  const ids = citationIds(keys);
  return finish({
    tool_name: "inspect_worker_status",
    status: "unavailable",
    summary:
      "No committed governed worker heartbeat is present in the submitted snapshot.",
    query: [
      fact(
        "worker_id",
        args.worker_id as JsonPrimitive,
        args.worker_id === null ? "not_applicable" : "observed",
        "Optional immutable worker selector.",
        ids,
      ),
    ],
    facts: [
      fact(
        "worker_state",
        null,
        "unavailable",
        "Without a committed heartbeat, online/offline state is not guessed.",
        ids,
      ),
      fact(
        "last_heartbeat",
        null,
        "unavailable",
        "No governed heartbeat timestamp is available.",
        ids,
      ),
      fact(
        "submitted_snapshot_requires_live_worker",
        false,
        "observed",
        "The website and submitted snapshot remain available when the M5 is offline.",
        ids,
      ),
    ],
    artifact_keys: keys,
    limitations: [
      "No process table, PID, workstore, or active log was inspected.",
    ],
  });
}

function selectedCount(row: JsonObject): number {
  return numberField(objectField(row.referenceCoverage).selectedCount);
}

function conflictCount(row: JsonObject): number {
  return arrayField(objectField(row.crosswalk).openConflicts).length;
}

function reviewSort(left: JsonObject, right: JsonObject): number {
  return (
    conflictCount(right) - conflictCount(left) ||
    selectedCount(left) - selectedCount(right) ||
    String(left.acceptedScientificName).localeCompare(
      String(right.acceptedScientificName),
      "en-AU",
    ) ||
    String(left.key).localeCompare(String(right.key), "en-AU")
  );
}

function priorityRecord(
  row: JsonObject,
  order: number,
  reason: string,
  ids: readonly string[],
): EvidenceRecord {
  const reference = objectField(row.referenceCoverage);
  const selected = selectedCount(row);
  const conflicts = conflictCount(row);
  return evidenceRecord(String(row.key), "species_workflow_priority", [
    fact(
      "priority_order",
      order,
      "derived",
      "Order within this bounded workflow result only.",
      ids,
    ),
    fact(
      "species_key",
      row.key as JsonPrimitive,
      "observed",
      "Stable accepted-species key.",
      ids,
    ),
    fact(
      "accepted_scientific_name",
      row.acceptedScientificName as JsonPrimitive,
      "observed",
      "Accepted name in the authoritative baseline.",
      ids,
    ),
    fact(
      "workflow_reason",
      reason,
      "derived",
      "Explicit non-scientific workflow reason.",
      ids,
    ),
    fact(
      "selected_reference_media",
      selected,
      "observed",
      "Provisional selected decode count.",
      ids,
      "media",
    ),
    fact(
      "target_support_gap",
      Math.max(0, 20 - selected),
      "derived",
      "Arithmetic workflow gap to 20, not biological absence.",
      ids,
      "media",
    ),
    fact(
      "open_conflict_count",
      conflicts,
      conflicts ? "conflict" : "observed",
      "Retained provider-concept conflicts.",
      ids,
      "conflicts",
    ),
    fact(
      "human_verified_media",
      numberField(reference.humanVerifiedCount),
      "unfinished",
      "No submitted reference media has human verification.",
      ids,
      "media",
    ),
  ], ids);
}

async function recommendNextReviewBatch(args: JsonObject): Promise<ToolResult> {
  const keys = ["species_catalogue", "reference_quality", "taxonomy_pack"];
  const ids = citationIds(keys);
  const query = [
    ...scopeQuery(args, ids),
    fact(
      "species_key",
      args.species_key as JsonPrimitive,
      args.species_key === null ? "not_applicable" : "observed",
      "Optional accepted-species constraint.",
      ids,
    ),
    fact(
      "limit",
      args.limit as JsonPrimitive,
      "observed",
      "Maximum bounded recommendation count.",
      ids,
      "species",
    ),
  ];
  if (args.scope_type !== "national") {
    return finish({
      tool_name: "recommend_next_review_batch",
      status: "unavailable",
      summary:
        "Lower-scope review recommendations require a committed map snapshot.",
      query,
      facts: [
        fact(
          "batch_state",
          null,
          "unavailable",
          "No lower-scope candidate frame is committed.",
          ids,
        ),
      ],
      artifact_keys: keys,
      limitations: ["Geographic missingness is not biological absence."],
    });
  }
  let rows = speciesRows();
  if (args.species_key !== null) {
    const row = findSpecies(args.species_key, null);
    if (!row) {
      return recommendationNotFound(
        "recommend_next_review_batch",
        query,
        keys,
        ids,
      );
    }
    rows = [row];
  }
  const selected = rows.filter((row) => selectedCount(row) > 0).sort(reviewSort)
    .slice(0, Number(args.limit));
  const records = selected.map((row, index) =>
    priorityRecord(row, index + 1, "targeted_reference_review", ids)
  );
  return finish({
    tool_name: "recommend_next_review_batch",
    status: records.length ? "available" : "unavailable",
    summary: records.length
      ? `Prepared ${records.length} deterministic species-level targeted review priorities.`
      : "No committed selected reference media exists for this constraint.",
    query,
    facts: [
      fact(
        "batch_kind",
        "targeted_failure_discovery",
        "derived",
        "This is not representative sampling.",
        ids,
      ),
      fact(
        "representative",
        false,
        "derived",
        "The queue cannot estimate population quality.",
        ids,
      ),
      fact(
        "ranking_of_people_or_species",
        false,
        "observed",
        "Workflow order is not scientific or personal rank.",
        ids,
      ),
      fact(
        "recommended_species",
        records.length,
        "derived",
        "Bounded returned count.",
        ids,
        "species",
      ),
    ],
    records,
    artifact_keys: keys,
    limitations: [
      "Priorities are not verified identities or occurrences.",
      "No Flickr candidate IDs are available.",
    ],
  });
}

async function recommendationNotFound(
  toolName: "recommend_next_review_batch",
  query: Fact[],
  keys: string[],
  ids: string[],
): Promise<ToolResult> {
  return finish({
    tool_name: toolName,
    status: "not_found",
    summary: "The requested species key is not in the authoritative catalogue.",
    query,
    facts: [
      fact(
        "recommendation_available",
        false,
        "unavailable",
        "Unknown taxa are never guessed.",
        ids,
      ),
    ],
    artifact_keys: keys,
    limitations: ["Only accepted ButterflyLens species keys are eligible."],
  });
}

async function recommendNextSpecies(args: JsonObject): Promise<ToolResult> {
  const keys = ["species_catalogue", "reference_quality", "taxonomy_pack"];
  const ids = citationIds(keys);
  const criterion = String(args.criterion);
  let rows = [...speciesRows()];
  let reason: string;
  if (criterion === "open_conflicts") {
    rows = rows.filter((row) => conflictCount(row) > 0).sort((left, right) =>
      conflictCount(right) - conflictCount(left) ||
      String(left.acceptedScientificName).localeCompare(
        String(right.acceptedScientificName),
        "en-AU",
      )
    );
    reason = "open_provider_conflicts";
  } else if (criterion === "reviewable_reference") {
    rows = rows.filter((row) => selectedCount(row) > 0).sort(reviewSort);
    reason = "selected_provisional_reference_media";
  } else {
    rows.sort((left, right) =>
      selectedCount(left) - selectedCount(right) ||
      numberField(objectField(left.referenceCoverage).candidateMediaCount) -
        numberField(objectField(right.referenceCoverage).candidateMediaCount) ||
      conflictCount(right) - conflictCount(left) ||
      String(left.acceptedScientificName).localeCompare(
        String(right.acceptedScientificName),
        "en-AU",
      )
    );
    reason = "reference_support_gap";
  }
  const selected = rows.slice(0, Number(args.limit));
  const records = selected.map((row, index) =>
    priorityRecord(row, index + 1, reason, ids)
  );
  return finish({
    tool_name: "recommend_next_species",
    status: records.length ? "available" : "unavailable",
    summary:
      `Prepared ${records.length} deterministic workflow priorities using criterion ${criterion}.`,
    query: [
      fact(
        "criterion",
        criterion,
        "observed",
        "Explicit workflow criterion.",
        ids,
      ),
      fact(
        "limit",
        args.limit as JsonPrimitive,
        "observed",
        "Maximum bounded recommendation count.",
        ids,
        "species",
      ),
    ],
    facts: [
      fact(
        "priority_basis",
        criterion,
        "derived",
        "Priority uses committed diagnostics only.",
        ids,
      ),
      fact(
        "scientific_importance_rank",
        false,
        "observed",
        "Workflow order is not rarity, conservation, presence, or importance.",
        ids,
      ),
      fact(
        "recommended_species",
        records.length,
        "derived",
        "Bounded accepted-species count.",
        ids,
        "species",
      ),
    ],
    records,
    artifact_keys: keys,
    limitations: [
      "Reference counts are provisional workflow diagnostics.",
      "No occurrence, probability, or model score is inferred.",
    ],
  });
}

async function explainGeographicContribution(
  args: JsonObject,
): Promise<ToolResult> {
  const keys = [
    "contributor_projection",
    "geographic_impact_contract",
    "geographic_impact_policy",
    "species_catalogue",
  ];
  const ids = citationIds(keys);
  return finish({
    tool_name: "explain_geographic_contribution",
    status: "unavailable",
    summary:
      "No authenticated fingerprinted geographic contribution snapshot is included in the submitted replay.",
    query: scopeQuery(args, ids),
    facts: [
      fact(
        "visibility",
        contributorProjection.visibility as JsonPrimitive,
        "observed",
        "Contributor impact is self-only.",
        ids,
      ),
      fact(
        "regions_helped",
        null,
        "unavailable",
        "Generalised region lineage is unavailable, not zero.",
        ids,
        "regions",
      ),
      fact(
        "potential_contribution_is_occurrence",
        false,
        "observed",
        "Potential contribution is never called a new occurrence.",
        ids,
      ),
      fact(
        "exact_sensitive_region_returned",
        false,
        "observed",
        "Exact sensitive locations are not exposed.",
        ids,
      ),
    ],
    artifact_keys: keys,
    limitations: [
      "Model arguments cannot select another contributor.",
      "Unavailable evidence is not zero contribution.",
    ],
  });
}

async function prepareImpactReport(args: JsonObject): Promise<ToolResult> {
  const keys = [
    "contributor_projection",
    "geographic_impact_contract",
    "geographic_impact_policy",
    "quality_projection",
  ];
  const ids = citationIds(keys);
  const metrics = objectField(contributorProjection.metrics);
  const mapping: Array<[string, string]> = [
    ["reviewed_images", "reviewedImages"],
    ["resolved_conflicts", "resolvedConflicts"],
    ["species_helped", "speciesHelped"],
    ["regions_helped", "regionsHelped"],
    ["control_coverage", "controlCoverage"],
    ["expert_contribution", "expertContribution"],
  ];
  const facts = mapping.map(([outputName, sourceName]) => {
    const metric = objectField(metrics[sourceName]);
    return fact(
      outputName,
      (metric.value ?? null) as JsonPrimitive,
      "unavailable",
      stringField(metric.reason) ??
        "Governed contribution evidence is unavailable.",
      ids,
    );
  });
  facts.push(
    fact(
      "visibility",
      contributorProjection.visibility as JsonPrimitive,
      "observed",
      "The report is private to the authenticated contributor.",
      ids,
    ),
    fact(
      "ranking_permitted",
      contributorProjection.rankingPermitted as JsonPrimitive,
      "observed",
      "Contributor rankings are prohibited.",
      ids,
    ),
    fact(
      "speed_metric_permitted",
      contributorProjection.speedMetricPermitted as JsonPrimitive,
      "observed",
      "Speed is not contribution quality.",
      ids,
    ),
    fact(
      "scientific_claim_allowed",
      contributorProjection.scientificClaimAllowed as JsonPrimitive,
      "observed",
      "Recognition does not create scientific authority.",
      ids,
    ),
  );
  return finish({
    tool_name: "prepare_impact_report",
    status: "unavailable",
    summary:
      "The self-impact report structure is available, but every submitted metric is unavailable.",
    query: [
      fact(
        "report_scope",
        args.report_scope as JsonPrimitive,
        "observed",
        "The model-facing report is self-only.",
        ids,
      ),
    ],
    facts,
    artifact_keys: keys,
    limitations: [
      "Unavailable metrics remain null, not zero.",
      "No speed, rank, private control, sensitive region, or reviewer weight is returned.",
    ],
  });
}
