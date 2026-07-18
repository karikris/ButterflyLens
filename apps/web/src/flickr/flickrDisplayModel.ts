import publicDisplayPolicyJson from '../../../../packages/flickr/public-display-policy.v1.json'

export const FLICKR_NOTICE =
  'This product uses the Flickr API but is not endorsed or certified by SmugMug, Inc.'

const ITEM_KEYS = [
  'schema_version',
  'display_asset_id',
  'flickr_photo_id',
  'title',
  'photographer',
  'owner_nsid',
  'source_url',
  'image_url',
  'licence_id',
  'licence_url',
  'attribution',
  'visibility_state',
  'is_current',
  'rights_status',
  'display_allowed',
  'redistribution_allowed',
  'media_state',
  'object_kind',
  'cached_at',
  'revalidated_at',
  'cache_expires_at',
  'removal_state',
  'removal_case_id',
  'source_record_fingerprint',
  'rights_fingerprint',
  'display_fingerprint',
] as const

const CONTEXT_KEYS = [
  'schema_version',
  'page_id',
  'application_approval_state',
  'privacy_disclosure_url',
  'flickr_notice',
] as const

const SHA256 = /^[0-9a-f]{64}$/u
const IDENTIFIER = /^[a-z0-9][a-z0-9._:-]{0,159}$/u
const PHOTO_ID = /^[0-9]+$/u

export interface FlickrDisplayItem {
  readonly schema_version: 'butterflylens-flickr-display-item:v1.0.0'
  readonly display_asset_id: string
  readonly flickr_photo_id: string
  readonly title: string
  readonly photographer: string
  readonly owner_nsid: string
  readonly source_url: string
  readonly image_url: string
  readonly licence_id: string
  readonly licence_url: string
  readonly attribution: string
  readonly visibility_state: 'public'
  readonly is_current: true
  readonly rights_status: 'allowed'
  readonly display_allowed: true
  readonly redistribution_allowed: true
  readonly media_state: 'committed'
  readonly object_kind: 'public_thumbnail'
  readonly cached_at: string
  readonly revalidated_at: string
  readonly cache_expires_at: string
  readonly removal_state: 'active'
  readonly removal_case_id: null
  readonly source_record_fingerprint: string
  readonly rights_fingerprint: string
  readonly display_fingerprint: string
}

export interface FlickrDisplayContext {
  readonly schema_version: 'butterflylens-flickr-display-context:v1.0.0'
  readonly page_id: string
  readonly application_approval_state:
    | 'not_recorded'
    | 'noncommercial_approved'
    | 'commercial_approved'
  readonly privacy_disclosure_url: string | null
  readonly flickr_notice: typeof FLICKR_NOTICE
}

export interface FlickrDisplayDecision {
  readonly state: 'eligible' | 'blocked'
  readonly items: readonly FlickrDisplayItem[]
  readonly reason: string
}

interface FlickrDisplayPolicy {
  readonly maximumPhotos: 30
  readonly maximumCacheAgeSeconds: number
  readonly maximumRevalidationAgeSeconds: number
  readonly sourceHost: 'www.flickr.com'
  readonly sourcePathPrefix: '/photos/'
  readonly thumbnailPathPrefix: '/media/flickr/'
}

export const flickrDisplayPolicy = parsePolicy(publicDisplayPolicyJson)

export const submittedFlickrDisplayContext: FlickrDisplayContext = {
  schema_version: 'butterflylens-flickr-display-context:v1.0.0',
  page_id: 'submitted-flickr-display-boundary',
  application_approval_state: 'not_recorded',
  privacy_disclosure_url: null,
  flickr_notice: FLICKR_NOTICE,
}

export function evaluateFlickrDisplayPage(
  values: readonly unknown[],
  contextValue: unknown,
  nowValue: string,
): FlickrDisplayDecision {
  const context = parseContext(contextValue)
  if (
    context.application_approval_state !== 'noncommercial_approved' &&
    context.application_approval_state !== 'commercial_approved'
  ) {
    return {
      state: 'blocked',
      items: [],
      reason:
        'No Flickr application approval and commercial-use determination are recorded for public release.',
    }
  }
  if (context.privacy_disclosure_url === null) {
    throw new Error('Flickr display requires a public privacy disclosure')
  }
  httpsUrl(context.privacy_disclosure_url, 'privacy disclosure URL')
  if (values.length > flickrDisplayPolicy.maximumPhotos) {
    throw new Error('Flickr display exceeds the 30-photo page limit')
  }
  const now = timestamp(nowValue, 'current time')
  const photoIds = new Set<string>()
  const assetIds = new Set<string>()
  const items = values.map((value) => parseItem(value, now))
  for (const item of items) {
    if (photoIds.has(item.flickr_photo_id) || assetIds.has(item.display_asset_id)) {
      throw new Error('Flickr display contains a duplicate photo or asset')
    }
    photoIds.add(item.flickr_photo_id)
    assetIds.add(item.display_asset_id)
  }
  return {
    state: 'eligible',
    items,
    reason: `${items.length} rights-approved Flickr photos passed the public display gate.`,
  }
}

