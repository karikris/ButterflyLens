import { useMemo, useState, type CSSProperties, type KeyboardEvent } from 'react'

import { EvidenceNotice, StateBadge } from '../design-system/EvidencePrimitives'
import {
  submittedMapSnapshot,
  type MapScopeKind,
  type SubmittedMapCell,
  type SubmittedMapScope,
  type SubmittedMapSnapshot,
} from './submittedMapModel'

const SCOPE_LABELS: Readonly<Record<MapScopeKind, string>> = {
  state: 'State / territory',
  ibra: 'IBRA v7',
  lga: 'LGA approximation',
  h3: 'H3 coarse cells',
}

const VIEW_WIDTH = 920
const VIEW_HEIGHT = 560

function formatCount(value: number) {
  return value.toLocaleString('en-AU')
}

function projectionBounds(cells: readonly SubmittedMapCell[]) {
  const points = cells.flatMap((cell) => cell.polygon)
  const longitudes = points.map(([longitude]) => longitude)
  const latitudes = points.map(([, latitude]) => latitude)
  return {
    minLongitude: Math.min(...longitudes),
    maxLongitude: Math.max(...longitudes),
    minLatitude: Math.min(...latitudes),
    maxLatitude: Math.max(...latitudes),
  }
}

function projectPoint(
  point: readonly [number, number],
  bounds: ReturnType<typeof projectionBounds>,
) {
  const [longitude, latitude] = point
  const padding = 18
  const x =
    padding +
    ((longitude - bounds.minLongitude) /
      (bounds.maxLongitude - bounds.minLongitude)) *
      (VIEW_WIDTH - padding * 2)
  const y =
    padding +
    ((bounds.maxLatitude - latitude) /
      (bounds.maxLatitude - bounds.minLatitude)) *
      (VIEW_HEIGHT - padding * 2)
  return `${x.toFixed(2)},${y.toFixed(2)}`
}

function selectedCellFrom(
  cells: readonly SubmittedMapCell[],
  selectedCellId: string,
) {
  return cells.find((cell) => cell.cellId === selectedCellId) ?? cells[0]
}

function ScopeBubble({ count, maximum }: { readonly count: number; readonly maximum: number }) {
  const scale = 0.35 + Math.sqrt(count / Math.max(maximum, 1)) * 0.65
  return (
    <span
      className="submitted-map__bubble"
      style={{ '--bubble-scale': scale.toFixed(3) } as CSSProperties}
      aria-hidden="true"
    />
  )
}

