#!/usr/bin/env bash
set -euo pipefail

required_names=(
  B2_ENDPOINT
  B2_REGION
  B2_PRIVATE_BUCKET
  B2_PUBLIC_BUCKET
  AWS_ACCESS_KEY_ID
  AWS_SECRET_ACCESS_KEY
)
for required_name in "${required_names[@]}"; do
  if [[ -z "${!required_name:-}" ]]; then
    printf 'Required environment variable is absent: %s\n' "$required_name" >&2
    exit 2
  fi
done

if [[ ! "$B2_ENDPOINT" =~ ^https://s3\.$B2_REGION\.backblazeb2\.com$ ]]; then
  printf '%s\n' 'B2_ENDPOINT must be the exact regional Backblaze S3 HTTPS origin.' >&2
  exit 2
fi
for bucket_name in "$B2_PRIVATE_BUCKET" "$B2_PUBLIC_BUCKET"; do
  if [[ ! "$bucket_name" =~ ^[a-z0-9][a-z0-9-]{4,48}[a-z0-9]$ ]] || [[ "$bucket_name" == b2-* ]]; then
    printf '%s\n' 'A B2 bucket name does not meet the project naming contract.' >&2
    exit 2
  fi
done
if [[ "$B2_PRIVATE_BUCKET" == "$B2_PUBLIC_BUCKET" ]]; then
  printf '%s\n' 'Private and public B2 buckets must be distinct.' >&2
  exit 2
fi

export AWS_DEFAULT_REGION="$B2_REGION"
export AWS_EC2_METADATA_DISABLED=true
existing_bucket_names="$(aws --endpoint-url "$B2_ENDPOINT" s3api list-buckets --query 'Buckets[].Name' --output text)"

ensure_bucket() {
  local bucket_name="$1"
  local bucket_acl="$2"
  if [[ " $existing_bucket_names " != *" $bucket_name "* ]]; then
    aws --endpoint-url "$B2_ENDPOINT" s3api create-bucket \
      --bucket "$bucket_name" --acl "$bucket_acl" >/dev/null
  fi
}

ensure_bucket "$B2_PRIVATE_BUCKET" private
ensure_bucket "$B2_PUBLIC_BUCKET" public-read

private_public_grants="$(aws --endpoint-url "$B2_ENDPOINT" s3api get-bucket-acl \
  --bucket "$B2_PRIVATE_BUCKET" \
  --query "length(Grants[?Grantee.URI=='http://acs.amazonaws.com/groups/global/AllUsers'])" \
  --output text)"
public_read_grants="$(aws --endpoint-url "$B2_ENDPOINT" s3api get-bucket-acl \
  --bucket "$B2_PUBLIC_BUCKET" \
  --query "length(Grants[?Grantee.URI=='http://acs.amazonaws.com/groups/global/AllUsers' && Permission=='READ'])" \
  --output text)"
if [[ "$private_public_grants" != "0" || "$public_read_grants" == "0" ]]; then
  printf '%s\n' 'Existing B2 bucket visibility differs from the deployment contract.' >&2
  exit 3
fi

for bucket_name in "$B2_PRIVATE_BUCKET" "$B2_PUBLIC_BUCKET"; do
  aws --endpoint-url "$B2_ENDPOINT" s3api put-bucket-cors \
    --bucket "$bucket_name" \
    --cors-configuration file://infra/b2/cors.github-pages.json
  aws --endpoint-url "$B2_ENDPOINT" s3api put-bucket-encryption \
    --bucket "$bucket_name" \
    --server-side-encryption-configuration \
      '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
  aws --endpoint-url "$B2_ENDPOINT" s3api get-bucket-cors \
    --bucket "$bucket_name" --output json >/dev/null
  aws --endpoint-url "$B2_ENDPOINT" s3api get-bucket-encryption \
    --bucket "$bucket_name" --output json >/dev/null
done

printf '%s\n' 'B2 bucket visibility, CORS, and SSE-B2 configuration verified.'
