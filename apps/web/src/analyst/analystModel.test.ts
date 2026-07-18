import { describe, expect, it, vi } from 'vitest'

import {
  createSupabaseAnalystClient,
  parseAnalystResponse,
  submittedAnalystClient,
  type AnalystResponse,
} from './analystModel'

const CITATION = {
  artifact_id: 'species-catalogue',
  repository: 'karikris/ButterflyLens',
  commit: 'a'.repeat(40),
  path: 'data/derived/species_catalogue.json',
  fingerprint: `sha256:${'b'.repeat(64)}`,
} as const

const RESPONSE: AnalystResponse = {
  schema_version: 'butterflylens-analyst-response:v1.0.0',
  mode: 'live',
  response_state: 'completed',
  summary: 'The submitted catalogue contains evidence for this species.',
  claims: [{
    claim_id: 'claim_1',
    statement: 'The submitted catalogue contains evidence for this species.',
    evidence_state: 'direct',
    citation_ids: [CITATION.artifact_id],
  }],
  citations: [CITATION],
  limitations: ['This does not identify a photograph.'],
  tools_used: ['inspect_species'],
  model: { id: 'gpt-5.6-sol', reasoning_effort: 'xhigh' },
  usage: { response_calls: 2, tool_calls: 1, budget_state: 'within_budget' },
}

describe('analyst browser contract', () => {
  it('accepts the exact live evidence response', () => {
    expect(parseAnalystResponse(RESPONSE)).toEqual(RESPONSE)
  })

  it.each([
    ['extra root field', { ...RESPONSE, extra: true }],
    ['wrong model', { ...RESPONSE, model: { ...RESPONSE.model, id: 'gpt-5.6' } }],
    ['wrong mode', { ...RESPONSE, mode: 'stored' }],
    ['modified citation', { ...RESPONSE, citations: [{ ...CITATION, commit: 'not-a-commit' }] }],
    ['uncited claim', { ...RESPONSE, claims: [{ ...RESPONSE.claims[0], citation_ids: ['missing'] }] }],
    ['over-budget tools', { ...RESPONSE, usage: { ...RESPONSE.usage, tool_calls: 9 } }],
    ['refusal with claims', { ...RESPONSE, response_state: 'refused' }],
    ['completed summary without claims', { ...RESPONSE, claims: [] }],
  ])('rejects %s', (_label, value) => {
    expect(() => parseAnalystResponse(value)).toThrow()
  })

  it('keeps the submitted experience credential-free and offline', async () => {
    const result = await submittedAnalystClient({ question: 'Question?', history: [] })
    expect(result).toEqual({
      state: 'unavailable',
      reason: 'The submitted replay has no authenticated live analyst session. No OpenAI call was made.',
    })
  })

  it('does not call the function without an authenticated user token', async () => {
    const fetchImpl = vi.fn<typeof fetch>()
    const client = createSupabaseAnalystClient({
      supabaseUrl: 'https://example.supabase.co',
      publishableKey: 'publishable-key',
      getAccessToken: async () => null,
      fetchImpl,
    })

    await expect(client({ question: 'Question?', history: [] })).resolves.toMatchObject({
      state: 'unavailable',
      reason: expect.stringContaining('No model call was made'),
    })
    expect(fetchImpl).not.toHaveBeenCalled()
  })

  it('sends only Supabase credentials and validates the function response', async () => {
    const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(RESPONSE), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    const client = createSupabaseAnalystClient({
      supabaseUrl: 'https://example.supabase.co',
      publishableKey: 'publishable-key',
      getAccessToken: async () => 'user-jwt',
      fetchImpl,
    })

    await expect(client({ question: ' Question? ', history: [] })).resolves.toEqual({
      state: 'response',
      response: RESPONSE,
    })
    expect(fetchImpl).toHaveBeenCalledOnce()
    const [url, init] = fetchImpl.mock.calls[0]
    expect(String(url)).toBe('https://example.supabase.co/functions/v1/ask-butterflylens')
    expect(init?.method).toBe('POST')
    expect(init?.headers).toEqual({
      Authorization: 'Bearer user-jwt',
      apikey: 'publishable-key',
      'Content-Type': 'application/json',
    })
    expect(JSON.parse(String(init?.body))).toEqual({ question: ' Question? ', history: [] })
    expect(JSON.stringify(init)).not.toMatch(/OPENAI_API_KEY|OpenAI-Organization/u)
  })

  it('rejects insecure remote endpoints and missing publishable keys', () => {
    expect(() => createSupabaseAnalystClient({
      supabaseUrl: 'http://example.com',
      publishableKey: 'key',
      getAccessToken: async () => 'token',
    })).toThrow('HTTPS')
    expect(() => createSupabaseAnalystClient({
      supabaseUrl: 'https://example.supabase.co',
      publishableKey: '',
      getAccessToken: async () => 'token',
    })).toThrow('publishable key')
  })
})
