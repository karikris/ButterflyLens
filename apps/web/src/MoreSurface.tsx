import { EvidenceNotice } from './design-system/EvidencePrimitives'
import { RoutePreview } from './shell/PublicShell'
import { SpeciesDirectory } from './species/SpeciesDirectory'
import { FlickrDisplayBoundary } from './flickr/FlickrDisplayBoundary'
import { OperationsDashboard } from './operations/OperationsDashboard'
import { QualityDashboard } from './quality/QualityDashboard'
import {
  submittedQualityDashboard,
} from './quality/qualityDashboardModel'

const moreTopics = [
  {
    id: 'more-evidence-lens',
    kicker: 'Evidence Lens',
    title: 'Accepted taxonomy and crosswalk diagnostics',
    description:
      'Explore accepted species, source assertions, and conservative provider alignments.',
  },
  {
    id: 'more-model-reference-evidence',
    kicker: 'Model and reference evidence',
    title: 'Reference diagnostics and screening status',
    description:
      'Track where model support is present, provisional, or unavailable.',
  },
  {
    id: 'more-data-quality',
    kicker: 'Data quality',
    title: 'Representative quality and blockers',
    description:
      'Inspect audit availability, blocker lists, and species-level quality signals.',
  },
  {
    id: 'more-data-governance',
    kicker: 'Data governance',
    title: 'Rights, attribution, and release rules',
    description: 'Public evidence boundaries and legal constraints remain explicit.',
  },
  {
    id: 'more-rights',
    kicker: 'Rights and attribution',
    title: 'What is and is not publishable',
    description: 'Map display and media access are rights-screened and withdrawal-aware.',
  },
  {
    id: 'more-provenance',
    kicker: 'Provenance',
    title: 'Snapshot lineage and contract integrity',
    description:
      'Each surface links the active evidence and map state to immutable artifact records.',
  },
  {
    id: 'more-live-ops',
    kicker: 'Live operations',
    title: 'Public worker and worker-independent artifacts',
    description:
      'Understand which operational signals are live and which remain committed.',
  },
  {
    id: 'more-exports',
    kicker: 'Exports',
    title: 'Governed release pathways',
    description:
      'Export surfaces are governed by explicit release gates and rights artifacts.',
  },
  {
    id: 'more-research-methods',
    kicker: 'Research methods',
    title: 'Methods by design boundary',
    description:
      'Human review, model screening, and release qualification remain separable and auditable.',
  },
]

export function MoreSurface({
  monitoringUrl,
}: {
  readonly monitoringUrl: string | null
}) {
  return (
    <section id="more" className="more-surface" aria-labelledby="more-heading">
      <header className="more-surface__intro">
        <div>
          <p className="eyebrow">More ▾</p>
          <h2 id="more-heading">Advanced project surfaces</h2>
          <p>
            These surfaces remain available for specialist work while the core
            public path stays focused on impact and immediate review.
          </p>
        </div>
      </header>

      <div className="more-surface__previews" role="list" aria-label="Advanced surface index">
        {moreTopics.map((topic) => (
          <RoutePreview
            key={topic.id}
            id={topic.id}
            kicker={topic.kicker}
            title={topic.title}
            description={topic.description}
          />
        ))}
      </div>

      <EvidenceNotice title="Advanced materials are not hidden history" tone="information">
        Legacy and draft assets are preserved where scientifically useful. These surfaces
        are grouped for context and are not the public-first review path.
      </EvidenceNotice>

      <section className="more-surface__surface" aria-labelledby="evidence-lens-heading">
        <p className="eyebrow">Evidence Lens</p>
        <h3 id="evidence-lens-heading">Evidence Lens</h3>
        <SpeciesDirectory />
      </section>

      <section aria-labelledby="model-reference-heading" className="more-surface__surface">
        <p className="eyebrow">Model and reference evidence</p>
        <h3 id="model-reference-heading">Reference diagnostics</h3>
        <FlickrDisplayBoundary />
      </section>

      <section aria-labelledby="data-quality-heading" className="more-surface__surface">
        <p className="eyebrow">Data quality</p>
        <h3 id="data-quality-heading">Quality and blockers</h3>
        <QualityDashboard snapshot={submittedQualityDashboard} />
      </section>

      <section aria-labelledby="provenance-heading" className="more-surface__surface">
        <p className="eyebrow">Data provenance and operations</p>
        <h3 id="provenance-heading">Operations and snapshot provenance</h3>
        <OperationsDashboard monitoringUrl={monitoringUrl} />
      </section>
    </section>
  )
}
