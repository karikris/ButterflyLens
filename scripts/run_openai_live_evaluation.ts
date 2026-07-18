#!/usr/bin/env -S deno run --allow-env=OPENAI_API_KEY,BUTTERFLYLENS_EVAL_SUBJECT --allow-read --allow-write --allow-net=api.openai.com

import OpenAI from "openai";

import evaluationSuiteJson from "../packages/openai/analyst-eval-cases.v1.json" with {
  type: "json",
};
import {
  type AnalystResponse,
  hashSafetyIdentifier,
  MODEL_ID,
  REASONING_EFFORT,
  type ResponseLike,
  type ResponseRequest,
  runAnalyst,
} from "../supabase/functions/_shared/analyst.ts";
import {
  canonicalJson,
  isJsonObject,
  type JsonValue,
  sha256Fingerprint,
} from "../supabase/functions/_shared/schema.ts";
import {
  executeSubmittedTool,
  TOOL_NAMES,
  type ToolName,
  type ToolResult,
} from "../supabase/functions/_shared/submittedTools.ts";

const TRACE_SCHEMA_VERSION = "butterflylens-analyst-eval-trace:v1.0.0" as const;
const CHECKPOINT_SCHEMA_VERSION =
  "butterflylens-analyst-live-eval-checkpoint:v1.0.0" as const;
const OPENAI_REQUEST_TIMEOUT_MS = 45_000;
const MAX_TRACE_NETWORK_CALLS = 400;

type EvaluationSuiteCase = {
  case_id: string;
  question: string;
  expected_live_response_state: "completed" | "incomplete";
  expected_tool_call: {
    name: ToolName;
    arguments: JsonValue;
  };
};

export type EvaluationSuite = {
  suite_fingerprint: string;
  cases: EvaluationSuiteCase[];
};

export type RecordedToolCall = {
  name: ToolName;
  arguments: JsonValue;
  output: ToolResult;
};

export type RecordedEvaluationCase = {
  case_id: string;
  tool_calls: RecordedToolCall[];
  response: AnalystResponse;
};

type EvaluationExecution = {
  run_kind: "recorded_live_openai" | "synthetic_grader_fixture";
  model_invoked: boolean;
  network_calls: number;
};

export type LiveEvaluationCheckpoint = {
  schema_version: typeof CHECKPOINT_SCHEMA_VERSION;
  suite_fingerprint: string;
  run_id: string;
  recorded_at: string;
  execution: EvaluationExecution;
  model: { id: typeof MODEL_ID; reasoning_effort: typeof REASONING_EFFORT };
  cases: RecordedEvaluationCase[];
  checkpoint_fingerprint: string;
};

export type RecordedEvaluationTrace = {
  schema_version: typeof TRACE_SCHEMA_VERSION;
  suite_fingerprint: string;
  run_id: string;
  recorded_at: string;
  execution: EvaluationExecution;
  model: { id: typeof MODEL_ID; reasoning_effort: typeof REASONING_EFFORT };
  cases: RecordedEvaluationCase[];
  trace_fingerprint: string;
};

export type LiveEvaluationOptions = {
  suite?: EvaluationSuite;
  runId: string;
  recordedAt: string;
  safetyIdentifier: string;
  execution: Omit<EvaluationExecution, "network_calls">;
  networkCallsPerResponse: 0 | 1;
  createResponse: (request: ResponseRequest) => Promise<ResponseLike>;
  executeTool?: (name: ToolName, args: unknown) => Promise<ToolResult>;
  checkpoint?: unknown;
  onCheckpoint?: (checkpoint: LiveEvaluationCheckpoint) => Promise<void>;
};

export type LiveEvaluationCliOptions = {
  output: string;
  checkpoint: string;
  confirmed: true;
};

export const EVALUATION_SUITE =
  evaluationSuiteJson as unknown as EvaluationSuite;

