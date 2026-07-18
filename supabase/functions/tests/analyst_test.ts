import {
  ANALYST_INSTRUCTIONS,
  AnalystInputError,
  FINAL_MODEL_SCHEMA,
  hashSafetyIdentifier,
  MAX_OUTPUT_TOKENS,
  MAX_RESPONSE_CALLS,
  MAX_TOOL_CALLS,
  MODEL_ID,
  parseAnalystRequest,
  REASONING_EFFORT,
  type ResponseLike,
  type ResponseRequest,
  runAnalyst,
  TransientToolError,
} from "../_shared/analyst.ts";
import {
  executeSubmittedTool,
  type ToolResult,
} from "../_shared/submittedTools.ts";

const SPECIES_KEY = "bltx:v1:997e8426f871a0602527d4ce";
const SAFETY_IDENTIFIER = "a".repeat(64);

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

function functionCall(
  callId = "call_1",
  name = "inspect_species",
  args: unknown = { species_key: SPECIES_KEY, scientific_name: null },
): ResponseLike {
  return {
    status: "completed",
    output: [
      {
        type: "function_call",
        call_id: callId,
        name,
        arguments: JSON.stringify(args),
      },
    ],
  };
}

function finalOutput(
  result: ToolResult,
  overrides: Record<string, unknown> = {},
): ResponseLike {
  const citation = result.citations[0];
  return {
    status: "completed",
    output_text: JSON.stringify({
      response_state: "completed",
      summary:
        "The accepted species is present in the submitted authoritative catalogue.",
      claims: [
        {
          claim_id: "claim_1",
          statement:
            "The accepted species is present in the submitted authoritative catalogue.",
          evidence_state: "direct",
          citation_ids: [citation.artifact_id],
        },
      ],
      citations: [citation],
      limitations: ["This does not verify a photo identity or occurrence."],
      tools_used: ["inspect_species"],
      ...overrides,
    }),
    output: [],
  };
}

Deno.test("request parser is exact bounded and trims content", () => {
  const parsed = parseAnalystRequest({
    question: "  What evidence exists?  ",
    history: [{ role: "user", content: " Earlier question " }],
  });
  assert(
    parsed.question === "What evidence exists?",
    "question was not trimmed",
  );
  assert(
    parsed.history[0].content === "Earlier question",
    "history was not trimmed",
  );
  assertThrows(
    () => parseAnalystRequest({ question: "", history: [] }),
    "question",
  );
  assertThrows(
    () => parseAnalystRequest({ question: "x", history: [], extra: true }),
    "only question",
  );
  assertThrows(
    () =>
      parseAnalystRequest({
        question: "x",
        history: Array(9).fill({ role: "user", content: "x" }),
      }),
    "at most 8",
  );
});

Deno.test("safety identifier is stable private and does not contain the auth subject", async () => {
  const first = await hashSafetyIdentifier("auth-user-123");
  const second = await hashSafetyIdentifier("auth-user-123");
  const other = await hashSafetyIdentifier("auth-user-456");
  assert(first === second, "safety identifier changed");
  assert(first !== other, "different users received one identifier");
  assert(/^[0-9a-f]{64}$/u.test(first), "identifier is not a SHA-256 digest");
  assert(!first.includes("auth-user"), "raw subject leaked");
});

