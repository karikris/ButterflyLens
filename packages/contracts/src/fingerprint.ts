export const CONTENT_CHECKSUM_SCHEMA_VERSION =
  'butterflylens-content-checksum:v1.0.0' as const
export const EVIDENCE_FINGERPRINT_SCHEMA_VERSION =
  'butterflylens-evidence-fingerprint:v1.0.0' as const
export const FINGERPRINT_CANONICALIZATION = 'RFC8785-JCS' as const
export const FINGERPRINT_HASH_ALGORITHM = 'sha256' as const
export const I_JSON_MAX_INTEGER = 9_007_199_254_740_991 as const

export const FINGERPRINT_KINDS = [
  'project_definition',
  'run_input_set',
  'taxon_concept',
  'name_assertion',
  'query_definition',
  'physical_api_request',
  'provider_snapshot',
  'api_response',
  'source_flickr_record',
  'downloaded_image',
  'media_object',
  'perceptual_duplicate_group',
  'model_artifact',
  'preprocessing',
  'yoloe_route',
  'full_frame_visual_input',
  'bioclip_embedding',
  'reference_bank',
  'prototype',
  'candidate_score',
  'review_event',
  'consensus',
  'quality_snapshot',
  'geographic_impact_cell',
  'map_snapshot',
  'release_candidate',
  'artifact_manifest',
  'export_manifest',
] as const

export const FINGERPRINT_PARENT_RELATIONSHIPS = [
  'derived_from',
  'contains',
  'produced_by',
  'supersedes',
  'reviews',
  'aggregates',
  'compares',
  'calibrates',
] as const

export type FingerprintKind = (typeof FINGERPRINT_KINDS)[number]
export type FingerprintParentRelationship =
  (typeof FINGERPRINT_PARENT_RELATIONSHIPS)[number]

export interface ContentChecksum {
  readonly schema_version: typeof CONTENT_CHECKSUM_SCHEMA_VERSION
  readonly algorithm: typeof FINGERPRINT_HASH_ALGORITHM
  readonly digest: string
  readonly byte_count: number
  readonly media_type: string
}

export interface EvidenceFingerprintParent {
  readonly relationship: FingerprintParentRelationship
  readonly fingerprint_kind: FingerprintKind
  readonly digest: string
}

export interface EvidenceFingerprintPreimage {
  readonly fingerprint_kind: FingerprintKind
  readonly subject_id: string
  readonly payload_schema_version: string
  readonly payload: Readonly<Record<string, unknown>>
  readonly parents: readonly EvidenceFingerprintParent[]
}

export interface EvidenceFingerprint {
  readonly schema_version: typeof EVIDENCE_FINGERPRINT_SCHEMA_VERSION
  readonly hash_algorithm: typeof FINGERPRINT_HASH_ALGORITHM
  readonly canonicalization: typeof FINGERPRINT_CANONICALIZATION
  readonly preimage: EvidenceFingerprintPreimage
  readonly digest: string
  readonly recorded_at: string
}

export class FingerprintCanonicalizationError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'FingerprintCanonicalizationError'
  }
}

export function canonicalizeJson(value: unknown): string {
  return canonicalizeNode(value, '$')
}

export function normalizeEvidencePreimage(
  preimage: EvidenceFingerprintPreimage,
): EvidenceFingerprintPreimage {
  const identities = new Set<string>()
  const parents = preimage.parents.map((parent, index) => {
    const identity = [
      parent.relationship,
      parent.fingerprint_kind,
      parent.digest,
    ].join('\u0000')
    if (identities.has(identity)) {
      throw new FingerprintCanonicalizationError(
        `$.parents[${index}]: duplicate parent reference`,
      )
    }
    identities.add(identity)
    return { ...parent }
  })
  parents.sort((left, right) =>
    compareStrings(left.relationship, right.relationship) ||
    compareStrings(left.fingerprint_kind, right.fingerprint_kind) ||
    compareStrings(left.digest, right.digest),
  )
  return { ...preimage, parents }
}

export function canonicalizeEvidencePreimage(
  preimage: EvidenceFingerprintPreimage,
): string {
  return canonicalizeJson(normalizeEvidencePreimage(preimage))
}

export function semanticFingerprintDigest(
  preimage: EvidenceFingerprintPreimage,
): string {
  return sha256Hex(utf8Bytes(canonicalizeEvidencePreimage(preimage)))
}