export async function runLiveEvaluation(
  options: LiveEvaluationOptions,
): Promise<RecordedEvaluationTrace> {
  const suite = options.suite ?? EVALUATION_SUITE;
  assertSuite(suite);
  assertRunMetadata(options.runId, options.recordedAt);
  if (!/^[0-9a-f]{64}$/u.test(options.safetyIdentifier)) {
    throw new Error("evaluation safety identifier must be a SHA-256 digest");
  }
  if (
    options.execution.run_kind === "recorded_live_openai" &&
    options.execution.model_invoked !== true
  ) {
    throw new Error("a recorded live run must declare model_invoked=true");
  }
  if (
    options.execution.run_kind === "synthetic_grader_fixture" &&
    options.execution.model_invoked !== false
  ) {
    throw new Error("a synthetic run cannot claim a model invocation");
  }
  if (
    options.execution.run_kind === "recorded_live_openai" &&
    options.networkCallsPerResponse !== 1
  ) {
    throw new Error("a recorded live run must count every Responses request");
  }
  if (
    options.execution.run_kind === "synthetic_grader_fixture" &&
    options.networkCallsPerResponse !== 0
  ) {
    throw new Error("a synthetic run cannot claim network calls");
  }

  let checkpoint = options.checkpoint === undefined
    ? await createCheckpoint({
      suite,
      runId: options.runId,
      recordedAt: options.recordedAt,
      execution: options.execution,
    })
    : await validateCheckpoint({
      value: options.checkpoint,
      suite,
      runId: options.runId,
      recordedAt: options.recordedAt,
      execution: options.execution,
    });
  const executeTool = options.executeTool ?? executeSubmittedTool;

  for (
    let caseIndex = checkpoint.cases.length;
    caseIndex < suite.cases.length;
    caseIndex += 1
  ) {
    const evaluationCase = suite.cases[caseIndex];
    const toolCalls: RecordedToolCall[] = [];
    let responseCalls = 0;
    const response = await runAnalyst({
      request: { question: evaluationCase.question, history: [] },
      safetyIdentifier: options.safetyIdentifier,
      createResponse: async (request) => {
        if (
          checkpoint.execution.network_calls +
              (responseCalls + 1) * options.networkCallsPerResponse >
            MAX_TRACE_NETWORK_CALLS
        ) {
          throw new Error("live evaluation network-call budget exhausted");
        }
        responseCalls += 1;
        return await options.createResponse(request);
      },
      executeTool: async (name, args) => {
        if (!TOOL_NAMES.includes(name as ToolName)) {
          throw new Error(
            "analyst selected a tool outside the trace allowlist",
          );
        }
        const toolName = name as ToolName;
        const output = await executeTool(toolName, args);
        toolCalls.push({
          name: toolName,
          arguments: jsonClone(args, "tool arguments"),
          output: jsonClone(output, "tool output") as unknown as ToolResult,
        });
        return output;
      },
    });

    const cases = [
      ...checkpoint.cases,
      {
        case_id: evaluationCase.case_id,
        tool_calls: toolCalls,
        response: jsonClone(
          response,
          "analyst response",
        ) as unknown as AnalystResponse,
      },
    ];
    checkpoint = await createCheckpoint({
      suite,
      runId: options.runId,
      recordedAt: options.recordedAt,
      execution: {
        ...options.execution,
        network_calls: checkpoint.execution.network_calls +
          responseCalls * options.networkCallsPerResponse,
      },
      cases,
    });
    if (options.onCheckpoint) await options.onCheckpoint(checkpoint);
  }

  const traceWithoutFingerprint = {
    schema_version: TRACE_SCHEMA_VERSION,
    suite_fingerprint: suite.suite_fingerprint,
    run_id: checkpoint.run_id,
    recorded_at: checkpoint.recorded_at,
    execution: checkpoint.execution,
    model: checkpoint.model,
    cases: checkpoint.cases,
  };
  return {
    ...traceWithoutFingerprint,
    trace_fingerprint: await sha256Fingerprint(
      traceWithoutFingerprint as unknown as JsonValue,
    ),
  };
}

export function parseLiveEvaluationArgs(
  args: string[],
): LiveEvaluationCliOptions {
  let confirmed = false;
  let output: string | undefined;
  let checkpoint: string | undefined;
  for (let index = 0; index < args.length; index += 1) {
    const argument = args[index];
    if (argument === "--confirm-live") {
      confirmed = true;
      continue;
    }
    if (argument === "--output" || argument === "--checkpoint") {
      const value = args[index + 1];
      if (!value || value.startsWith("--")) {
        throw new Error(`${argument} requires a path`);
      }
      if (argument === "--output") output = value;
      else checkpoint = value;
      index += 1;
      continue;
    }
    throw new Error(`unsupported argument: ${argument}`);
  }
  if (!confirmed) {
    throw new Error("live evaluation requires --confirm-live");
  }
  if (!output || !checkpoint) {
    throw new Error("live evaluation requires --output and --checkpoint");
  }
  if (output === checkpoint) {
    throw new Error("output and checkpoint paths must differ");
  }
  return { output, checkpoint, confirmed: true };
}

