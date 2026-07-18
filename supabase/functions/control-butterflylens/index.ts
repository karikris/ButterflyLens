import { withSupabase } from "@supabase/server";

import {
  type AuthorizedRun,
  createServerActionHandler,
  ServerActionConflictError,
  ServerActionForbiddenError,
  type ServerActionReceipt,
} from "../_shared/serverActionBoundary.ts";
import type { EdgeDatabase } from "../_shared/database.ts";

const RECEIPT_COLUMNS =
  "server_action_id,action,prior_status,result_status,result_revision,applied_at,request_fingerprint";

export default {
  fetch: withSupabase<EdgeDatabase>(
    { auth: "user" },
    async (request, context) => {
      const handler = createServerActionHandler({
        lookupRun: async (runId): Promise<AuthorizedRun | null> => {
          const { data, error } = await context.supabase
            .from("runs")
            .select("id,project_pk,run_id")
            .eq("run_id", runId)
            .maybeSingle();
          if (error) throw new Error("caller-scoped run lookup failed");
          if (
            !data ||
            !Number.isSafeInteger(data.id) ||
            !Number.isSafeInteger(data.project_pk) ||
            typeof data.run_id !== "string"
          ) return null;
          return {
            runPk: data.id,
            projectPk: data.project_pk,
            runId: data.run_id,
          };
        },
        apply: async (input): Promise<ServerActionReceipt> => {
          const inserted = await context.supabaseAdmin
            .from("server_action_receipts")
            .insert({
              server_action_id: input.serverActionId,
              project_pk: input.run.projectPk,
              run_pk: input.run.runPk,
              requested_by: input.subject,
              action: input.action,
              expected_revision: input.expectedRevision,
              request_fingerprint: input.requestFingerprint,
            })
            .select(RECEIPT_COLUMNS)
            .single();
          if (!inserted.error && inserted.data) {
            return inserted.data as ServerActionReceipt;
          }
          if (inserted.error?.code === "42501") {
            throw new ServerActionForbiddenError();
          }
          if (
            inserted.error?.code === "40001" || inserted.error?.code === "23514"
          ) {
            throw new ServerActionConflictError();
          }
          if (inserted.error?.code === "23505") {
            const existing = await context.supabaseAdmin
              .from("server_action_receipts")
              .select(RECEIPT_COLUMNS)
              .eq("server_action_id", input.serverActionId)
              .maybeSingle();
            if (
              !existing.error &&
              existing.data?.request_fingerprint === input.requestFingerprint
            ) return existing.data as ServerActionReceipt;
            throw new ServerActionConflictError();
          }
          throw new Error("controlled server action insert failed");
        },
      });
      return await handler(request, context.jwtClaims?.sub);
    },
  ),
};
