import { withSupabase } from "@supabase/server";

import type { EdgeDatabase } from "../_shared/database.ts";
import {
  createPublicMonitoringHandler,
  type PublicMonitoringRow,
} from "../_shared/monitoringBoundary.ts";

const MONITORING_COLUMNS = [
  "observed_at",
  "heartbeat_state",
  "heartbeat_observed_at",
  "worker_state",
  "heartbeat_reason",
  "api_budget_state",
  "api_budget_limit",
  "api_budget_used",
  "api_budget_remaining",
  "api_budget_resets_at",
  "api_budget_reason",
  "stage_health_state",
  "current_stage",
  "stage_state",
  "healthy_stage_count",
  "failed_stage_count",
  "stage_health_reason",
  "queue_state",
  "queue_depth",
  "queue_capacity",
  "queue_reason",
  "failure_state",
  "failure_count",
  "failure_reason",
  "artifact_state",
  "artifact_fingerprint",
  "artifact_committed_at",
  "artifact_reason",
  "map_state",
  "map_fingerprint",
  "map_refreshed_at",
  "map_reason",
  "model_state",
  "yoloe_state",
  "bioclip_state",
  "model_reason",
  "resource_state",
  "free_disk_bytes",
  "process_rss_bytes",
  "memory_capacity_bytes",
  "mps_allocated_bytes",
  "mps_reserved_bytes",
  "resource_reason",
  "scientific_claim_allowed",
].join(",");

export default {
  fetch: withSupabase<EdgeDatabase>(
    { auth: "none", cors: "disabled" },
    async (request, context) => {
      const handler = createPublicMonitoringHandler({
        projectId: Deno.env.get("BUTTERFLYLENS_PUBLIC_PROJECT_ID") ?? null,
        allowedOrigin: Deno.env.get("BUTTERFLYLENS_PUBLIC_ORIGIN") ?? null,
        lookupLatest: async (
          projectId,
        ): Promise<PublicMonitoringRow | null> => {
          const project = await context.supabaseAdmin
            .from("projects")
            .select("id")
            .eq("project_id", projectId)
            .maybeSingle();
          if (project.error) {
            throw new Error("monitoring project lookup failed");
          }
          if (!project.data) return null;

          const snapshot = await context.supabaseAdmin
            .from("operational_monitoring_snapshots")
            .select(MONITORING_COLUMNS)
            .eq("project_pk", project.data.id)
            .order("observed_at", { ascending: false })
            .order("id", { ascending: false })
            .limit(1)
            .maybeSingle();
          if (snapshot.error) {
            throw new Error("monitoring snapshot lookup failed");
          }
          return snapshot.data as PublicMonitoringRow | null;
        },
      });
      return await handler(request);
    },
  ),
};