async function createCheckpoint(input: {
  suite: EvaluationSuite;
  runId: string;
  recordedAt: string;
  execution: Omit<EvaluationExecution, "network_calls"> | EvaluationExecution;
  cases?: RecordedEvaluationCase[];
}): Promise<LiveEvaluationCheckpoint> {
  const checkpointWithoutFingerprint = {
    schema_version: CHECKPOINT_SCHEMA_VERSION,
    suite_fingerprint: input.suite.suite_fingerprint,
    run_id: input.runId,
    recorded_at: input.recordedAt,
    execution: {
      ...input.execution,
      network_calls: "network_calls" in input.execution
        ? input.execution.network_calls
        : 0,
    },
    model: { id: MODEL_ID, reasoning_effort: REASONING_EFFORT },
    cases: input.cases ?? [],
  };
  return {
    ...checkpointWithoutFingerprint,
    checkpoint_fingerprint: await sha256Fingerprint(
      checkpointWithoutFingerprint as unknown as JsonValue,
    ),
  };
}

async function validateCheckpoint(input: {
  value: unknown;
  suite: EvaluationSuite;
  runId: string;
  recordedAt: string;
  execution: Omit<EvaluationExecution, "network_calls">;
}): Promise<LiveEvaluationCheckpoint> {
  if (!isJsonObject(input.value)) {
    throw new Error("checkpoint must be an object");
  }
  const checkpoint = input.value as unknown as LiveEvaluationCheckpoint;
  if (checkpoint.schema_version !== CHECKPOINT_SCHEMA_VERSION) {
    throw new Error("checkpoint schema version changed");
  }
  if (checkpoint.suite_fingerprint !== input.suite.suite_fingerprint) {
    throw new Error("checkpoint suite fingerprint changed");
  }
  if (
    checkpoint.run_id !== input.runId ||
    checkpoint.recorded_at !== input.recordedAt
  ) {
    throw new Error("checkpoint run metadata changed");
  }
  if (
    checkpoint.execution?.run_kind !== input.execution.run_kind ||
    checkpoint.execution?.model_invoked !== input.execution.model_invoked ||
    !Number.isInteger(checkpoint.execution?.network_calls) ||
    checkpoint.execution.network_calls < 0 ||
    checkpoint.execution.network_calls > MAX_TRACE_NETWORK_CALLS
  ) {
    throw new Error("checkpoint execution metadata is invalid");
  }
  if (
    checkpoint.model?.id !== MODEL_ID ||
    checkpoint.model?.reasoning_effort !== REASONING_EFFORT
  ) {
    throw new Error("checkpoint model metadata changed");
  }
  if (
    !Array.isArray(checkpoint.cases) ||
    checkpoint.cases.length > input.suite.cases.length
  ) {
    throw new Error("checkpoint cases are invalid");
  }
  checkpoint.cases.forEach((recordedCase, index) => {
    if (recordedCase.case_id !== input.suite.cases[index].case_id) {
      throw new Error("checkpoint is not an exact suite prefix");
    }
    assertRecordedCase(recordedCase);
  });
  const { checkpoint_fingerprint: observed, ...payload } = checkpoint;
  if (
    typeof observed !== "string" ||
    observed !== await sha256Fingerprint(payload as unknown as JsonValue)
  ) {
    throw new Error("checkpoint fingerprint mismatch");
  }
  return jsonClone(
    checkpoint,
    "checkpoint",
  ) as unknown as LiveEvaluationCheckpoint;
}

function assertRecordedCase(value: RecordedEvaluationCase): void {
  if (!isJsonObject(value) || typeof value.case_id !== "string") {
    throw new Error("checkpoint case is invalid");
  }
  if (!Array.isArray(value.tool_calls) || value.tool_calls.length > 8) {
    throw new Error("checkpoint tool calls are invalid");
  }
  for (const call of value.tool_calls) {
    if (
      !isJsonObject(call) || !TOOL_NAMES.includes(call.name as ToolName) ||
      !isJsonObject(call.arguments) || !isJsonObject(call.output) ||
      call.output.tool_name !== call.name
    ) {
      throw new Error("checkpoint tool call is invalid");
    }
  }
  if (
    !isJsonObject(value.response) ||
    value.response.schema_version !==
      "butterflylens-analyst-response:v1.0.0" ||
    value.response.model?.id !== MODEL_ID ||
    value.response.model?.reasoning_effort !== REASONING_EFFORT
  ) {
    throw new Error("checkpoint response is invalid");
  }
}

