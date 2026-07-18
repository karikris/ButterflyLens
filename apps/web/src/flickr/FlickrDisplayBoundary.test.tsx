import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { FlickrDisplayBoundary } from './FlickrDisplayBoundary'
import {
  FLICKR_NOTICE,
  submittedFlickrDisplayContext,
} from './flickrDisplayModel'

const NOW = '2026-07-18T05:00:00Z'
const approvedContext = {
  ...submittedFlickrDisplayContext,
  application_approval_state: 'noncommercial_approved' as const,
  privacy_disclosure_url: 'https://butterflylens.example/privacy',
}

describe('Flickr display boundary', () => {
  it('publishes the enforcement policy while displaying no partial fetch output', () => {
    render(<FlickrDisplayBoundary />)
    expect(screen.getByText('0 Flickr photos displayed')).toBeVisible()
    expect(screen.getByText(/No Flickr application approval/u)).toBeVisible()
    expect(screen.getByText(FLICKR_NOTICE)).toBeVisible()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
    expect(screen.getByText(/At most 30/u)).toBeVisible()
    expect(screen.getByText(/quarantined immediately/u)).toBeVisible()
  })

  it('renders source, photographer and licence only after every gate passes', () => {
    render(
      <FlickrDisplayBoundary
        items={[validItem()]}
        context={approvedContext}
        now={NOW}
      />,
    )
    expect(screen.getByText('1 Flickr photos displayed')).toBeVisible()
    expect(screen.getByRole('img', { name: 'Fixture butterfly' })).toHaveAttribute(
      'src',
      '/media/flickr/fixture.jpg',
    )
    expect(screen.getByText('Photographer: Example photographer')).toBeVisible()
    expect(screen.getByRole('link', { name: /original photo on Flickr/u })).toHaveAttribute(
      'href',
      'https://www.flickr.com/photos/example/123456789/',
    )
    expect(screen.getByRole('link', { name: 'CC BY 2.0' })).toBeVisible()
  })

  it('fails the whole page closed when one private item is supplied', () => {
    render(
      <FlickrDisplayBoundary
        items={[validItem({ visibility_state: 'private' })]}
        context={approvedContext}
        now={NOW}
      />,
    )
    expect(screen.getByText('0 Flickr photos displayed')).toBeVisible()
    expect(screen.getByText(/visibility state/u)).toBeVisible()
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })
})

function validItem(changes: Record<string, unknown> = {}) {
  return {
    schema_version: 'butterflylens-flickr-display-item:v1.0.0',
    display_asset_id: 'flickr-display:1',
    flickr_photo_id: '123456789',
    title: 'Fixture butterfly',
    photographer: 'Example photographer',
    owner_nsid: 'owner@N00',
    source_url: 'https://www.flickr.com/photos/example/123456789/',
    image_url: '/media/flickr/fixture.jpg',
    licence_id: 'CC BY 2.0',
    licence_url: 'https://creativecommons.org/licenses/by/2.0/',
    attribution: 'Fixture butterfly by Example photographer, CC BY 2.0',
    visibility_state: 'public',
    is_current: true,
    rights_status: 'allowed',
    display_allowed: true,
    redistribution_allowed: true,
    media_state: 'committed',
    object_kind: 'public_thumbnail',
    cached_at: '2026-07-18T04:30:00Z',
    revalidated_at: '2026-07-18T04:59:00Z',
    cache_expires_at: '2026-07-19T04:30:00Z',
    removal_state: 'active',
    removal_case_id: null,
    source_record_fingerprint: 'a'.repeat(64),
    rights_fingerprint: 'b'.repeat(64),
    display_fingerprint: 'c'.repeat(64),
    ...changes,
  }
}
