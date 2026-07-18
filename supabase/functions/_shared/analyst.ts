import analystResponseSchemaJson from "../../../packages/openai/analyst-response.schema.json" with {
  type: "json",
};
import type {
  ResponseCreateParamsNonStreaming,
  ResponseInputItem,
} from "openai/responses";

import {
  assertJsonSchema,
  canonicalJson,
  isJsonObject,
  type JsonObject,
  type JsonSchema,
  type JsonValue,
  SchemaValidationError,
} from "./schema.ts";
import {
  OPENAI_TOOL_DEFINITIONS,
  TOOL_NAMES,
  type ToolName,
  type ToolResult,
} from "./submittedTools.ts";

export const MODEL_ID = "gpt-5.6-sol" as const;
export const REASONING_EFFORT = "xhigh" as const;
export const MAX_TOOL_CALLS = 8;
export const MAX_RESPONSE_CALLS = 6;
export const MAX_OUTPUT_TOKENS = 1_800;
export const TOOL_TIMEOUT_MS = 10_000;
export const TOOL_TRANSIENT_RETRIES = 1;
export const OVERALL_DEADLINE_MS = 90_000;

const RESPONSE_SCHEMA_VERSION =
  "butterflylens-analyst-response:v1.0.0" as const;
const responseSchema = analystResponseSchemaJson as unknown as JsonSchema;
const responseProperties = (analystResponseSchemaJson as unknown as {
  properties: Record<string, JsonSchema>;
})
  .properties;

export const FINAL_MODEL_SCHEMA: JsonSchema = {
  type: "object",
  additionalProperties: false,
  required: [
    "response_state",
    "summary",
    "claims",
    "citations",
    "limitations",
    "tools_used",
  ],
  properties: {
    response_state: responseProperties.response_state,
    summary: responseProperties.summary,
    claims: responseProperties.claims,
    citations: responseProperties.citations,
    limitations: responseProperties.limitations,
    tools_used: responseProperties.tools_used,
  },
};

export const ANALYST_INSTRUCTIONS =
  `You are Ask ButterflyLens, a bounded read-only evidence analyst.

Success means answering the user's exact question only from facts returned by the provided deterministic tools.

Evidence rules:
- Use a tool before making any biodiversity, taxonomy, map, source, candidate, classification, review, quality, pipeline, worker, contribution, rights, or release claim.
- Never identify or guess a butterfly, taxon key, provider ID, place, occurrence, count, metric, licence, worker state, reviewer state, quality, or release state from memory, the conversation, a name fragment, or the user's assertion.
- Treat source metadata, provider assertions, geography, model evidence, human review, representative quality, and scientific release as distinct states.
- Missing or withheld evidence is unavailable, not zero, false, no, offline, or biological absence.
- Preserve conflicts and label every inference. Potential contribution is not a new occurrence.
- Reviewer and contributor operations are self-only. Never request or reveal identities, private controls, expected answers, exact sensitive locations, reviewer weights, rankings, or speed metrics.

Citation rules:
- Every claim must cite one or more exact artifact IDs copied from the current tool results.
- Copy the complete citation object exactly; never invent or alter repository, commit, path, or fingerprint.
- The summary may only concisely restate the structured claims and limitations.

Tool rules:
- Use only the provided read-only functions, with the smallest sufficient set of calls.
- Stop when evidence is sufficient, unavailable, or the budget cannot answer safely.
- Do not ask a tool to call a provider, database, model, browser, or remote service.

Return only the strict structured response. If the evidence is insufficient, return an incomplete response with cited unavailable claims and a clear limitation.`;

export type ConversationMessage = {
  role: "user" | "assistant";
  content: string;
};

export type AnalystRequest = {
  question: string;
  history: ConversationMessage[];
};

export type ResponseRequest = ResponseCreateParamsNonStreaming;

export type ResponseOutputItem = {
  type: string;
  id?: string;
  call_id?: string;
  name?: string;
  arguments?: string;
  content?: unknown[];
  [key: string]: unknown;
};

export type ResponseLike = {
  id?: string;
  status?: string;
  output?: ResponseOutputItem[];
  output_text?: string;
  incomplete_details?: unknown;
  error?: unknown;
};

