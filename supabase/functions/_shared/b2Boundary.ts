import {
  type B2SignedObject,
  type B2SignerConfig,
  B2SigningError,
  presignB2Object,
  sha256Hex,
} from "./b2Signer.ts";

const MAX_REQUEST_BYTES = 4_096;
const MEDIA_OBJECT_ID = /^[a-z0-9][a-z0-9._:-]{0,159}$/u;

export type AuthorizedB2Object = {
  mediaObjectPk: number;
  projectPk: number;
  mediaObjectId: string;
  storageKey: string;
  contentSha256: string;
  byteCount: number;
  mediaType: string;
};

export type B2SigningReceipt = {
  signingReceiptId: string;
  projectPk: number;
  mediaObjectPk: number;
  authUserId: string;
  method: "GET" | "HEAD";
  ttlSeconds: number;
  issuedAt: string;
  expiresAt: string;
  requestFingerprint: string;
};

function jsonResponse(body: unknown, status = 200): Response {
  return Response.json(body, {
    status,
    headers: {
      "Cache-Control": "no-store",
      "Referrer-Policy": "no-referrer",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

async function readBody(request: Request): Promise<Record<string, unknown>> {
  const declaredLength = Number(request.headers.get("content-length") ?? "0");
  if (Number.isFinite(declaredLength) && declaredLength > MAX_REQUEST_BYTES) {
    throw new B2SigningError("request body exceeds 4096 bytes");
  }
  const text = await request.text();
  if (new TextEncoder().encode(text).length > MAX_REQUEST_BYTES) {
    throw new B2SigningError("request body exceeds 4096 bytes");
  }
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    throw new B2SigningError("request body must be valid JSON");
  }
  if (!isRecord(value)) {
    throw new B2SigningError("request body must be an object");
  }
  return value;
}

function parseRequest(value: Record<string, unknown>): {
  mediaObjectId: string;
  method: "GET" | "HEAD";
  ttlSeconds?: number;
} {
  const keys = Object.keys(value).sort();
  if (
    keys.some((key) =>
      !["media_object_id", "method", "ttl_seconds"].includes(key)
    ) ||
    !keys.includes("media_object_id") ||
    !keys.includes("method") ||
    typeof value.media_object_id !== "string" ||
    !MEDIA_OBJECT_ID.test(value.media_object_id) ||
    (value.method !== "GET" && value.method !== "HEAD") ||
    (value.ttl_seconds !== undefined &&
      (!Number.isInteger(value.ttl_seconds) ||
        Number(value.ttl_seconds) < 1 ||
        Number(value.ttl_seconds) > 900))
  ) {
    throw new B2SigningError("signed-object request is invalid");
  }
  return {
    mediaObjectId: value.media_object_id,
    method: value.method,
    ttlSeconds: value.ttl_seconds === undefined
      ? undefined
      : Number(value.ttl_seconds),
  };
}

export function createB2SigningHandler(dependencies: {
  getConfig: () => B2SignerConfig | null;
  authorize: (mediaObjectId: string) => Promise<AuthorizedB2Object | null>;
  record: (receipt: B2SigningReceipt) => Promise<void>;
  sign?: typeof presignB2Object;
  now?: () => Date;
  uuid?: () => string;
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
      const parsed = parseRequest(await readBody(request));
      const config = dependencies.getConfig();
      if (config === null) {
        return jsonResponse(
          {
            code: "b2_signing_unavailable",
            message: "Private media signing is not configured.",
          },
          503,
        );
      }
      const media = await dependencies.authorize(parsed.mediaObjectId);
      if (media === null) {
        return jsonResponse(
          {
            code: "media_unavailable",
            message: "Authorized media is unavailable.",
          },
          404,
        );
      }
      const signingReceiptId = `b2sign:${
        (dependencies.uuid ?? crypto.randomUUID)()
      }`;
      const signed: B2SignedObject =
        await (dependencies.sign ?? presignB2Object)({
          config,
          objectKey: media.storageKey,
          method: parsed.method,
          ttlSeconds: parsed.ttlSeconds,
          now: (dependencies.now ?? (() => new Date()))(),
        });
      const requestFingerprint = await sha256Hex([
        "butterflylens-b2-signing-request:v1",
        signingReceiptId,
        subject,
        media.mediaObjectId,
        signed.method,
        signed.issuedAt,
        String(signed.ttlSeconds),
      ].join("\n"));
      await dependencies.record({
        signingReceiptId,
        projectPk: media.projectPk,
        mediaObjectPk: media.mediaObjectPk,
        authUserId: subject,
        method: signed.method,
        ttlSeconds: signed.ttlSeconds,
        issuedAt: signed.issuedAt,
        expiresAt: signed.expiresAt,
        requestFingerprint,
      });
      return jsonResponse({
        schema_version: "butterflylens-b2-signed-url:v1.0.0",
        media_object_id: media.mediaObjectId,
        method: signed.method,
        expires_at: signed.expiresAt,
        content_sha256: media.contentSha256,
        byte_count: media.byteCount,
        media_type: media.mediaType,
        url: signed.url,
      });
    } catch (error) {
      if (error instanceof B2SigningError) {
        return jsonResponse(
          { code: "invalid_request", message: error.message },
          400,
        );
      }
      return jsonResponse(
        {
          code: "b2_signing_incomplete",
          message: "Private media signing failed closed.",
        },
        503,
      );
    }
  };
}