function parsePolicy(value: unknown): FlickrDisplayPolicy {
  const policy = record(value, 'Flickr display policy')
  exact(
    policy.schema_version,
    'butterflylens-flickr-public-display-policy:v1.0.0',
    'policy schema',
  )
  const release = record(policy.release_gate, 'release gate')
  exact(release.application_approval_evidence, 'required', 'approval evidence')
  exact(release.commercial_use_determination, 'required', 'commercial use')
  exact(release.privacy_disclosure, 'required', 'privacy disclosure')
  exact(release.public_photo_display, 'conditional_all_gates', 'public photo display')
  const page = record(policy.page, 'page policy')
  exact(page.maximum_flickr_photos, 30, 'maximum Flickr photos')
  exact(page.flickr_notice, FLICKR_NOTICE, 'Flickr notice')
  exact(page.privacy_disclosure_required, true, 'privacy disclosure')
  const photo = record(policy.photo, 'photo policy')
  exact(photo.source_host, 'www.flickr.com', 'source host')
  exact(photo.source_path_prefix, '/photos/', 'source path')
  exact(photo.public_thumbnail_path_prefix, '/media/flickr/', 'thumbnail path')
  const branding = record(policy.branding, 'branding policy')
  exact(branding.flickr_logo_permitted, false, 'Flickr logo')
  exact(branding.endorsement_claim_permitted, false, 'endorsement')
  exact(
    branding.replicate_essential_experience_permitted,
    false,
    'essential experience',
  )
  const cache = record(policy.cache, 'cache policy')
  exact(cache.purge_if_private, 'immediate', 'private purge')
  exact(cache.purge_on_removal_case, 'immediate', 'removal purge')
  const removal = record(policy.removal, 'removal policy')
  exact(removal.owner_request_deadline_hours, 24, 'owner removal deadline')
  exact(removal.quarantine_before_traversal, true, 'removal quarantine')
  return {
    maximumPhotos: 30,
    maximumCacheAgeSeconds: positiveInteger(
      cache.maximum_age_seconds,
      'maximum cache age',
    ),
    maximumRevalidationAgeSeconds: positiveInteger(
      cache.maximum_revalidation_age_seconds,
      'maximum revalidation age',
    ),
    sourceHost: 'www.flickr.com',
    sourcePathPrefix: '/photos/',
    thumbnailPathPrefix: '/media/flickr/',
  }
}

function parseContext(value: unknown): FlickrDisplayContext {
  const context = record(value, 'Flickr display context')
  exactKeys(context, CONTEXT_KEYS, 'Flickr display context')
  exact(
    context.schema_version,
    'butterflylens-flickr-display-context:v1.0.0',
    'context schema',
  )
  matches(context.page_id, IDENTIFIER, 'page ID')
  if (
    context.application_approval_state !== 'not_recorded' &&
    context.application_approval_state !== 'noncommercial_approved' &&
    context.application_approval_state !== 'commercial_approved'
  ) {
    throw new Error('invalid Flickr application approval state')
  }
  if (
    context.privacy_disclosure_url !== null &&
    typeof context.privacy_disclosure_url !== 'string'
  ) {
    throw new Error('invalid Flickr privacy disclosure URL')
  }
  exact(context.flickr_notice, FLICKR_NOTICE, 'Flickr notice')
  return context as unknown as FlickrDisplayContext
}

