from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))

from butterflylens.contracts import (  # noqa: E402
    CanonicalizationError,
    canonicalize_evidence_preimage,
    canonicalize_json,
    normalize_evidence_preimage,
    semantic_fingerprint_digest,
)


class FingerprintCanonicalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preimage = {
            "fingerprint_kind": "review_event",
            "subject_id": "event:canonical",
            "payload_schema_version": "v1",
            "payload": {"outcome": "yes", "confidence": 4},
            "parents": [
                {
                    "relationship": "reviews",
                    "fingerprint_kind": "media_object",
                    "digest": "b" * 64,
                },
                {
                    "relationship": "derived_from",
                    "fingerprint_kind": "source_flickr_record",
                    "digest": "a" * 64,
                },
            ],
        }

    def test_jcs_numbers_keys_and_literals_match_frozen_vector(self) -> None:
        value = {
            "z": [3, True, None],
            "a": "butterfly",
            "numbers": [333333333.33333329, 1e30, 4.50, 2e-3, 1e-27],
        }
        self.assertEqual(
            canonicalize_json(value),
            b'{"a":"butterfly","numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],"z":[3,true,null]}',
        )

    def test_parent_order_is_semantic_and_input_is_not_mutated(self) -> None:
        normalized = normalize_evidence_preimage(self.preimage)
        self.assertEqual(self.preimage["parents"][0]["relationship"], "reviews")
        self.assertEqual(normalized["parents"][0]["relationship"], "derived_from")
        canonical = canonicalize_evidence_preimage(self.preimage)
        self.assertLess(canonical.index(b"derived_from"), canonical.index(b"reviews"))

    def test_digest_hashes_exact_canonical_preimage_bytes(self) -> None:
        canonical = canonicalize_evidence_preimage(self.preimage)
        self.assertEqual(semantic_fingerprint_digest(self.preimage), hashlib.sha256(canonical).hexdigest())
        self.assertEqual(
            semantic_fingerprint_digest(self.preimage),
            "919a3bfc043d06fb360057855273964b3e4df0d11f6e315d64ddc4cb52900fdc",
        )

    def test_duplicate_parent_is_rejected(self) -> None:
        self.preimage["parents"].append(dict(self.preimage["parents"][0]))
        with self.assertRaisesRegex(CanonicalizationError, "duplicate parent"):
            canonicalize_evidence_preimage(self.preimage)

    def test_non_i_json_values_fail_closed(self) -> None:
        invalid_values = (
            -0.0,
            float("nan"),
            float("inf"),
            9_007_199_254_740_992,
            "\ud800",
            {1: "non-string key"},
            ("tuple",),
        )
        for value in invalid_values:
            with self.subTest(value=repr(value)):
                with self.assertRaises(CanonicalizationError):
                    canonicalize_json(value)

    def test_payload_array_order_remains_meaningful(self) -> None:
        first = {**self.preimage, "payload": {"ranked": ["a", "b"]}}
        second = {**self.preimage, "payload": {"ranked": ["b", "a"]}}
        self.assertNotEqual(
            semantic_fingerprint_digest(first),
            semantic_fingerprint_digest(second),
        )


if __name__ == "__main__":
    unittest.main()
