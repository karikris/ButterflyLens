import type { ResponseLike, ResponseRequest } from "../_shared/analyst.ts";
import { type JsonValue, sha256Fingerprint } from "../_shared/schema.ts";
import type { ToolResult } from "../_shared/submittedTools.ts";
import {
  EVALUATION_SUITE,
  type LiveEvaluationCheckpoint,
  parseLiveEvaluationArgs,
  runLiveEvaluation,
} from "../../../scripts/run_openai_live_evaluation.ts";

const SAFETY_IDENTIFIER = "a".repeat(64);
const RECORDED_AT = "2026-07-18T18:50:00.000Z";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

async function assertRejects(
  operation: Promise<unknown>,
  expected: string,
): Promise<void> {
  try {
    await operation;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    assert(message.includes(expected), `unexpected rejection: ${message}`);
    return;
  }
  throw new Error(`expected rejection containing ${expected}`);
}

function fakeResponsesTransport(): {
  create: (request: ResponseRequest) => Promise<ResponseLike>;
  calls: () => number;
} {
  let calls = 0;
  const byQuestion = new Map(
    EVALUATION_SUITE.cases.map((evaluationCase) => [
      evaluationCase.question,
      evaluationCase,
    ]),
  );
  return {
    calls: () => calls,
    create: (request) => {
      calls += 1;
      const input = request.input;
      assert(Array.isArray(input), "evaluation input must be an item array");
      const user = input.findLast((item) =>
        typeof item === "object" && item !== null && "role" in item &&
        item.role === "user"
      ) as { content?: unknown } | undefined;
      assert(typeof user?.content === "string", "evaluation question missing");
      const evaluationCase = byQuestion.get(user.content);
      assert(evaluationCase, "unknown evaluation question");
      const toolOutput = input.findLast((item) =>
        typeof item === "object" && item !== null && "type" in item &&
        item.type === "function_call_output"
      ) as { output?: unknown } | undefined;
      if (!toolOutput) {
        return Promise.resolve({
          status: "completed",
          output: [
            {
              type: "function_call",
              call_id: `call_${evaluationCase.case_id}`,
              name: evaluationCase.expected_tool_call.name,
              arguments: JSON.stringify(
                evaluationCase.expected_tool_call.arguments,
              ),
            },
          ],
        });
      }
      assert(typeof toolOutput.output === "string", "tool output missing");
      const result = JSON.parse(toolOutput.output) as ToolResult;
      const citations = structuredClone(result.citations);
      return Promise.resolve({
        status: "completed",
        output: [],
        output_text: JSON.stringify({
          response_state: evaluationCase.expected_live_response_state,
          summary: result.summary,
          claims: [
            {
              claim_id: "claim_1",
              statement: result.summary,
              evidence_state:
                evaluationCase.expected_live_response_state === "completed"
                  ? "direct"
                  : "unavailable",
              citation_ids: citations.map((citation) => citation.artifact_id),
            },
          ],
          citations,
          limitations: [
            "Synthetic transport fixture only; no model or network call occurred.",
          ],
          tools_used: [evaluationCase.expected_tool_call.name],
        }),
      });
    },
  };
}

