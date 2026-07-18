import {
  createPublicMonitoringHandler,
  type PublicMonitoringRow,
} from "../_shared/monitoringBoundary.ts";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

const ORIGIN = "https://karikris.github.io";
const ENDPOINT = "https://example.supabase.co/functions/v1/operations-status";
const ROW: PublicMonitoringRow = {
  observed_at: "2026-07-18T09:00:00+00:00",
  heartbeat_state: "available",
  heartbeat_observed_at: "2026-07-18T08:59:45+00:00",
  worker_state: "running",
  heartbeat_reason: "A fresh governed heartbeat is available.",
  api_budget_state: "available",
  api_budget_limit: 1000,
  api_budget_used: 240,
  api_budget_remaining: 760,
  api_budget_resets_at: "2026-07-19T00:00:00+00:00",
  api_budget_reason: "A governed aggregate request budget is available.",
  stage_health_state: "degraded",
  current_stage: "metadata",
  stage_state: "running",
  healthy_stage_count: 11,
  failed_stage_count: 1,
  stage_health_reason: "One stage failure is retained for investigation.",
  queue_state: "available",
  queue_depth: 12,
  queue_capacity: 512,
  queue_reason: "Aggregate queue occupancy is available.",
  failure_state: "degraded",
  failure_count: 1,
  failure_reason: "One terminal stage failure is recorded.",
  artifact_state: "available",
  artifact_fingerprint: "a".repeat(64),
  artifact_committed_at: "2026-07-18T08:58:00+00:00",
  artifact_reason: "Latest immutable artifact fingerprint.",
  map_state: "available",
  map_fingerprint: "b".repeat(64),
  map_refreshed_at: "2026-07-18T08:57:00+00:00",
  map_reason: "Latest governed map refresh fingerprint.",
  model_state: "unfinished",
  yoloe_state: "unfinished",
  bioclip_state: "unfinished",
  model_reason: "YOLOE and BioCLIP are explicitly unfinished in this goal.",
  resource_state: "available",
  free_disk_bytes: 500_000_000_000,
  process_rss_bytes: 2_000_000_000,
  memory_capacity_bytes: 32_000_000_000,
  mps_allocated_bytes: null,
  mps_reserved_bytes: null,
  resource_reason: "Bounded worker resource counters are available.",
  scientific_claim_allowed: false,
};

function handler(overrides: Record<string, unknown> = {}) {
  return createPublicMonitoringHandler({
    projectId: "project:butterflylens-australia",
    allowedOrigin: ORIGIN,
    lookupLatest: async () => ROW,
    ...overrides,
  });
}

Deno.test("public monitoring rejects methods, query input, and foreign origins", async () => {
  const serve = handler();
  const post = await serve(new Request(ENDPOINT, { method: "POST" }));
  const query = await serve(new Request(`${ENDPOINT}?project=private`));
  const origin = await serve(
    new Request(ENDPOINT, {
      headers: { Origin: "https://attacker.example" },
    }),
  );
  assert(post.status === 405, "POST monitoring request was accepted");
  assert(
    post.headers.get("Allow") === "GET, OPTIONS",
    "Allow boundary changed",
  );
  assert(query.status === 400, "query input was accepted");
  assert(origin.status === 403, "foreign browser origin was accepted");
  assert(
    origin.headers.get("Access-Control-Allow-Origin") === null,
    "foreign origin received CORS authority",
  );
});

Deno.test("public monitoring preflight allows only the configured GET origin", async () => {
  const serve = handler();
  const accepted = await serve(
    new Request(ENDPOINT, {
      method: "OPTIONS",
      headers: {
        Origin: ORIGIN,
        "Access-Control-Request-Method": "GET",
      },
    }),
  );
  const denied = await serve(
    new Request(ENDPOINT, {
      method: "OPTIONS",
      headers: {
        Origin: ORIGIN,
        "Access-Control-Request-Method": "POST",
      },
    }),
  );
  assert(accepted.status === 204, "valid monitoring preflight failed");
  assert(
    accepted.headers.get("Access-Control-Allow-Origin") === ORIGIN,
    "exact origin was not returned",
  );
  assert(denied.status === 403, "invalid preflight method was accepted");
});

Deno.test("public monitoring returns the exact privacy-safe aggregate", async () => {
  let projectId = "";
  const serve = handler({
    lookupLatest: async (value: string) => {
      projectId = value;
      return ROW;
    },
  });
  const response = await serve(
    new Request(ENDPOINT, { headers: { Origin: ORIGIN } }),
  );
  const payload = await response.json() as Record<string, unknown>;
  const serialized = JSON.stringify(payload);
  assert(response.status === 200, "valid monitoring request failed");
  assert(
    projectId === "project:butterflylens-australia",
    "configured project changed",
  );
  assert(
    payload.schemaVersion === "butterflylens-public-monitoring:v1.0.0",
    "schema changed",
  );
  assert(payload.snapshotMode === "live", "live snapshot label changed");
  assert(
    payload.observedAt === "2026-07-18T09:00:00.000Z",
    "UTC was not canonicalized",
  );
  assert(
    payload.scientificClaimAllowed === false,
    "scientific boundary changed",
  );
  assert(
    response.headers.get("Cache-Control")?.includes("no-store"),
    "status was cacheable",
  );
  for (
    const forbidden of [
      "worker_heartbeat_pk",
      "project_pk",
      "run_pk",
      "machine_fingerprint",
      "storage_key",
      "error_message",
      "coordinates",
    ]
  ) assert(!serialized.includes(forbidden), `${forbidden} leaked`);
});

Deno.test("public monitoring reports absent state without fabricating zeroes", async () => {
  const response = await handler({ lookupLatest: async () => null })(
    new Request(ENDPOINT),
  );
  const payload = await response.json() as Record<string, unknown>;
  assert(response.status === 404, "absent monitoring did not return 404");
  assert(payload.error === "monitoring_unavailable", "absent error changed");
  assert(
    !JSON.stringify(payload).includes(":0"),
    "absent state fabricated zero",
  );
});

Deno.test("public monitoring fails closed on configuration and storage errors", async () => {
  let lookedUp = false;
  const unconfigured = handler({
    projectId: null,
    lookupLatest: async () => {
      lookedUp = true;
      return ROW;
    },
  });
  const broken = handler({
    lookupLatest: async () => {
      throw new Error("private database topology");
    },
  });
  const unconfiguredResponse = await unconfigured(new Request(ENDPOINT));
  const brokenResponse = await broken(new Request(ENDPOINT));
  assert(unconfiguredResponse.status === 503, "missing config was accepted");
  assert(!lookedUp, "storage was queried before configuration validation");
  assert(brokenResponse.status === 503, "storage failure status changed");
  assert(
    !JSON.stringify(await brokenResponse.json()).includes("topology"),
    "private storage error leaked",
  );
});

Deno.test("public monitoring refuses a row that grants scientific authority", async () => {
  const unsafe = {
    ...ROW,
    scientific_claim_allowed: true,
  } as unknown as PublicMonitoringRow;
  const response = await handler({ lookupLatest: async () => unsafe })(
    new Request(ENDPOINT),
  );
  assert(response.status === 503, "scientifically unsafe row was returned");
});