function parseItem(value: unknown, now: number): FlickrDisplayItem {
  const item = record(value, 'Flickr display item')
  exactKeys(item, ITEM_KEYS, 'Flickr display item')
  exact(
    item.schema_version,
    'butterflylens-flickr-display-item:v1.0.0',
    'item schema',
  )
  matches(item.display_asset_id, IDENTIFIER, 'display asset ID')
  matches(item.flickr_photo_id, PHOTO_ID, 'Flickr photo ID')
  for (const field of [
    'photographer',
    'owner_nsid',
    'licence_id',
    'attribution',
  ] as const) {
    nonEmpty(item[field], field)
  }
  if (typeof item.title !== 'string') throw new Error('title must be a string')
  const source = httpsUrl(item.source_url, 'Flickr source URL')
  if (
    source.hostname !== flickrDisplayPolicy.sourceHost ||
    !source.pathname.startsWith(flickrDisplayPolicy.sourcePathPrefix)
  ) {
    throw new Error('Flickr source URL must link to the exact photo')
  }
  httpsUrl(item.licence_url, 'licence URL')
  const imageUrl = nonEmpty(item.image_url, 'thumbnail URL')
  if (
    !imageUrl.startsWith(flickrDisplayPolicy.thumbnailPathPrefix) ||
    imageUrl.includes('?') ||
    imageUrl.includes('#') ||
    imageUrl.includes('://')
  ) {
    throw new Error('Flickr thumbnail must use the internal public path')
  }
  exact(item.visibility_state, 'public', 'visibility state')
  exact(item.is_current, true, 'current source record')
  exact(item.rights_status, 'allowed', 'rights status')
  exact(item.display_allowed, true, 'display permission')
  exact(item.redistribution_allowed, true, 'redistribution permission')
  exact(item.media_state, 'committed', 'media state')
  exact(item.object_kind, 'public_thumbnail', 'object kind')
  exact(item.removal_state, 'active', 'removal state')
  exact(item.removal_case_id, null, 'removal case')
  for (const field of [
    'source_record_fingerprint',
    'rights_fingerprint',
    'display_fingerprint',
  ] as const) {
    matches(item[field], SHA256, field)
  }
  const cachedAt = timestamp(item.cached_at, 'cached_at')
  const revalidatedAt = timestamp(item.revalidated_at, 'revalidated_at')
  const expiresAt = timestamp(item.cache_expires_at, 'cache_expires_at')
  if (cachedAt > revalidatedAt || revalidatedAt > now) {
    throw new Error('Flickr revalidation timeline is invalid')
  }
  if (expiresAt - cachedAt > flickrDisplayPolicy.maximumCacheAgeSeconds * 1000) {
    throw new Error('Flickr cache exceeds the reasonable period')
  }
  if (expiresAt <= now) throw new Error('Flickr cache is expired')
  if (
    now - revalidatedAt >
    flickrDisplayPolicy.maximumRevalidationAgeSeconds * 1000
  ) {
    throw new Error('Flickr visibility/licence revalidation is stale')
  }
  return item as unknown as FlickrDisplayItem
}

function record(value: unknown, field: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new Error(`${field} must be an object`)
  }
  return value as Record<string, unknown>
}

function exactKeys(
  value: Record<string, unknown>,
  expected: readonly string[],
  field: string,
): void {
  const actual = Object.keys(value).sort()
  const wanted = [...expected].sort()
  if (actual.length !== wanted.length || actual.some((key, index) => key !== wanted[index])) {
    throw new Error(`${field} has unexpected fields`)
  }
}

function exact(value: unknown, expected: unknown, field: string): void {
  if (value !== expected) throw new Error(`${field} must equal ${String(expected)}`)
}

function matches(value: unknown, pattern: RegExp, field: string): string {
  const text = nonEmpty(value, field)
  if (!pattern.test(text)) throw new Error(`${field} is invalid`)
  return text
}

function nonEmpty(value: unknown, field: string): string {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new Error(`${field} is required`)
  }
  return value
}

function positiveInteger(value: unknown, field: string): number {
  if (!Number.isInteger(value) || Number(value) <= 0) {
    throw new Error(`${field} must be a positive integer`)
  }
  return Number(value)
}

function httpsUrl(value: unknown, field: string): URL {
  const text = nonEmpty(value, field)
  let parsed: URL
  try {
    parsed = new URL(text)
  } catch {
    throw new Error(`${field} must be an HTTPS URL`)
  }
  if (parsed.protocol !== 'https:' || parsed.username !== '' || parsed.password !== '') {
    throw new Error(`${field} must be an HTTPS URL`)
  }
  return parsed
}

function timestamp(value: unknown, field: string): number {
  const text = nonEmpty(value, field)
  if (!text.endsWith('Z')) throw new Error(`${field} must be UTC`)
  const parsed = Date.parse(text)
  if (!Number.isFinite(parsed)) throw new Error(`${field} is invalid`)
  return parsed
}
