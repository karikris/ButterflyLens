import type { ReactNode } from 'react'

export type EvidenceBadgeState =
  | 'submitted'
  | 'verified'
  | 'caution'
  | 'unavailable'
  | 'unfinished'
  | 'critical'

const STATE_MARKERS: Readonly<Record<EvidenceBadgeState, string>> = {
  submitted: 'S',
  verified: '✓',
  caution: '!',
  unavailable: '—',
  unfinished: '…',
  critical: '×',
}

export function StateBadge({
  children,
  state,
}: {
  readonly children: ReactNode
  readonly state: EvidenceBadgeState
}) {
  return (
    <span className="bl-state-badge" data-state={state}>
      <span className="bl-state-badge__marker" aria-hidden="true">
        {STATE_MARKERS[state]}
      </span>
      {children}
    </span>
  )
}

export function EvidenceNotice({
  announce = false,
  children,
  className,
  title,
  tone = 'information',
}: {
  readonly announce?: boolean
  readonly children: ReactNode
  readonly className?: string
  readonly title: string
  readonly tone?: 'information' | 'caution' | 'critical'
}) {
  const classes = ['bl-evidence-notice', className].filter(Boolean).join(' ')
  return (
    <div
      className={classes}
      data-tone={tone}
      role={announce ? (tone === 'critical' ? 'alert' : 'status') : undefined}
    >
      <strong>{title}:</strong> {children}
    </div>
  )
}
