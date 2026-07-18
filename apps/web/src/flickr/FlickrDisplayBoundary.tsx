import { EvidenceNotice, StateBadge } from '../design-system/EvidencePrimitives'
import {
  FLICKR_NOTICE,
  evaluateFlickrDisplayPage,
  submittedFlickrDisplayContext,
  type FlickrDisplayContext,
} from './flickrDisplayModel'

const submittedTime = '2026-07-18T04:59:50Z'

export function FlickrDisplayBoundary({
  items = [],
  context = submittedFlickrDisplayContext,
  now = submittedTime,
}: {
  readonly items?: readonly unknown[]
  readonly context?: FlickrDisplayContext
  readonly now?: string
}) {
  let decision
  try {
    decision = evaluateFlickrDisplayPage(items, context, now)
  } catch (error) {
    decision = {
      state: 'blocked' as const,
      items: [],
      reason:
        error instanceof Error
          ? `Public display blocked: ${error.message}.`
          : 'Public display blocked by an unknown policy error.',
    }
  }

  return (
    <section
      id="flickr-display-policy"
      className="flickr-display-boundary"
      aria-labelledby="flickr-display-heading"
    >
      <header>
        <div>
          <p className="eyebrow">Rights before reach</p>
          <h2 id="flickr-display-heading">Flickr public display gate</h2>
          <p>
            Every public photo must pass application, owner, licence, cache,
            privacy, attribution, and removal checks. Discovery is not display
            permission or species identity.
          </p>
        </div>
        <StateBadge state={decision.state === 'eligible' ? 'submitted' : 'critical'}>
          {decision.items.length} Flickr photos displayed
        </StateBadge>
      </header>

      <EvidenceNotice
        title={decision.state === 'eligible' ? 'Display gate passed' : 'Display remains blocked'}
        tone={decision.state === 'eligible' ? 'information' : 'critical'}
      >
        {decision.reason} The active parallel fetch and its partial outputs are
        not public evidence.
      </EvidenceNotice>

      {decision.items.length === 0 ? null : (
        <ul className="flickr-display-grid" aria-label="Rights-approved Flickr photos">
          {decision.items.map((item) => (
            <li key={item.display_asset_id}>
              <figure>
                <img src={item.image_url} alt={item.title} />
                <figcaption>
                  <strong>{item.title || 'Untitled photograph'}</strong>
                  <span>Photographer: {item.photographer}</span>
                  <span>{item.attribution}</span>
                  <span>
                    <a href={item.source_url}>View the original photo on Flickr</a>
                    {' · '}
                    <a href={item.licence_url}>{item.licence_id}</a>
                  </span>
                </figcaption>
              </figure>
            </li>
          ))}
        </ul>
      )}

      <div className="flickr-display-boundary__rules">
        <section aria-labelledby="flickr-page-rules-heading">
          <h3 id="flickr-page-rules-heading">Page and attribution gate</h3>
          <ul>
            <li>At most 30 Flickr user photos on one page.</li>
            <li>Exact source, photographer, licence, and attribution per photo.</li>
            <li>No Flickr logo, endorsement claim, private image, or remote thumbnail.</li>
          </ul>
        </section>
        <section aria-labelledby="flickr-removal-rules-heading">
          <h3 id="flickr-removal-rules-heading">Cache and removal gate</h3>
          <ul>
            <li>Visibility and licence revalidated within 24 hours.</li>
            <li>Private or removal-requested media quarantined immediately.</li>
            <li>Owner requests completed within 24 hours across dependencies.</li>
          </ul>
        </section>
      </div>

      <p className="flickr-display-boundary__notice">{FLICKR_NOTICE}</p>
      <p className="flickr-display-boundary__removal">
        Photo owners and rights holders can request removal through the{' '}
        <a href="https://github.com/karikris/ButterflyLens/blob/main/DATA_RIGHTS.md#removal-and-downstream-invalidation">
          documented removal workflow
        </a>
        .
      </p>
    </section>
  )
}
