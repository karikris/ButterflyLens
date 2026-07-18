export const blindReviewFields = [
  'model_label',
  'model_score',
  'flickr_query_term',
  'source_comments',
  'majority_vote',
  'other_reviewer_decisions',
] as const

export type BlindReviewField = (typeof blindReviewFields)[number]

export const blindReviewFieldLabels: Readonly<Record<BlindReviewField, string>> = {
  model_label: 'Model label',
  model_score: 'Model score',
  flickr_query_term: 'Flickr query term',
  source_comments: 'Source comments',
  majority_vote: 'Majority vote',
  other_reviewer_decisions: 'Other reviewer decisions',
}

export interface ReviewDisclosure {
  readonly state: 'available' | 'unavailable'
  readonly reason: string
  readonly modelLabel: string | null
  readonly modelScoreBand: string | null
  readonly flickrQueryTerm: string | null
  readonly sourceCommentExcerpt: string | null
  readonly peerSummary: {
    readonly decisive: number
    readonly yes: number
    readonly no: number
    readonly uncertain: number
  } | null
  readonly scientificClaimAllowed: false
}

export const submittedReviewDisclosure: ReviewDisclosure = {
  state: 'unavailable',
  reason:
    'No model, Flickr query, source-comment, or peer-review evidence is present in this credential-free replay.',
  modelLabel: null,
  modelScoreBand: null,
  flickrQueryTerm: null,
  sourceCommentExcerpt: null,
  peerSummary: null,
  scientificClaimAllowed: false,
}