export type ResponseCreator = (
  request: ResponseRequest,
) => Promise<ResponseLike>;
export type ToolExecutor = (name: string, args: unknown) => Promise<ToolResult>;

export type AnalystResponse = {
  schema_version: typeof RESPONSE_SCHEMA_VERSION;
  mode: "live";
  response_state: "completed" | "incomplete" | "refused";
  summary: string;
  claims: Array<{
    claim_id: string;
    statement: string;
    evidence_state: "direct" | "inference" | "unavailable" | "conflict";
    citation_ids: string[];
  }>;
  citations: Array<{
    artifact_id: string;
    repository: "karikris/ButterflyLens";
    commit: string;
    path: string;
    fingerprint: string;
  }>;
  limitations: string[];
  tools_used: ToolName[];
  model: { id: typeof MODEL_ID; reasoning_effort: typeof REASONING_EFFORT };
  usage: {
    response_calls: number;
    tool_calls: number;
    budget_state: "within_budget" | "exhausted";
  };
};

export class AnalystInputError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AnalystInputError";
  }
}

export class TransientToolError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "TransientToolError";
  }
}

export function parseAnalystRequest(value: unknown): AnalystRequest {
  if (!isJsonObject(value)) {
    throw new AnalystInputError("request must be a JSON object");
  }
  const keys = Object.keys(value).sort();
  if (
    canonicalJson(keys as JsonValue) !== canonicalJson(["history", "question"])
  ) {
    throw new AnalystInputError("request requires only question and history");
  }
  if (typeof value.question !== "string") {
    throw new AnalystInputError("question must be text");
  }
  const question = value.question.trim();
  if (question.length < 1 || question.length > 1_200) {
    throw new AnalystInputError("question must contain 1 to 1200 characters");
  }
  if (!Array.isArray(value.history) || value.history.length > 8) {
    throw new AnalystInputError("history must contain at most 8 messages");
  }
  const history = value.history.map((message, index): ConversationMessage => {
    if (!isJsonObject(message)) {
      throw new AnalystInputError(`history[${index}] must be an object`);
    }
    if (Object.keys(message).sort().join(",") !== "content,role") {
      throw new AnalystInputError(`history[${index}] has unexpected fields`);
    }
    if (message.role !== "user" && message.role !== "assistant") {
      throw new AnalystInputError(`history[${index}].role is invalid`);
    }
    if (typeof message.content !== "string") {
      throw new AnalystInputError(`history[${index}].content must be text`);
    }
    const content = message.content.trim();
    if (content.length < 1 || content.length > 1_000) {
      throw new AnalystInputError(
        `history[${index}].content must contain 1 to 1000 characters`,
      );
    }
    return { role: message.role, content };
  });
  return { question, history };
}

export async function hashSafetyIdentifier(subject: string): Promise<string> {
  if (!subject) {
    throw new AnalystInputError("authenticated subject is required");
  }
  const bytes = new TextEncoder().encode(
    `butterflylens-auth-subject-v1:${subject}`,
  );
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
  return Array.from(digest, (byte) => byte.toString(16).padStart(2, "0")).join(
    "",
  );
}

