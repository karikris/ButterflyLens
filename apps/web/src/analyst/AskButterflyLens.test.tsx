import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { AskButterflyLens } from './AskButterflyLens'
import type { AnalystClient, AnalystResponse } from './analystModel'

const RESPONSE: AnalystResponse = {
  schema_version: 'butterflylens-analyst-response:v1.0.0',
  mode: 'live',
  response_state: 'completed',
  summary: 'The accepted species is present in the submitted catalogue.',
  claims: [{
    claim_id: 'claim_1',
    statement: 'The accepted species is present in the submitted catalogue.',
    evidence_state: 'direct',
    citation_ids: ['species-catalogue'],
  }],
  citations: [{
    artifact_id: 'species-catalogue',
    repository: 'karikris/ButterflyLens',
    commit: 'a'.repeat(40),
    path: 'data/derived/species_catalogue.json',
    fingerprint: `sha256:${'b'.repeat(64)}`,
  }],
  limitations: ['This does not identify a photograph.'],
  tools_used: ['inspect_species'],
  model: { id: 'gpt-5.6-sol', reasoning_effort: 'xhigh' },
  usage: { response_calls: 2, tool_calls: 1, budget_state: 'within_budget' },
}

describe('Ask ButterflyLens', () => {
  it('publishes the evidence boundary and an accessible bounded composer', () => {
    render(<AskButterflyLens />)

    expect(screen.getByRole('heading', { name: 'Ask ButterflyLens' })).toBeInTheDocument()
    expect(screen.getByText(/deterministic read-only tools/)).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Your evidence question' })).toHaveAttribute('maxlength', '1200')
    expect(screen.getByRole('button', { name: 'Replay stored evidence' })).toBeDisabled()
    expect(screen.getByText('Credential-free replay')).toBeInTheDocument()
    expect(screen.getByText(/invokes no model, tool, or network/)).toBeInTheDocument()
  })

  it('fills a suggested question and renders the exact stored replay trace', async () => {
    render(<AskButterflyLens />)

    fireEvent.click(screen.getByRole('button', { name: 'What evidence is available for Acraea andromacha?' }))
    expect(screen.getByRole('textbox', { name: 'Your evidence question' })).toHaveValue(
      'What evidence is available for Acraea andromacha?',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Replay stored evidence' }))
    expect(await screen.findByText('Replayed · completed')).toBeInTheDocument()
    expect(screen.getByText(/Model not invoked · replayed/)).toBeInTheDocument()
    expect(screen.getByText('1 stored tool call')).toBeInTheDocument()
    expect(screen.getByText('Stored tool trace (1)')).toBeInTheDocument()
    expect(screen.getByText('inspect_species')).toBeInTheDocument()
    expect(screen.getByText(/sha256:4402e9fd/)).toBeInTheDocument()
    expect(screen.getByText('apps/web/src/species/submittedSpeciesCatalogue.json')).toBeInTheDocument()
    expect(screen.queryByText(/Live ·/)).not.toBeInTheDocument()
  })

  it('renders a validated live answer with artifact and model provenance', async () => {
    const client: AnalystClient = async () => ({ state: 'response', response: RESPONSE })
    render(<AskButterflyLens client={client} clientMode="live" />)

    fireEvent.change(screen.getByRole('textbox', { name: 'Your evidence question' }), {
      target: { value: 'Inspect this species.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Ask with evidence' }))

    expect(await screen.findByText('Live · completed')).toBeInTheDocument()
    expect(screen.getAllByText(RESPONSE.claims[0].statement)).toHaveLength(2)
    expect(screen.getByText(RESPONSE.citations[0].path)).toBeInTheDocument()
    expect(screen.getByText(RESPONSE.citations[0].fingerprint)).toBeInTheDocument()
    expect(screen.getByText('gpt-5.6-sol · xhigh')).toBeInTheDocument()
    expect(screen.getByText('1/8 tool calls')).toBeInTheDocument()
  })

  it('does not expose thrown implementation errors', async () => {
    const client: AnalystClient = async () => {
      throw new Error('secret upstream detail')
    }
    render(<AskButterflyLens client={client} clientMode="live" />)
    fireEvent.change(screen.getByRole('textbox', { name: 'Your evidence question' }), {
      target: { value: 'Question?' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Ask with evidence' }))

    await waitFor(() => expect(screen.getByText(/failed closed/)).toBeInTheDocument())
    expect(screen.queryByText(/secret upstream detail/)).not.toBeInTheDocument()
  })
})
