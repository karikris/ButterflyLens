export const analystToolNames = [
  'inspect_map_scope',
  'compare_ala_and_flickr',
  'inspect_species',
  'inspect_flickr_candidate',
  'trace_record_evidence',
  'explain_classification',
  'inspect_review_consensus',
  'inspect_reviewer_quality',
  'inspect_pipeline_status',
  'inspect_worker_status',
  'recommend_next_review_batch',
  'recommend_next_species',
  'explain_geographic_contribution',
  'prepare_impact_report',
] as const

export type AnalystToolName = (typeof analystToolNames)[number]

export interface AnalystCitation {
  readonly artifact_id: string
  readonly repository: 'karikris/ButterflyLens'
  readonly commit: string
  readonly path: string
  readonly fingerprint: string
}

export interface AnalystClaim {
  readonly claim_id: string
  readonly statement: string
  readonly evidence_state: 'direct' | 'inference' | 'unavailable' | 'conflict'
  readonly citation_ids: readonly string[]
}

export interface AnalystResponse {
  readonly schema_version: 'butterflylens-analyst-response:v1.0.0'
  readonly mode: 'live'
  readonly response_state: 'completed' | 'incomplete' | 'refused'
  readonly summary: string
  readonly claims: readonly AnalystClaim[]
  readonly citations: readonly AnalystCitation[]
  readonly limitations: readonly string[]
  readonly tools_used: readonly AnalystToolName[]
  readonly model: {
    readonly id: 'gpt-5.6-sol'
    readonly reasoning_effort: 'xhigh'
  }
  readonly usage: {
    readonly response_calls: number
    readonly tool_calls: number
    readonly budget_state: 'within_budget' | 'exhausted'
  }
}

export interface ConversationMessage {
  readonly role: 'user' | 'assistant'
  readonly content: string
}

export type AnalystClientResult =
  | { readonly state: 'response'; readonly response: AnalystResponse }
  | { readonly state: 'unavailable'; readonly reason: string }

export type AnalystClient = (input: {
  readonly question: string
  readonly history: readonly ConversationMessage[]
}) => Promise<AnalystClientResult>

const ROOT_KEYS = new Set([
  'schema_version',
  'mode',
  'response_state',
  'summary',
  'claims',
  'citations',
  'limitations',
  'tools_used',
  'model',
  'usage',
])
const CLAIM_KEYS = new Set(['claim_id', 'statement', 'evidence_state', 'citation_ids'])
const CITATION_KEYS = new Set(['artifact_id', 'repository', 'commit', 'path', 'fingerprint'])
const MODEL_KEYS = new Set(['id', 'reasoning_effort'])
const USAGE_KEYS = new Set(['response_calls', 'tool_calls', 'budget_state'])

export function parseAnalystResponse(value: unknown): AnalystResponse {
  if (!isRecord(value) || !hasExactKeys(value, ROOT_KEYS)) {
    throw new Error('analyst response must have the exact public shape')
  }
  if (
    value.schema_version !== 'butterflylens-analyst-response:v1.0.0' ||
    value.mode !== 'live' ||
    !['completed', 'incomplete', 'refused'].includes(String(value.response_state)) ||
    !boundedText(value.summary, 800)
  ) {
    throw new Error('analyst response version, mode, state, or summary is invalid')
  }
  if (!Array.isArray(value.citations) || value.citations.length > 16) {
    throw new Error('analyst citations exceed their bound')
  }
  const citationIds = new Set<string>()
  for (const citation of value.citations) {
    assertCitation(citation)
    if (citationIds.has(citation.artifact_id)) {
      throw new Error('analyst citation IDs must be unique')
    }
    citationIds.add(citation.artifact_id)
  }
  if (!Array.isArray(value.claims) || value.claims.length > 12) {
    throw new Error('analyst claims exceed their bound')
  }
  const claimIds = new Set<string>()
  for (const claim of value.claims) {
    assertClaim(claim, citationIds)
    if (claimIds.has(claim.claim_id)) throw new Error('analyst claim IDs must be unique')
    claimIds.add(claim.claim_id)
  }
  if (
    !Array.isArray(value.limitations) ||
    value.limitations.length > 12 ||
    !value.limitations.every((item) => boundedText(item, 600)) ||
    new Set(value.limitations).size !== value.limitations.length
  ) {
    throw new Error('analyst limitations are invalid')
  }
  if (
    !Array.isArray(value.tools_used) ||
    value.tools_used.length > 8 ||
    !value.tools_used.every((tool) => analystToolNames.includes(tool as AnalystToolName)) ||
    new Set(value.tools_used).size !== value.tools_used.length
  ) {
    throw new Error('analyst tools are invalid')
  }
  if (
    !isRecord(value.model) ||
    !hasExactKeys(value.model, MODEL_KEYS) ||
    value.model.id !== 'gpt-5.6-sol' ||
    value.model.reasoning_effort !== 'xhigh'
  ) {
    throw new Error('analyst model provenance is invalid')
  }
  if (
    !isRecord(value.usage) ||
    !hasExactKeys(value.usage, USAGE_KEYS) ||
    !boundedInteger(value.usage.response_calls, 0, 6) ||
    !boundedInteger(value.usage.tool_calls, 0, 8) ||
    !['within_budget', 'exhausted'].includes(String(value.usage.budget_state))
  ) {
    throw new Error('analyst usage budget is invalid')
  }
  if (
    value.response_state === 'refused' &&
    (value.claims.length !== 0 || value.citations.length !== 0)
  ) {
    throw new Error('refused analyst response cannot contain claims or citations')
  }
  if (value.response_state === 'completed' && value.claims.length === 0) {
    throw new Error('completed analyst response requires a cited claim')
  }
  return value as unknown as AnalystResponse
}

