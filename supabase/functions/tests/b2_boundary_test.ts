import {
  type AuthorizedB2Object,
  type B2SigningReceipt,
  createB2SigningHandler,
} from "../_shared/b2Boundary.ts";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

async function body(response: Response): Promise<Record<string, unknown>> {
  return await response.json() as Record<string, unknown>;
}

function request(value: unknown): Request {
  return new Request("http://127.0.0.1/functions/v1/sign-b2-object", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(value),
  });
}

const MEDIA: AuthorizedB2Object = {
  mediaObjectPk: 11,
  projectPk: 12,
  mediaObjectId: "media:test",
  storageKey: `butterflylens/v1/projects/test/runs/test/review-media/test/aa/${
    "f".repeat(64)
  }.jpg`,
  contentSha256: "f".repeat(64),
  byteCount: 1200,
  mediaType: "image/jpeg",
};

function dependencies(overrides: Record<string, unknown> = {}) {
  return {
    getConfig: () => ({
      endpoint: "https://s3.us-west-004.backblazeb2.com",
      bucket: "butterflylens-private-test",
      accessKeyId: "test-id",
      applicationKey: "test-secret",
    }),
    authorize: async () => MEDIA,
    record: async (_receipt: B2SigningReceipt) => {},
    sign: async () => ({
      url:
        "https://s3.us-west-004.backblazeb2.com/private?X-Amz-Signature=test",
      method: "GET" as const,
      issuedAt: "2026-07-18T08:00:00.000Z",
      expiresAt: "2026-07-18T08:05:00.000Z",
      ttlSeconds: 300,
    }),
    uuid: () => "00000000-0000-4000-8000-000000000001",
    ...overrides,
  };
}

Deno.test("B2 boundary rejects non-POST and missing identity", async () => {
  let authorized = false;
  const handler = createB2SigningHandler(dependencies({
    authorize: async () => {
      authorized = true;
      return MEDIA;
    },
  }));
  const method = await handler(
    new Request("http://127.0.0.1/functions/v1/sign-b2-object"),
    "user",
  );
  const identity = await handler(
    request({ media_object_id: "media:test", method: "GET" }),
    null,
  );
  assert(method.status === 405, "non-POST request was accepted");
  assert(identity.status === 401, "missing identity was accepted");
  assert(!authorized, "authorization ran before request gates");
});

Deno.test("B2 boundary rejects permissive or oversized inputs", async () => {
  const handler = createB2SigningHandler(dependencies());
  for (
    const value of [
      { media_object_id: "media:test", method: "PUT" },
      { media_object_id: "media:test", method: "GET", ttl_seconds: 901 },
      { media_object_id: "media:test", method: "GET", extra: true },
    ]
  ) {
    assert(
      (await handler(request(value), "user")).status === 400,
      "unsafe input was accepted",
    );
  }
  const oversized = request({ media_object_id: "media:test", method: "GET" });
  oversized.headers.set("Content-Length", "4097");
  assert(
    (await handler(oversized, "user")).status === 400,
    "oversized body was accepted",
  );
});

Deno.test("B2 boundary fails closed when configuration or rights are absent", async () => {
  const missingConfig = createB2SigningHandler(
    dependencies({ getConfig: () => null }),
  );
  const missingRights = createB2SigningHandler(
    dependencies({ authorize: async () => null }),
  );
  assert(
    (await missingConfig(
      request({ media_object_id: "media:test", method: "GET" }),
      "user",
    )).status === 503,
    "missing configuration did not fail closed",
  );
  assert(
    (await missingRights(
      request({ media_object_id: "media:test", method: "GET" }),
      "user",
    )).status === 404,
    "unavailable rights did not fail closed",
  );
});

Deno.test("B2 boundary records a URL-free receipt before returning signed access", async () => {
  const receipts: B2SigningReceipt[] = [];
  const handler = createB2SigningHandler(dependencies({
    record: async (receipt: B2SigningReceipt) => receipts.push(receipt),
  }));
  const response = await handler(
    request({ media_object_id: "media:test", method: "GET", ttl_seconds: 300 }),
    "auth-user",
  );
  const payload = await body(response);
  assert(response.status === 200, "authorized signing failed");
  assert(
    response.headers.get("Cache-Control") === "no-store",
    "signed URL can be cached",
  );
  assert(
    response.headers.get("Referrer-Policy") === "no-referrer",
    "referrer policy is missing",
  );
  assert(
    String(payload.url).includes("X-Amz-Signature"),
    "signed URL is missing",
  );
  assert(receipts.length === 1, "receipt was not recorded exactly once");
  assert(
    receipts[0]?.authUserId === "auth-user",
    "verified subject was not audited",
  );
  assert(
    !JSON.stringify(receipts[0]).includes("X-Amz"),
    "signed URL leaked into receipt",
  );
  assert(
    !JSON.stringify(receipts[0]).includes(MEDIA.storageKey),
    "storage key leaked into receipt",
  );
  assert(
    /^[0-9a-f]{64}$/u.test(receipts[0]?.requestFingerprint ?? ""),
    "receipt is not fingerprinted",
  );
});

Deno.test("B2 boundary never returns an unaudited signed URL", async () => {
  const handler = createB2SigningHandler(dependencies({
    record: async () => {
      throw new Error("private database detail");
    },
  }));
  const response = await handler(
    request({ media_object_id: "media:test", method: "GET" }),
    "auth-user",
  );
  const payload = await body(response);
  assert(response.status === 503, "audit failure was accepted");
  assert(
    !JSON.stringify(payload).includes("X-Amz"),
    "signed URL leaked after audit failure",
  );
  assert(
    !JSON.stringify(payload).includes("database detail"),
    "private error leaked",
  );
});
