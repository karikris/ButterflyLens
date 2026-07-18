import { useState } from 'react'
import type { FormEvent } from 'react'

import { EvidenceNotice, StateBadge } from '../design-system/EvidencePrimitives'
import {
  submittedAnalystClient,
  type AnalystClient,
  type AnalystClientResult,
  type AnalystPresentation,
  type StoredToolTrace,
} from './analystModel'

const SUGGESTED_QUESTIONS = [
  'What evidence is available for Acraea andromacha?',
  'Can ALA and Flickr counts be compared yet?',
  'Which species should receive the next reference review?',
] as const

export function AskButterflyLens({
  client = submittedAnalystClient,
  clientMode = 'replayed',
}: {
  readonly client?: AnalystClient
  readonly clientMode?: 'live' | 'replayed'
}) {
  const [question, setQuestion] = useState('')
  const [pending, setPending] = useState(false)
  const [answer, setAnswer] = useState<Extract<AnalystClientResult, { state: 'response' }> | null>(null)
  const [unavailableReason, setUnavailableReason] = useState<string | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = question.trim()
    if (!trimmed || pending) return
    setPending(true)
    setAnswer(null)
    setUnavailableReason(null)
    try {
      const result = await client({ question: trimmed, history: [] })
      if (result.state === 'response') setAnswer(result)
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
        <StateBadge state={clientMode === 'live' ? 'unfinished' : 'submitted'}>
          {clientMode === 'live' ? 'Live session required' : 'Credential-free replay'}
        </StateBadge>
      </div>

      <EvidenceNotice title="Evidence boundary" tone="caution">
        Answers must use deterministic read-only tools and exact artifact citations.
        The analyst does not identify butterflies from memory, turn missing evidence
        into zero, or create scientific authority.
        {clientMode === 'replayed' ? (
          <> The submitted replay loads exact stored calls and outputs; it invokes no model, tool, or network.</>
        ) : null}
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
            {pending
              ? clientMode === 'live' ? 'Checking evidence…' : 'Loading stored evidence…'
              : clientMode === 'live' ? 'Ask with evidence' : 'Replay stored evidence'}
          </button>
        </form>

        <div className="analyst-result" aria-live="polite" aria-busy={pending}>
          {pending ? (
            <p>{clientMode === 'live' ? 'Running bounded evidence tools…' : 'Validating stored fingerprints…'}</p>
          ) : null}
          {unavailableReason ? (
            <EvidenceNotice
              announce
              title={clientMode === 'live' ? 'Live analyst unavailable' : 'Stored replay unavailable'}
              tone="information"
            >
              {unavailableReason}
            </EvidenceNotice>
          ) : null}
          {answer ? (
            <AnalystAnswer
              response={answer.response}
              replayTrace={answer.replay_trace ?? []}
            />
          ) : null}
          {!pending && !unavailableReason && !answer ? (
            <div className="analyst-result__empty">
              <strong>No answer has been requested.</strong>
              <p>
                {clientMode === 'live'
                  ? 'Live answers require an authenticated server session.'
                  : 'Choose one of the three exact questions to inspect its stored, fingerprinted tool trace.'}
              </p>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  )
}

function AnalystAnswer({
  response,
  replayTrace,
}: {
  readonly response: AnalystPresentation
  readonly replayTrace: readonly StoredToolTrace[]
}) {
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
          {response.mode === 'live' ? 'Live' : 'Replayed'} · {response.response_state}
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
      {response.mode === 'replayed' ? (
        <details className="analyst-trace">
          <summary>Stored tool trace ({replayTrace.length})</summary>
          <ol>
            {replayTrace.map((item) => (
              <li key={item.call_id}>
                <strong>{item.name}</strong>
                <span>Call {item.call_id}</span>
                <span>Arguments {JSON.stringify(item.arguments)}</span>
                <span>Output {item.output.status}: {item.output.summary}</span>
                <span>{item.output.result_fingerprint}</span>
              </li>
            ))}
          </ol>
        </details>
      ) : null}
      <footer>
        {response.mode === 'live' ? (
          <>
            <span>{response.model.id} · {response.model.reasoning_effort}</span>
            <span>{response.usage.tool_calls}/8 tool calls</span>
          </>
        ) : (
          <>
            <span>Model not invoked · replayed {response.replay.recorded_at}</span>
            <span>{response.replay.tool_calls} stored tool call</span>
          </>
        )}
      </footer>
    </article>
  )
}