export async function runAnalyst(input: {
  request: AnalystRequest;
  safetyIdentifier: string;
  createResponse: ResponseCreator;
  executeTool: ToolExecutor;
  now?: () => number;
}): Promise<AnalystResponse> {
  if (!/^[0-9a-f]{64}$/u.test(input.safetyIdentifier)) {
    throw new AnalystInputError("safety identifier must be a SHA-256 digest");
  }
  const now = input.now ?? Date.now;
  const deadline = now() + OVERALL_DEADLINE_MS;
  const transcript: ResponseInputItem[] = input.request.history.map((
    message,
  ) => ({
    role: message.role,
    content: message.content,
  }));
  transcript.push({ role: "user", content: input.request.question });

  let responseCalls = 0;
  let toolCalls = 0;
  const usedTools: ToolName[] = [];
  const toolResults: ToolResult[] = [];

  while (responseCalls < MAX_RESPONSE_CALLS) {
    if (now() >= deadline) {
      return incompleteResult(
        "The analyst deadline was exhausted before a supported answer completed.",
        responseCalls,
        toolCalls,
        usedTools,
        toolResults,
        "exhausted",
      );
    }
    responseCalls += 1;
    let response: ResponseLike;
    try {
      response = await withTimeout(
        input.createResponse(
          buildResponseRequest(transcript, input.safetyIdentifier),
        ),
        Math.max(1, deadline - now()),
      );
    } catch {
      return incompleteResult(
        "The OpenAI response failed closed; no unsupported answer was returned.",
        responseCalls,
        toolCalls,
        usedTools,
        toolResults,
        now() >= deadline ? "exhausted" : "within_budget",
      );
    }
    const output = Array.isArray(response.output) ? response.output : [];
    const calls = output.filter(isFunctionCall);

    if (calls.length > 0) {
      transcript.push(...(output as unknown as ResponseInputItem[]));
      for (const call of calls) {
        if (toolCalls >= MAX_TOOL_CALLS || now() >= deadline) {
          return incompleteResult(
            "The bounded tool budget was exhausted before a supported answer completed.",
            responseCalls,
            toolCalls,
            usedTools,
            toolResults,
            "exhausted",
          );
        }
        const name = call.name as ToolName;
        if (!TOOL_NAMES.includes(name)) {
          return incompleteResult(
            "The model requested a tool outside the ButterflyLens allowlist.",
            responseCalls,
            toolCalls,
            usedTools,
            toolResults,
            "within_budget",
          );
        }
        if (
          typeof call.call_id !== "string" || !call.call_id ||
          typeof call.arguments !== "string"
        ) {
          return incompleteResult(
            "The model returned a malformed function call.",
            responseCalls,
            toolCalls,
            usedTools,
            toolResults,
            "within_budget",
          );
        }
        let args: unknown;
        try {
          args = JSON.parse(call.arguments);
        } catch {
          return incompleteResult(
            "The model returned malformed JSON tool arguments.",
            responseCalls,
            toolCalls,
            usedTools,
            toolResults,
            "within_budget",
          );
        }
        toolCalls += 1;
        if (!usedTools.includes(name)) usedTools.push(name);
        let result: ToolResult;
        try {
          result = await executeToolWithPolicy(
            input.executeTool,
            name,
            args,
            () => deadline - now(),
          );
        } catch {
          const exhausted = now() >= deadline;
          return incompleteResult(
            exhausted
              ? "The analyst deadline was exhausted during a deterministic evidence tool."
              : "A deterministic evidence tool failed closed.",
            responseCalls,
            toolCalls,
            usedTools,
            toolResults,
            exhausted ? "exhausted" : "within_budget",
          );
        }
        toolResults.push(result);
        transcript.push({
          type: "function_call_output",
          call_id: call.call_id,
          output: canonicalJson(result as unknown as JsonValue),
        } as ResponseInputItem);
      }
      continue;
    }

    const refusal = extractRefusal(output);
    if (refusal !== null) {
      return validateServerResponse({
        schema_version: RESPONSE_SCHEMA_VERSION,
        mode: "live",
        response_state: "refused",
        summary: refusal.slice(0, 800) || "The model refused this request.",
        claims: [],
        citations: [],
        limitations: ["No unsupported scientific answer was returned."],
        tools_used: usedTools,
        model: { id: MODEL_ID, reasoning_effort: REASONING_EFFORT },
        usage: {
          response_calls: responseCalls,
          tool_calls: toolCalls,
          budget_state: "within_budget",
        },
      });
    }
    if (
      response.status === "incomplete" || response.status === "failed" ||
      response.status === "cancelled"
    ) {
      return incompleteResult(
        "The OpenAI response did not complete; no unsupported answer was returned.",
        responseCalls,
        toolCalls,
        usedTools,
        toolResults,
        "within_budget",
      );
    }
    const outputText = extractOutputText(response, output);
    if (outputText === null) {
      return incompleteResult(
        "The OpenAI response contained no structured final answer.",
        responseCalls,
        toolCalls,
        usedTools,
        toolResults,
        "within_budget",
      );
    }
    let modelResult: unknown;
    try {
      modelResult = JSON.parse(outputText);
      assertJsonSchema(FINAL_MODEL_SCHEMA, modelResult, "model_result");
    } catch {
      return incompleteResult(
        "The structured final answer failed schema validation.",
        responseCalls,
        toolCalls,
        usedTools,
        toolResults,
        "within_budget",
      );
    }
    if (!isJsonObject(modelResult)) {
      return incompleteResult(
        "The structured final answer was not an object.",
        responseCalls,
        toolCalls,
        usedTools,
        toolResults,
        "within_budget",
      );
    }
    try {
      validateGrounding(modelResult, usedTools, toolResults);
    } catch {
      return incompleteResult(
        "The structured final answer failed artifact-grounding validation.",
        responseCalls,
        toolCalls,
        usedTools,
        toolResults,
        "within_budget",
      );
    }
    return validateServerResponse({
      schema_version: RESPONSE_SCHEMA_VERSION,
      mode: "live",
      ...(modelResult as Omit<
        AnalystResponse,
        "schema_version" | "mode" | "model" | "usage"
      >),
      model: { id: MODEL_ID, reasoning_effort: REASONING_EFFORT },
      usage: {
        response_calls: responseCalls,
        tool_calls: toolCalls,
        budget_state: "within_budget",
      },
    });
  }

  return incompleteResult(
    "The bounded response loop was exhausted before a supported answer completed.",
    responseCalls,
    toolCalls,
    usedTools,
    toolResults,
    "exhausted",
  );
}