function assertSuite(suite: EvaluationSuite): void {
  if (
    !/^sha256:[0-9a-f]{64}$/u.test(suite.suite_fingerprint) ||
    !Array.isArray(suite.cases) || suite.cases.length !== 48
  ) {
    throw new Error("evaluation suite contract changed");
  }
  const ids = new Set<string>();
  for (const evaluationCase of suite.cases) {
    if (
      !/^[a-z][a-z0-9_]{2,79}$/u.test(evaluationCase.case_id) ||
      !evaluationCase.question || ids.has(evaluationCase.case_id)
    ) {
      throw new Error("evaluation suite cases are invalid");
    }
    ids.add(evaluationCase.case_id);
  }
}

function assertRunMetadata(runId: string, recordedAt: string): void {
  if (!/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,179}$/u.test(runId)) {
    throw new Error("evaluation run ID is invalid");
  }
  if (new Date(recordedAt).toISOString() !== recordedAt) {
    throw new Error("evaluation timestamp must be canonical UTC ISO-8601");
  }
}

function jsonClone(value: unknown, label: string): JsonValue {
  try {
    return JSON.parse(canonicalJson(value as JsonValue)) as JsonValue;
  } catch {
    throw new Error(`${label} is not canonical JSON`);
  }
}

async function readJsonIfPresent(path: string): Promise<unknown | undefined> {
  try {
    return JSON.parse(await Deno.readTextFile(path));
  } catch (error) {
    if (error instanceof Deno.errors.NotFound) return undefined;
    throw new Error(`cannot read checkpoint ${path}`);
  }
}

async function assertPathAbsent(path: string): Promise<void> {
  try {
    await Deno.stat(path);
  } catch (error) {
    if (error instanceof Deno.errors.NotFound) return;
    throw error;
  }
  throw new Error(`refusing to overwrite existing output ${path}`);
}

async function writeJsonAtomic(path: string, value: unknown): Promise<void> {
  const temporary = `${path}.next-${Deno.pid}`;
  await Deno.writeTextFile(temporary, `${JSON.stringify(value, null, 2)}\n`, {
    create: true,
  });
  await Deno.rename(temporary, path);
}

async function main(args: string[]): Promise<void> {
  const cli = parseLiveEvaluationArgs(args);
  const apiKey = Deno.env.get("OPENAI_API_KEY");
  const privateSubject = Deno.env.get("BUTTERFLYLENS_EVAL_SUBJECT");
  if (!apiKey) throw new Error("OPENAI_API_KEY is required in the environment");
  if (!privateSubject) {
    throw new Error(
      "BUTTERFLYLENS_EVAL_SUBJECT is required in the environment",
    );
  }
  await assertPathAbsent(cli.output);
  const existing = await readJsonIfPresent(cli.checkpoint);
  const now = new Date().toISOString();
  const existingObject = isJsonObject(existing) ? existing : null;
  const runId = typeof existingObject?.run_id === "string"
    ? existingObject.run_id
    : `openai-live:${now}`;
  const recordedAt = typeof existingObject?.recorded_at === "string"
    ? existingObject.recorded_at
    : now;
  const safetyIdentifier = await hashSafetyIdentifier(privateSubject);
  const openai = new OpenAI({
    apiKey,
    maxRetries: 0,
    timeout: OPENAI_REQUEST_TIMEOUT_MS,
  });
  const trace = await runLiveEvaluation({
    runId,
    recordedAt,
    safetyIdentifier,
    execution: { run_kind: "recorded_live_openai", model_invoked: true },
    networkCallsPerResponse: 1,
    checkpoint: existing,
    createResponse: async (request) => {
      const response = await openai.responses.create(request);
      return response as unknown as ResponseLike;
    },
    onCheckpoint: async (checkpoint) => {
      await writeJsonAtomic(cli.checkpoint, checkpoint);
    },
  });
  await writeJsonAtomic(cli.output, trace);
  console.log(
    `recorded ${trace.cases.length} cases and ${trace.execution.network_calls} Responses calls to ${cli.output}`,
  );
  console.log(
    `grade with: uv run python scripts/grade_openai_evaluation.py ${cli.output}`,
  );
}

if (import.meta.main) {
  try {
    await main(Deno.args);
  } catch (error) {
    const message = error instanceof Error ? error.message : "unknown failure";
    console.error(`live evaluation recorder failed: ${message}`);
    Deno.exit(1);
  }
}
