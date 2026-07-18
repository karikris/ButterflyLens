import { useId, useMemo, useState } from 'react'

import { EvidenceNotice } from '../design-system/EvidencePrimitives'
import {
  blindReviewFieldLabels,
  blindReviewFields,
  submittedReviewDisclosure,
  type ReviewDisclosure,
} from './blindReviewModel'
import {
  reviewOutcomeLabels,
  type ReviewLandingItem,
  type ReviewOutcome,
} from './reviewLandingModel'

const scientificOutcomes: readonly ReviewOutcome[] = [
  'yes',
  'no',
  'cant_tell',
]

const allOutcomes: readonly ReviewOutcome[] = [
  ...scientificOutcomes,
  'cant_view',
  'skip',
]

export function ReviewLanding({
  item,
  qualifiedReviewer,
  disclosure = submittedReviewDisclosure,
}: {
  readonly item: ReviewLandingItem
  readonly qualifiedReviewer: boolean
  readonly disclosure?: ReviewDisclosure
}) {
  const [comment, setComment] = useState('')
  const [alternativeTaxon, setAlternativeTaxon] = useState('')
  const [outcome, setOutcome] = useState<ReviewOutcome | null>(null)
  const [verifiedImageDisplayed, setVerifiedImageDisplayed] = useState(false)
  const [decisionLocked, setDecisionLocked] = useState(false)
  const [contextRevealed, setContextRevealed] = useState(false)
  const readinessId = useId()

  const scientificDecisionReady =
    item.media.state === 'verified' && verifiedImageDisplayed
  const contributionSummary = useMemo(
    () =>
      outcome === null
        ? 'No decision selected'
        : reviewOutcomeLabels[outcome],
    [outcome],
  )

  function revealPermittedContext() {
    if (outcome === null) return
    setDecisionLocked(true)
    setContextRevealed(true)
  }

  function startNewDraft() {
    setOutcome(null)
    setComment('')
    setAlternativeTaxon('')
    setDecisionLocked(false)
    setContextRevealed(false)
  }

  return (
    <article id="verify" className="review-landing" aria-labelledby="review-heading">
      <header className="review-intro">
        <div>
          <p className="eyebrow">Help verify Australia’s butterfly evidence</p>
          <h2 id="review-heading">One careful look can strengthen the record.</h2>
          <p className="review-intro__lede">
            Review what is visible, abstain when evidence is weak, and leave the
            scientific release decision to the full evidence process.
          </p>
        </div>
        <div className="review-count" aria-label="Review queue position">
          <strong>1</strong>
          <span>image awaiting review</span>
        </div>
      </header>

      <EvidenceNotice
        className="review-evidence-notice"
        title="Independent review"
      >
        model labels, model scores, search terms, source comments, and other
        reviewers’ decisions are hidden.
      </EvidenceNotice>

      <div className="review-grid">
        <section className="media-card" aria-labelledby="review-image-heading">
          <div className="card-kicker">
            <span>{item.campaignName}</span>
            <span>Awaiting review</span>
          </div>
          <div className="media-frame bl-photo-frame">
            {item.media.state === 'verified' ? (
              <img
                src={item.media.src}
                alt={item.media.alt}
                onLoad={() => setVerifiedImageDisplayed(true)}
                onError={() => setVerifiedImageDisplayed(false)}
              />
            ) : (
              <div
                className="media-unavailable"
                role="img"
                aria-label="Review image unavailable"
              >
                <span className="media-unavailable__icon" aria-hidden="true">
                  ×
                </span>
                <strong>Image can’t be displayed</strong>
                <span>{item.media.reason}</span>
              </div>
            )}
          </div>
          <div className="media-card__body">
            {item.media.state === 'verified' ? (
              <p className="media-attribution">
                Image by {item.media.creator}.{' '}
                <a href={item.media.licenseUri}>{item.media.licenseName}</a>.
                Full source attribution stays withheld until the draft decision
                is locked.
              </p>
            ) : null}
            <h2 id="review-image-heading">{item.question}</h2>
            <p id={readinessId} className="readiness" role="status">
              {scientificDecisionReady
                ? 'Integrity-checked media displayed. Scientific review choices are available.'
                : 'Yes, No, and Can’t tell require the integrity-checked image to be displayed. Can’t view and Skip remain available.'}
            </p>
            <p className="item-id">Review item · {item.itemId}</p>
          </div>
        </section>

        <form className="decision-card" onSubmit={(event) => event.preventDefault()}>
          <div>
            <p className="eyebrow">Your assessment</p>
            <h2>What can you support from this image?</h2>
          </div>
          <fieldset>
            <legend>Choose one response</legend>
            <div className="decision-buttons">
              {allOutcomes.map((candidateOutcome) => {
                const scientific = scientificOutcomes.includes(candidateOutcome)
                return (
                  <button
                    key={candidateOutcome}
                    type="button"
                    data-outcome={candidateOutcome}
                    aria-pressed={outcome === candidateOutcome}
                    aria-describedby={scientific ? readinessId : undefined}
                    disabled={decisionLocked || (scientific && !scientificDecisionReady)}
                    onClick={() => setOutcome(candidateOutcome)}
                  >
                    {reviewOutcomeLabels[candidateOutcome]}
                  </button>
                )
              })}
            </div>
          </fieldset>
          <label className="field-label">
            Comment <span>optional</span>
            <textarea
              rows={4}
              value={comment}
              disabled={decisionLocked}
              placeholder="Note a visible feature, ambiguity, or media problem."
              onChange={(event) => setComment(event.target.value)}
            />
          </label>
          <label className="field-label">
            Alternative taxon <span>qualified reviewers only</span>
            <input
              type="text"
              value={alternativeTaxon}
              disabled={!qualifiedReviewer || decisionLocked}
              aria-describedby="alternative-taxon-help"
              placeholder={qualifiedReviewer ? 'Accepted taxon name or key' : ''}
              onChange={(event) => setAlternativeTaxon(event.target.value)}
            />
          </label>
          <p id="alternative-taxon-help" className="field-help">
            {qualifiedReviewer
              ? 'Suggest an accepted taxon only when the displayed evidence supports it.'
              : 'Your current reviewer role cannot propose a taxon. You can still leave a comment.'}
          </p>
        </form>
      </div>

      <section className="blind-context" aria-labelledby="blind-context-heading">
        <div>
          <p className="eyebrow">Blind review context</p>
          <h2 id="blind-context-heading">
            {contextRevealed ? 'Permitted context revealed' : 'Withheld until decision'}
          </h2>
        </div>
        {contextRevealed ? (
          <div className="blind-context__revealed" role="status">
            <p>
              The draft decision is now locked locally. Revealed context cannot
              change it; start a new draft to return to a blind state.
            </p>
            {item.media.state === 'verified' ? (
              <p>
                <strong>Source:</strong> {item.media.attribution}.{' '}
                <a href={item.media.sourceUri}>Wikimedia Commons source</a>.
              </p>
            ) : null}
            <dl>
              <DisclosureValue label="Model label" value={disclosure.modelLabel} />
              <DisclosureValue label="Model score band" value={disclosure.modelScoreBand} />
              <DisclosureValue label="Flickr query term" value={disclosure.flickrQueryTerm} />
              <DisclosureValue
                label="Source comment"
                value={disclosure.sourceCommentExcerpt}
              />
              <DisclosureValue
                label="Peer summary"
                value={formatPeerSummary(disclosure)}
              />
            </dl>
            <p className="blind-context__reason">{disclosure.reason}</p>
            <button type="button" className="secondary-button" onClick={startNewDraft}>
              Start a new blind draft
            </button>
          </div>
        ) : (
          <div>
            <p>
              The following context is absent from this decision surface and is
              not merely visually obscured:
            </p>
            <ul>
              {blindReviewFields.map((field) => (
                <li key={field}>{blindReviewFieldLabels[field]}</li>
              ))}
            </ul>
            <button
              type="button"
              className="secondary-button"
              disabled={outcome === null}
              onClick={revealPermittedContext}
            >
              Lock draft decision and reveal permitted context
            </button>
          </div>
        )}
      </section>

      <div className="review-context-grid">
        <section className="map-card" aria-labelledby="map-preview-heading">
          <div>
            <p className="eyebrow">Map preview</p>
            <h2 id="map-preview-heading">{item.regionLabel}</h2>
          </div>
          <div className="map-preview" role="img" aria-label="Australia location unavailable">
            <svg viewBox="0 0 420 210" aria-hidden="true">
              <path
                d="M94 119 115 81l52-18 46 12 31-23 53 19 18 39-21 47-53 9-35-16-39 19-52-12Z"
              />
              <circle cx="323" cy="176" r="9" />
              <path className="map-preview__dash" d="M52 177h316" />
            </svg>
            <span>Record location unavailable</span>
          </div>
          <p className="map-card__note">{item.locationReason}</p>
          <dl className="map-facts">
            <div>
              <dt>Location state</dt>
              <dd>{item.locationState}</dd>
            </div>
            <div>
              <dt>Coordinates</dt>
              <dd>Not exposed</dd>
            </div>
          </dl>
        </section>

        <aside className="contribution-card" aria-labelledby="contribution-heading">
          <div>
            <p className="eyebrow">Current contribution</p>
            <h2 id="contribution-heading">Draft review</h2>
          </div>
          <dl>
            <div>
              <dt>Decision</dt>
              <dd>{contributionSummary}</dd>
            </div>
            <div>
              <dt>Comment</dt>
              <dd>{comment.trim() === '' ? 'No comment' : comment}</dd>
            </div>
            <div>
              <dt>Alternative taxon</dt>
              <dd>
                {alternativeTaxon.trim() === ''
                  ? 'None proposed'
                  : alternativeTaxon}
              </dd>
            </div>
          </dl>
          <p className="draft-notice">
            Draft only — this page does not submit or claim a stored review.
          </p>
        </aside>
      </div>
    </article>
  )
}

function DisclosureValue({ label, value }: { readonly label: string; readonly value: string | null }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value ?? 'Unavailable'}</dd>
    </div>
  )
}

function formatPeerSummary(disclosure: ReviewDisclosure): string | null {
  const summary = disclosure.peerSummary
  if (summary === null) return null
  return `${summary.decisive} decisive · ${summary.yes} yes · ${summary.no} no · ${summary.uncertain} uncertain`
}
