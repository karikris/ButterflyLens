export type PublicMonitoringRow = {
  observed_at: string;
  heartbeat_state: string;
  heartbeat_observed_at: string | null;
  worker_state: string | null;
  heartbeat_reason: string;
  api_budget_state: string;
  api_budget_limit: number | null;
  api_budget_used: number | null;
  api_budget_remaining: number | null;
  api_budget_resets_at: string | null;
  api_budget_reason: string;
  stage_health_state: string;
  current_stage: string | null;
  stage_state: string | null;
  healthy_stage_count: number | null;
  failed_stage_count: number | null;
  stage_health_reason: string;
  queue_state: string;
  queue_depth: number | null;
  queue_capacity: number | null;
  queue_reason: string;
  failure_state: string;
  failure_count: number | null;
  failure_reason: string;
  artifact_state: string;
  artifact_fingerprint: string | null;
  artifact_committed_at: string | null;
  artifact_reason: string;
  map_state: string;
  map_fingerprint: string | null;
  map_refreshed_at: string | null;
  map_reason: string;
  model_state: string;
  yoloe_state: string;
  bioclip_state: string;
  model_reason: string;
  resource_state: string;
  free_disk_bytes: number | null;
  process_rss_bytes: number | null;
  memory_capacity_bytes: number | null;
  mps_allocated_bytes: number | null;
  mps_reserved_bytes: number | null;
  resource_reason: string;
  scientific_claim_allowed: false;
};

type MonitoringDependencies = {
  projectId: string | null;
  allowedOrigin: string | null;
  lookupLatest: (projectId: string) => Promise<PublicMonitoringRow | null>;
};

const PROJECT_ID = /^[a-z0-9][a-z0-9._:-]{0,159}$/u;

function canonicalUtc(value: string | null): string | null {
  if (value === null) return null;
  const milliseconds = Date.parse(value);
  if (!Number.isFinite(milliseconds)) {
    throw new Error("invalid monitoring time");
  }
  return new Date(milliseconds).toISOString();
}

function configuredOrigin(value: string | null): string | null {
  if (value === null) return null;
  try {
    const parsed = new URL(value);
    if (
      parsed.protocol !== "https:" || parsed.username !== "" ||
      parsed.password !== "" || parsed.pathname !== "/" ||
      parsed.search !== "" || parsed.hash !== ""
    ) return null;
    return parsed.origin;
  } catch {
    return null;
  }
}

function headers(origin: string | null, contentType = true): Headers {
  const result = new Headers({
    "Cache-Control": "no-store, max-age=0",
    "Content-Security-Policy": "default-src 'none'",
    "Referrer-Policy": "no-referrer",
    "Vary": "Origin",
    "X-Content-Type-Options": "nosniff",
  });
  if (contentType) {
    result.set("Content-Type", "application/json; charset=utf-8");
  }
  if (origin !== null) {
    result.set("Access-Control-Allow-Origin", origin);
    result.set("Access-Control-Allow-Methods", "GET, OPTIONS");
    result.set("Access-Control-Allow-Headers", "Accept");
    result.set("Access-Control-Max-Age", "600");
  }
  return result;
}

function json(status: number, code: string, origin: string | null): Response {
  return new Response(JSON.stringify({ error: code }), {
    status,
    headers: headers(origin),
  });
}

export function publicMonitoringPayload(row: PublicMonitoringRow) {
  if (row.scientific_claim_allowed !== false) {
    throw new Error("monitoring scientific boundary changed");
  }
  return {
    schemaVersion: "butterflylens-public-monitoring:v1.0.0",
    snapshotMode: "live",
    observedAt: canonicalUtc(row.observed_at),
    heartbeat: {
      state: row.heartbeat_state,
      observedAt: canonicalUtc(row.heartbeat_observed_at),
      workerState: row.worker_state,
      reason: row.heartbeat_reason,
    },
    apiBudget: {
      state: row.api_budget_state,
      limit: row.api_budget_limit,
      used: row.api_budget_used,
      remaining: row.api_budget_remaining,
      resetsAt: canonicalUtc(row.api_budget_resets_at),
      reason: row.api_budget_reason,
    },
    stageHealth: {
      state: row.stage_health_state,
      currentStage: row.current_stage,
      stageState: row.stage_state,
      healthyCount: row.healthy_stage_count,
      failedCount: row.failed_stage_count,
      reason: row.stage_health_reason,
    },
    queue: {
      state: row.queue_state,
      depth: row.queue_depth,
      capacity: row.queue_capacity,
      reason: row.queue_reason,
    },
    failures: {
      state: row.failure_state,
      count: row.failure_count,
      reason: row.failure_reason,
    },
    lastArtifact: {
      state: row.artifact_state,
      fingerprint: row.artifact_fingerprint,
      committedAt: canonicalUtc(row.artifact_committed_at),
      reason: row.artifact_reason,
    },
    lastMapRefresh: {
      state: row.map_state,
      fingerprint: row.map_fingerprint,
      refreshedAt: canonicalUtc(row.map_refreshed_at),
      reason: row.map_reason,
    },
    models: {
      state: row.model_state,
      yoloe: row.yoloe_state,
      bioclip: row.bioclip_state,
      reason: row.model_reason,
    },
    resources: {
      state: row.resource_state,
      freeDiskBytes: row.free_disk_bytes,
      processRssBytes: row.process_rss_bytes,
      memoryCapacityBytes: row.memory_capacity_bytes,
      mpsAllocatedBytes: row.mps_allocated_bytes,
      mpsReservedBytes: row.mps_reserved_bytes,
      reason: row.resource_reason,
    },
    scientificClaimAllowed: false,
  } as const;
}

export function createPublicMonitoringHandler(
  dependencies: MonitoringDependencies,
): (request: Request) => Promise<Response> {
  return async (request) => {
    const origin = configuredOrigin(dependencies.allowedOrigin);
    if (
      origin === null || dependencies.projectId === null ||
      !PROJECT_ID.test(dependencies.projectId)
    ) return json(503, "monitoring_not_configured", null);

    const requestOrigin = request.headers.get("Origin");
    if (requestOrigin !== null && requestOrigin !== origin) {
      return json(403, "origin_not_allowed", null);
    }

    if (request.method === "OPTIONS") {
      if (
        requestOrigin !== origin ||
        request.headers.get("Access-Control-Request-Method") !== "GET"
      ) return json(403, "preflight_not_allowed", null);
      return new Response(null, {
        status: 204,
        headers: headers(origin, false),
      });
    }
    if (request.method !== "GET") {
      const response = json(405, "method_not_allowed", requestOrigin);
      response.headers.set("Allow", "GET, OPTIONS");
      return response;
    }

    const url = new URL(request.url);
    if (url.search !== "") return json(400, "query_not_allowed", requestOrigin);

    try {
      const row = await dependencies.lookupLatest(dependencies.projectId);
      if (row === null) {
        return json(404, "monitoring_unavailable", requestOrigin);
      }
      return new Response(JSON.stringify(publicMonitoringPayload(row)), {
        status: 200,
        headers: headers(requestOrigin),
      });
    } catch {
      return json(503, "monitoring_unavailable", requestOrigin);
    }
  };
}
