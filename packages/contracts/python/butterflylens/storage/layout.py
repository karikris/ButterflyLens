"""Executable key, manifest, checksum, and local-cache storage policy."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Mapping

from jsonschema import Draft202012Validator, FormatChecker
import rfc8785


ARTIFACT_LAYOUT_SCHEMA_VERSION = "butterflylens-artifact-layout:v1.0.0"
ARTIFACT_MANIFEST_SCHEMA_VERSION = (
    "butterflylens-artifact-storage-manifest:v1.0.0"
)
REQUIRED_ARTIFACT_CLASSES = {
    "source_metadata",
    "source_images",
    "reference_images",
    "object_crops",
    "full_frame_inputs",
    "embeddings",
    "parquet_shards",
    "reports",
    "public_thumbnails",
    "private_review_media",
    "manifests",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,159}$")
_PLACEHOLDER = re.compile(r"{([a-z0-9_]+)}")


class ArtifactLayoutError(ValueError):
    """Raised when a layout, key, manifest, or cache object fails closed."""


@dataclass(frozen=True)
class ArtifactClass:
    id: str
    bucket: str
    key_template: str
    extensions: tuple[str, ...]
    required_permissions: tuple[str, ...]
    cache_ttl_seconds: int


class ArtifactLayout:
    """Validated artifact classes and deterministic immutable key construction."""

    def __init__(self, document: Mapping[str, object]) -> None:
        if document.get("schema_version") != ARTIFACT_LAYOUT_SCHEMA_VERSION:
            raise ArtifactLayoutError("unsupported artifact layout version")
        if document.get("root_prefix") != "butterflylens/v1":
            raise ArtifactLayoutError("unexpected artifact root prefix")
        raw_classes = document.get("artifact_classes")
        if not isinstance(raw_classes, list):
            raise ArtifactLayoutError("artifact_classes must be an array")
        classes: dict[str, ArtifactClass] = {}
        for raw in raw_classes:
            if not isinstance(raw, dict):
                raise ArtifactLayoutError("artifact class must be an object")
            artifact_id = raw.get("id")
            if not isinstance(artifact_id, str) or artifact_id in classes:
                raise ArtifactLayoutError("artifact class ID is invalid or duplicated")
            bucket = raw.get("bucket")
            template = raw.get("key_template")
            extensions = raw.get("extensions")
            permissions = raw.get("required_permissions")
            ttl = raw.get("cache_ttl_seconds")
            if bucket not in {"private", "public"}:
                raise ArtifactLayoutError(f"{artifact_id}: invalid bucket class")
            if not isinstance(template, str) or not template.startswith(
                "butterflylens/v1/"
            ):
                raise ArtifactLayoutError(f"{artifact_id}: invalid key template")
            if ".." in template or "?" in template or "//" in template:
                raise ArtifactLayoutError(f"{artifact_id}: unsafe key template")
            if not isinstance(extensions, list) or not extensions:
                raise ArtifactLayoutError(f"{artifact_id}: extensions are required")
            if not isinstance(permissions, list) or not permissions:
                raise ArtifactLayoutError(f"{artifact_id}: permissions are required")
            if not isinstance(ttl, int) or ttl <= 0 or ttl > 604_800:
                raise ArtifactLayoutError(f"{artifact_id}: invalid cache TTL")
            classes[artifact_id] = ArtifactClass(
                id=artifact_id,
                bucket=bucket,
                key_template=template,
                extensions=tuple(extensions),
                required_permissions=tuple(permissions),
                cache_ttl_seconds=ttl,
            )
        if set(classes) != REQUIRED_ARTIFACT_CLASSES:
            raise ArtifactLayoutError("artifact class inventory is incomplete")
        if classes["public_thumbnails"].bucket != "public" or any(
            item.bucket != "private"
            for item in classes.values()
            if item.id != "public_thumbnails"
        ):
            raise ArtifactLayoutError("public/private bucket separation is invalid")
        self._document = deepcopy(dict(document))
        self._classes = classes

    @classmethod
    def load(cls, path: Path) -> "ArtifactLayout":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    @property
    def artifact_classes(self) -> tuple[str, ...]:
        return tuple(sorted(self._classes))

    def artifact_class(self, artifact_id: str) -> ArtifactClass:
        try:
            return self._classes[artifact_id]
        except KeyError as error:
            raise ArtifactLayoutError(f"unknown artifact class: {artifact_id}") from error

    def build_key(
        self,
        artifact_id: str,
        *,
        content_sha256: str,
        extension: str,
        identifiers: Mapping[str, str],
    ) -> str:
        artifact = self.artifact_class(artifact_id)
        if _SHA256.fullmatch(content_sha256) is None:
            raise ArtifactLayoutError("content_sha256 must be lowercase SHA-256")
        if extension not in artifact.extensions:
            raise ArtifactLayoutError(f"{artifact_id}: extension is not permitted")
        values = dict(identifiers)
        values.update(
            content_sha256=content_sha256,
            digest_prefix_2=content_sha256[:2],
        )
        required = set(_PLACEHOLDER.findall(artifact.key_template))
        if "extension" in required:
            values["extension"] = extension
        if set(values) != required:
            missing = sorted(required - set(values))
            additional = sorted(set(values) - required)
            raise ArtifactLayoutError(
                f"{artifact_id}: key identifiers mismatch; missing={missing}, additional={additional}"
            )
        for name, value in values.items():
            if name in {"content_sha256", "digest_prefix_2", "extension"}:
                continue
            if _IDENTIFIER.fullmatch(value) is None:
                raise ArtifactLayoutError(f"{artifact_id}: unsafe identifier {name}")
        key = artifact.key_template.format_map(values)
        if len(key.encode("utf-8")) > 1024 or ".." in key or "?" in key or "//" in key:
            raise ArtifactLayoutError(f"{artifact_id}: unsafe or oversized key")
        return key


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cache_path(root: Path, digest: str) -> Path:
    if _SHA256.fullmatch(digest) is None:
        raise ArtifactLayoutError("cache digest must be lowercase SHA-256")
    return root / "sha256" / digest[:2] / digest[2:4] / digest


def atomic_cache_write(root: Path, digest: str, data: bytes) -> Path:
    if sha256_bytes(data) != digest:
        raise ArtifactLayoutError("cache write checksum mismatch")
    target = cache_path(root, digest)
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.exists():
        if read_cached_bytes(root, digest) != data:
            raise ArtifactLayoutError("existing cache object has conflicting bytes")
        return target
    descriptor, temporary_name = tempfile.mkstemp(prefix=".write-", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        directory = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return target


def read_cached_bytes(root: Path, digest: str) -> bytes:
    target = cache_path(root, digest)
    try:
        data = target.read_bytes()
    except FileNotFoundError as error:
        raise ArtifactLayoutError("cache object is missing") from error
    if sha256_bytes(data) != digest:
        raise ArtifactLayoutError("cache object checksum mismatch")
    return data


def validate_artifact_manifest(
    manifest: Mapping[str, object], *, layout: ArtifactLayout, schema_path: Path
) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(manifest),
        key=lambda error: list(error.path),
    )
    if errors:
        raise ArtifactLayoutError("manifest schema violation: " + errors[0].message)
    objects = manifest["objects"]
    assert isinstance(objects, list)
    identities: set[tuple[str, str, str]] = set()
    order: list[tuple[str, str, str]] = []
    for raw in objects:
        assert isinstance(raw, dict)
        artifact = layout.artifact_class(raw["artifact_class"])
        if raw["bucket_class"] != artifact.bucket:
            raise ArtifactLayoutError("manifest bucket differs from artifact layout")
        key = raw["key"]
        digest = raw["content_sha256"]
        version = raw["b2_version_id"]
        assert isinstance(key, str) and isinstance(digest, str) and isinstance(version, str)
        if digest not in key:
            raise ArtifactLayoutError("manifest key does not bind content SHA-256")
        if "/.staging/" in key or "?" in key:
            raise ArtifactLayoutError("manifest contains staging key or signed URL")
        identity = (raw["bucket_class"], key, version)
        if identity in identities:
            raise ArtifactLayoutError("manifest contains duplicate object version")
        identities.add(identity)
        order.append((raw["artifact_class"], key, version))
        if raw["artifact_class"] in {
            "object_crops",
            "full_frame_inputs",
            "embeddings",
            "public_thumbnails",
            "private_review_media",
        } and raw["source_media_fingerprint"] is None:
            raise ArtifactLayoutError("derived media must bind its source fingerprint")
    if order != sorted(order):
        raise ArtifactLayoutError("manifest objects must be canonically ordered")
    preimage = deepcopy(dict(manifest))
    claimed = preimage.pop("manifest_fingerprint")
    computed = hashlib.sha256(rfc8785.dumps(preimage)).hexdigest()
    if claimed != computed:
        raise ArtifactLayoutError("manifest fingerprint mismatch")
