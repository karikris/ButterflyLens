import submittedReplayCatalogJson from '../../../../packages/openai/submitted-replays.v1.json'

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

export interface StoredToolOutput {
  readonly schema_version: 'butterflylens-openai-tool-result:v1.0.0'
  readonly tool_name: AnalystToolName
  readonly status: 'available' | 'partial' | 'unavailable' | 'not_found' | 'forbidden'
  readonly summary: string
  readonly query: readonly unknown[]
  readonly facts: readonly unknown[]
  readonly records: readonly unknown[]
  readonly citations: readonly AnalystCitation[]
  readonly limitations: readonly string[]
  readonly result_fingerprint: string
}

export interface StoredToolTrace {
  readonly sequence: number
  readonly call_id: string
  readonly name: AnalystToolName
  readonly arguments: Readonly<Record<string, unknown>>
  readonly output: StoredToolOutput
}

export interface AnalystReplayResponse {
  readonly schema_version: 'butterflylens-analyst-replay-response:v1.0.0'
  readonly mode: 'replayed'
  readonly response_state: 'completed' | 'incomplete'
  readonly summary: string
  readonly claims: readonly AnalystClaim[]
  readonly citations: readonly AnalystCitation[]
  readonly limitations: readonly string[]
  readonly tools_used: readonly AnalystToolName[]
  readonly replay: {
    readonly replay_id: string
    readonly recorded_at: string
    readonly source_commit: string
    readonly model_invoked: false
    readonly response_calls: 0
    readonly tool_calls: number
    readonly trace_fingerprint: string
  }
}

export type AnalystPresentation = AnalystResponse | AnalystReplayResponse

export interface StoredReplayCatalog {
  readonly schema_version: 'butterflylens-analyst-replay-catalog:v1.0.0'
  readonly mode: 'replayed'
  readonly source: {
    readonly repository: 'karikris/ButterflyLens'
    readonly implementation_commit: string
    readonly tool_artifact_commit: string
    readonly recorded_at: string
    readonly model_invoked: false
    readonly network_calls: 0
  }
  readonly cases: readonly {
    readonly replay_id: string
    readonly accepted_questions: readonly string[]
    readonly tool_trace: readonly StoredToolTrace[]
    readonly response: AnalystReplayResponse
  }[]
  readonly catalog_fingerprint: string
}

export interface ConversationMessage {
  readonly role: 'user' | 'assistant'
  readonly content: string
}

export type AnalystClientResult =
  | {
      readonly state: 'response'
      readonly response: AnalystPresentation
      readonly replay_trace?: readonly StoredToolTrace[]
    }
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
const REPLAY_CATALOG_KEYS = new Set([
  'schema_version',
  'mode',
  'source',
  'cases',
  'catalog_fingerprint',
])
const REPLAY_SOURCE_KEYS = new Set([
  'repository',
  'implementation_commit',
  'tool_artifact_commit',
  'recorded_at',
  'model_invoked',
  'network_calls',
])
const REPLAY_CASE_KEYS = new Set(['replay_id', 'accepted_questions', 'tool_trace', 'response'])
const TRACE_KEYS = new Set(['sequence', 'call_id', 'name', 'arguments', 'output'])
const TOOL_OUTPUT_KEYS = new Set([
  'schema_version',
  'tool_name',
  'status',
  'summary',
  'query',
  'facts',
  'records',
  'citations',
  'limitations',
  'result_fingerprint',
])
const REPLAY_RESPONSE_KEYS = new Set([
  'schema_version',
  'mode',
  'response_state',
  'summary',
  'claims',
  'citations',
  'limitations',
  'tools_used',
  'replay',
])
const REPLAY_METADATA_KEYS = new Set([
  'replay_id',
  'recorded_at',
  'source_commit',
  'model_invoked',
  'response_calls',
  'tool_calls',
  'trace_fingerprint',
])

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