Deno.test("Responses loop sends the frozen supported request and preserves call IDs", async () => {
  const requests: ResponseRequest[] = [];
  let toolResult: ToolResult | null = null;
  const response = await runAnalyst({
    request: { question: "Inspect Acraea andromacha.", history: [] },
    safetyIdentifier: SAFETY_IDENTIFIER,
    executeTool: async (name, args) => {
      toolResult = await executeSubmittedTool(name, args);
      return toolResult;
    },
    createResponse: async (request) => {
      requests.push(request);
      return requests.length === 1 ? functionCall() : finalOutput(toolResult!);
    },
  });
  assert(response.response_state === "completed", "response did not complete");
  assert(response.mode === "live", "response was not labelled live");
  assert(response.model.id === MODEL_ID, "model metadata changed");
  assert(
    response.model.reasoning_effort === REASONING_EFFORT,
    "effort changed",
  );
  assert(response.usage.response_calls === 2, "wrong response-call count");
  assert(response.usage.tool_calls === 1, "wrong tool-call count");
  assert(requests.length === 2, "wrong API request count");
  for (const request of requests) {
    assert(request.model === MODEL_ID, "wrong request model");
    assert(request.store === false, "response storage was enabled");
    assert(
      request.parallel_tool_calls === false,
      "parallel tools were enabled",
    );
    assert(
      request.max_output_tokens === MAX_OUTPUT_TOKENS,
      "output budget changed",
    );
    assert(request.tool_choice === "auto", "tool choice changed");
    assert(
      request.reasoning?.effort === REASONING_EFFORT,
      "reasoning effort changed",
    );
    assert(
      request.reasoning?.context === "current_turn",
      "reasoning context changed",
    );
    assert(
      request.safety_identifier === SAFETY_IDENTIFIER,
      "safety identifier changed",
    );
    assert(request.tools?.length === 14, "tool inventory changed");
    assert(
      request.text?.format?.type === "json_schema",
      "structured output is not JSON Schema",
    );
    assert(
      request.text?.format?.strict === true,
      "structured output is not strict",
    );
    assert(
      !("max_tool_calls" in request),
      "unsupported max_tool_calls field was sent",
    );
    assert(
      !("previous_response_id" in request),
      "stored response chaining was enabled",
    );
  }
  const secondInput = requests[1].input;
  assert(Array.isArray(secondInput), "continuation input is not an array");
  const outputItem = secondInput.find(
    (item) =>
      typeof item === "object" && item !== null && "type" in item &&
      item.type === "function_call_output",
  );
  assert(
    outputItem && "call_id" in outputItem && outputItem.call_id === "call_1",
    "call ID was not preserved",
  );
});

Deno.test("tool budget exhausts at exactly eight calls", async () => {
  const calls = Array.from({ length: MAX_TOOL_CALLS + 1 }, (_, index) => ({
    type: "function_call",
    call_id: `call_${index + 1}`,
    name: "inspect_worker_status",
    arguments: JSON.stringify({ worker_id: null }),
  }));
  const result = await runAnalyst({
    request: { question: "Inspect worker state.", history: [] },
    safetyIdentifier: SAFETY_IDENTIFIER,
    executeTool: executeSubmittedTool,
    createResponse: async () => ({ status: "completed", output: calls }),
  });
  assert(
    result.response_state === "incomplete",
    "budget exhaustion did not fail closed",
  );
  assert(
    result.usage.tool_calls === MAX_TOOL_CALLS,
    "tool budget was not exact",
  );
  assert(
    result.usage.budget_state === "exhausted",
    "budget state was not exhausted",
  );
});

Deno.test("response loop exhausts at exactly six calls", async () => {
  let index = 0;
  const result = await runAnalyst({
    request: { question: "Inspect pipeline state.", history: [] },
    safetyIdentifier: SAFETY_IDENTIFIER,
    executeTool: executeSubmittedTool,
    createResponse: async () => {
      index += 1;
      return functionCall(`call_${index}`, "inspect_pipeline_status", {
        pipeline_id: null,
      });
    },
  });
  assert(
    result.response_state === "incomplete",
    "loop exhaustion did not fail closed",
  );
  assert(
    result.usage.response_calls === MAX_RESPONSE_CALLS,
    "response-call budget changed",
  );
  assert(
    result.usage.budget_state === "exhausted",
    "loop budget was not exhausted",
  );
});