function assertCitation(value: unknown): asserts value is AnalystCitation {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, CITATION_KEYS) ||
    !boundedText(value.artifact_id, 180) ||
    value.repository !== 'karikris/ButterflyLens' ||
    typeof value.commit !== 'string' ||
    !/^[0-9a-f]{40}$/.test(value.commit) ||
    !boundedText(value.path, 300) ||
    typeof value.fingerprint !== 'string' ||
    !/^sha256:[0-9a-f]{64}$/.test(value.fingerprint)
  ) {
    throw new Error('analyst citation is invalid')
  }
}

function assertClaim(value: unknown, citationIds: Set<string>): asserts value is AnalystClaim {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, CLAIM_KEYS) ||
    typeof value.claim_id !== 'string' ||
    !/^claim_[1-9][0-9]{0,2}$/.test(value.claim_id) ||
    !boundedText(value.statement, 800) ||
    !['direct', 'inference', 'unavailable', 'conflict'].includes(String(value.evidence_state)) ||
    !Array.isArray(value.citation_ids) ||
    value.citation_ids.length < 1 ||
    value.citation_ids.length > 8 ||
    !value.citation_ids.every((id) => typeof id === 'string' && citationIds.has(id)) ||
    new Set(value.citation_ids).size !== value.citation_ids.length
  ) {
    throw new Error('analyst claim is not fully cited')
  }
}

export function createSupabaseAnalystClient(options: {
  readonly supabaseUrl: string
  readonly publishableKey: string
  readonly getAccessToken: () => Promise<string | null>
  readonly fetchImpl?: typeof fetch
}): AnalystClient {
  const endpoint = new URL('/functions/v1/ask-butterflylens', options.supabaseUrl)
  if (endpoint.protocol !== 'https:' && endpoint.hostname !== '127.0.0.1' && endpoint.hostname !== 'localhost') {
    throw new Error('analyst endpoint must use HTTPS outside local development')
  }
  if (!options.publishableKey) throw new Error('Supabase publishable key is required')
  const fetchImpl = options.fetchImpl ?? fetch
  return async ({ question, history }) => {
    const token = await options.getAccessToken()
    if (!token) {
      return {
        state: 'unavailable',
        reason: 'Sign in before using the live analyst. No model call was made.',
      }
    }
    const response = await fetchImpl(endpoint, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        apikey: options.publishableKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question, history }),
    })
    let payload: unknown
    try {
      payload = await response.json()
    } catch {
      return { state: 'unavailable', reason: 'The analyst returned an unreadable response.' }
    }
    if (!response.ok) {
      const reason =
        isRecord(payload) && boundedText(payload.message, 400)
          ? payload.message
          : 'The live analyst is unavailable.'
      return { state: 'unavailable', reason }
    }
    try {
      return { state: 'response', response: parseAnalystResponse(payload) }
    } catch {
      return {
        state: 'unavailable',
        reason: 'The analyst response failed the browser evidence contract.',
      }
    }
  }
}

export const submittedAnalystClient: AnalystClient = async () => ({
  state: 'unavailable',
  reason:
    'The submitted replay has no authenticated live analyst session. No OpenAI call was made.',
})

function hasExactKeys(value: Record<string, unknown>, expected: Set<string>): boolean {
  const keys = Object.keys(value)
  return keys.length === expected.size && keys.every((key) => expected.has(key))
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function boundedText(value: unknown, maximum: number): value is string {
  return typeof value === 'string' && value.trim().length > 0 && value.length <= maximum
}

function boundedInteger(value: unknown, minimum: number, maximum: number): boolean {
  return Number.isSafeInteger(value) && Number(value) >= minimum && Number(value) <= maximum
}