export function parseStoredReplayCatalog(value: unknown): StoredReplayCatalog {
  if (!isRecord(value) || !hasExactKeys(value, REPLAY_CATALOG_KEYS)) {
    throw new Error('stored replay catalogue must have the exact public shape')
  }
  if (
    value.schema_version !== 'butterflylens-analyst-replay-catalog:v1.0.0' ||
    value.mode !== 'replayed' ||
    !sha256Fingerprint(value.catalog_fingerprint) ||
    !isRecord(value.source) ||
    !hasExactKeys(value.source, REPLAY_SOURCE_KEYS) ||
    value.source.repository !== 'karikris/ButterflyLens' ||
    !gitCommit(value.source.implementation_commit) ||
    !gitCommit(value.source.tool_artifact_commit) ||
    !isoTimestamp(value.source.recorded_at) ||
    value.source.model_invoked !== false ||
    value.source.network_calls !== 0 ||
    !Array.isArray(value.cases) ||
    value.cases.length < 3 ||
    value.cases.length > 12
  ) {
    throw new Error('stored replay catalogue provenance is invalid')
  }
  const replayIds = new Set<string>()
  const questions = new Set<string>()
  for (const [caseIndex, replayCase] of value.cases.entries()) {
    if (!isRecord(replayCase) || !hasExactKeys(replayCase, REPLAY_CASE_KEYS)) {
      throw new Error(`stored replay case ${caseIndex} has unexpected fields`)
    }
    if (
      !boundedIdentifier(replayCase.replay_id) ||
      replayIds.has(replayCase.replay_id) ||
      !Array.isArray(replayCase.accepted_questions) ||
      replayCase.accepted_questions.length < 1 ||
      replayCase.accepted_questions.length > 8 ||
      !replayCase.accepted_questions.every((question) => boundedText(question, 1200)) ||
      !Array.isArray(replayCase.tool_trace) ||
      replayCase.tool_trace.length < 1 ||
      replayCase.tool_trace.length > 8
    ) {
      throw new Error(`stored replay case ${caseIndex} is invalid`)
    }
    replayIds.add(replayCase.replay_id)
    for (const question of replayCase.accepted_questions as string[]) {
      const normalized = normalizeQuestion(question)
      if (questions.has(normalized)) throw new Error('stored replay questions must be unique')
      questions.add(normalized)
    }
    const callIds = new Set<string>()
    const trace = replayCase.tool_trace.map((item, traceIndex) => {
      if (!isRecord(item) || !hasExactKeys(item, TRACE_KEYS)) {
        throw new Error(`stored replay trace ${caseIndex}.${traceIndex} has unexpected fields`)
      }
      if (
        item.sequence !== traceIndex + 1 ||
        !boundedIdentifier(item.call_id) ||
        callIds.has(item.call_id) ||
        !analystToolNames.includes(item.name as AnalystToolName) ||
        !isRecord(item.arguments) ||
        canonicalJson(item.arguments).length > 4_096
      ) {
        throw new Error(`stored replay trace ${caseIndex}.${traceIndex} is invalid`)
      }
      callIds.add(item.call_id)
      const output = parseStoredToolOutput(item.output, item.name as AnalystToolName)
      return { ...item, output } as StoredToolTrace
    })
    parseReplayResponse(replayCase.response, replayCase.replay_id, trace)
  }
  return cloneJson(value) as unknown as StoredReplayCatalog
}