Deno.test("one transient tool retry is allowed and recorded as one model tool call", async () => {
  let attempts = 0;
  let stored: ToolResult | null = null;
  let responses = 0;
  const result = await runAnalyst({
    request: { question: "Inspect the worker.", history: [] },
    safetyIdentifier: SAFETY_IDENTIFIER,
    executeTool: async (name, args) => {
      attempts += 1;
      if (attempts === 1) throw new TransientToolError("temporary");
      stored = await executeSubmittedTool(name, args);
      return stored;
    },
    createResponse: async () => {
      responses += 1;
      return responses === 1
        ? functionCall("call_worker", "inspect_worker_status", {
          worker_id: null,
        })
        : finalOutput(stored!, {
          summary: "Worker state is unavailable.",
          claims: [{
            claim_id: "claim_1",
            statement: "Worker state is unavailable.",
            evidence_state: "unavailable",
            citation_ids: [stored!.citations[0].artifact_id],
          }],
          citations: [stored!.citations[0]],
          tools_used: ["inspect_worker_status"],
        });
    },
  });
  assert(
    result.response_state === "completed",
    "transient retry did not recover",
  );
  assert(attempts === 2, "transient retry count changed");
  assert(
    result.usage.tool_calls === 1,
    "tool retry inflated model-call budget",
  );
});

Deno.test("permanent tool errors and malformed calls fail closed", async () => {
  const failed = await runAnalyst({
    request: { question: "Inspect the worker.", history: [] },
    safetyIdentifier: SAFETY_IDENTIFIER,
    executeTool: async () => {
      throw new Error("private implementation detail");
    },
    createResponse: async () =>
      functionCall("call_worker", "inspect_worker_status", { worker_id: null }),
  });
  assert(
    failed.response_state === "incomplete",
    "permanent tool failure escaped",
  );
  assert(
    !failed.summary.includes("private implementation detail"),
    "raw tool error leaked",
  );
  const malformed = await runAnalyst({
    request: { question: "Inspect the worker.", history: [] },
    safetyIdentifier: SAFETY_IDENTIFIER,
    executeTool: executeSubmittedTool,
    createResponse: async () => ({
      status: "completed",
      output: [{
        type: "function_call",
        call_id: "c",
        name: "inspect_worker_status",
        arguments: "{",
      }],
    }),
  });
  assert(
    malformed.response_state === "incomplete",
    "malformed arguments escaped",
  );
});

Deno.test("OpenAI transport errors become structured incomplete responses", async () => {
  const failed = await runAnalyst({
    request: { question: "Inspect the species.", history: [] },
    safetyIdentifier: SAFETY_IDENTIFIER,
    executeTool: executeSubmittedTool,
    createResponse: async () => {
      throw new Error("private upstream detail");
    },
  });
  assert(failed.response_state === "incomplete", "transport error escaped");
  assert(
    failed.usage.response_calls === 1,
    "attempted response call was not counted",
  );
  assert(
    !failed.summary.includes("private upstream detail"),
    "upstream detail leaked",
  );
});

Deno.test("fabricated and modified citations are rejected", async () => {
  let stored: ToolResult | null = null;
  let responses = 0;
  const result = await runAnalyst({
    request: { question: "Inspect the species.", history: [] },
    safetyIdentifier: SAFETY_IDENTIFIER,
    executeTool: async (name, args) => {
      stored = await executeSubmittedTool(name, args);
      return stored;
    },
    createResponse: async () => {
      responses += 1;
      if (responses === 1) return functionCall();
      const changed = { ...stored!.citations[0], path: "invented/path.json" };
      return finalOutput(stored!, { citations: [changed] });
    },
  });
  assert(result.response_state === "incomplete", "fabricated citation escaped");
  assert(result.claims.length === 0, "unsupported claims escaped");
});

