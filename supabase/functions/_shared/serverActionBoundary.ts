import { sha256Hex } from "./b2Signer.ts";

const MAX_REQUEST_BYTES = 4_096;
const STABLE_ID = /^[a-z0-9][a-z0-9._:-]{0,159}$/u;
const ACTIONS = ["pause_run", "resume_run", "cancel_run"] as const;

export class ServerActionConflictError extends Error {}
export class ServerActionForbiddenError extends Error {}
export class ServerActionInputError extends Error {}

export type ServerAction = typeof ACTIONS[number];
export type AuthorizedRun = {
  runPk: number;
  projectPk: number;
  runId: string;
};
export type ServerActionReceipt = {
  server_action_id: string;
  action: ServerAction;
  prior_status: string;
  result_status: string;
  result_revision: number;
  applied_at: string;
  request_fingerprint: string;
};

function jsonResponse(body: unknown, status = 200): Response {
  return Response.json(body, {
    status,
    headers: {
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

async function parseRequest(request: Request): Promise<{
  serverActionId: string;
  runId: string;
  action: ServerAction;
  expectedRevision: number;
}> {
  const declaredLength = Number(request.headers.get("content-length") ?? "0");
  if (Number.isFinite(declaredLength) && declaredLength > MAX_REQUEST_BYTES) {
    throw new ServerActionInputError("request body exceeds 4096 bytes");
  }
  const text = await request.text();
  if (new TextEncoder().encode(text).length > MAX_REQUEST_BYTES) {
    throw new ServerActionInputError("request body exceeds 4096 bytes");
  }
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    throw new ServerActionInputError("request body must be valid JSON");
  }
  if (!isRecord(value)) {
    throw new ServerActionInputError("request body must be an object");
  }
  const keys = Object.keys(value).sort();
  if (
    keys.join(",") !== "action,expected_revision,run_id,server_action_id" ||
    typeof value.server_action_id !== "string" ||
    !STABLE_ID.test(value.server_action_id) ||
    typeof value.run_id !== "string" ||
    !STABLE_ID.test(value.run_id) ||
    !ACTIONS.includes(value.action as ServerAction) ||
    !Number.isSafeInteger(value.expected_revision) ||
    Number(value.expected_revision) < 1
  ) {
    throw new ServerActionInputError("controlled server action is invalid");
  }
  return {
    serverActionId: value.server_action_id,
    runId: value.run_id,
    action: value.action as ServerAction,
    expectedRevision: Number(value.expected_revision),
  };
}

export async function hashServerActionRequest(input: {
  subject: string;
  serverActionId: string;
  runId: string;
  action: ServerAction;
  expectedRevision: number;
}): Promise<string> {
  return await sha256Hex([
    "butterflylens-controlled-server-action:v1",
    input.subject,
    input.serverActionId,
    input.runId,
    input.action,
    String(input.expectedRevision),
  ].join("\n"));
}

export function createServerActionHandler(dependencies: {
  lookupRun: (runId: string) => Promise<AuthorizedRun | null>;
  apply: (input: {
    run: AuthorizedRun;
    subject: string;
    serverActionId: string;
    action: ServerAction;
    expectedRevision: number;
    requestFingerprint: string;
  }) => Promise<ServerActionReceipt>;
}): (request: Request, subject: unknown) => Promise<Response> {
  return async (request, subject) => {
    if (request.method !== "POST") {
      return jsonResponse(
        { code: "method_not_allowed", message: "Use POST." },
        405,
      );
    }
    if (typeof subject !== "string" || !subject) {
      return jsonResponse(
        { code: "unauthorized", message: "A verified user is required." },
        401,
      );
    }
    try {
      const parsed = await parseRequest(request);
      const run = await dependencies.lookupRun(parsed.runId);
      if (run === null) {
        return jsonResponse(
          {
            code: "run_unavailable",
            message: "Authorized run is unavailable.",
          },
          404,
        );
      }
      const requestFingerprint = await hashServerActionRequest({
        subject,
        ...parsed,
      });
      const receipt = await dependencies.apply({
        run,
        subject,
        ...parsed,
        requestFingerprint,
      });
      return jsonResponse({
        schema_version: "butterflylens-server-action-receipt:v1.0.0",
        server_action_id: receipt.server_action_id,
        run_id: run.runId,
        action: receipt.action,
        prior_status: receipt.prior_status,
        result_status: receipt.result_status,
        result_revision: receipt.result_revision,
        applied_at: receipt.applied_at,
        request_fingerprint: receipt.request_fingerprint,
      });
    } catch (error) {
      if (error instanceof ServerActionInputError) {
        return jsonResponse(
          { code: "invalid_request", message: error.message },
          400,
        );
      }
      if (error instanceof ServerActionForbiddenError) {
        return jsonResponse(
          { code: "forbidden", message: "Run-control authority is required." },
          403,
        );
      }
      if (error instanceof ServerActionConflictError) {
        return jsonResponse(
          {
            code: "action_conflict",
            message: "Run state or action ID has changed.",
          },
          409,
        );
      }
      return jsonResponse(
        {
          code: "server_action_incomplete",
          message: "Server action failed closed.",
        },
        503,
      );
    }
  };
}
