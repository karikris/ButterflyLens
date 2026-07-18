import { createHash } from 'node:crypto'
import { readFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const webRoot = join(dirname(fileURLToPath(import.meta.url)), '..')
const manifestPath = join(webRoot, 'src/review/reviewMediaManifest.json')
const manifest = JSON.parse(await readFile(manifestPath, 'utf8'))
const asset = await readFile(join(webRoot, manifest.assetPath))
const observedSha256 = createHash('sha256').update(asset).digest('hex')

const required = {
  schemaVersion: 'butterflylens-review-media/v1',
  publicSrc: '/media/review-fixture-47248e36944c.jpg',
  mediaType: 'image/jpeg',
  identityState: 'provider_asserted',
  representative: false,
  scientificClaimAllowed: false,
}

for (const [field, expected] of Object.entries(required)) {
  if (manifest[field] !== expected) {
    throw new Error(`review media ${field} must be ${JSON.stringify(expected)}`)
  }
}

if (manifest.sha256 !== observedSha256) {
  throw new Error(`review media SHA-256 mismatch: ${observedSha256}`)
}
if (manifest.byteCount !== asset.byteLength) {
  throw new Error(`review media byte count mismatch: ${asset.byteLength}`)
}
if (
  manifest.rights?.creator !== 'Jeevan Jose' ||
  manifest.rights?.licenseName !== 'CC BY-SA 4.0' ||
  manifest.rights?.licenseUri !== 'https://creativecommons.org/licenses/by-sa/4.0/' ||
  !manifest.rights?.attribution ||
  !manifest.rights?.sourceUri
) {
  throw new Error('review media rights metadata is incomplete or unexpected')
}

console.log(
  `review media verification: PASS (sha256=${observedSha256}, bytes=${asset.byteLength})`,
)
