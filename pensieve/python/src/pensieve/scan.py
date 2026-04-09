"""Repository scanner (milestone B12).

Walks a directory, finds all files with supported extensions, extracts
each using the appropriate language extractor, caches results for
incremental re-runs, and writes the aggregated output to
`agent-docs/structure.json`.

Usage:
    from pensieve.scan import scan_repo

    result = scan_repo(Path("/path/to/repo"))
    # result.structure_path → Path to structure.json
    # result.extractions → list of FileExtraction (schema-valid only)
    # result.errors → list of dicts for failed files
    # result.stats → {"total_files", "cached", "extracted", "failed"}

Or via CLI:
    pensieve scan /path/to/repo

Invariants:
  1. File paths in structure.json are RELATIVE to the repo root.
  2. Cache-aware: unchanged files served from cache (B11).
  3. structure.json `files` contains ONLY schema-valid FileExtraction
     records. Failed files go in a separate `errors` array.
  4. Ignored directories are pruned during walk (os.walk), not
     filtered after traversal.
  5. `extract_file() → None` on a file with a supported extension is
     treated as a failure, not a skip. After _collect_files filters by
     extension, None means the extractor failed to load.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from pensieve import __version__
from pensieve._version import EXTRACTOR_HASH
from pensieve.cache import ExtractionCache
from pensieve.extractors import extract_file, supported_extensions
from pensieve.graph import build_graph
from pensieve.schema import FileExtraction, SchemaError, validate_extraction

# ---------------------------------------------------------------------------
# Default ignore patterns
# ---------------------------------------------------------------------------

DEFAULT_IGNORE_DIRS: frozenset[str] = frozenset({
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "vendor",
    "__pycache__",
    ".venv",
    "venv",
    ".env",
    "env",
    "dist",
    "build",
    "target",         # Rust, Java (Maven)
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".cache",         # our own cache dir
    "agent-docs",     # don't scan our own output
    ".claude",
})


# ---------------------------------------------------------------------------
# Scan result
# ---------------------------------------------------------------------------


@dataclass
class ScanResult:
    """Result of a full repo scan."""

    repo_root: Path
    structure_path: Path
    graph_path: Path
    extractions: list[FileExtraction]
    errors: list[dict]
    stats: dict[str, int]
    scan_time_seconds: float
    extractor_version: str = field(default_factory=lambda: EXTRACTOR_HASH)


# ---------------------------------------------------------------------------
# File detection (os.walk with pruning)
# ---------------------------------------------------------------------------


def _collect_files(
    root: Path,
    extensions: frozenset[str],
    ignore_dirs: frozenset[str],
) -> list[Path]:
    """Walk the directory tree and collect files with supported extensions.

    Uses os.walk with in-place pruning of `dirnames` to skip ignored
    subtrees entirely (no traversal cost for node_modules, .git, etc.).
    Returns absolute paths sorted for deterministic output.
    """
    root = root.resolve()
    files: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        # Prune ignored directories IN-PLACE so os.walk doesn't descend
        dirnames[:] = sorted(
            d for d in dirnames if d not in ignore_dirs
        )

        for filename in sorted(filenames):
            filepath = Path(dirpath) / filename
            if filepath.suffix.lower() in extensions:
                files.append(filepath)

    return files


# ---------------------------------------------------------------------------
# Main scan function
# ---------------------------------------------------------------------------


def scan_repo(
    repo_root: Path,
    output_dir: Path | None = None,
    ignore_dirs: frozenset[str] | None = None,
) -> ScanResult:
    """Scan a repository and produce structure.json.

    Args:
        repo_root: Path to the repository root directory.
        output_dir: Where to write output files. Defaults to
            `repo_root / "agent-docs"`.
        ignore_dirs: Directory names to skip. Defaults to
            DEFAULT_IGNORE_DIRS.

    Returns:
        A ScanResult with all extractions and statistics.
    """
    start = time.monotonic()
    repo_root = repo_root.resolve()

    if output_dir is None:
        output_dir = repo_root / "agent-docs"

    if ignore_dirs is None:
        ignore_dirs = DEFAULT_IGNORE_DIRS

    cache = ExtractionCache(output_dir / ".cache")
    extensions = supported_extensions()

    # --- Detect files ---
    files = _collect_files(repo_root, extensions, ignore_dirs)

    # --- Extract each file ---
    extractions: list[FileExtraction] = []
    errors: list[dict] = []
    stats = {
        "total_files": len(files),
        "cached": 0,
        "extracted": 0,
        "failed": 0,
    }

    for file_path in files:
        rel_path = str(file_path.relative_to(repo_root))

        try:
            sha = cache.hash_file(file_path)
            ext = file_path.suffix

            # Try cache first (keyed by hash + extension)
            cached = cache.get(sha, ext=ext)
            if cached is not None:
                cached.file_path = rel_path
                extractions.append(cached)
                stats["cached"] += 1
                continue

            # Cache miss — extract
            extraction = extract_file(file_path)

            if extraction is None:
                # extract_file returned None on a file with a supported
                # extension. This means the extractor failed to load
                # (lazy import failure), NOT "unsupported file". Record
                # as failure, not skip.
                errors.append({
                    "file_path": rel_path,
                    "error": (
                        f"Extractor returned None for supported extension "
                        f"'{ext}'. Likely a missing or broken extractor module."
                    ),
                })
                stats["failed"] += 1
                continue

            # Normalize file_path to relative
            extraction.file_path = rel_path
            extraction.sha256 = sha

            # Validate BEFORE caching or writing to files[].
            # A buggy extractor should not poison the cache or
            # structure.json with schema-invalid entries.
            try:
                validate_extraction(extraction)
            except SchemaError as ve:
                errors.append({
                    "file_path": rel_path,
                    "error": f"Extractor produced schema-invalid output: {ve}",
                })
                stats["failed"] += 1
                continue

            # Cache the result (only schema-valid extractions)
            cache.put(extraction, ext=ext)
            extractions.append(extraction)
            stats["extracted"] += 1

        except Exception as e:
            # Record failed extraction in the errors channel, not in
            # the files list. The files list must contain only schema-
            # valid FileExtraction records.
            errors.append({
                "file_path": rel_path,
                "error": f"Extraction failed: {e}",
            })
            stats["failed"] += 1

    # --- Write structure.json ---
    output_dir.mkdir(parents=True, exist_ok=True)
    structure_path = output_dir / "structure.json"

    structure_data = {
        "version": __version__,
        "repo_root": str(repo_root),
        "scan_stats": stats,
        "files": [ext.to_dict() for ext in extractions],
        "errors": errors,
    }

    structure_path.write_text(
        json.dumps(structure_data, indent=2),
        encoding="utf-8",
    )

    # --- Build and write graph.json (B13: cross-file edges) ---
    graph_data = build_graph(extractions)
    graph_path = output_dir / "graph.json"
    graph_path.write_text(
        json.dumps(graph_data, indent=2),
        encoding="utf-8",
    )

    elapsed = time.monotonic() - start

    return ScanResult(
        repo_root=repo_root,
        structure_path=structure_path,
        graph_path=graph_path,
        extractions=extractions,
        errors=errors,
        stats=stats,
        scan_time_seconds=round(elapsed, 3),
    )