Deno.test("claims without current tool evidence are rejected", async () => {
  const result = await runAnalyst({
    request: { question: "Invent a butterfly fact.", history: [] },
    safetyIdentifier: SAFETY_IDENTIFIER,
    executeTool: executeSubmittedTool,
    createResponse: async () => ({
      status: "completed",
      output_text: JSON.stringify({
        response_state: "completed",
        summary: "Invented.",
        claims: [{
          claim_id: "claim_1",
          statement: "Invented.",
          evidence_state: "direct",
          citation_ids: ["invented"],
        }],
        citations: [],
        limitations: [],
        tools_used: [],
      }),
      output: [],
    }),
  });
  assert(
    result.response_state === "incomplete",
    "uncited memory claim escaped",
  );
});

Deno.test("citation-free completed summaries and refused claims are rejected", async () => {
  const summaryOnly = await runAnalyst({
    request: { question: "Invent a butterfly fact.", history: [] },
    safetyIdentifier: SAFETY_IDENTIFIER,
    executeTool: executeSubmittedTool,
    createResponse: async () => ({
      status: "completed",
      output_text: JSON.stringify({
        response_state: "completed",
        summary: "Invented species fact.",
        claims: [],
        citations: [],
        limitations: [],
        tools_used: [],
      }),
      output: [],
    }),
  });
  assert(
    summaryOnly.response_state === "incomplete",
    "summary-only answer escaped",
  );

  let stored: ToolResult | null = null;
  let responses = 0;
  const refusedClaim = await runAnalyst({
    request: { question: "Inspect the species.", history: [] },
    safetyIdentifier: SAFETY_IDENTIFIER,
    executeTool: async (name, args) => {
      stored = await executeSubmittedTool(name, args);
      return stored;
    },
    createResponse: async () => {
      responses += 1;
      return responses === 1
        ? functionCall()
        : finalOutput(stored!, { response_state: "refused" });
    },
  });
  assert(refusedClaim.response_state === "incomplete", "refused claim escaped");
  assert(refusedClaim.claims.length === 0, "refused claim reached the caller");
});

Deno.test("refusal and incomplete response states are first class", async () => {
  const refused = await runAnalyst({
    request: { question: "Unsafe request.", history: [] },
    safetyIdentifier: SAFETY_IDENTIFIER,
    executeTool: executeSubmittedTool,
    createResponse: async () => ({
      status: "completed",
      output: [{
        type: "message",
        content: [{ type: "refusal", refusal: "I cannot help with that." }],
      }],
    }),
  });
  assert(refused.response_state === "refused", "refusal was not preserved");
  assert(refused.claims.length === 0, "refusal returned claims");
  const incomplete = await runAnalyst({
    request: { question: "Question.", history: [] },
    safetyIdentifier: SAFETY_IDENTIFIER,
    executeTool: executeSubmittedTool,
    createResponse: async () => ({
      status: "incomplete",
      output: [],
      incomplete_details: { reason: "max_output_tokens" },
    }),
  });
  assert(
    incomplete.response_state === "incomplete",
    "incomplete response was not preserved",
  );
});

Deno.test("prompt and final schema preserve the biodiversity evidence boundary", () => {
  for (
    const term of [
      "Never identify or guess a butterfly",
      "Missing or withheld evidence is unavailable",
      "Every claim must cite",
      "self-only",
      "Potential contribution is not a new occurrence",
    ]
  ) {
    assert(ANALYST_INSTRUCTIONS.includes(term), `prompt is missing ${term}`);
  }
  assert(
    FINAL_MODEL_SCHEMA.additionalProperties === false,
    "final schema is not strict",
  );
  assert(
    JSON.stringify(FINAL_MODEL_SCHEMA.required) ===
      JSON.stringify([
        "response_state",
        "summary",
        "claims",
        "citations",
        "limitations",
        "tools_used",
      ]),
    "final schema fields changed",
  );
});

function assertThrows(operation: () => unknown, text: string): void {
  try {
    operation();
  } catch (error) {
    assert(error instanceof AnalystInputError, "wrong input error type");
    assert(error.message.includes(text), `missing error text: ${text}`);
    return;
  }
  throw new Error("expected operation to throw");
}
