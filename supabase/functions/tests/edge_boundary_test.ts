import {
  createAskButterflyLensHandler,
  type EdgeAnalystRunner,
} from "../_shared/edgeBoundary.ts";
import type { AnalystResponse } from "../_shared/analyst.ts";

const RESPONSE: AnalystResponse = {
  schema_version: "butterflylens-analyst-response:v1.0.0",
  mode: "live",
  response_state: "incomplete",
  summary: "No unsupported answer was returned.",
  claims: [],
  citations: [],
  limitations: ["Evidence is unavailable."],
  tools_used: [],
  model: { id: "gpt-5.6-sol", reasoning_effort: "xhigh" },
  usage: { response_calls: 1, tool_calls: 0, budget_state: "within_budget" },
};

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

async function body(response: Response): Promise<Record<string, unknown>> {
  return await response.json() as Record<string, unknown>;
}

function request(value: unknown, headers: HeadersInit = {}): Request {
  return new Request("http://127.0.0.1/functions/v1/ask-butterflylens", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(value),
  });
}

Deno.test("Edge boundary rejects non-POST methods", async () => {
  let called = false;
  const handler = createAskButterflyLensHandler({
    getOpenAiApiKey: () => "server-secret",
    run: async () => {
      called = true;
      return RESPONSE;
    },
  });
  const response = await handler(
    new Request("http://127.0.0.1/functions/v1/ask-butterflylens"),
    { subject: "user" },
  );
  assert(response.status === 405, "non-POST method was accepted");
  assert(!called, "analyst ran for non-POST method");
});

Deno.test("Edge boundary makes no model call without the server secret", async () => {
  let called = false;
  const handler = createAskButterflyLensHandler({
    getOpenAiApiKey: () => undefined,
    run: async () => {
      called = true;
      return RESPONSE;
    },
  });
  const response = await handler(
    request({ question: "Question?", history: [] }),
    {
      subject: "user",
    },
  );
  assert(response.status === 503, "missing secret did not fail closed");
  assert(!called, "analyst ran without the server secret");
  assert(
    String((await body(response)).message).includes("No model call"),
    "missing-secret message changed",
  );
});

Deno.test("Edge boundary requires the verified auth subject", async () => {
  let called = false;
  const handler = createAskButterflyLensHandler({
    getOpenAiApiKey: () => "server-secret",
    run: async () => {
      called = true;
      return RESPONSE;
    },
  });
  const response = await handler(
    request({ question: "Question?", history: [] }),
    {
      subject: null,
    },
  );
  assert(response.status === 401, "missing auth subject was accepted");
  assert(!called, "analyst ran without an auth subject");
});

Deno.test("Edge boundary rejects malformed and oversized request bodies", async () => {
  const handler = createAskButterflyLensHandler({
    getOpenAiApiKey: () => "server-secret",
    run: async () => RESPONSE,
  });
  const malformed = await handler(
    new Request("http://127.0.0.1/functions/v1/ask-butterflylens", {
      method: "POST",
      body: "{",
    }),
    { subject: "user" },
  );
  assert(malformed.status === 400, "malformed JSON was accepted");
  const oversized = await handler(
    request({ question: "Question?", history: [] }, {
      "Content-Length": "32769",
    }),
    { subject: "user" },
  );
  assert(oversized.status === 400, "oversized body was accepted");
});

Deno.test("Edge boundary hashes identity and returns no-store structured output", async () => {
  const observations: Parameters<EdgeAnalystRunner>[0][] = [];
  const handler = createAskButterflyLensHandler({
    getOpenAiApiKey: () => "server-secret",
    run: async (input) => {
      observations.push(input);
      return RESPONSE;
    },
  });
  const response = await handler(
    request({ question: "  Question?  ", history: [] }),
    { subject: "auth-user-123" },
  );
  assert(response.status === 200, "valid request failed");
  assert(
    response.headers.get("Cache-Control") === "no-store",
    "response can be cached",
  );
  assert(
    response.headers.get("X-Content-Type-Options") === "nosniff",
    "nosniff is missing",
  );
  assert(
    observations[0]?.apiKey === "server-secret",
    "internal secret did not reach runner",
  );
  assert(
    observations[0]?.request.question === "Question?",
    "question was not normalized",
  );
  assert(
    /^[0-9a-f]{64}$/u.test(observations[0]?.safetyIdentifier ?? ""),
    "safety ID is not hashed",
  );
  assert(
    observations[0]?.safetyIdentifier !== "auth-user-123",
    "raw subject became safety ID",
  );
  assert((await body(response)).mode === "live", "live mode was not returned");
});

Deno.test("Edge boundary sanitizes unexpected runner failures", async () => {
  const handler = createAskButterflyLensHandler({
    getOpenAiApiKey: () => "server-secret",
    run: async () => {
      throw new Error("private runner and secret detail");
    },
  });
  const response = await handler(
    request({ question: "Question?", history: [] }),
    {
      subject: "user",
    },
  );
  const payload = await body(response);
  assert(response.status === 502, "unexpected failure status changed");
  assert(
    !JSON.stringify(payload).includes("private runner"),
    "private failure leaked",
  );
});
