import { withSupabase } from "@supabase/server";

import {
  type AuthorizedB2Object,
  createB2SigningHandler,
} from "../_shared/b2Boundary.ts";
import type { EdgeDatabase } from "../_shared/database.ts";

function signingConfig() {
  const endpoint = Deno.env.get("B2_S3_ENDPOINT");
  const bucket = Deno.env.get("B2_PRIVATE_BUCKET");
  const accessKeyId = Deno.env.get("B2_KEY_ID");
  const applicationKey = Deno.env.get("B2_APPLICATION_KEY");
  return endpoint && bucket && accessKeyId && applicationKey
    ? { endpoint, bucket, accessKeyId, applicationKey }
    : null;
}

export default {
  fetch: withSupabase<EdgeDatabase>(
    { auth: "user" },
    async (request, context) => {
      const handler = createB2SigningHandler({
        getConfig: signingConfig,
        authorize: async (
          mediaObjectId,
        ): Promise<AuthorizedB2Object | null> => {
          const { data: visible, error: visibleError } = await context.supabase
            .from("media_objects")
            .select("media_object_id,project_pk")
            .eq("media_object_id", mediaObjectId)
            .maybeSingle();
          if (visibleError) {
            throw new Error("caller-scoped media lookup failed");
          }
          if (!visible) return null;

          const { data: media, error: mediaError } = await context.supabaseAdmin
            .from("media_objects")
            .select(
              "id,project_pk,media_object_id,storage_backend,storage_key,media_state,content_sha256,byte_count,media_type,decode_status,rights_status,display_allowed,removed_at",
            )
            .eq("media_object_id", mediaObjectId)
            .eq("project_pk", visible.project_pk)
            .maybeSingle();
          if (mediaError) throw new Error("administrative media lookup failed");
          if (
            !media ||
            media.storage_backend !== "b2" ||
            media.media_state !== "committed" ||
            media.decode_status !== "valid" ||
            media.rights_status !== "allowed" ||
            media.display_allowed !== true ||
            media.removed_at !== null ||
            typeof media.storage_key !== "string" ||
            typeof media.content_sha256 !== "string" ||
            typeof media.byte_count !== "number" ||
            typeof media.media_type !== "string" ||
            !Number.isSafeInteger(media.id) ||
            !Number.isSafeInteger(media.project_pk)
          ) return null;
          return {
            mediaObjectPk: media.id,
            projectPk: media.project_pk,
            mediaObjectId: media.media_object_id,
            storageKey: media.storage_key,
            contentSha256: media.content_sha256,
            byteCount: media.byte_count,
            mediaType: media.media_type,
          };
        },
        record: async (receipt) => {
          const { error } = await context.supabaseAdmin
            .from("b2_signing_receipts")
            .insert({
              signing_receipt_id: receipt.signingReceiptId,
              project_pk: receipt.projectPk,
              media_object_pk: receipt.mediaObjectPk,
              auth_user_id: receipt.authUserId,
              method: receipt.method,
              ttl_seconds: receipt.ttlSeconds,
              issued_at: receipt.issuedAt,
              expires_at: receipt.expiresAt,
              request_fingerprint: receipt.requestFingerprint,
            });
          if (error) throw new Error("signing receipt write failed");
        },
      });
      return await handler(request, context.jwtClaims?.sub);
    },
  ),
};
