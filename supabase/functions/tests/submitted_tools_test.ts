import {
  executeSubmittedTool,
  OPENAI_TOOL_DEFINITIONS,
  SubmittedToolError,
  TOOL_NAMES,
  type ToolResult,
} from "../_shared/submittedTools.ts";

const SPECIES_KEY = "bltx:v1:997e8426f871a0602527d4ce";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

function fact(result: ToolResult, name: string) {
  const row = result.facts.find((candidate) => candidate.name === name);
  if (!row) throw new Error(`missing fact ${name}`);
  return row;
}

Deno.test("exports the exact fourteen strict read-only tool definitions", () => {
  assert(TOOL_NAMES.length === 14, "tool count changed");
  assert(OPENAI_TOOL_DEFINITIONS.length === 14, "definition count changed");
  assert(
    JSON.stringify(
      OPENAI_TOOL_DEFINITIONS.map((definition) => definition.name),
    ) ===
      JSON.stringify(TOOL_NAMES),
    "tool order changed",
  );
  for (const definition of OPENAI_TOOL_DEFINITIONS) {
    assert(
      definition.type === "function",
      `${definition.name} is not a function`,
    );
    assert(definition.strict === true, `${definition.name} is not strict`);
  }
});

Deno.test("executes all fourteen tools with bounded cited results", async () => {
  const cases: Record<string, unknown> = {
    inspect_map_scope: { scope_type: "national", scope_id: null },
    compare_ala_and_flickr: {
      scope_type: "national",
      scope_id: null,
      species_key: null,
    },
    inspect_species: { species_key: SPECIES_KEY, scientific_name: null },
    inspect_flickr_candidate: { candidate_id: "candidate:123" },
    trace_record_evidence: { record_type: "species", record_id: SPECIES_KEY },
    explain_classification: { classification_id: "classification:123" },
    inspect_review_consensus: { item_id: "item:123" },
    inspect_reviewer_quality: { subject: "self", domain_key: null },
    inspect_pipeline_status: { pipeline_id: null },
    inspect_worker_status: { worker_id: null },
    recommend_next_review_batch: {
      scope_type: "national",
      scope_id: null,
      species_key: null,
      limit: 3,
    },
    recommend_next_species: { criterion: "reference_gap", limit: 3 },
    explain_geographic_contribution: { scope_type: "national", scope_id: null },
    prepare_impact_report: { report_scope: "self" },
  };
  assert(
    JSON.stringify(Object.keys(cases)) === JSON.stringify(TOOL_NAMES),
    "case order changed",
  );
  for (const [name, args] of Object.entries(cases)) {
    const result = await executeSubmittedTool(name, args);
    assert(result.tool_name === name, `${name} result mismatch`);
    assert(
      /^sha256:[0-9a-f]{64}$/u.test(result.result_fingerprint),
      `${name} has no fingerprint`,
    );
    assert(result.records.length <= 20, `${name} returned too many records`);
    assert(
      result.citations.length > 0 && result.citations.length <= 12,
      `${name} citation bounds failed`,
    );
    assert(
      new TextEncoder().encode(JSON.stringify(result)).length <= 65_536,
      `${name} is too large`,
    );
  }
});

Deno.test("species evidence is accepted but not scientific authority", async () => {
  const result = await executeSubmittedTool("inspect_species", {
    species_key: SPECIES_KEY,
    scientific_name: null,
  });
  assert(result.status === "available", "species should be available");
  assert(result.records[0].record_id === SPECIES_KEY, "wrong species record");
  assert(
    fact(result, "scientific_claim_allowed").value === false,
    "scientific claim leaked",
  );
});

Deno.test("map and comparison preserve withheld and unavailable values", async () => {
  const map = await executeSubmittedTool("inspect_map_scope", {
    scope_type: "national",
    scope_id: null,
  });
  assert(
    fact(map, "ala_occurrence_count").value === null,
    "ALA count must be null",
  );
  assert(
    fact(map, "ala_occurrence_count").state === "withheld",
    "ALA state must be withheld",
  );
  assert(
    fact(map, "flickr_candidate_count").value === null,
    "Flickr count must be null",
  );
  assert(
    fact(map, "absence_inference_permitted").value === false,
    "absence was inferred",
  );
  const comparison = await executeSubmittedTool("compare_ala_and_flickr", {
    scope_type: "national",
    scope_id: null,
    species_key: null,
  });
  assert(
    fact(comparison, "count_difference").value === null,
    "difference was fabricated",
  );
});

Deno.test("private and live tools fail closed without governed snapshots", async () => {
  const reviewer = await executeSubmittedTool("inspect_reviewer_quality", {
    subject: "self",
    domain_key: null,
  });
  assert(
    reviewer.status === "unavailable",
    "reviewer state should be unavailable",
  );
  assert(
    fact(reviewer, "visibility").value === "self_only",
    "reviewer visibility leaked",
  );
  assert(
    fact(reviewer, "public_ranking_allowed").value === false,
    "ranking was allowed",
  );
  const worker = await executeSubmittedTool("inspect_worker_status", {
    worker_id: null,
  });
  assert(worker.status === "unavailable", "worker should be unavailable");
  assert(
    fact(worker, "worker_state").value === null,
    "worker state was guessed",
  );
  const impact = await executeSubmittedTool("prepare_impact_report", {
    report_scope: "self",
  });
  assert(
    fact(impact, "reviewed_images").value === null,
    "impact null became zero",
  );
  assert(
    fact(impact, "speed_metric_permitted").value === false,
    "speed metric was allowed",
  );
});

Deno.test("recommendations are deterministic bounded workflow priorities", async () => {
  const args = { criterion: "open_conflicts", limit: 5 };
  const first = await executeSubmittedTool("recommend_next_species", args);
  const second = await executeSubmittedTool("recommend_next_species", args);
  assert(
    JSON.stringify(first) === JSON.stringify(second),
    "result was not deterministic",
  );
  assert(first.records.length === 5, "wrong recommendation count");
  assert(
    fact(first, "scientific_importance_rank").value === false,
    "scientific rank leaked",
  );
});

Deno.test("strict argument and semantic validation reject model inventions", async () => {
  await assertRejects(
    () =>
      executeSubmittedTool("inspect_worker_status", {
        worker_id: null,
        live: true,
      }),
    "not allowed",
  );
  await assertRejects(
    () =>
      executeSubmittedTool("inspect_map_scope", {
        scope_type: "national",
        scope_id: "AU",
      }),
    "national scope",
  );
  await assertRejects(
    () =>
      executeSubmittedTool("inspect_species", {
        species_key: null,
        scientific_name: null,
      }),
    "exactly one",
  );
  await assertRejects(
    () => executeSubmittedTool("invent_species", {}),
    "unknown butterflylens",
  );
});

async function assertRejects(
  operation: () => Promise<unknown>,
  message: string,
): Promise<void> {
  try {
    await operation();
  } catch (error) {
    assert(error instanceof SubmittedToolError, "wrong error type");
    assert(
      error.message.toLocaleLowerCase("en-AU").includes(message),
      `missing error text: ${message}`,
    );
    return;
  }
  throw new Error("expected operation to reject");
}