function canonicalizeNode(value: unknown, path: string): string {
  if (value === null) return 'null'
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  if (typeof value === 'string') {
    assertValidUnicode(value, path)
    return JSON.stringify(value)
  }
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) {
      throw new FingerprintCanonicalizationError(`${path}: number must be finite`)
    }
    if (Object.is(value, -0)) {
      throw new FingerprintCanonicalizationError(`${path}: negative zero is forbidden`)
    }
    const serialized = JSON.stringify(value)
    if (
      Number.isInteger(value) && !Number.isSafeInteger(value) &&
      !serialized.includes('e')
    ) {
      throw new FingerprintCanonicalizationError(
        `${path}: integer exceeds the I-JSON safe range`,
      )
    }
    return serialized
  }
  if (Array.isArray(value)) {
    return `[${value.map((item, index) =>
      canonicalizeNode(item, `${path}[${index}]`)
    ).join(',')}]`
  }
  if (typeof value === 'object') {
    const prototype = Object.getPrototypeOf(value)
    if (prototype !== Object.prototype && prototype !== null) {
      throw new FingerprintCanonicalizationError(
        `${path}: expected a plain JSON object`,
      )
    }
    const object = value as Readonly<Record<string, unknown>>
    return `{${Object.keys(object).sort().map((key) => {
      assertValidUnicode(key, `${path}.<key>`)
      return `${JSON.stringify(key)}:${canonicalizeNode(object[key], `${path}.${key}`)}`
    }).join(',')}}`
  }
  throw new FingerprintCanonicalizationError(
    `${path}: unsupported JSON value ${typeof value}`,
  )
}

function assertValidUnicode(value: string, path: string): void {
  for (let index = 0; index < value.length; index += 1) {
    const unit = value.charCodeAt(index)
    if (unit >= 0xd800 && unit <= 0xdbff) {
      const next = value.charCodeAt(index + 1)
      if (!(next >= 0xdc00 && next <= 0xdfff)) {
        throw new FingerprintCanonicalizationError(
          `${path}: string is not valid Unicode`,
        )
      }
      index += 1
    } else if (unit >= 0xdc00 && unit <= 0xdfff) {
      throw new FingerprintCanonicalizationError(
        `${path}: string is not valid Unicode`,
      )
    }
  }
}

function compareStrings(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0
}

function utf8Bytes(value: string): Uint8Array {
  const bytes: number[] = []
  for (const character of value) {
    const point = character.codePointAt(0)
    if (point === undefined) continue
    if (point <= 0x7f) bytes.push(point)
    else if (point <= 0x7ff) {
      bytes.push(0xc0 | (point >>> 6), 0x80 | (point & 0x3f))
    } else if (point <= 0xffff) {
      bytes.push(
        0xe0 | (point >>> 12),
        0x80 | ((point >>> 6) & 0x3f),
        0x80 | (point & 0x3f),
      )
    } else {
      bytes.push(
        0xf0 | (point >>> 18),
        0x80 | ((point >>> 12) & 0x3f),
        0x80 | ((point >>> 6) & 0x3f),
        0x80 | (point & 0x3f),
      )
    }
  }
  return new Uint8Array(bytes)
}

const SHA256_ROUND_CONSTANTS = [
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
  0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
  0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
  0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
  0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
  0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
  0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
  0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
  0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
] as const

function sha256Hex(input: Uint8Array): string {
  const bitLength = input.length * 8
  const paddedLength = Math.ceil((input.length + 9) / 64) * 64
  const padded = new Uint8Array(paddedLength)
  padded.set(input)
  padded[input.length] = 0x80
  const view = new DataView(padded.buffer)
  view.setUint32(paddedLength - 8, Math.floor(bitLength / 0x1_0000_0000))
  view.setUint32(paddedLength - 4, bitLength >>> 0)

  const hash = new Uint32Array([
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
  ])
  const words = new Uint32Array(64)
  for (let offset = 0; offset < paddedLength; offset += 64) {
    for (let index = 0; index < 16; index += 1) {
      words[index] = view.getUint32(offset + index * 4)
    }
    for (let index = 16; index < 64; index += 1) {
      const x = words[index - 15]
      const y = words[index - 2]
      const sigma0 = rotateRight(x, 7) ^ rotateRight(x, 18) ^ (x >>> 3)
      const sigma1 = rotateRight(y, 17) ^ rotateRight(y, 19) ^ (y >>> 10)
      words[index] = (words[index - 16] + sigma0 + words[index - 7] + sigma1) >>> 0
    }
    let [a, b, c, d, e, f, g, h] = hash
    for (let index = 0; index < 64; index += 1) {
      const upper1 = rotateRight(e, 6) ^ rotateRight(e, 11) ^ rotateRight(e, 25)
      const choice = (e & f) ^ (~e & g)
      const temporary1 = (h + upper1 + choice + SHA256_ROUND_CONSTANTS[index] + words[index]) >>> 0
      const upper0 = rotateRight(a, 2) ^ rotateRight(a, 13) ^ rotateRight(a, 22)
      const majority = (a & b) ^ (a & c) ^ (b & c)
      const temporary2 = (upper0 + majority) >>> 0
      h = g; g = f; f = e; e = (d + temporary1) >>> 0
      d = c; c = b; b = a; a = (temporary1 + temporary2) >>> 0
    }
    hash[0] = (hash[0] + a) >>> 0; hash[1] = (hash[1] + b) >>> 0
    hash[2] = (hash[2] + c) >>> 0; hash[3] = (hash[3] + d) >>> 0
    hash[4] = (hash[4] + e) >>> 0; hash[5] = (hash[5] + f) >>> 0
    hash[6] = (hash[6] + g) >>> 0; hash[7] = (hash[7] + h) >>> 0
  }
  return Array.from(hash, (word) => word.toString(16).padStart(8, '0')).join('')
}

function rotateRight(value: number, count: number): number {
  return (value >>> count) | (value << (32 - count))
}
