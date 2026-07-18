import { useMemo, useState } from 'react'

import { EvidenceNotice, StateBadge } from '../design-system/EvidencePrimitives'
import reviewMediaManifest from '../review/reviewMediaManifest.json'
import {
  submittedSpeciesCatalogue,
  type SpeciesCatalogue,
  type SpeciesCatalogueEntry,
  type SpeciesProviderMatch,
} from './speciesCatalogueModel'

const FEATURED_PHOTO_TAXON_KEY = 'bltx:v1:2e0d17436e8a7d6211d5bf72'
const numberFormatter = new Intl.NumberFormat('en-AU')

export function SpeciesDirectory({
  catalogue = submittedSpeciesCatalogue,
}: {
  readonly catalogue?: SpeciesCatalogue
}) {
  const families = useMemo(
    () =>
      Array.from(
        new Set(
          catalogue.species.map(
            (species) => species.hierarchy.family.acceptedScientificName,
          ),
        ),
      ).sort((first, second) => first.localeCompare(second, 'en-AU')),
    [catalogue],
  )
  const [query, setQuery] = useState('')
  const [family, setFamily] = useState('all')
  const [selectedKey, setSelectedKey] = useState(FEATURED_PHOTO_TAXON_KEY)
  const filteredSpecies = useMemo(() => {
    const normalizedQuery = normalize(query)
    return catalogue.species.filter((species) => {
      const familyMatches =
        family === 'all' ||
        species.hierarchy.family.acceptedScientificName === family
      if (!familyMatches) return false
      if (normalizedQuery === '') return true
      return searchableText(species).includes(normalizedQuery)
    })
  }, [catalogue, family, query])
  const selectedSpecies =
    filteredSpecies.find((species) => species.key === selectedKey) ??
    filteredSpecies[0] ??
    null

  return (
    <section
      id="species"
      className="species-directory"
      aria-labelledby="species-directory-heading"
    >
      <header className="species-directory__intro">
        <div>
          <p className="eyebrow">Australian field guide</p>
          <h2 id="species-directory-heading">Meet the accepted butterfly catalogue.</h2>
          <p>
            Browse every accepted species in the frozen Australian Faunal
            Directory hierarchy. Names, crosswalks, provisional references,
            and unresolved evidence stay visibly separate.
          </p>
        </div>
        <StateBadge state="submitted">
          {numberFormatter.format(catalogue.speciesCount)} accepted species
        </StateBadge>
      </header>

      <EvidenceNotice title="Catalogue boundary" tone="caution">
        Taxonomy is an accepted authority snapshot. English names are source
        assertions awaiting review. This surface makes no occurrence,
        distribution, identity, or release-ready claim.
      </EvidenceNotice>

      <div className="species-controls" role="search">
        <label>
          Search species
          <input
            type="search"
            value={query}
            placeholder="Scientific, English, genus, or family name"
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <label>
          Family
          <select value={family} onChange={(event) => setFamily(event.target.value)}>
            <option value="all">All six families</option>
            {families.map((familyName) => (
              <option key={familyName} value={familyName}>
                {familyName}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="species-controls__clear"
          disabled={query === '' && family === 'all'}
          onClick={() => {
            setQuery('')
            setFamily('all')
          }}
        >
          Clear filters
        </button>
        <output aria-live="polite">
          {numberFormatter.format(filteredSpecies.length)} species shown
        </output>
      </div>

      <div className="species-directory__layout">
        <section className="species-results" aria-labelledby="species-results-heading">
          <header>
            <p className="eyebrow">Catalogue index</p>
            <h3 id="species-results-heading">Choose a species page</h3>
          </header>
          {filteredSpecies.length > 0 ? (
            <ol aria-label="Australian butterfly species">
              {filteredSpecies.map((species) => {
                const commonName = species.englishNames[0]?.name
                const selected = selectedSpecies?.key === species.key
                return (
                  <li key={species.key}>
                    <button
                      type="button"
                      aria-pressed={selected}
                      aria-label={`Open species page for ${
                        commonName === undefined ? '' : `${commonName}, `
                      }${species.acceptedScientificName}`}
                      onClick={() => setSelectedKey(species.key)}
                    >
                      {commonName === undefined ? (
                        <span className="species-result__gap">English name unavailable</span>
                      ) : (
                        <strong>{commonName}</strong>
                      )}
                      <i>{species.acceptedScientificName}</i>
                      <small>{species.hierarchy.family.acceptedScientificName}</small>
                    </button>
                  </li>
                )
              })}
            </ol>
          ) : (
            <div className="species-results__empty" role="status">
              <strong>No catalogue match</strong>
              <p>Try a scientific name, an English source name, or another family.</p>
            </div>
          )}
        </section>

        {selectedSpecies === null ? null : (
          <SpeciesProfile species={selectedSpecies} catalogue={catalogue} />
        )}
      </div>
    </section>
  )
}

function SpeciesProfile({
  catalogue,
  species,
}: {
  readonly catalogue: SpeciesCatalogue
  readonly species: SpeciesCatalogueEntry
}) {
  const commonName = species.englishNames[0]?.name
  return (
    <article
      className="species-profile"
      aria-labelledby="selected-species-heading"
      data-species-key={species.key}
    >
      <p className="bl-visually-hidden" role="status">
        Showing species page for {species.acceptedScientificName}
      </p>
      <header className="species-profile__header">
        <div>
          <p className="eyebrow">
            {commonName ?? 'English source name unavailable'}
          </p>
          <h3 id="selected-species-heading">
            <i>{species.acceptedScientificName}</i>
          </h3>
          <p>{species.sourceTitle}</p>
        </div>
        <div className="species-profile__states">
          <StateBadge state="submitted">Accepted taxonomy snapshot</StateBadge>
          <StateBadge state={crosswalkBadgeState(species.crosswalk.status)}>
            {crosswalkLabel(species.crosswalk.status)}
          </StateBadge>
        </div>
      </header>

      <div className="species-profile__lead">
        <SpeciesPhoto species={species} />
        <section aria-labelledby="taxonomy-heading">
          <p className="eyebrow">Accepted hierarchy</p>
          <h4 id="taxonomy-heading">Taxonomic placement</h4>
          <dl className="species-taxonomy">
            {['family', 'subfamily', 'tribe', 'genus'].map((rank) => {
              const value = species.hierarchy[rank]
              return value === undefined ? null : (
                <div key={rank}>
                  <dt>{titleCase(rank)}</dt>
                  <dd>
                    <i>{value.acceptedScientificName}</i>
                  </dd>
                </div>
              )
            })}
          </dl>
          <p className="species-profile__source">
            Source: Australian Faunal Directory, retrieved{' '}
            <time dateTime={species.sourceRetrievedAt}>
              {formatDate(species.sourceRetrievedAt)}
            </time>
            . <a href={species.sourceUrl}>Open the source taxon record</a>.
          </p>
        </section>
      </div>

      <div className="species-profile__detail-grid">
        <section className="species-panel" aria-labelledby="species-names-heading">
          <div>
            <p className="eyebrow">Name evidence</p>
            <h4 id="species-names-heading">Source-reported names</h4>
          </div>
          <NameAssertions species={species} />
          <EvidenceNotice title="First Nations language names">
            {catalogue.firstNationsNameBoundary.reason}
          </EvidenceNotice>
        </section>

        <section className="species-panel" aria-labelledby="species-crosswalk-heading">
          <div>
            <p className="eyebrow">Provider identity</p>
            <h4 id="species-crosswalk-heading">Conservative crosswalk</h4>
          </div>
          <div className="species-table-scroll">
            <table>
              <caption>Provider relationships for this accepted taxon</caption>
              <thead>
                <tr>
                  <th scope="col">Provider</th>
                  <th scope="col">State</th>
                  <th scope="col">Identifier or reason</th>
                </tr>
              </thead>
              <tbody>
                {species.crosswalk.providers.map((provider) => (
                  <ProviderRow key={provider.provider} provider={provider} />
                ))}
              </tbody>
            </table>
          </div>
          {species.crosswalk.openConflicts.length > 0 ? (
            <EvidenceNotice title="Open provider conflict" tone="caution">
              {species.crosswalk.openConflicts
                .map(
                  (conflict) =>
                    `${providerLabel(conflict.provider)}: ${conflict.reasons
                      .map(humanizeIdentifier)
                      .join(', ')}`,
                )
                .join('; ')}
              . No automatic resolution is permitted.
            </EvidenceNotice>
          ) : null}
        </section>
      </div>

      <section className="species-evidence" aria-labelledby="species-evidence-heading">
        <header>
          <div>
            <p className="eyebrow">Evidence coverage</p>
            <h4 id="species-evidence-heading">What the submitted artifacts support</h4>
          </div>
          <StateBadge state={coverageBadgeState(species.referenceCoverage.status)}>
            {coverageLabel(species.referenceCoverage.status)}
          </StateBadge>
        </header>
        <dl>
          <EvidenceFact
            label="Provider candidate media"
            value={species.referenceCoverage.candidateMediaCount}
          />
          <EvidenceFact
            label="Automated-gate eligible"
            value={species.referenceCoverage.automatedGateEligibleCount}
          />
          <EvidenceFact
            label="Selected media"
            value={species.referenceCoverage.selectedCount}
          />
          <EvidenceFact
            label="Valid decodes"
            value={species.referenceCoverage.validDecodeCount}
          />
          <EvidenceFact
            label="Human-verified media"
            value={species.referenceCoverage.humanVerifiedCount}
          />
        </dl>
        <p>
          Counts above are provisional workflow diagnostics—not verified species
          identities or occurrence records. YOLOE and BioCLIP are unfinished;
          model evidence is unavailable, not negative evidence.
        </p>
        <ul aria-label="Active species evidence flags">
          {species.referenceCoverage.qualityFlags.map((flag) => (
            <li key={flag}>{humanizeIdentifier(flag)}</li>
          ))}
        </ul>
      </section>

      <EvidenceNotice title="ALA occurrence evidence withheld" tone="caution">
        {catalogue.alaOccurrenceBoundary.reason} Rights review remains open for{' '}
        {catalogue.alaOccurrenceBoundary.rightsReviewRequiredDatasetUids.join(', ')}.
      </EvidenceNotice>

      <details className="species-provenance">
        <summary>Species-page evidence and provenance</summary>
        <dl>
          <EvidenceFact label="ButterflyLens taxon key" value={species.key} code />
          <EvidenceFact
            label="Reference evidence"
            value={species.referenceCoverage.evidenceFingerprint}
            code
          />
          <EvidenceFact
            label="Catalogue"
            value={catalogue.catalogueFingerprint}
            code
          />
          <EvidenceFact
            label="ALA snapshot"
            value={catalogue.alaOccurrenceBoundary.snapshotId}
            code
          />
          <EvidenceFact
            label="Authoritative baseline"
            value={catalogue.authoritativeBaseline}
          />
        </dl>
        <p>
          No displayed value authorizes a scientific occurrence claim. English
          names and provider mappings retain their source-assertion state.
        </p>
      </details>
    </article>
  )
}

function SpeciesPhoto({ species }: { readonly species: SpeciesCatalogueEntry }) {
  if (species.key !== FEATURED_PHOTO_TAXON_KEY) {
    return (
      <figure className="species-photo species-photo--unavailable">
        <div
          role="img"
          aria-label={`No public species photograph for ${species.acceptedScientificName}`}
        >
          <span aria-hidden="true">—</span>
          <strong>Public photograph unavailable</strong>
          <small>No media is promoted from provisional reference evidence.</small>
        </div>
        <figcaption>Missing media is a data gap—not evidence of absence.</figcaption>
      </figure>
    )
  }
  return (
    <figure className="species-photo bl-photo-frame">
      <img
        src={reviewMediaManifest.publicSrc}
        alt="Open-wing butterfly; its Wikimedia Commons source labels it Papilio demoleus"
        width={reviewMediaManifest.width}
        height={reviewMediaManifest.height}
      />
      <figcaption>
        Provider-asserted review fixture; not representative and not identity
        verification. Image by {reviewMediaManifest.rights.creator}.{' '}
        <a href={reviewMediaManifest.rights.sourceUri}>Wikimedia Commons</a>,{' '}
        <a href={reviewMediaManifest.rights.licenseUri}>
          {reviewMediaManifest.rights.licenseName}
        </a>
        .
      </figcaption>
    </figure>
  )
}

function NameAssertions({ species }: { readonly species: SpeciesCatalogueEntry }) {
  return (
    <div className="species-names">
      <section aria-labelledby="english-names-heading">
        <h5 id="english-names-heading">English source names</h5>
        {species.englishNames.length === 0 ? (
          <p>Unavailable in the submitted source assertions.</p>
        ) : (
          <ul>
            {species.englishNames.map((name) => (
              <li key={name.assertionId}>
                <strong>{name.name}</strong>
                <small>
                  {humanizeIdentifier(name.trustTier ?? 'source assertion')} ·{' '}
                  {name.sourceProvider} · unreviewed
                </small>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section aria-labelledby="scientific-synonyms-heading">
        <h5 id="scientific-synonyms-heading">Scientific synonyms</h5>
        {species.scientificSynonyms.length === 0 ? (
          <p>No provider-linked synonym is present in this submitted pack.</p>
        ) : (
          <ul>
            {species.scientificSynonyms.map((name) => (
              <li key={name.assertionId}>
                <i>{name.name}</i>
                <small>{name.sourceProvider} · source assertion unreviewed</small>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

function ProviderRow({ provider }: { readonly provider: SpeciesProviderMatch }) {
  const explanation =
    provider.identifier ??
    (provider.reasons.length > 0
      ? provider.reasons.map(humanizeIdentifier).join(', ')
      : 'No accepted provider relationship')
  return (
    <tr data-state={provider.state}>
      <th scope="row">{provider.label}</th>
      <td>{titleCase(provider.state)}</td>
      <td>{provider.identifier === null ? explanation : <code>{explanation}</code>}</td>
    </tr>
  )
}

function EvidenceFact({
  code = false,
  label,
  value,
}: {
  readonly code?: boolean
  readonly label: string
  readonly value: number | string
}) {
  return (
    <div>
      <dt>{label}</dt>
      <dd className={typeof value === 'number' ? 'bl-tabular-number' : undefined}>
        {code ? <code>{value}</code> : typeof value === 'number' ? numberFormatter.format(value) : value}
      </dd>
    </div>
  )
}

function searchableText(species: SpeciesCatalogueEntry): string {
  return normalize(
    [
      species.acceptedScientificName,
      species.queryScientificName,
      ...Object.values(species.hierarchy).map(
        (taxon) => taxon.acceptedScientificName,
      ),
      ...species.englishNames.map((name) => name.name),
      ...species.scientificSynonyms.map((name) => name.name),
    ].join(' '),
  )
}

function normalize(value: string): string {
  return value.trim().toLocaleLowerCase('en-AU')
}

function crosswalkBadgeState(status: string): 'submitted' | 'caution' | 'critical' {
  if (status === 'complete') return 'submitted'
  if (status === 'partial') return 'caution'
  return 'critical'
}

function crosswalkLabel(status: string): string {
  if (status === 'complete') return 'Three provider matches'
  if (status === 'partial') return 'Partial provider crosswalk'
  return 'Provider crosswalk unresolved'
}

function coverageBadgeState(status: string): 'caution' | 'unavailable' {
  return status === 'provisional_decode_only' ? 'caution' : 'unavailable'
}

function coverageLabel(status: string): string {
  if (status === 'provisional_decode_only') return 'Provisional decode evidence'
  if (status === 'no_automated_gate_eligible_media') {
    return 'No gate-eligible reference media'
  }
  return 'No candidate reference media'
}

function providerLabel(provider: string): string {
  const labels: Readonly<Record<string, string>> = {
    ala: 'ALA',
    gbif: 'GBIF',
    inaturalist: 'iNaturalist',
  }
  return labels[provider] ?? provider
}

function humanizeIdentifier(value: string): string {
  const acronyms: Readonly<Record<string, string>> = {
    ala: 'ALA',
    bioclip: 'BioCLIP',
    gbif: 'GBIF',
    yoloe: 'YOLOE',
  }
  return value
    .split('_')
    .map((word, index) => {
      const acronym = acronyms[word.toLocaleLowerCase('en-AU')]
      if (acronym !== undefined) return acronym
      return index === 0 ? titleCase(word) : word
    })
    .join(' ')
}

function titleCase(value: string): string {
  return `${value.charAt(0).toLocaleUpperCase('en-AU')}${value.slice(1)}`
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('en-AU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(value))
}