function EvidenceRecords({ cell }: { readonly cell: SubmittedMapCell }) {
  return (
    <section className="submitted-map__records" aria-labelledby="map-records-heading">
      <div className="submitted-map__subheading">
        <div>
          <p className="eyebrow">Evidence links</p>
          <h4 id="map-records-heading">Provider-record sample</h4>
        </div>
        <StateBadge state="caution">Assertions only</StateBadge>
      </div>
      <p>
        Up to two deterministic records link this aggregate back to source evidence.
        Coordinates are never included here.
      </p>
      {cell.records.length === 0 ? (
        <p>No public record sample is attached to this cell.</p>
      ) : (
        <ul>
          {cell.records.map((record) => (
            <li key={record.recordId}>
              <strong>{record.providerScientificName ?? 'Provider name unavailable'}</strong>
              <span>
                {record.dataResourceName} · {record.basisOfRecord ?? 'basis unavailable'} ·{' '}
                {record.eventYear ?? 'year unavailable'}
              </span>
              <span>{record.evidenceLabel}</span>
              <a href={record.sourceReference} rel="noreferrer">
                Inspect source record
              </a>
              <code>{record.recordFingerprint.slice(0, 16)}…</code>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export function SubmittedEvidenceMap({
  snapshot = submittedMapSnapshot,
}: {
  readonly snapshot?: SubmittedMapSnapshot
}) {
  const initialCell = useMemo(
    () =>
      snapshot.cells.reduce((largest, cell) =>
        cell.count > largest.count ? cell : largest,
      ),
    [snapshot.cells],
  )
  const [selectedCellId, setSelectedCellId] = useState(initialCell.cellId)
  const [scopeKind, setScopeKind] = useState<MapScopeKind>('state')
  const [selectedScopeId, setSelectedScopeId] = useState(
    snapshot.scopes.state.reduce((largest, scope) =>
      scope.count > largest.count ? scope : largest,
    ).scopeId,
  )
  const [scopeFilter, setScopeFilter] = useState('')
  const [showAla, setShowAla] = useState(true)

  const bounds = useMemo(() => projectionBounds(snapshot.cells), [snapshot.cells])
  const maximumCellCount = useMemo(
    () => Math.max(...snapshot.cells.map((cell) => cell.count)),
    [snapshot.cells],
  )
  const selectedCell = selectedCellFrom(snapshot.cells, selectedCellId)
  const sortedCells = useMemo(
    () => [...snapshot.cells].sort((left, right) => right.count - left.count),
    [snapshot.cells],
  )
  const filteredScopes = useMemo(() => {
    const normalizedFilter = scopeFilter.trim().toLocaleLowerCase('en-AU')
    return [...snapshot.scopes[scopeKind]]
      .filter(
        (scope) =>
          normalizedFilter === '' ||
          scope.label.toLocaleLowerCase('en-AU').includes(normalizedFilter),
      )
      .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label))
  }, [scopeFilter, scopeKind, snapshot.scopes])
  const selectedScope: SubmittedMapScope | null =
    filteredScopes.find((scope) => scope.scopeId === selectedScopeId) ??
    filteredScopes[0] ??
    null
  const maximumScopeCount = filteredScopes[0]?.count ?? 1

  const inspectCell = (cellId: string) => {
    setSelectedCellId(cellId)
    const element = document.getElementById('submitted-map-cell-detail')
    element?.focus({ preventScroll: true })
  }

  const handlePolygonKey = (
    event: KeyboardEvent<SVGPolygonElement>,
    cellId: string,
  ) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      inspectCell(cellId)
    }
  }

  const chooseScope = (kind: MapScopeKind) => {
    setScopeKind(kind)
    setScopeFilter('')
    const next = [...snapshot.scopes[kind]].sort(
      (left, right) => right.count - left.count,
    )[0]
    setSelectedScopeId(next.scopeId)
    if (kind === 'h3') setSelectedCellId(next.label)
  }

  const chooseScopeRow = (scope: SubmittedMapScope) => {
    setSelectedScopeId(scope.scopeId)
    if (scopeKind === 'h3') setSelectedCellId(scope.label)
  }

  return (
    <section className="submitted-map" aria-labelledby="submitted-map-heading">
      <header className="submitted-map__intro">
        <div>
          <p className="eyebrow">Rights-screened submitted map</p>
          <h2 id="submitted-map-heading">Where the baseline has evidence</h2>
          <p>
            Explore exact aggregate counts from the rebuilt ALA baseline. This is
            evidence coverage—not species presence, absence, abundance, or a human
            identification.
          </p>
        </div>
        <div className="submitted-map__mode" aria-label="Map data mode">
          <button type="button" aria-pressed="true">Submitted</button>
          <button
            type="button"
            aria-pressed="false"
            disabled
            title="No authenticated live map snapshot is attached"
          >
            Live unavailable
          </button>
        </div>
      </header>

      <dl className="submitted-map__metrics">
        <div>
          <dt>Map-eligible baseline</dt>
          <dd>{formatCount(snapshot.counts.mapEligible)}</dd>
        </div>
        <div>
          <dt>H3 cells</dt>
          <dd>{formatCount(snapshot.counts.mapCells)}</dd>
        </div>
        <div>
          <dt>Rights-screened selected</dt>
          <dd>{formatCount(snapshot.counts.rightsScreenedSelected)}</dd>
        </div>
        <div>
          <dt>Conservatively excluded</dt>
          <dd>{formatCount(snapshot.counts.rightsExcludedSelected)}</dd>
        </div>
      </dl>

      <EvidenceNotice title="Public projection, not complete truth" tone="caution">
        The complete {formatCount(snapshot.counts.authoritativeBaselineSelected)}-row
        rebuilt baseline remains authoritative. This map excludes all records from
        three citation-rights review datasets; exclusion is not a legal conclusion.
      </EvidenceNotice>

      <div className="submitted-map__workspace">
        <article className="submitted-map__canvas-card" aria-labelledby="map-canvas-heading">
          <div className="submitted-map__card-heading">
            <div>
              <p className="eyebrow">National heatmap</p>
              <h3 id="map-canvas-heading">Spatially eligible ALA evidence</h3>
            </div>
            <StateBadge state="verified">Aggregate layer available</StateBadge>
          </div>

          <fieldset className="submitted-map__layers">
            <legend>Evidence layers</legend>
            <label>
              <input
                type="checkbox"
                checked={showAla}
                onChange={(event) => setShowAla(event.currentTarget.checked)}
              />
              <span className="submitted-map__legend-symbol" data-layer="ala" />
              ALA baseline · blue filled cells
            </label>
            <label data-disabled="true">
              <input type="checkbox" checked={false} disabled readOnly />
              <span className="submitted-map__legend-symbol" data-layer="flickr" />
              Flickr candidate · amber diamonds · unavailable
            </label>
            <p>{snapshot.layers.flickrCandidate.reason}</p>
          </fieldset>

          <svg
            className="submitted-map__svg"
            viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
            role="img"
            aria-label={`Australia evidence heatmap with ${formatCount(snapshot.counts.mapCells)} H3 aggregate cells`}
            data-webgl="not-used"
          >
            <rect width={VIEW_WIDTH} height={VIEW_HEIGHT} rx="18" />
            <g aria-hidden={!showAla} data-visible={showAla ? 'true' : 'false'}>
              {snapshot.cells.map((cell) => {
                const intensity =
                  0.18 +
                  (Math.log10(cell.count + 1) / Math.log10(maximumCellCount + 1)) * 0.82
                return (
                  <polygon
                    key={cell.cellId}
                    className="submitted-map__cell"
                    data-selected={cell.cellId === selectedCell.cellId ? 'true' : 'false'}
                    points={cell.polygon.map((point) => projectPoint(point, bounds)).join(' ')}
                    style={{ '--cell-intensity': intensity.toFixed(3) } as CSSProperties}
                    role="button"
                    tabIndex={showAla && cell.cellId === selectedCell.cellId ? 0 : -1}
                    aria-label={`H3 ${cell.cellId}: ${formatCount(cell.count)} ALA baseline records`}
                    onClick={() => inspectCell(cell.cellId)}
                    onKeyDown={(event) => handlePolygonKey(event, cell.cellId)}
                  >
                    <title>
                      H3 {cell.cellId}: {formatCount(cell.count)} ALA baseline records
                    </title>
                  </polygon>
                )
              })}
            </g>
          </svg>
          <div className="submitted-map__scale" aria-label="ALA baseline count scale">
            <span>Fewer records</span>
            <span aria-hidden="true" />
            <span>More records</span>
          </div>
          <p className="submitted-map__geometry-note">
            H3 resolution 3 polygons are derived aggregate geometry. They are not
            occurrence coordinates, and no external tiles or boundary geometry are used.
          </p>
        </article>

        <aside
          className="submitted-map__cell-detail"
          id="submitted-map-cell-detail"
          tabIndex={-1}
          aria-labelledby="selected-cell-heading"
        >
          <div className="submitted-map__card-heading">
            <div>
              <p className="eyebrow">Selected H3 cell</p>
              <h3 id="selected-cell-heading">{selectedCell.cellId}</h3>
            </div>
            <StateBadge state="submitted">Submitted</StateBadge>
          </div>
          <dl>
            <div>
              <dt>ALA baseline records</dt>
              <dd>{formatCount(selectedCell.count)}</dd>
            </div>
            <div>
              <dt>Latest parseable event year</dt>
              <dd>{selectedCell.latestEventYear ?? 'Unavailable'}</dd>
            </div>
            <div>
              <dt>Publicly generalised rows</dt>
              <dd>{formatCount(selectedCell.publiclyGeneralisedCount)}</dd>
            </div>
            <div>
              <dt>Flickr candidates</dt>
              <dd>Unavailable—not zero</dd>
            </div>
          </dl>
          <p className="submitted-map__fingerprint">
            Evidence <code>{selectedCell.evidenceFingerprint}</code>
          </p>
          <EvidenceRecords cell={selectedCell} />
        </aside>
      </div>

      <section className="submitted-map__drilldown" aria-labelledby="map-drilldown-heading">
        <div className="submitted-map__drilldown-heading">
          <div>
            <p className="eyebrow">Exact-count drilldowns</p>
            <h3 id="map-drilldown-heading">Move from national to local context</h3>
          </div>
          <p>
            State, IBRA, and LGA labels are ALA contextual assertions. LGA is a
            statistical approximation, not a legal boundary.
          </p>
        </div>
        <div className="submitted-map__scope-tabs" role="group" aria-label="Map scope">
          {(Object.keys(SCOPE_LABELS) as MapScopeKind[]).map((kind) => (
            <button
              type="button"
              key={kind}
              aria-pressed={scopeKind === kind}
              onClick={() => chooseScope(kind)}
            >
              {SCOPE_LABELS[kind]}
            </button>
          ))}
        </div>
        <label className="submitted-map__scope-filter">
          Filter {SCOPE_LABELS[scopeKind]}
          <input
            type="search"
            value={scopeFilter}
            onChange={(event) => setScopeFilter(event.currentTarget.value)}
            placeholder="Type a place or H3 identifier"
          />
        </label>

        {filteredScopes.length === 0 ? (
          <EvidenceNotice title="No matching scope" tone="caution" announce>
            Clear the filter to inspect the complete submitted scope table.
          </EvidenceNotice>
        ) : (
          <>
            <div className="submitted-map__scope-layout">
              <ol className="submitted-map__bubbles" aria-label={`Top ${SCOPE_LABELS[scopeKind]} counts`}>
                {filteredScopes.slice(0, 12).map((scope) => (
                  <li key={scope.scopeId}>
                    <button
                      type="button"
                      data-selected={scope.scopeId === selectedScope?.scopeId ? 'true' : 'false'}
                      onClick={() => chooseScopeRow(scope)}
                    >
                      <ScopeBubble count={scope.count} maximum={maximumScopeCount} />
                      <span>{scope.label}</span>
                      <strong>{formatCount(scope.count)}</strong>
                    </button>
                  </li>
                ))}
              </ol>
              {selectedScope ? (
                <article className="submitted-map__scope-detail" aria-live="polite">
                  <p className="eyebrow">Selected scope</p>
                  <h4>{selectedScope.label}</h4>
                  <dl>
                    <div>
                      <dt>ALA baseline records</dt>
                      <dd>{formatCount(selectedScope.count)}</dd>
                    </div>
                    <div>
                      <dt>Exactly crosswalked records</dt>
                      <dd>{formatCount(selectedScope.matchedTaxonCount)}</dd>
                    </div>
                    <div>
                      <dt>Unmatched provider assertions</dt>
                      <dd>{formatCount(selectedScope.unmatchedTaxonAssertionCount)}</dd>
                    </div>
                    <div>
                      <dt>Distinct crosswalked taxon keys</dt>
                      <dd>{formatCount(selectedScope.uniqueTaxonCount)}</dd>
                    </div>
                  </dl>
                  <code>{selectedScope.evidenceFingerprint}</code>
                </article>
              ) : null}
            </div>

            <div className="submitted-map__table-wrap" tabIndex={0}>
              <table>
                <caption>
                  Exact {SCOPE_LABELS[scopeKind]} counts; {formatCount(filteredScopes.length)} rows
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Scope</th>
                    <th scope="col">ALA baseline</th>
                    <th scope="col">Crosswalked</th>
                    <th scope="col">Provider assertion only</th>
                    <th scope="col">Latest year</th>
                    <th scope="col">Inspect</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredScopes.map((scope) => (
                    <tr key={scope.scopeId} data-selected={scope.scopeId === selectedScope?.scopeId ? 'true' : 'false'}>
                      <th scope="row">{scope.label}</th>
                      <td>{formatCount(scope.count)}</td>
                      <td>{formatCount(scope.matchedTaxonCount)}</td>
                      <td>{formatCount(scope.unmatchedTaxonAssertionCount)}</td>
                      <td>{scope.latestEventYear ?? 'Unavailable'}</td>
                      <td>
                        <button type="button" onClick={() => chooseScopeRow(scope)}>
                          Inspect
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      <details className="submitted-map__cell-table">
        <summary>Open the synchronized H3 exact-count table</summary>
        <div className="submitted-map__table-wrap" tabIndex={0}>
          <table>
            <caption>
              All {formatCount(snapshot.cells.length)} submitted H3 cells and exact ALA baseline counts
            </caption>
            <thead>
              <tr>
                <th scope="col">H3 cell</th>
                <th scope="col">ALA baseline</th>
                <th scope="col">Generalised rows</th>
                <th scope="col">Latest year</th>
                <th scope="col">Inspect</th>
              </tr>
            </thead>
            <tbody>
              {sortedCells.map((cell) => (
                <tr key={cell.cellId} data-selected={cell.cellId === selectedCell.cellId ? 'true' : 'false'}>
                  <th scope="row"><code>{cell.cellId}</code></th>
                  <td>{formatCount(cell.count)}</td>
                  <td>{formatCount(cell.publiclyGeneralisedCount)}</td>
                  <td>{cell.latestEventYear ?? 'Unavailable'}</td>
                  <td>
                    <button type="button" onClick={() => inspectCell(cell.cellId)}>
                      Inspect H3 {cell.cellId}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>

      <details className="submitted-map__rights">
        <summary>Rights screen, exclusions, attribution, and provenance</summary>
        <p>{snapshot.source.attribution}</p>
        <p>{snapshot.source.notice}</p>
        <ul>
          {snapshot.rights.excludedDatasets.map((dataset) => (
            <li key={dataset.dataResourceUid}>
              <strong>{dataset.dataResourceName}</strong> ({dataset.dataResourceUid}) ·{' '}
              {formatCount(dataset.selectedRecordCount)} selected records excluded ·{' '}
              <code>{dataset.datasetFingerprint.slice(0, 16)}…</code>
            </li>
          ))}
        </ul>
        <p>
          Snapshot <code>{snapshot.snapshotId}</code> · source commit{' '}
          <code>{snapshot.sourceCommit}</code> · fingerprint{' '}
          <code>{snapshot.snapshotFingerprint}</code>
        </p>
      </details>
    </section>
  )
}
