import reviewMediaManifest from './reviewMediaManifest.json'

export type ReviewOutcome =
  | 'yes'
  | 'no'
  | 'cant_tell'
  | 'cant_view'
  | 'skip'

export type ReviewMedia =
  | {
      readonly state: 'unavailable'
      readonly reason: string
    }
  | {
      readonly state: 'verified'
      readonly src: string
      readonly alt: string
      readonly sha256: string
      readonly creator: string
      readonly attribution: string
      readonly sourceUri: string
      readonly licenseName: string
      readonly licenseUri: string
    }

export interface ReviewLandingItem {
  readonly itemId: string
  readonly campaignName: string
  readonly question: string
  readonly media: ReviewMedia
  readonly regionLabel: string
  readonly locationState: 'unavailable' | 'generalised' | 'available'
  readonly locationReason: string
}

export const reviewOutcomeLabels: Readonly<Record<ReviewOutcome, string>> = {
  yes: 'Yes',
  no: 'No',
  cant_tell: 'Can’t tell',
  cant_view: 'Can’t view',
  skip: 'Skip',
}

export const submittedReviewItem: ReviewLandingItem = {
  itemId: 'commons-review-fixture-47248e36944c',
  campaignName: 'Butterfly image verification',
  question: 'Does the displayed image show an adult butterfly?',
  media: {
    state: 'verified',
    src: reviewMediaManifest.publicSrc,
    alt: 'Rights-cleared butterfly review fixture',
    sha256: reviewMediaManifest.sha256,
    creator: reviewMediaManifest.rights.creator,
    attribution: reviewMediaManifest.rights.attribution,
    sourceUri: reviewMediaManifest.rights.sourceUri,
    licenseName: reviewMediaManifest.rights.licenseName,
    licenseUri: reviewMediaManifest.rights.licenseUri,
  },
  regionLabel: 'Australia',
  locationState: 'unavailable',
  locationReason:
    'A record-level location is unavailable until permitted candidate evidence exists.',
}
