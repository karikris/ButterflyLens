import OpenAI from "openai";
import { withSupabase } from "@supabase/server";

import {
  type ResponseLike,
  type ResponseRequest,
  runAnalyst,
} from "../_shared/analyst.ts";
import { createAskButterflyLensHandler } from "../_shared/edgeBoundary.ts";
import { executeSubmittedTool } from "../_shared/submittedTools.ts";

const OPENAI_REQUEST_TIMEOUT_MS = 45_000;

const handleRequest = createAskButterflyLensHandler({
  getOpenAiApiKey: () => Deno.env.get("OPENAI_API_KEY"),
  run: async ({ apiKey, request, safetyIdentifier }) => {
    const openai = new OpenAI({
      apiKey,
      maxRetries: 0,
      timeout: OPENAI_REQUEST_TIMEOUT_MS,
    });
    return await runAnalyst({
      request,
      safetyIdentifier,
      executeTool: executeSubmittedTool,
      createResponse: async (
        responseRequest: ResponseRequest,
      ): Promise<ResponseLike> => {
        const response = await openai.responses.create(responseRequest);
        return response as unknown as ResponseLike;
      },
    });
  },
});

export default {
  fetch: withSupabase({ auth: "user" }, async (request, context) => {
    return await handleRequest(request, { subject: context.jwtClaims?.sub });
  }),
};
