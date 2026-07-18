"""Fail-closed Flickr public-display policy with no provider transport."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Mapping, Sequence
from urllib.parse import urlparse


POLICY_SCHEMA_VERSION = "butterflylens-flickr-public-display-policy:v1.0.0"
CONTEXT_SCHEMA_VERSION = "butterflylens-flickr-display-context:v1.0.0"
ITEM_SCHEMA_VERSION = "butterflylens-flickr-display-item:v1.0.0"
APPROVAL_STATES = {"noncommercial_approved", "commercial_approved"}
NOTICE = (
    "This product uses the Flickr API but is not endorsed or certified by "
    "SmugMug, Inc."
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,159}$")
_PHOTO_ID = re.compile(r"^[0-9]+$")
_ITEM_KEYS = {
    "schema_version",
    "display_asset_id",
    "flickr_photo_id",
    "title",
    "photographer",
    "owner_nsid",
    "source_url",
    "image_url",
    "licence_id",
    "licence_url",
    "attribution",
    "visibility_state",
    "is_current",
    "rights_status",
    "display_allowed",
    "redistribution_allowed",
    "media_state",
    "object_kind",
    "cached_at",
    "revalidated_at",
    "cache_expires_at",
    "removal_state",
    "removal_case_id",
    "source_record_fingerprint",
    "rights_fingerprint",
    "display_fingerprint",
}
_CONTEXT_KEYS = {
    "schema_version",
    "page_id",
    "application_approval_state",
    "privacy_disclosure_url",
    "flickr_notice",
}


class FlickrDisplayPolicyError(ValueError):
    """Raised when a page is not eligible to display Flickr photos."""


@dataclass(frozen=True)
class FlickrDisplayPolicy:
    maximum_photos_per_page: int
    maximum_cache_age_seconds: int
    maximum_revalidation_age_seconds: int
    removal_deadline_hours: int
    source_host: str
    source_path_prefix: str
    thumbnail_path_prefix: str
    notice: str

    @classmethod
    def load(cls, path: Path) -> "FlickrDisplayPolicy":
        document = json.loads(path.read_text(encoding="utf-8"))
        if document.get("schema_version") != POLICY_SCHEMA_VERSION:
            raise FlickrDisplayPolicyError("unsupported Flickr display policy")
        if document.get("release_gate") != {
            "application_approval_evidence": "required",
            "commercial_use_determination": "required",
            "privacy_disclosure": "required",
            "public_photo_display": "conditional_all_gates",
        }:
            raise FlickrDisplayPolicyError("Flickr release requirements changed")
        page = _mapping(document.get("page"), "page")
        photo = _mapping(document.get("photo"), "photo")
        branding = _mapping(document.get("branding"), "branding")
        cache = _mapping(document.get("cache"), "cache")
        removal = _mapping(document.get("removal"), "removal")
        if page.get("maximum_flickr_photos") != 30 or page.get("flickr_notice") != NOTICE:
            raise FlickrDisplayPolicyError("Flickr page limit or notice changed")
        if branding != {
            "flickr_logo_permitted": False,
            "endorsement_claim_permitted": False,
            "replicate_essential_experience_permitted": False,
        }:
            raise FlickrDisplayPolicyError("Flickr branding boundary changed")
        if cache.get("purge_if_private") != "immediate" or cache.get(
            "purge_on_removal_case"
        ) != "immediate":
            raise FlickrDisplayPolicyError("Flickr cache purge policy changed")
        if removal.get("owner_request_deadline_hours") != 24 or removal.get(
            "quarantine_before_traversal"
        ) is not True:
            raise FlickrDisplayPolicyError("Flickr removal policy changed")
        return cls(
            maximum_photos_per_page=30,
            maximum_cache_age_seconds=_positive_int(
                cache.get("maximum_age_seconds"), "maximum cache age"
            ),
            maximum_revalidation_age_seconds=_positive_int(
                cache.get("maximum_revalidation_age_seconds"),
                "maximum revalidation age",
            ),
            removal_deadline_hours=24,
            source_host=_nonempty(photo.get("source_host"), "source host"),
            source_path_prefix=_nonempty(
                photo.get("source_path_prefix"), "source path prefix"
            ),
            thumbnail_path_prefix=_nonempty(
                photo.get("public_thumbnail_path_prefix"),
                "thumbnail path prefix",
            ),
            notice=NOTICE,
        )


def admit_public_display_page(
    items: Sequence[Mapping[str, object]],
    *,
    context: Mapping[str, object],
    policy: FlickrDisplayPolicy,
    now: datetime,
) -> tuple[dict[str, object], ...]:
    """Validate a complete display context and return an immutable page projection."""

    _validate_context(context, policy)
    if now.tzinfo is None or now.utcoffset() is None:
        raise FlickrDisplayPolicyError("now must be timezone-aware")
    now = now.astimezone(timezone.utc)
    if len(items) > policy.maximum_photos_per_page:
        raise FlickrDisplayPolicyError("Flickr page exceeds 30 photos")
    admitted: list[dict[str, object]] = []
    photo_ids: set[str] = set()
    asset_ids: set[str] = set()
    for item in items:
        admitted_item = _admit_item(item, policy=policy, now=now)
        photo_id = str(admitted_item["flickr_photo_id"])
        asset_id = str(admitted_item["display_asset_id"])
        if photo_id in photo_ids or asset_id in asset_ids:
            raise FlickrDisplayPolicyError("Flickr display page contains a duplicate")
        photo_ids.add(photo_id)
        asset_ids.add(asset_id)
        admitted.append(admitted_item)
    return tuple(admitted)


def _validate_context(
    context: Mapping[str, object], policy: FlickrDisplayPolicy
) -> None:
    if set(context) != _CONTEXT_KEYS:
        raise FlickrDisplayPolicyError("Flickr display context has unexpected fields")
    if context.get("schema_version") != CONTEXT_SCHEMA_VERSION:
        raise FlickrDisplayPolicyError("unsupported Flickr display context")
    if _IDENTIFIER.fullmatch(_nonempty(context.get("page_id"), "page ID")) is None:
        raise FlickrDisplayPolicyError("invalid Flickr page ID")
    if context.get("application_approval_state") not in APPROVAL_STATES:
        raise FlickrDisplayPolicyError("Flickr application approval is not recorded")
    if context.get("flickr_notice") != policy.notice:
        raise FlickrDisplayPolicyError("required Flickr notice is missing")
    privacy_url = _https_url(
        context.get("privacy_disclosure_url"), "privacy disclosure URL"
    )
    if privacy_url.hostname is None:
        raise FlickrDisplayPolicyError("privacy disclosure URL has no host")


def _admit_item(
    item: Mapping[str, object], *, policy: FlickrDisplayPolicy, now: datetime
) -> dict[str, object]:
    if set(item) != _ITEM_KEYS:
        raise FlickrDisplayPolicyError("Flickr display item has unexpected fields")
    if item.get("schema_version") != ITEM_SCHEMA_VERSION:
        raise FlickrDisplayPolicyError("unsupported Flickr display item")
    asset_id = _nonempty(item.get("display_asset_id"), "display asset ID")
    if _IDENTIFIER.fullmatch(asset_id) is None:
        raise FlickrDisplayPolicyError("invalid Flickr display asset ID")
    photo_id = _nonempty(item.get("flickr_photo_id"), "Flickr photo ID")
    if _PHOTO_ID.fullmatch(photo_id) is None:
        raise FlickrDisplayPolicyError("invalid Flickr photo ID")
    for field in ("photographer", "owner_nsid", "licence_id", "attribution"):
        _nonempty(item.get(field), field)
    source = _https_url(item.get("source_url"), "Flickr source URL")
    if source.hostname != policy.source_host or not source.path.startswith(
        policy.source_path_prefix
    ):
        raise FlickrDisplayPolicyError("Flickr source link is not an exact photo link")
    _https_url(item.get("licence_url"), "licence URL")
    image_url = _nonempty(item.get("image_url"), "thumbnail URL")
    parsed_image = urlparse(image_url)
    if (
        not image_url.startswith(policy.thumbnail_path_prefix)
        or parsed_image.scheme
        or parsed_image.netloc
        or parsed_image.query
        or parsed_image.fragment
    ):
        raise FlickrDisplayPolicyError("Flickr thumbnail must be an internal public path")
    required_states = {
        "visibility_state": "public",
        "is_current": True,
        "rights_status": "allowed",
        "display_allowed": True,
        "redistribution_allowed": True,
        "media_state": "committed",
        "object_kind": "public_thumbnail",
        "removal_state": "active",
        "removal_case_id": None,
    }
    for field, required in required_states.items():
        if item.get(field) != required:
            raise FlickrDisplayPolicyError(f"Flickr {field} is not display eligible")
    for field in (
        "source_record_fingerprint",
        "rights_fingerprint",
        "display_fingerprint",
    ):
        if _SHA256.fullmatch(_nonempty(item.get(field), field)) is None:
            raise FlickrDisplayPolicyError(f"invalid {field}")
    cached_at = _timestamp(item.get("cached_at"), "cached_at")
    revalidated_at = _timestamp(item.get("revalidated_at"), "revalidated_at")
    expires_at = _timestamp(item.get("cache_expires_at"), "cache_expires_at")
    if not cached_at <= revalidated_at <= now:
        raise FlickrDisplayPolicyError("Flickr revalidation timeline is invalid")
    if (expires_at - cached_at).total_seconds() > policy.maximum_cache_age_seconds:
        raise FlickrDisplayPolicyError("Flickr cache exceeds the reasonable period")
    if expires_at <= now:
        raise FlickrDisplayPolicyError("Flickr cache is expired")
    if (now - revalidated_at).total_seconds() > policy.maximum_revalidation_age_seconds:
        raise FlickrDisplayPolicyError("Flickr visibility/licence revalidation is stale")
    return dict(item)


def _timestamp(value: object, field: str) -> datetime:
    text = _nonempty(value, field)
    if not text.endswith("Z"):
        raise FlickrDisplayPolicyError(f"{field} must be a UTC timestamp")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise FlickrDisplayPolicyError(f"{field} is invalid") from error
    return parsed.astimezone(timezone.utc)


def _https_url(value: object, field: str):
    parsed = urlparse(_nonempty(value, field))
    if parsed.scheme != "https" or not parsed.netloc or parsed.username is not None:
        raise FlickrDisplayPolicyError(f"{field} must be an HTTPS URL")
    return parsed


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise FlickrDisplayPolicyError(f"{field} must be an object")
    return value


def _nonempty(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FlickrDisplayPolicyError(f"{field} is required")
    return value


def _positive_int(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise FlickrDisplayPolicyError(f"{field} must be a positive integer")
    return value
