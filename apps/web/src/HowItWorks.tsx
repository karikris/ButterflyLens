import { EvidenceNotice } from './design-system/EvidencePrimitives'

const pipelineStages = [
  'ALA authority snapshot is ingested as a complete, rights-screened baseline.',
  'Flickr discovery candidates are generated from taxonomy-aware query plans.',
  'Every candidate image stays as candidate evidence until screened.',
  'Community members provide blind review decisions and comments locally.',
  'Review receipts feed release-boundary indicators and map updates.',
] as const

export function HowItWorks() {
  return (
    <section
      id="how-it-works"
      className="how-it-works"
      aria-labelledby="how-it-works-heading"
    >
      <header className="how-it-works__intro">
        <div>
          <p className="eyebrow">How ButterflyLens works</p>
          <h2 id="how-it-works-heading">Evidence moves only by evidence gates.</h2>
          <p>
            This surface is intentionally concise. Model outputs, rights boundaries,
            and final release limits are separated so the workflow remains auditable.
          </p>
        </div>
      </header>

      <ol className="how-it-works__pipeline" aria-label="Five-stage pipeline">
        {pipelineStages.map((description, index) => (
          <li key={description}>
            <span aria-hidden="true">Stage {index + 1}</span>
            <p>{description}</p>
          </li>
        ))}
      </ol>

      <EvidenceNotice title="Scientific boundary" tone="caution">
        This flow does not add model memory. Model labels stay separate from
        human review and from occurrence release boundaries.
      </EvidenceNotice>
    </section>
  )
}