function parseStoredToolOutput(value: unknown, toolName: AnalystToolName): StoredToolOutput {
  if (!isRecord(value) || !hasExactKeys(value, TOOL_OUTPUT_KEYS)) {
    throw new Error('stored tool output has unexpected fields')
  }
  if (
    value.schema_version !== 'butterflylens-openai-tool-result:v1.0.0' ||
    value.tool_name !== toolName ||
    !['available', 'partial', 'unavailable', 'not_found', 'forbidden'].includes(String(value.status)) ||
    !boundedText(value.summary, 800) ||
    !Array.isArray(value.query) ||
    value.query.length > 20 ||
    !Array.isArray(value.facts) ||
    value.facts.length > 64 ||
    !Array.isArray(value.records) ||
    value.records.length > 20 ||
    !Array.isArray(value.citations) ||
    value.citations.length < 1 ||
    value.citations.length > 20 ||
    !Array.isArray(value.limitations) ||
    value.limitations.length > 20 ||
    !value.limitations.every((item) => boundedText(item, 600)) ||
    !sha256Fingerprint(value.result_fingerprint)
  ) {
    throw new Error('stored tool output is invalid')
  }
  const citationIds = new Set<string>()
  for (const citation of value.citations) {
    assertCitation(citation)
    if (citationIds.has(citation.artifact_id)) throw new Error('stored tool citations repeat')
    citationIds.add(citation.artifact_id)
  }
  if (canonicalJson(value).length > 65_536) throw new Error('stored tool output exceeds its bound')
  return value as unknown as StoredToolOutput
}

function parseReplayResponse(
  value: unknown,
  replayId: string,
  trace: readonly StoredToolTrace[],
): AnalystReplayResponse {
  if (!isRecord(value) || !hasExactKeys(value, REPLAY_RESPONSE_KEYS)) {
    throw new Error('stored replay response has unexpected fields')
  }
  if (
    value.schema_version !== 'butterflylens-analyst-replay-response:v1.0.0' ||
    value.mode !== 'replayed' ||
    !['completed', 'incomplete'].includes(String(value.response_state)) ||
    !boundedText(value.summary, 800) ||
    !Array.isArray(value.citations) ||
    value.citations.length < 1 ||
    value.citations.length > 16 ||
    !Array.isArray(value.claims) ||
    value.claims.length < 1 ||
    value.claims.length > 12 ||
    !Array.isArray(value.limitations) ||
    value.limitations.length < 1 ||
    value.limitations.length > 12 ||
    !value.limitations.every((item) => boundedText(item, 600)) ||
    new Set(value.limitations).size !== value.limitations.length ||
    !Array.isArray(value.tools_used)
  ) {
    throw new Error('stored replay response is invalid')
  }
  const expectedCitations = new Map<string, AnalystCitation>()
  for (const item of trace) {
    for (const citation of item.output.citations) {
      expectedCitations.set(citation.artifact_id, citation)
    }
  }
  const citationIds = new Set<string>()
  for (const citation of value.citations) {
    assertCitation(citation)
    if (citationIds.has(citation.artifact_id)) throw new Error('stored replay citations repeat')
    citationIds.add(citation.artifact_id)
  }
  if (canonicalJson(value.citations) !== canonicalJson([...expectedCitations.values()])) {
    throw new Error('stored replay citations do not exactly match stored tool outputs')
  }
  const claimIds = new Set<string>()
  for (const claim of value.claims) {
    assertClaim(claim, citationIds)
    if (claimIds.has(claim.claim_id)) throw new Error('stored replay claim IDs repeat')
    claimIds.add(claim.claim_id)
  }
  const expectedTools = [...new Set(trace.map((item) => item.name))]
  if (canonicalJson(value.tools_used) !== canonicalJson(expectedTools)) {
    throw new Error('stored replay tools do not exactly match its trace')
  }
  if (
    !isRecord(value.replay) ||
    !hasExactKeys(value.replay, REPLAY_METADATA_KEYS) ||
    value.replay.replay_id !== replayId ||
    !isoTimestamp(value.replay.recorded_at) ||
    !gitCommit(value.replay.source_commit) ||
    value.replay.model_invoked !== false ||
    value.replay.response_calls !== 0 ||
    value.replay.tool_calls !== trace.length ||
    !sha256Fingerprint(value.replay.trace_fingerprint)
  ) {
    throw new Error('stored replay execution provenance is invalid')
  }
  return value as unknown as AnalystReplayResponse
}

