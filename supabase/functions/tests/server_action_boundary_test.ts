import {
  createServerActionHandler,
  hashServerActionRequest,
  ServerActionConflictError,
  ServerActionForbiddenError,
  type ServerActionReceipt,
} from "../_shared/serverActionBoundary.ts";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

async function body(response: Response): Promise<Record<string, unknown>> {
  return await response.json() as Record<string, unknown>;
}

function request(value: unknown): Request {
  return new Request("http://127.0.0.1/functions/v1/control-butterflylens", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(value),
  });
}

const INPUT = {
  server_action_id: "action:test-pause",
  run_id: "run:test",
  action: "pause_run",
  expected_revision: 3,
};
const RECEIPT: ServerActionReceipt = {
  server_action_id: "action:test-pause",
  action: "pause_run",
  prior_status: "running",
  result_status: "paused",
  result_revision: 4,
  applied_at: "2026-07-18T08:00:00.000Z",
  request_fingerprint: "f".repeat(64),
};

function dependencies(overrides: Record<string, unknown> = {}) {
  return {
    lookupRun: async () => ({ runPk: 1, projectPk: 2, runId: "run:test" }),
    apply: async () => RECEIPT,
    ...overrides,
  };
}

Deno.test("server action boundary rejects method, identity, and open inputs", async () => {
  let lookedUp = false;
  const handler = createServerActionHandler(dependencies({
    lookupRun: async () => {
      lookedUp = true;
      return { runPk: 1, projectPk: 2, runId: "run:test" };
    },
  }));
  assert(
    (await handler(new Request("http://127.0.0.1/control"), "user")).status ===
      405,
    "non-POST request was accepted",
  );
  assert(
    (await handler(request(INPUT), null)).status === 401,
    "missing identity was accepted",
  );
  assert(
    (await handler(request({ ...INPUT, action: "delete_run" }), "user"))
      .status === 400,
    "open action was accepted",
  );
  assert(
    (await handler(request({ ...INPUT, extra: "value" }), "user")).status ===
      400,
    "extra input was accepted",
  );
  assert(!lookedUp, "run lookup happened before request validation");
});

Deno.test("server action request fingerprints bind actor and expected revision", async () => {
  const first = await hashServerActionRequest({
    subject: "user-one",
    serverActionId: "action:test-pause",
    runId: "run:test",
    action: "pause_run",
    expectedRevision: 3,
  });
  const repeated = await hashServerActionRequest({
    subject: "user-one",
    serverActionId: "action:test-pause",
    runId: "run:test",
    action: "pause_run",
    expectedRevision: 3,
  });
  const changed = await hashServerActionRequest({
    subject: "user-one",
    serverActionId: "action:test-pause",
    runId: "run:test",
    action: "pause_run",
    expectedRevision: 4,
  });
  assert(first === repeated, "request fingerprint is not deterministic");
  assert(first !== changed, "expected revision is not fingerprinted");
  assert(/^[0-9a-f]{64}$/u.test(first), "request fingerprint shape changed");
});

Deno.test("server action boundary requires caller-scoped run visibility", async () => {
  let applied = false;
  const handler = createServerActionHandler(dependencies({
    lookupRun: async () => null,
    apply: async () => {
      applied = true;
      return RECEIPT;
    },
  }));
  const response = await handler(request(INPUT), "user");
  assert(response.status === 404, "unavailable run was exposed");
  assert(!applied, "action ran without caller-scoped visibility");
});

Deno.test("server action boundary returns the atomic receipt", async () => {
  const applied: unknown[] = [];
  const handler = createServerActionHandler(dependencies({
    apply: async (value: unknown) => {
      applied.push(value);
      return RECEIPT;
    },
  }));
  const response = await handler(request(INPUT), "user-one");
  const payload = await body(response);
  assert(response.status === 200, "valid controlled action failed");
  assert(payload.result_status === "paused", "result state changed");
  assert(payload.result_revision === 4, "result revision changed");
  assert(applied.length === 1, "action was not applied exactly once");
  assert(
    !JSON.stringify(payload).includes("user-one"),
    "auth identity leaked in response",
  );
});

Deno.test("server action boundary maps authority and revision failures safely", async () => {
  const forbidden = createServerActionHandler(dependencies({
    apply: async () => {
      throw new ServerActionForbiddenError("private role detail");
    },
  }));
  const conflict = createServerActionHandler(dependencies({
    apply: async () => {
      throw new ServerActionConflictError("private revision detail");
    },
  }));
  const forbiddenResponse = await forbidden(request(INPUT), "user");
  const conflictResponse = await conflict(request(INPUT), "user");
  assert(forbiddenResponse.status === 403, "authority failure status changed");
  assert(conflictResponse.status === 409, "revision failure status changed");
  assert(
    !JSON.stringify(await body(forbiddenResponse)).includes("private"),
    "authority detail leaked",
  );
  assert(
    !JSON.stringify(await body(conflictResponse)).includes("private"),
    "revision detail leaked",
  );
});
