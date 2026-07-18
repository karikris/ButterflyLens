import { useState } from 'react'
import type { FormEvent } from 'react'

import { EvidenceNotice, StateBadge } from '../design-system/EvidencePrimitives'
import {
  submittedAnalystClient,
  type AnalystClient,
  type AnalystResponse,
} from './analystModel'

const SUGGESTED_QUESTIONS = [
  'What evidence is available for Acraea andromacha?',
  'Can ALA and Flickr counts be compared yet?',
  'Which species should receive the next reference review?',
] as const

export function AskButterflyLens({
  client = submittedAnalystClient,
}: {
  readonly client?: AnalystClient
}) {
  const [question, setQuestion] = useState('')
  const [pending, setPending] = useState(false)
  const [response, setResponse] = useState<AnalystResponse | null>(null)
  const [unavailableReason, setUnavailableReason] = useState<string | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = question.trim()
    if (!trimmed || pending) return
    setPending(true)
    setResponse(null)
    setUnavailableReason(null)
    try {
      const result = await client({ question: trimmed, history: [] })
      if (result.state === 'response') setResponse(result.response)
      else setUnavailableReason(result.reason)
    } catch {
      setUnavailableReason('The analyst failed closed. No unsupported answer was returned.')
    } finally {
      setPending(false)
    }
  }

  return (
    <section
      className="analyst-experience"
      id="ask-butterflylens"
      aria-labelledby="ask-butterflylens-heading"
    >
      <div className="analyst-experience__intro">
        <div>
          <p className="eyebrow">Bounded evidence analyst</p>
          <h2 id="ask-butterflylens-heading">Ask ButterflyLens</h2>
          <p>
            Ask about submitted map scope, species maturity, evidence lineage,
            pipeline state, review priorities, or community impact.
          </p>
        </div>
        <StateBadge state="unfinished">Live session required</StateBadge>
      </div>

      <EvidenceNotice title="Evidence boundary" tone="caution">
        Answers must use deterministic read-only tools and exact artifact citations.
        The analyst does not identify butterflies from memory, turn missing evidence
        into zero, or create scientific authority.
      </EvidenceNotice>

      <div className="analyst-layout">
        <form className="analyst-composer" onSubmit={submit}>
          <label htmlFor="analyst-question">Your evidence question</label>
          <textarea
            id="analyst-question"
            value={question}
            maxLength={1200}
            rows={5}
            onChange={(event) => setQuestion(event.target.value)}
            aria-describedby="analyst-question-help analyst-question-count"
          />
          <div className="analyst-composer__meta">
            <span id="analyst-question-help">Do not include private or sensitive information.</span>
            <span id="analyst-question-count">{question.length}/1200</span>
          </div>
          <div className="analyst-suggestions" aria-label="Suggested questions">
            {SUGGESTED_QUESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                className="secondary-button"
                onClick={() => setQuestion(suggestion)}
              >
                {suggestion}
              </button>
            ))}
          </div>
          <button
            className="analyst-submit"
            type="submit"
            disabled={pending || question.trim().length === 0}
          >
            {pending ? 'Checking evidence…' : 'Ask with evidence'}
          </button>
        </form>

        <div className="analyst-result" aria-live="polite" aria-busy={pending}>
          {pending ? <p>Running bounded evidence tools…</p> : null}
          {unavailableReason ? (
            <EvidenceNotice announce title="Live analyst unavailable" tone="information">
              {unavailableReason}
            </EvidenceNotice>
          ) : null}
          {response ? <AnalystAnswer response={response} /> : null}
          {!pending && !unavailableReason && !response ? (
            <div className="analyst-result__empty">
              <strong>No answer has been requested.</strong>
              <p>
                Live answers require an authenticated server session. Task 11.4 adds
                a visibly labelled credential-free stored replay.
              </p>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  )
}

function AnalystAnswer({ response }: { readonly response: AnalystResponse }) {
  return (
    <article className="analyst-answer">
      <header>
        <StateBadge
          state={
            response.response_state === 'completed'
              ? 'verified'
              : response.response_state === 'refused'
                ? 'critical'
                : 'caution'
          }
        >
          Live · {response.response_state}
        </StateBadge>
        <p>{response.summary}</p>
      </header>
      {response.claims.length > 0 ? (
        <ol className="analyst-claims" aria-label="Evidence claims">
          {response.claims.map((claim) => (
            <li key={claim.claim_id}>
              <span>{claim.evidence_state}</span>
              <p>{claim.statement}</p>
              <small>Citations: {claim.citation_ids.join(', ')}</small>
            </li>
          ))}
        </ol>
      ) : null}
      {response.limitations.length > 0 ? (
        <div className="analyst-limitations">
          <h3>Limits</h3>
          <ul>{response.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
        </div>
      ) : null}
      {response.citations.length > 0 ? (
        <details className="analyst-citations">
          <summary>Artifact citations ({response.citations.length})</summary>
          <dl>
            {response.citations.map((citation) => (
              <div key={citation.artifact_id}>
                <dt>{citation.artifact_id}</dt>
                <dd>{citation.path}</dd>
                <dd>Commit {citation.commit.slice(0, 12)}</dd>
                <dd>{citation.fingerprint}</dd>
              </div>
            ))}
          </dl>
        </details>
      ) : null}
      <footer>
        <span>{response.model.id} · {response.model.reasoning_effort}</span>
        <span>{response.usage.tool_calls}/8 tool calls</span>
      </footer>
    </article>
  )
}