function buildResponseRequest(
  transcript: ResponseInputItem[],
  safetyIdentifier: string,
): ResponseRequest {
  return {
    model: MODEL_ID,
    instructions: ANALYST_INSTRUCTIONS,
    input: [...transcript],
    tools: OPENAI_TOOL_DEFINITIONS as ResponseCreateParamsNonStreaming["tools"],
    tool_choice: "auto",
    parallel_tool_calls: false,
    max_output_tokens: MAX_OUTPUT_TOKENS,
    reasoning: { effort: REASONING_EFFORT, context: "current_turn" },
    text: {
      format: {
        type: "json_schema",
        name: "butterflylens_analyst_response",
        strict: true,
        schema: FINAL_MODEL_SCHEMA as Record<string, unknown>,
      },
    },
    store: false,
    safety_identifier: safetyIdentifier,
  };
}

function isFunctionCall(
  item: ResponseOutputItem,
): item is ResponseOutputItem & {
  type: "function_call";
  call_id: string;
  name: string;
  arguments: string;
} {
  return item.type === "function_call";
}

async function executeToolWithPolicy(
  executeTool: ToolExecutor,
  name: ToolName,
  args: unknown,
  remainingMs: () => number,
): Promise<ToolResult> {
  for (let attempt = 0; attempt <= TOOL_TRANSIENT_RETRIES; attempt += 1) {
    try {
      const remaining = remainingMs();
      if (remaining <= 0) throw new Error("overall analyst deadline exhausted");
      return await withTimeout(
        executeTool(name, args),
        Math.min(TOOL_TIMEOUT_MS, remaining),
      );
    } catch (error) {
      if (
        !(error instanceof TransientToolError) ||
        attempt === TOOL_TRANSIENT_RETRIES
      ) throw error;
    }
  }
  throw new Error("unreachable tool retry state");
}

async function withTimeout<T>(
  operation: Promise<T>,
  timeoutMs: number,
): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      operation,
      new Promise<T>((_, reject) => {
        timer = setTimeout(() => reject(new Error("tool timeout")), timeoutMs);
      }),
    ]);
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
}

function extractOutputText(
  response: ResponseLike,
  output: ResponseOutputItem[],
): string | null {
  if (typeof response.output_text === "string" && response.output_text) {
    return response.output_text;
  }
  for (const item of output) {
    if (item.type !== "message" || !Array.isArray(item.content)) continue;
    for (const content of item.content) {
      if (
        isJsonObject(content) && content.type === "output_text" &&
        typeof content.text === "string"
      ) {
        return content.text;
      }
    }
  }
  return null;
}

