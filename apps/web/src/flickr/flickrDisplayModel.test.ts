import { describe, expect, it } from 'vitest'

import {
  FLICKR_NOTICE,
  evaluateFlickrDisplayPage,
  flickrDisplayPolicy,
  submittedFlickrDisplayContext,
} from './flickrDisplayModel'

const NOW = '2026-07-18T05:00:00Z'
const approvedContext = {
  ...submittedFlickrDisplayContext,
  application_approval_state: 'noncommercial_approved' as const,
  privacy_disclosure_url: 'https://butterflylens.example/privacy',
}

describe('Flickr public display model', () => {
  it('keeps the submitted surface blocked without application approval', () => {
    const decision = evaluateFlickrDisplayPage([], submittedFlickrDisplayContext, NOW)
    expect(decision.state).toBe('blocked')
    expect(decision.items).toHaveLength(0)
    expect(flickrDisplayPolicy.maximumPhotos).toBe(30)
  })

  it('admits a complete public, current, attributed and revalidated item', () => {
    const decision = evaluateFlickrDisplayPage([validItem()], approvedContext, NOW)
    expect(decision.state).toBe('eligible')
    expect(decision.items).toHaveLength(1)
  })

  it('rejects a thirty-first photo before rendering anything', () => {
    const items = Array.from({ length: 31 }, (_, index) =>
      validItem({
        display_asset_id: `flickr-display:${index}`,
        flickr_photo_id: String(index + 1),
      }),
    )
    expect(() => evaluateFlickrDisplayPage(items, approvedContext, NOW)).toThrow(
      /30-photo page limit/u,
    )
  })

  it.each([
    ['private photo', { visibility_state: 'private' }, /visibility state/u],
    ['removed photo', { removal_state: 'removed' }, /removal state/u],
    ['active removal case', { removal_case_id: 'removal:1' }, /removal case/u],
    ['missing photographer', { photographer: '' }, /photographer/u],
    ['remote thumbnail', { image_url: 'https://live.staticflickr.com/photo.jpg' }, /internal/u],
    ['stale cache', { cache_expires_at: '2026-07-18T04:59:59Z' }, /expired/u],
  ])('fails closed for %s', (_label, changes, message) => {
    expect(() =>
      evaluateFlickrDisplayPage([validItem(changes)], approvedContext, NOW),
    ).toThrow(message)
  })

  it('requires the exact non-endorsement notice', () => {
    expect(() =>
      evaluateFlickrDisplayPage(
        [validItem()],
        { ...approvedContext, flickr_notice: 'Flickr' },
        NOW,
      ),
    ).toThrow(/Flickr notice/u)
    expect(FLICKR_NOTICE).toMatch(/not endorsed or certified/u)
  })
})

function validItem(changes: Record<string, unknown> = {}) {
  return {
    schema_version: 'butterflylens-flickr-display-item:v1.0.0',
    display_asset_id: 'flickr-display:1',
    flickr_photo_id: '123456789',
    title: 'Rights-approved butterfly fixture',
    photographer: 'Example photographer',
    owner_nsid: 'owner@N00',
    source_url: 'https://www.flickr.com/photos/example/123456789/',
    image_url: '/media/flickr/fixture.jpg',
    licence_id: 'CC BY 2.0',
    licence_url: 'https://creativecommons.org/licenses/by/2.0/',
    attribution: 'Rights-approved butterfly fixture by Example photographer, CC BY 2.0',
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
