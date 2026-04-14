"""SHA256 extraction cache (milestone B11).

Stores per-file `FileExtraction` results keyed by the SHA256 hash of
the file's content AND the file extension. This ensures that identical
bytes parsed by different language extractors (e.g., `.js` vs `.ts`)
produce separate cache entries.

Cache location: `{cache_dir}/{sha256}_{ext}.json`
Default cache_dir: `agent-docs/.cache/` in the target repo root.

Invariants:
  1. Same content + same extension → cache hit.
  2. Same content + different extension → cache miss (different extractor).
  3. Extractor source code changed → cache miss (stale extraction).
     The invalidation key is a SHA256 hash of all extractor source files,
     not the package version string. This means ANY change to ANY
     extractor file automatically invalidates all cache entries, with
     zero developer discipline required.
  4. Corrupted/unreadable/schema-invalid cache files → cache miss + warning.
  5. Cache directory created lazily on first put().
  6. Removing the cache directory produces identical output, just slower.

Caller responsibility (documented here, enforced in B12):
  - The `file_path` in a cached extraction may differ from the current
    file's path. The caller must update `file_path` on the returned
    extraction if the path doesn't match.
"""

from __future__ import annotations

import hashlib
import json
import warnings
from pathlib import Path

from pensieve._version import EXTRACTOR_HASH
from pensieve.schema import FileExtraction, SchemaError, validate_extraction


# ---------------------------------------------------------------------------
# Cache class
# ---------------------------------------------------------------------------


class ExtractionCache:
    """Cache for FileExtraction results, keyed by (SHA256, extension).

    Usage:
        cache = ExtractionCache(repo_root / "agent-docs" / ".cache")

        sha = cache.hash_file(path)
        cached = cache.get(sha, ext=path.suffix)
        if cached is not None:
            cached.file_path = str(relative_path)
            return cached

        extraction = extract_python(path)
        cache.put(extraction, ext=path.suffix)
        return extraction
    """

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    @staticmethod
    def hash_file(path: Path) -> str:
        """Compute the SHA256 hash of a file's content."""
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def hash_bytes(content: bytes) -> str:
        """Compute the SHA256 hash of raw bytes."""
        return hashlib.sha256(content).hexdigest()

    def _cache_path(self, sha256: str, ext: str) -> Path:
        """Cache key includes both content hash AND file extension."""
        ext_clean = ext.lstrip(".").lower()
        return self._cache_dir / f"{sha256}_{ext_clean}.json"

    def get(
        self,
        sha256: str,
        ext: str,
        extractor_version: str | None = None,
    ) -> FileExtraction | None:
        """Look up a cached extraction by content hash and extension.

        Returns the cached FileExtraction if:
          1. A cache file exists for this (hash, ext) pair, AND
          2. The extractor_version matches (defaults to EXTRACTOR_HASH), AND
          3. The loaded extraction passes schema validation.

        Returns None on miss. Never raises.

        Args:
            sha256: SHA256 of file content.
            ext: File extension (e.g., ".py").
            extractor_version: Expected version. Defaults to
                EXTRACTOR_HASH (computed from extractor source files).
        """
        if extractor_version is None:
            extractor_version = EXTRACTOR_HASH

        cache_file = self._cache_path(sha256, ext)

        if not cache_file.exists():
            return None

        try:
            extraction = FileExtraction.load(cache_file)
        except (json.JSONDecodeError, KeyError, TypeError, OSError) as e:
            warnings.warn(
                f"Corrupted cache entry at {cache_file}: {e}. "
                f"Treating as cache miss.",
                stacklevel=2,
            )
            return None

        # Version check: extractor source changed since this was cached
        if extraction.extractor_version != extractor_version:
            return None

        # Hash sanity check
        if extraction.sha256 != sha256:
            warnings.warn(
                f"Cache integrity error: {cache_file} has sha256="
                f"{extraction.sha256!r} but was looked up by sha256="
                f"{sha256!r}. Treating as cache miss.",
                stacklevel=2,
            )
            return None

        # Schema validation
        try:
            validate_extraction(extraction)
        except SchemaError as e:
            warnings.warn(
                f"Cache entry at {cache_file} fails schema validation: "
                f"{e}. Treating as cache miss.",
                stacklevel=2,
            )
            return None

        return extraction

    def put(self, extraction: FileExtraction, ext: str) -> Path:
        """Store an extraction in the cache.

        Sets the extraction's extractor_version to EXTRACTOR_HASH
        before writing, so future lookups match against the current
        extractor source code.
        """
        extraction.extractor_version = EXTRACTOR_HASH
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self._cache_path(extraction.sha256, ext)
        extraction.save(cache_file)
        return cache_file

    def has(self, sha256: str, ext: str) -> bool:
        """Check whether a cache file exists (existence only, no validation)."""
        return self._cache_path(sha256, ext).exists()

    def invalidate(self, sha256: str, ext: str) -> bool:
        """Remove a specific cache entry. Returns True if removed."""
        cache_file = self._cache_path(sha256, ext)
        if cache_file.exists():
            cache_file.unlink()
            return True
        return False

    def clear(self) -> int:
        """Remove all cache entries. Returns count removed."""
        if not self._cache_dir.exists():
            return 0
        count = 0
        for f in self._cache_dir.glob("*.json"):
            f.unlink()
            count += 1
        return count

    def stats(self) -> dict[str, int]:
        """Return basic cache statistics."""
        if not self._cache_dir.exists():
            return {"entries": 0, "size_bytes": 0}
        entries = list(self._cache_dir.glob("*.json"))
        return {
            "entries": len(entries),
            "size_bytes": sum(f.stat().st_size for f in entries),
        }