Deno.test("live evaluation recorder checkpoints and resumes all 48 cases without repeats", async () => {
  const transport = fakeResponsesTransport();
  let interrupted: LiveEvaluationCheckpoint | undefined;
  await assertRejects(
    runLiveEvaluation({
      runId: "synthetic:live-recorder-test",
      recordedAt: RECORDED_AT,
      safetyIdentifier: SAFETY_IDENTIFIER,
      execution: {
        run_kind: "synthetic_grader_fixture",
        model_invoked: false,
      },
      networkCallsPerResponse: 0,
      createResponse: transport.create,
      onCheckpoint: (checkpoint) => {
        interrupted = checkpoint;
        throw new Error("deliberate interruption after durable checkpoint");
      },
    }),
    "deliberate interruption",
  );
  assert(interrupted?.cases.length === 1, "first case was not checkpointed");
  assert(transport.calls() === 2, "first case used the wrong response count");

  let finalCheckpoint: LiveEvaluationCheckpoint | undefined;
  const trace = await runLiveEvaluation({
    runId: "synthetic:live-recorder-test",
    recordedAt: RECORDED_AT,
    safetyIdentifier: SAFETY_IDENTIFIER,
    execution: {
      run_kind: "synthetic_grader_fixture",
      model_invoked: false,
    },
    networkCallsPerResponse: 0,
    checkpoint: interrupted,
    createResponse: transport.create,
    onCheckpoint: (checkpoint) => {
      finalCheckpoint = checkpoint;
      return Promise.resolve();
    },
  });

  assert(trace.cases.length === 48, "complete trace must contain 48 cases");
  assert(finalCheckpoint?.cases.length === 48, "checkpoint did not complete");
  assert(transport.calls() === 96, "a checkpointed case was repeated");
  assert(trace.execution.network_calls === 0, "synthetic network calls leaked");
  assert(
    trace.execution.model_invoked === false,
    "synthetic model call leaked",
  );
  assert(
    trace.cases.every((row) => row.tool_calls.length === 1),
    "actual tool calls were not retained",
  );
  const { trace_fingerprint: observed, ...payload } = trace;
  assert(
    observed === await sha256Fingerprint(payload as unknown as JsonValue),
    "trace fingerprint is not complete",
  );
});

Deno.test("live evaluation recorder rejects altered checkpoints", async () => {
  const transport = fakeResponsesTransport();
  let checkpoint: LiveEvaluationCheckpoint | undefined;
  await assertRejects(
    runLiveEvaluation({
      runId: "synthetic:checkpoint-mutation-test",
      recordedAt: RECORDED_AT,
      safetyIdentifier: SAFETY_IDENTIFIER,
      execution: {
        run_kind: "synthetic_grader_fixture",
        model_invoked: false,
      },
      networkCallsPerResponse: 0,
      createResponse: transport.create,
      onCheckpoint: (value) => {
        checkpoint = value;
        throw new Error("capture checkpoint");
      },
    }),
    "capture checkpoint",
  );
  assert(checkpoint, "checkpoint was not captured");
  const changed = structuredClone(checkpoint);
  changed.cases[0].response.summary = "changed without refingerprinting";
  await assertRejects(
    runLiveEvaluation({
      runId: "synthetic:checkpoint-mutation-test",
      recordedAt: RECORDED_AT,
      safetyIdentifier: SAFETY_IDENTIFIER,
      execution: {
        run_kind: "synthetic_grader_fixture",
        model_invoked: false,
      },
      networkCallsPerResponse: 0,
      checkpoint: changed,
      createResponse: transport.create,
    }),
    "checkpoint fingerprint mismatch",
  );
});

Deno.test("live evaluation CLI requires explicit confirmation and separate paths", () => {
  assertThrows(
    () =>
      parseLiveEvaluationArgs([
        "--output",
        "trace.json",
        "--checkpoint",
        "checkpoint.json",
      ]),
    "--confirm-live",
  );
  assertThrows(
    () =>
      parseLiveEvaluationArgs([
        "--confirm-live",
        "--output",
        "same.json",
        "--checkpoint",
        "same.json",
      ]),
    "must differ",
  );
  const parsed = parseLiveEvaluationArgs([
    "--confirm-live",
    "--checkpoint",
    "checkpoint.json",
    "--output",
    "trace.json",
  ]);
  assert(parsed.confirmed, "live confirmation was not retained");
  assert(parsed.output === "trace.json", "output path changed");
  assert(parsed.checkpoint === "checkpoint.json", "checkpoint path changed");
});

function assertThrows(operation: () => unknown, expected: string): void {
  try {
    operation();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    assert(message.includes(expected), `unexpected error: ${message}`);
    return;
  }
  throw new Error(`expected error containing ${expected}`);
}