export function createStoredReplayAnalystClient(value: unknown): AnalystClient {
  const catalogue = parseStoredReplayCatalog(value)
  let verification: Promise<void> | null = null
  return async ({ question, history }) => {
    if (history.length > 0) {
      return {
        state: 'unavailable',
        reason: 'Stored replay is single-turn and does not simulate a live conversation.',
      }
    }
    try {
      verification ??= verifyStoredReplayFingerprints(catalogue)
      await verification
    } catch {
      return {
        state: 'unavailable',
        reason: 'The stored replay failed its fingerprint contract. No model call was made.',
      }
    }
    const normalized = normalizeQuestion(question)
    const replayCase = catalogue.cases.find((candidate) =>
      candidate.accepted_questions.some((accepted) => normalizeQuestion(accepted) === normalized)
    )
    if (!replayCase) {
      return {
        state: 'unavailable',
        reason: 'No exact stored replay exists for that question. No live inference was simulated.',
      }
    }
    return {
      state: 'response',
      response: cloneJson(replayCase.response),
      replay_trace: cloneJson(replayCase.tool_trace),
    }
  }
}

async function verifyStoredReplayFingerprints(catalogue: StoredReplayCatalog): Promise<void> {
  for (const replayCase of catalogue.cases) {
    for (const item of replayCase.tool_trace) {
      const { result_fingerprint: observed, ...payload } = item.output
      if (await sha256Canonical(payload) !== observed) {
        throw new Error('stored tool output fingerprint mismatch')
      }
    }
    if (await sha256Canonical(replayCase.tool_trace) !== replayCase.response.replay.trace_fingerprint) {
      throw new Error('stored replay trace fingerprint mismatch')
    }
  }
  const { catalog_fingerprint: observed, ...payload } = catalogue
  if (await sha256Canonical(payload) !== observed) {
    throw new Error('stored replay catalogue fingerprint mismatch')
  }
}

let submittedReplayClient: AnalystClient | null = null

export const submittedAnalystClient: AnalystClient = async (input) => {
  try {
    submittedReplayClient ??= createStoredReplayAnalystClient(submittedReplayCatalogJson)
    return await submittedReplayClient(input)
  } catch {
    return {
      state: 'unavailable',
      reason: 'The submitted stored replay failed closed. No model call was made.',
    }
  }
}

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

function boundedIdentifier(value: unknown): value is string {
  return typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,179}$/.test(value)
}

function gitCommit(value: unknown): value is string {
  return typeof value === 'string' && /^[0-9a-f]{40}$/.test(value)
}

function sha256Fingerprint(value: unknown): value is string {
  return typeof value === 'string' && /^sha256:[0-9a-f]{64}$/.test(value)
}

function isoTimestamp(value: unknown): value is string {
  return typeof value === 'string' && !Number.isNaN(Date.parse(value)) && value.includes('T')
}

function normalizeQuestion(value: string): string {
  return value.normalize('NFKC').trim().replace(/\s+/g, ' ').toLocaleLowerCase('en-AU')
}

function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

function canonicalJson(value: unknown): string {
  if (value === null || typeof value !== 'object') {
    const encoded = JSON.stringify(value)
    if (encoded === undefined || (typeof value === 'number' && !Number.isFinite(value))) {
      throw new Error('stored replay contains a non-JSON value')
    }
    return encoded
  }
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`
  const record = value as Record<string, unknown>
  return `{${Object.keys(record)
    .sort()
    .map((key) => `${JSON.stringify(key)}:${canonicalJson(record[key])}`)
    .join(',')}}`
}

async function sha256Canonical(value: unknown): Promise<string> {
  const bytes = new TextEncoder().encode(canonicalJson(value))
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))
  return `sha256:${Array.from(digest, (byte) => byte.toString(16).padStart(2, '0')).join('')}`
}