function extractRefusal(output: ResponseOutputItem[]): string | null {
  for (const item of output) {
    if (item.type !== "message" || !Array.isArray(item.content)) continue;
    for (const content of item.content) {
      if (
        isJsonObject(content) && content.type === "refusal" &&
        typeof content.refusal === "string"
      ) {
        return content.refusal;
      }
    }
  }
  return null;
}

function validateGrounding(
  modelResult: JsonObject,
  usedTools: ToolName[],
  toolResults: ToolResult[],
): void {
  const responseState = modelResult.response_state;
  const claims = modelResult.claims as JsonValue[];
  const citations = modelResult.citations as JsonValue[];
  if (
    responseState === "refused" && (claims.length > 0 || citations.length > 0)
  ) {
    throw new SchemaValidationError(
      "refused responses cannot contain claims or citations",
    );
  }
  if (responseState === "completed" && claims.length === 0) {
    throw new SchemaValidationError(
      "completed responses require a cited claim",
    );
  }
  if (
    responseState !== "refused" &&
    (toolResults.length === 0 || citations.length === 0)
  ) {
    throw new SchemaValidationError(
      "non-refusal model answers require current tool evidence",
    );
  }
  const declaredTools = modelResult.tools_used as JsonValue[];
  if (canonicalJson(declaredTools) !== canonicalJson(usedTools)) {
    throw new SchemaValidationError(
      "declared tools do not match executed tools",
    );
  }
  const allowedCitations = new Map<string, JsonValue>();
  for (const result of toolResults) {
    for (const citation of result.citations) {
      allowedCitations.set(
        citation.artifact_id,
        citation as unknown as JsonValue,
      );
    }
  }
  const returnedCitations = citations;
  const returnedIds = new Set<string>();
  for (const citation of returnedCitations) {
    if (!isJsonObject(citation) || typeof citation.artifact_id !== "string") {
      throw new SchemaValidationError("citation is malformed");
    }
    const allowed = allowedCitations.get(citation.artifact_id);
    if (!allowed || canonicalJson(citation) !== canonicalJson(allowed)) {
      throw new SchemaValidationError(
        "citation was not returned by a current tool",
      );
    }
    returnedIds.add(citation.artifact_id);
  }
  for (const claim of claims) {
    if (!isJsonObject(claim) || !Array.isArray(claim.citation_ids)) {
      throw new SchemaValidationError("claim is malformed");
    }
    for (const id of claim.citation_ids) {
      if (typeof id !== "string" || !returnedIds.has(id)) {
        throw new SchemaValidationError(
          "claim citation is missing from the final citation list",
        );
      }
    }
  }
  if (
    claims.length > 0 && toolResults.length === 0
  ) {
    throw new SchemaValidationError(
      "factual claims require current tool evidence",
    );
  }
}

function incompleteResult(
  summary: string,
  responseCalls: number,
  toolCalls: number,
  usedTools: ToolName[],
  toolResults: ToolResult[],
  budgetState: "within_budget" | "exhausted",
): AnalystResponse {
  const citationMap = new Map<string, AnalystResponse["citations"][number]>();
  for (const result of toolResults) {
    for (const citation of result.citations) {
      citationMap.set(citation.artifact_id, citation);
    }
  }
  return validateServerResponse({
    schema_version: RESPONSE_SCHEMA_VERSION,
    mode: "live",
    response_state: "incomplete",
    summary,
    claims: [],
    citations: [...citationMap.values()].slice(0, 16),
    limitations: [
      "The analyst stopped rather than fabricate or overstate evidence.",
    ],
    tools_used: usedTools,
    model: { id: MODEL_ID, reasoning_effort: REASONING_EFFORT },
    usage: {
      response_calls: responseCalls,
      tool_calls: toolCalls,
      budget_state: budgetState,
    },
  });
}

function validateServerResponse(value: AnalystResponse): AnalystResponse {
  assertJsonSchema(responseSchema, value, "analyst_response");
  if (
    value.response_state === "refused" &&
    (value.claims.length > 0 || value.citations.length > 0)
  ) {
    throw new SchemaValidationError(
      "refused responses cannot contain claims or citations",
    );
  }
  return value;
}
