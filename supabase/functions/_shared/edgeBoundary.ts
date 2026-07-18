import {
  AnalystInputError,
  type AnalystRequest,
  type AnalystResponse,
  hashSafetyIdentifier,
  parseAnalystRequest,
} from "./analyst.ts";

const MAX_REQUEST_BYTES = 32_768;

export type EdgeAnalystRunner = (input: {
  apiKey: string;
  request: AnalystRequest;
  safetyIdentifier: string;
}) => Promise<AnalystResponse>;

export type EdgeAuthContext = {
  subject: unknown;
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

async function readRequestBody(request: Request): Promise<unknown> {
  const declaredLength = Number(request.headers.get("content-length") ?? "0");
  if (Number.isFinite(declaredLength) && declaredLength > MAX_REQUEST_BYTES) {
    throw new AnalystInputError("request body exceeds 32768 bytes");
  }
  const text = await request.text();
  if (new TextEncoder().encode(text).length > MAX_REQUEST_BYTES) {
    throw new AnalystInputError("request body exceeds 32768 bytes");
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new AnalystInputError("request body must be valid JSON");
  }
}

export function createAskButterflyLensHandler(dependencies: {
  getOpenAiApiKey: () => string | undefined;
  run: EdgeAnalystRunner;
}): (request: Request, context: EdgeAuthContext) => Promise<Response> {
  return async (request, context) => {
    if (request.method !== "POST") {
      return jsonResponse(
        { code: "method_not_allowed", message: "Use POST." },
        405,
      );
    }
    const apiKey = dependencies.getOpenAiApiKey();
    if (!apiKey) {
      return jsonResponse(
        {
          code: "live_analyst_unavailable",
          message:
            "The live analyst is not configured. No model call was made.",
        },
        503,
      );
    }
    if (typeof context.subject !== "string" || !context.subject) {
      return jsonResponse(
        { code: "unauthorized", message: "A verified user is required." },
        401,
      );
    }
    try {
      const analystRequest = parseAnalystRequest(
        await readRequestBody(request),
      );
      const safetyIdentifier = await hashSafetyIdentifier(context.subject);
      return jsonResponse(
        await dependencies.run({
          apiKey,
          request: analystRequest,
          safetyIdentifier,
        }),
      );
    } catch (error) {
      if (error instanceof AnalystInputError) {
        return jsonResponse(
          { code: "invalid_request", message: error.message },
          400,
        );
      }
      return jsonResponse(
        {
          code: "analyst_incomplete",
          message:
            "The analyst failed closed. No unsupported answer was returned.",
        },
        502,
      );
    }
  };
}
