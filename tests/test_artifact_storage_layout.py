from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator
import rfc8785


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))

from butterflylens.storage import (  # noqa: E402
    ArtifactLayout,
    ArtifactLayoutError,
    atomic_cache_write,
    read_cached_bytes,
    sha256_bytes,
    validate_artifact_manifest,
)


LAYOUT_PATH = ROOT / "packages/storage/artifact-layout.v1.json"
SCHEMA_PATH = ROOT / "packages/storage/schemas/artifact-manifest.schema.json"
DOC_PATH = ROOT / "packages/storage/ARTIFACT_LAYOUT.md"


def permissions(**overrides: str) -> dict[str, str]:
    value = {
        "metadata_storage": "permitted",
        "download": "not_applicable",
        "cache": "not_applicable",
        "transformation": "not_applicable",
        "model_inference": "not_applicable",
        "human_review": "not_applicable",
        "public_display": "not_applicable",
        "redistribution": "not_applicable",
    }
    value.update(overrides)
    return value


class ArtifactStorageLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.layout = ArtifactLayout.load(LAYOUT_PATH)
        cls.document = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.docs = DOC_PATH.read_text(encoding="utf-8")

    def test_inventory_buckets_and_unfinished_model_classes_are_explicit(self) -> None:
        self.assertEqual(len(self.layout.artifact_classes), 11)
        self.assertEqual(self.layout.artifact_class("public_thumbnails").bucket, "public")
        for artifact_id in self.layout.artifact_classes:
            if artifact_id != "public_thumbnails":
                self.assertEqual(self.layout.artifact_class(artifact_id).bucket, "private")
        self.assertIn("unfinished YOLOE work creates no crops", json.dumps(self.document))
        self.assertIn("unfinished BioCLIP work creates no embeddings", json.dumps(self.document))

    def test_content_addressed_keys_are_deterministic_and_safe(self) -> None:
        digest = "a" * 64
        identifiers = {
            "project_id": "project:australian-butterflies",
            "run_id": "run:fixture",
            "provider": "ala",
        }
        key = self.layout.build_key(
            "source_metadata",
            content_sha256=digest,
            extension="json.zst",
            identifiers=identifiers,
        )
        self.assertEqual(
            key,
            "butterflylens/v1/projects/project:australian-butterflies/runs/"
            f"run:fixture/source-metadata/ala/aa/{digest}.json.zst",
        )
        with self.assertRaises(ArtifactLayoutError):
            self.layout.build_key(
                "source_metadata",
                content_sha256=digest,
                extension="exe",
                identifiers=identifiers,
            )
        unsafe = {**identifiers, "provider": "../../private"}
        with self.assertRaises(ArtifactLayoutError):
            self.layout.build_key(
                "source_metadata",
                content_sha256=digest,
                extension="json",
                identifiers=unsafe,
            )

    def test_every_artifact_template_builds_an_immutable_digest_key(self) -> None:
        digest = "f" * 64
        common = {
            "project_id": "project:fixture",
            "run_id": "run:fixture",
        }
        cases = {
            "source_metadata": ("json", {**common, "provider": "gbif"}),
            "source_images": ("jpg", {**common, "provider": "gbif"}),
            "reference_images": (
                "jpg", {**common, "accepted_taxon_key": "taxon:fixture"}
            ),
            "object_crops": (
                "jpg", {**common, "source_media_fingerprint": "a" * 64}
            ),
            "full_frame_inputs": (
                "jpg", {**common, "source_media_fingerprint": "a" * 64}
            ),
            "embeddings": (
                "parquet", {**common, "model_fingerprint": "b" * 64}
            ),
            "parquet_shards": (
                "parquet",
                {
                    **common,
                    "dataset_id": "dataset:fixture",
                    "partition_fingerprint": "c" * 64,
                },
            ),
            "reports": ("json", {**common, "report_type": "quality"}),
            "public_thumbnails": (
                "webp",
                {
                    "project_id": "project:fixture",
                    "source_media_fingerprint": "a" * 64,
                },
            ),
            "private_review_media": (
                "jpg", {**common, "campaign_id": "campaign:fixture"}
            ),
            "manifests": (
                "json", {**common, "manifest_kind": "run-root"}
            ),
        }
        for artifact_id, (extension, identifiers) in cases.items():
            with self.subTest(artifact_id):
                key = self.layout.build_key(
                    artifact_id,
                    content_sha256=digest,
                    extension=extension,
                    identifiers=identifiers,
                )
                self.assertIn(digest, key)
                self.assertNotIn("{", key)

    def test_atomic_cache_write_permissions_and_integrity(self) -> None:
        data = b"synthetic artifact bytes"
        digest = sha256_bytes(data)
        with tempfile.TemporaryDirectory(prefix="butterflylens-cache-test-") as temporary:
            root = Path(temporary) / "cache"
            path = atomic_cache_write(root, digest, data)
            self.assertEqual(read_cached_bytes(root, digest), data)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertFalse(any(path.parent.glob(".write-*")))
            path.write_bytes(b"tampered")
            with self.assertRaisesRegex(ArtifactLayoutError, "checksum mismatch"):
                read_cached_bytes(root, digest)
        with self.assertRaisesRegex(ArtifactLayoutError, "checksum mismatch"):
            atomic_cache_write(Path("unused"), "0" * 64, data)

    def test_complete_manifest_is_schema_valid_and_recomputed(self) -> None:
        digest = "b" * 64
        key = self.layout.build_key(
            "reports",
            content_sha256=digest,
            extension="json",
            identifiers={
                "project_id": "project:australian-butterflies",
                "run_id": "run:fixture",
                "report_type": "quality",
            },
        )
        manifest = {
            "schema_version": "butterflylens-artifact-storage-manifest:v1.0.0",
            "layout_version": "butterflylens-artifact-layout:v1.0.0",
            "project_id": "project:australian-butterflies",
            "run_id": "run:fixture",
            "created_at": "2026-07-17T22:30:00Z",
            "publication_state": "complete",
            "objects": [{
                "artifact_class": "reports",
                "bucket_class": "private",
                "key": key,
                "b2_version_id": "4_zfixture",
                "content_sha256": digest,
                "byte_count": 42,
                "media_type": "application/json",
                "semantic_fingerprint": "c" * 64,
                "rights_decision_fingerprint": "d" * 64,
                "source_media_fingerprint": None,
                "permissions": permissions(),
            }],
        }
        manifest["manifest_fingerprint"] = hashlib.sha256(
            rfc8785.dumps(manifest)
        ).hexdigest()
        validate_artifact_manifest(
            manifest, layout=self.layout, schema_path=SCHEMA_PATH
        )
        tampered = deepcopy(manifest)
        tampered["objects"][0]["byte_count"] = 43
        with self.assertRaisesRegex(ArtifactLayoutError, "fingerprint mismatch"):
            validate_artifact_manifest(
                tampered, layout=self.layout, schema_path=SCHEMA_PATH
            )

    def test_public_thumbnail_and_crop_permissions_fail_closed(self) -> None:
        validator = Draft202012Validator(self.schema)
        base_object = {
            "artifact_class": "public_thumbnails",
            "bucket_class": "public",
            "key": "butterflylens/v1/projects/project:fixture/public-thumbnails/"
            + "a" * 64 + "/aa/" + "a" * 64 + ".jpg",
            "b2_version_id": "4_zfixture",
            "content_sha256": "a" * 64,
            "byte_count": 1,
            "media_type": "image/jpeg",
            "semantic_fingerprint": "b" * 64,
            "rights_decision_fingerprint": "c" * 64,
            "source_media_fingerprint": "d" * 64,
            "permissions": permissions(
                transformation="permitted",
                public_display="permitted",
                redistribution="permitted",
            ),
        }
        document = {
            "schema_version": "butterflylens-artifact-storage-manifest:v1.0.0",
            "layout_version": "butterflylens-artifact-layout:v1.0.0",
            "project_id": "project:fixture",
            "run_id": "run:fixture",
            "created_at": "2026-07-17T22:30:00Z",
            "publication_state": "complete",
            "objects": [base_object],
            "manifest_fingerprint": "e" * 64,
        }
        self.assertEqual(list(validator.iter_errors(document)), [])
        document["objects"][0]["permissions"]["public_display"] = "unknown"
        self.assertTrue(list(validator.iter_errors(document)))
        document["objects"][0]["artifact_class"] = "object_crops"
        document["objects"][0]["bucket_class"] = "private"
        document["objects"][0]["permissions"]["public_display"] = "not_applicable"
        document["objects"][0]["permissions"]["model_inference"] = "blocked"
        self.assertTrue(list(validator.iter_errors(document)))

    def test_manifest_last_signing_cache_and_removal_policies_are_closed(self) -> None:
        policies = self.document["policies"]
        self.assertTrue(policies["manifest_last"])
        self.assertFalse(policies["overwrite_final_keys"])
        self.assertFalse(policies["etag_is_content_checksum"])
        self.assertEqual(policies["signed_urls"]["maximum_ttl_seconds"], 900)
        self.assertFalse(policies["signed_urls"]["persist_url"])
        self.assertTrue(policies["local_cache"]["verify_on_read"])
        self.assertEqual(policies["removal"]["deadline_hours"], 24)
        self.assertFalse(policies["removal"]["object_lock_removable_media"])
        for phrase in (
            "compare-and-swap",
            "manifest last",
            "never treated as SHA-256",
            "Delete all B2 versions",
            "no crop, full-frame input, or embedding is created",
        ):
            self.assertIn(phrase, self.docs)


if __name__ == "__main__":
    unittest.main()
