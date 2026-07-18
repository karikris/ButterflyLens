const textEncoder = new TextEncoder();

export const DEFAULT_B2_SIGNED_URL_TTL_SECONDS = 300;
export const MAXIMUM_B2_SIGNED_URL_TTL_SECONDS = 900;

export class B2SigningError extends Error {}

export type B2SignerConfig = {
  endpoint: string;
  bucket: string;
  accessKeyId: string;
  applicationKey: string;
};

export type B2SignedObject = {
  url: string;
  method: "GET" | "HEAD";
  issuedAt: string;
  expiresAt: string;
  ttlSeconds: number;
};

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join(
    "",
  );
}

export async function sha256Hex(value: string): Promise<string> {
  return bytesToHex(
    new Uint8Array(
      await crypto.subtle.digest("SHA-256", textEncoder.encode(value)),
    ),
  );
}

async function hmacSha256(
  key: Uint8Array,
  value: string,
): Promise<Uint8Array> {
  const keyBuffer = new ArrayBuffer(key.byteLength);
  new Uint8Array(keyBuffer).set(key);
  const imported = await crypto.subtle.importKey(
    "raw",
    keyBuffer,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  return new Uint8Array(
    await crypto.subtle.sign("HMAC", imported, textEncoder.encode(value)),
  );
}

function encodeRfc3986(value: string): string {
  return encodeURIComponent(value).replace(
    /[!'()*]/gu,
    (character) => `%${character.charCodeAt(0).toString(16).toUpperCase()}`,
  );
}

function canonicalObjectPath(bucket: string, objectKey: string): string {
  return `/${encodeRfc3986(bucket)}/${
    objectKey.split("/").map(encodeRfc3986).join("/")
  }`;
}

function validateConfig(config: B2SignerConfig): {
  endpoint: URL;
  region: string;
} {
  let endpoint: URL;
  try {
    endpoint = new URL(config.endpoint);
  } catch {
    throw new B2SigningError("B2 endpoint is invalid");
  }
  const regionMatch = /^s3\.([a-z0-9-]+)\.backblazeb2\.com$/u.exec(
    endpoint.hostname,
  );
  if (
    endpoint.protocol !== "https:" ||
    endpoint.username ||
    endpoint.password ||
    endpoint.port ||
    endpoint.pathname !== "/" ||
    endpoint.search ||
    endpoint.hash ||
    regionMatch === null
  ) {
    throw new B2SigningError(
      "B2 endpoint must be an exact regional HTTPS origin",
    );
  }
  if (
    !/^[a-z0-9][a-z0-9-]{4,48}[a-z0-9]$/u.test(config.bucket) ||
    config.bucket.startsWith("b2-")
  ) {
    throw new B2SigningError("B2 bucket name is invalid");
  }
  if (
    config.accessKeyId.length < 1 ||
    config.accessKeyId.length > 200 ||
    /\s/u.test(config.accessKeyId) ||
    config.applicationKey.length < 1 ||
    config.applicationKey.length > 200 ||
    /\s/u.test(config.applicationKey)
  ) {
    throw new B2SigningError("B2 signing credential shape is invalid");
  }
  return { endpoint, region: regionMatch[1] };
}

function validateObjectKey(objectKey: string): void {
  if (
    objectKey.length < 1 ||
    objectKey.length > 1000 ||
    !objectKey.startsWith("butterflylens/v1/") ||
    objectKey.includes("\\") ||
    objectKey.includes("?") ||
    objectKey.includes("#") ||
    objectKey.split("/").some((part) =>
      part === "" || part === "." || part === ".."
    )
  ) {
    throw new B2SigningError(
      "B2 object key is outside the immutable project prefix",
    );
  }
}

export async function presignB2Object(input: {
  config: B2SignerConfig;
  objectKey: string;
  method: "GET" | "HEAD";
  ttlSeconds?: number;
  now?: Date;
}): Promise<B2SignedObject> {
  const { endpoint, region } = validateConfig(input.config);
  validateObjectKey(input.objectKey);
  if (input.method !== "GET" && input.method !== "HEAD") {
    throw new B2SigningError("B2 signing method is not permitted");
  }
  const ttlSeconds = input.ttlSeconds ?? DEFAULT_B2_SIGNED_URL_TTL_SECONDS;
  if (
    !Number.isInteger(ttlSeconds) ||
    ttlSeconds < 1 ||
    ttlSeconds > MAXIMUM_B2_SIGNED_URL_TTL_SECONDS
  ) {
    throw new B2SigningError(
      "B2 signing TTL must be between 1 and 900 seconds",
    );
  }
  const now = input.now ?? new Date();
  if (!Number.isFinite(now.getTime())) {
    throw new B2SigningError("B2 signing time is invalid");
  }

  const amzDate = now.toISOString().replace(/[:-]|\.\d{3}/gu, "");
  const dateStamp = amzDate.slice(0, 8);
  const credentialScope = `${dateStamp}/${region}/s3/aws4_request`;
  const canonicalUri = canonicalObjectPath(
    input.config.bucket,
    input.objectKey,
  );
  const queryEntries = [
    ["X-Amz-Algorithm", "AWS4-HMAC-SHA256"],
    ["X-Amz-Credential", `${input.config.accessKeyId}/${credentialScope}`],
    ["X-Amz-Date", amzDate],
    ["X-Amz-Expires", String(ttlSeconds)],
    ["X-Amz-SignedHeaders", "host"],
  ].map(([key, value]) => [encodeRfc3986(key), encodeRfc3986(value)] as const)
    .sort(([left], [right]) => left.localeCompare(right));
  const canonicalQuery = queryEntries.map(([key, value]) => `${key}=${value}`)
    .join("&");
  const canonicalHeaders = `host:${endpoint.host}\n`;
  const canonicalRequest = [
    input.method,
    canonicalUri,
    canonicalQuery,
    canonicalHeaders,
    "host",
    "UNSIGNED-PAYLOAD",
  ].join("\n");
  const stringToSign = [
    "AWS4-HMAC-SHA256",
    amzDate,
    credentialScope,
    await sha256Hex(canonicalRequest),
  ].join("\n");

  const dateKey = await hmacSha256(
    textEncoder.encode(`AWS4${input.config.applicationKey}`),
    dateStamp,
  );
  const regionKey = await hmacSha256(dateKey, region);
  const serviceKey = await hmacSha256(regionKey, "s3");
  const signingKey = await hmacSha256(serviceKey, "aws4_request");
  const signature = bytesToHex(await hmacSha256(signingKey, stringToSign));
  const issuedAt = now.toISOString();

  return {
    url:
      `${endpoint.origin}${canonicalUri}?${canonicalQuery}&X-Amz-Signature=${signature}`,
    method: input.method,
    issuedAt,
    expiresAt: new Date(now.getTime() + ttlSeconds * 1000).toISOString(),
    ttlSeconds,
  };
}
