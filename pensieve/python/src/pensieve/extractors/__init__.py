"""Language-specific structural extractors.

Each extractor takes a file path, parses it with tree-sitter, walks
the AST, and returns a `FileExtraction` (defined in `pensieve.schema`).

Registry of extractors by file extension:

  .py              → extractors.python
  .js, .mjs, .cjs → extractors.javascript
  .ts, .tsx        → extractors.typescript
  .go              → extractors.go
  .java            → extractors.java
  .rs              → extractors.rust

Extractors are loaded LAZILY on first use, not eagerly at package
import. This means a broken or missing language module (e.g., missing
tree-sitter-rust) won't prevent other extractors from working.
"""

from __future__ import annotations

import importlib
from pathlib import Path

from pensieve.schema import FileExtraction

# ---------------------------------------------------------------------------
# Lazy extractor registry
# ---------------------------------------------------------------------------

# Maps file extension → (module_name, function_name).
# Each extractor module calls `register()` at import time, but we also
# maintain this static map so we can lazy-import modules that haven't
# been loaded yet.
_LAZY_REGISTRY: dict[str, tuple[str, str]] = {
    ".py": ("pensieve.extractors.python", "extract_python"),
    ".js": ("pensieve.extractors.javascript", "extract_javascript"),
    ".mjs": ("pensieve.extractors.javascript", "extract_javascript"),
    ".cjs": ("pensieve.extractors.javascript", "extract_javascript"),
    ".ts": ("pensieve.extractors.typescript", "extract_typescript"),
    ".tsx": ("pensieve.extractors.typescript", "extract_typescript"),
    ".go": ("pensieve.extractors.go", "extract_go"),
    ".java": ("pensieve.extractors.java", "extract_java"),
    ".rs": ("pensieve.extractors.rust", "extract_rust"),
}

# Cache of already-resolved extractor functions to avoid repeated
# importlib lookups.
_RESOLVED: dict[str, object] = {}


def _resolve(ext: str) -> object | None:
    """Lazily resolve an extractor function for a file extension."""
    if ext in _RESOLVED:
        return _RESOLVED[ext]

    entry = _LAZY_REGISTRY.get(ext)
    if entry is None:
        return None

    module_name, func_name = entry
    try:
        module = importlib.import_module(module_name)
        func = getattr(module, func_name)
        _RESOLVED[ext] = func
        return func
    except (ImportError, AttributeError) as e:
        # Log but don't crash — one broken extractor shouldn't take
        # down the whole package.
        import warnings
        warnings.warn(
            f"Failed to load extractor for '{ext}' from {module_name}: {e}",
            stacklevel=2,
        )
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def register(extensions: list[str], func: object) -> None:
    """Register an extractor function for one or more file extensions.

    Called by each extractor module at import time. Also pre-populates
    the resolved cache so subsequent calls skip importlib.
    """
    for ext in extensions:
        _RESOLVED[ext] = func


def extract_file(path: Path) -> FileExtraction | None:
    """Extract structural data from a source file.

    Returns a FileExtraction if the file's extension has a registered
    extractor, or None if the extension is unsupported. The extractor
    module is loaded lazily on first use.
    """
    ext = path.suffix.lower()
    extractor = _resolve(ext)
    if extractor is None:
        return None
    return extractor(path)  # type: ignore[operator]


def supported_extensions() -> frozenset[str]:
    """Return the set of file extensions with registered extractors."""
    return frozenset(_LAZY_REGISTRY.keys())


# NO eager imports. Each extractor module is loaded on first use via
# _resolve() → importlib.import_module(). This is the fix for Codex
# review finding #1: one broken language module no longer takes down
# the whole extractor package.
