import { B2SigningError, presignB2Object } from "../_shared/b2Signer.ts";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

const CONFIG = {
  endpoint: "https://s3.us-west-004.backblazeb2.com",
  bucket: "butterflylens-private-test",
  accessKeyId: "test-key-id",
  applicationKey: "test-application-key",
};
const OBJECT_KEY =
  `butterflylens/v1/projects/project-one/runs/run-one/review-media/campaign/aa/${
    "f".repeat(64)
  }.jpg`;

Deno.test("B2 signer emits deterministic bounded SigV4 query", async () => {
  const signed = await presignB2Object({
    config: CONFIG,
    objectKey: OBJECT_KEY,
    method: "GET",
    ttlSeconds: 300,
    now: new Date("2026-07-18T08:00:00.000Z"),
  });
  const url = new URL(signed.url);
  assert(url.protocol === "https:", "signed URL is not HTTPS");
  assert(
    url.hostname === "s3.us-west-004.backblazeb2.com",
    "signed URL changed host",
  );
  assert(url.pathname.endsWith(`${"f".repeat(64)}.jpg`), "object path changed");
  assert(
    url.searchParams.get("X-Amz-Algorithm") === "AWS4-HMAC-SHA256",
    "algorithm changed",
  );
  assert(
    url.searchParams.get("X-Amz-Date") === "20260718T080000Z",
    "date changed",
  );
  assert(url.searchParams.get("X-Amz-Expires") === "300", "TTL changed");
  assert(
    url.searchParams.get("X-Amz-SignedHeaders") === "host",
    "signed headers changed",
  );
  assert(
    url.searchParams.get("X-Amz-Credential") ===
      "test-key-id/20260718/us-west-004/s3/aws4_request",
    "credential scope changed",
  );
  assert(
    url.searchParams.get("X-Amz-Signature") ===
      "efd02fd31a4d36d30f5b4edd8c96c7465f910530acd283e272ba7dd085ab84be",
    "independent SigV4 test vector changed",
  );
  assert(signed.issuedAt === "2026-07-18T08:00:00.000Z", "issued time changed");
  assert(signed.expiresAt === "2026-07-18T08:05:00.000Z", "expiry changed");
});

Deno.test("B2 signer separates GET and HEAD signatures", async () => {
  const get = await presignB2Object({
    config: CONFIG,
    objectKey: OBJECT_KEY,
    method: "GET",
    now: new Date("2026-07-18T08:00:00.000Z"),
  });
  const head = await presignB2Object({
    config: CONFIG,
    objectKey: OBJECT_KEY,
    method: "HEAD",
    now: new Date("2026-07-18T08:00:00.000Z"),
  });
  assert(get.url !== head.url, "HTTP method is not bound into the signature");
  assert(head.method === "HEAD", "HEAD method changed");
});

Deno.test("B2 signer rejects endpoints, keys, and TTLs outside policy", async () => {
  for (
    const attempt of [
      () =>
        presignB2Object({
          ...base(),
          config: { ...CONFIG, endpoint: "http://example.test" },
        }),
      () => presignB2Object({ ...base(), objectKey: "../private.jpg" }),
      () =>
        presignB2Object({
          ...base(),
          objectKey: "butterflylens/v1/a/../private.jpg",
        }),
      () => presignB2Object({ ...base(), ttlSeconds: 901 }),
    ]
  ) {
    let rejected = false;
    try {
      await attempt();
    } catch (error) {
      rejected = error instanceof B2SigningError;
    }
    assert(rejected, "unsafe B2 signing input was accepted");
  }
});

function base() {
  return {
    config: CONFIG,
    objectKey: OBJECT_KEY,
    method: "GET" as const,
    now: new Date("2026-07-18T08:00:00.000Z"),
  };
}
