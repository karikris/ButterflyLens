"""Checksum-verified submitted evidence repository for analyst tools."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable


REGISTRY_PATH = Path("packages/openai/submitted-artifacts.v1.json")
REGISTRY_SCHEMA_VERSION = "butterflylens-openai-artifact-registry:v1.1.0"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")


class ArtifactIntegrityError(RuntimeError):
    """Raised when the pinned submitted artifact registry fails closed."""


@dataclass(frozen=True, slots=True)
class SourceArtifact:
    key: str
    artifact_id: str
    path: str
    sha256: str


class SubmittedEvidenceRepository:
    """Read only checksum-pinned artifacts from one committed submitted snapshot."""

    def __init__(
        self,
        repo_root: str | Path,
        *,
        registry_path: str | Path = REGISTRY_PATH,
    ) -> None:
        self.root = Path(repo_root).resolve()
        configured_path = Path(registry_path)
        self.registry_path = (
            configured_path
            if configured_path.is_absolute()
            else self.root / configured_path
        )
        self._registry = self._load_registry()
        self.repository = self._require_text(self._registry, "repository")
        self.commit = self._require_text(self._registry, "commit")
        if self.repository != "karikris/ButterflyLens":
            raise ArtifactIntegrityError("artifact registry repository is not allowlisted")
        if _COMMIT.fullmatch(self.commit) is None:
            raise ArtifactIntegrityError("artifact registry commit is not an exact SHA")
        self.snapshot_mode = self._require_text(self._registry, "snapshot_mode")
        if self.snapshot_mode != "submitted":
            raise ArtifactIntegrityError("only the submitted snapshot is allowed")
        self._artifacts = self._load_artifacts()
        self._artifact_bytes_cache: dict[str, bytes] = {}
        self._json_cache: dict[str, Any] = {}
        self._verify_all()
        self._species_by_key: dict[str, dict[str, Any]] | None = None
        self._species_by_name: dict[str, dict[str, Any]] | None = None

    def _load_registry(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ArtifactIntegrityError(
                f"cannot read artifact registry: {self.registry_path}"
            ) from error
        if not isinstance(payload, dict):
            raise ArtifactIntegrityError("artifact registry must be a JSON object")
        if payload.get("schema_version") != REGISTRY_SCHEMA_VERSION:
            raise ArtifactIntegrityError("artifact registry schema version is unsupported")
        return payload

    @staticmethod
    def _require_text(payload: dict[str, Any], field: str) -> str:
        value = payload.get(field)
        if not isinstance(value, str) or not value:
            raise ArtifactIntegrityError(f"artifact registry {field} is missing")
        return value

    def _load_artifacts(self) -> dict[str, SourceArtifact]:
        rows = self._registry.get("artifacts")
        if not isinstance(rows, list) or not rows:
            raise ArtifactIntegrityError("artifact registry has no artifacts")
        artifacts: dict[str, SourceArtifact] = {}
        artifact_ids: set[str] = set()
        paths: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                raise ArtifactIntegrityError("artifact registry row must be an object")
            values = {
                field: row.get(field)
                for field in ("key", "artifact_id", "path", "sha256")
            }
            if any(not isinstance(value, str) or not value for value in values.values()):
                raise ArtifactIntegrityError("artifact registry row has missing fields")
            key = values["key"]
            artifact_id = values["artifact_id"]
            relative_path = values["path"]
            digest = values["sha256"]
            if key in artifacts or artifact_id in artifact_ids or relative_path in paths:
                raise ArtifactIntegrityError("artifact keys, IDs, and paths must be unique")
            if Path(relative_path).is_absolute() or ".." in Path(relative_path).parts:
                raise ArtifactIntegrityError("artifact path escapes the repository")
            if _SHA256.fullmatch(digest) is None:
                raise ArtifactIntegrityError("artifact SHA-256 is malformed")
            artifacts[key] = SourceArtifact(
                key=key,
                artifact_id=artifact_id,
                path=relative_path,
                sha256=digest,
            )
            artifact_ids.add(artifact_id)
            paths.add(relative_path)
        return artifacts

    def _verify_all(self) -> None:
        for artifact in self._artifacts.values():
            digest = hashlib.sha256(self._read_pinned_bytes(artifact)).hexdigest()
            if digest != artifact.sha256:
                raise ArtifactIntegrityError(
                    f"pinned artifact checksum mismatch: {artifact.path}"
                )

    def _read_pinned_bytes(self, artifact: SourceArtifact) -> bytes:
        if artifact.key not in self._artifact_bytes_cache:
            try:
                completed = subprocess.run(
                    ["git", "show", f"{self.commit}:{artifact.path}"],
                    cwd=self.root,
                    check=True,
                    capture_output=True,
                )
            except (OSError, subprocess.CalledProcessError) as error:
                raise ArtifactIntegrityError(
                    f"cannot read pinned artifact: {artifact.path}"
                ) from error
            self._artifact_bytes_cache[artifact.key] = completed.stdout
        return self._artifact_bytes_cache[artifact.key]

    @property
    def artifact_keys(self) -> tuple[str, ...]:
        return tuple(self._artifacts)

    def artifact(self, key: str) -> SourceArtifact:
        try:
            return self._artifacts[key]
        except KeyError as error:
            raise ArtifactIntegrityError(f"unknown artifact key: {key}") from error

    def citation(self, key: str) -> dict[str, str]:
        artifact = self.artifact(key)
        return {
            "artifact_id": artifact.artifact_id,
            "repository": self.repository,
            "commit": self.commit,
            "path": artifact.path,
            "fingerprint": f"sha256:{artifact.sha256}",
        }

    def citations(self, keys: Iterable[str]) -> list[dict[str, str]]:
        seen: set[str] = set()
        result: list[dict[str, str]] = []
        for key in keys:
            citation = self.citation(key)
            artifact_id = citation["artifact_id"]
            if artifact_id not in seen:
                result.append(citation)
                seen.add(artifact_id)
        return result

    def read_json(self, key: str) -> Any:
        if key not in self._json_cache:
            artifact = self.artifact(key)
            try:
                payload = json.loads(self._read_pinned_bytes(artifact))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ArtifactIntegrityError(
                    f"pinned artifact is not readable JSON: {artifact.path}"
                ) from error
            self._json_cache[key] = payload
        return deepcopy(self._json_cache[key])

    def species_catalogue(self) -> dict[str, Any]:
        payload = self.read_json("species_catalogue")
        if not isinstance(payload, dict) or not isinstance(payload.get("species"), list):
            raise ArtifactIntegrityError("species catalogue shape is invalid")
        return payload

    def submitted_map(self) -> dict[str, Any]:
        payload = self.read_json("submitted_map")
        if not isinstance(payload, dict):
            raise ArtifactIntegrityError("submitted map shape is invalid")
        if (
            payload.get("schemaVersion")
            != "butterflylens-submitted-map-browser-snapshot/v1"
        ):
            raise ArtifactIntegrityError("submitted map schema version is unsupported")
        counts = payload.get("counts")
        layers = payload.get("layers")
        scopes = payload.get("scopes")
        cells = payload.get("cells")
        rights = payload.get("rights")
        if not all(isinstance(value, dict) for value in (counts, layers, scopes, rights)):
            raise ArtifactIntegrityError("submitted map metadata is malformed")
        if not isinstance(cells, list) or not all(isinstance(row, dict) for row in cells):
            raise ArtifactIntegrityError("submitted map cells are malformed")
        if layers.get("alaBaseline", {}).get("status") != "available":
            raise ArtifactIntegrityError("submitted map ALA layer is not available")
        if layers.get("flickrCandidate", {}).get("status") != "unavailable":
            raise ArtifactIntegrityError("submitted map Flickr boundary is invalid")
        if rights.get("legalConclusion") is not False:
            raise ArtifactIntegrityError("submitted map rights boundary is invalid")
        for scope_type in ("state", "ibra", "lga", "h3"):
            rows = scopes.get(scope_type)
            if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
                raise ArtifactIntegrityError(
                    f"submitted map {scope_type} scopes are malformed"
                )
        return payload

    def find_map_scope(
        self,
        *,
        scope_type: str,
        scope_id: str | None,
    ) -> dict[str, Any] | None:
        if scope_type == "national":
            return {"scopeId": "AU", "label": "Australia"} if scope_id is None else None
        payload = self.submitted_map()
        rows = payload["scopes"].get(scope_type)
        if not isinstance(rows, list):
            return None
        for row in rows:
            if row.get("scopeId") == scope_id:
                return deepcopy(row)
        return None

    def species(self) -> tuple[dict[str, Any], ...]:
        rows = self.species_catalogue()["species"]
        if not all(isinstance(row, dict) for row in rows):
            raise ArtifactIntegrityError("species catalogue rows must be objects")
        return tuple(rows)

    def find_species(
        self,
        *,
        species_key: str | None,
        scientific_name: str | None,
    ) -> dict[str, Any] | None:
        self._ensure_species_indexes()
        if species_key is not None:
            row = self._species_by_key.get(species_key)  # type: ignore[union-attr]
            return deepcopy(row) if row is not None else None
        if scientific_name is not None:
            row = self._species_by_name.get(  # type: ignore[union-attr]
                scientific_name.casefold()
            )
            return deepcopy(row) if row is not None else None
        return None

    def _ensure_species_indexes(self) -> None:
        if self._species_by_key is not None:
            return
        by_key: dict[str, dict[str, Any]] = {}
        by_name: dict[str, dict[str, Any]] = {}
        for row in self.species():
            key = row.get("key")
            name = row.get("acceptedScientificName")
            if not isinstance(key, str) or not isinstance(name, str):
                raise ArtifactIntegrityError("species row has no stable key or name")
            folded = name.casefold()
            if key in by_key or folded in by_name:
                raise ArtifactIntegrityError("species keys and accepted names must be unique")
            by_key[key] = row
            by_name[folded] = row
        self._species_by_key = by_key
        self._species_by_name = by_name
