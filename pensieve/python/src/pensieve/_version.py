"""Extractor source hash computation.

Computes a SHA256 hash of all extractor source files at import time.
Both schema.py and cache.py import EXTRACTOR_HASH from here.

IMPORTANT: This module must NOT import any other pensieve module
(to avoid circular imports). It locates source files via __file__
paths only.
"""

from __future__ import annotations

import hashlib
import warnings
from pathlib import Path


def _compute_extractor_hash() -> str:
    """Compute a SHA256 hash of all extractor source files.

    Uses __file__ to locate source files — no module imports, so no
    circular import risk.

    Includes: extractors/*.py and schema.py.
    Falls back to package version with a warning on failure.
    """
    try:
        this_dir = Path(__file__).parent  # pensieve/
        pkg_dir = this_dir / "extractors"
        schema_path = this_dir / "schema.py"

        source_files: list[Path] = []

        if pkg_dir.is_dir():
            source_files.extend(sorted(pkg_dir.glob("*.py")))

        if schema_path.exists():
            source_files.append(schema_path)

        if not source_files:
            warnings.warn(
                "No extractor source files found for hash computation. "
                "Falling back to __version__ for cache invalidation.",
                stacklevel=2,
            )
            # Import __version__ lazily here only in fallback path
            from pensieve import __version__
            return __version__

        hasher = hashlib.sha256()
        for src_file in sorted(source_files):
            hasher.update(src_file.read_bytes())

        return hasher.hexdigest()[:16]

    except (OSError, ImportError) as e:
        warnings.warn(
            f"Cannot compute extractor source hash: {e}. "
            f"Falling back to __version__ for cache invalidation. "
            f"Cache entries may be stale after extractor changes.",
            stacklevel=2,
        )
        from pensieve import __version__
        return __version__


EXTRACTOR_HASH: str = _compute_extractor_hash()
