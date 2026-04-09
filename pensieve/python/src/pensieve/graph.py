"""Cross-file edge aggregation (milestone B13).

Takes a list of per-file FileExtraction records (from B12's scan) and
resolves cross-file relationships:

  1. **Import edges:** `from utils import helper` in `main.py` →
     edge from main.py to utils.py.
  2. **Cross-file call edges:** `main()` calls `helper()` which was
     imported from utils.py → cross-file call edge.
  3. **Test→source mapping:** `test_main.py` imports from `main` →
     test_main.py tests main.py.

Output: a graph dict suitable for writing to `graph.json`.

Invariants:
  - External imports (stdlib, third-party packages not in the repo)
    are recorded as external_imports, not as cross-file edges.
  - NO false positives: if a module name can't be unambiguously resolved
    to a repo file, it's external. We never fall back to partial matches.
  - Circular imports are handled correctly (both edges appear).
  - Relative imports resolved against the importing file's directory.
  - Aliased imports tracked for cross-file call resolution.

Graph-level semantics:
  - **Import edges are module-level (file-to-file).** Multiple import
    statements from the same source to the same target are deduplicated
    into one edge. `import_count` on nodes reflects unique modules
    imported, not import statement count. The `detail` and `line` fields
    on deduped import edges are representative (first seen), not
    exhaustive.
  - **Test edges are module-level.** Same dedup as imports.
  - **Call edges are function-level.** Each distinct caller→callee
    relationship is preserved as a separate edge with its own detail,
    line, and confidence. Call edges are NOT deduplicated.
  - **Default-import call edges** are only emitted when the target's
    default export is a callable symbol (function or method). Classes
    and constants do not produce call edges.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from pensieve.schema import FileExtraction


# ---------------------------------------------------------------------------
# Module resolution
# ---------------------------------------------------------------------------


# Sentinel for ambiguous module names (multiple files share the same key).
# _resolve_module treats this as unresolvable.
_AMBIGUOUS = "<ambiguous>"


def _build_module_index(extractions: list[FileExtraction]) -> dict[str, str]:
    """Build a mapping from importable module names to file paths.

    Multiple keys per file to handle different import styles:
      - "utils" (stem) for `import utils` / `from utils import X`
      - "src.utils" (dotted path) for `from src.utils import X`
      - "models" for `models/__init__.py`

    Also builds a path-based index for JS/TS-style relative imports
    like `./utils.js` or `../lib/helpers.ts`.

    When two files produce the same key (e.g., pkg1/utils.py and
    pkg2/utils.py both map stem "utils"), the key is marked AMBIGUOUS.
    Ambiguous keys resolve to None (no edge), not a wrong edge.
    """
    index: dict[str, str] = {}

    def _put(key: str, value: str) -> None:
        """Insert a key, marking as ambiguous if already mapped to a
        DIFFERENT file."""
        existing = index.get(key)
        if existing is None:
            index[key] = value
        elif existing != value and existing != _AMBIGUOUS:
            index[key] = _AMBIGUOUS

    for ext in extractions:
        fp = ext.file_path
        p = PurePosixPath(fp)

        stem = p.stem
        parent = str(p.parent)

        # Module name = filename without extension
        _put(stem, fp)

        # Dotted module path from repo root: "src.utils"
        if parent != ".":
            dotted = parent.replace("/", ".").replace("\\", ".") + "." + stem
            _put(dotted, fp)

        # __init__.py → the directory is the module
        if stem == "__init__":
            dir_name = p.parent.name
            if dir_name:
                _put(dir_name, fp)

        # Full relative path for JS/TS: "./utils.js" resolves via path
        # These are unambiguous (unique file paths)
        index[fp] = fp
        no_ext = str(p.with_suffix(""))
        _put(no_ext, fp)

    return index


def _resolve_module(
    module_name: str,
    module_index: dict[str, str],
    importer_path: str,
) -> str | None:
    """Resolve a module name to a file path in the repo.

    Returns None if the module is external (not in the repo).
    NO false positives: we never fall back to partial/last-segment matches.
    """
    # Relative imports (Python: .utils, ..bar; JS/TS: ./utils, ../lib)
    if module_name.startswith("."):
        return _resolve_relative(module_name, importer_path, module_index)

    # Direct lookup (exact match only, reject ambiguous)
    if module_name in module_index:
        result = module_index[module_name]
        if result == _AMBIGUOUS:
            return None  # multiple files share this name — can't resolve
        if result != importer_path:
            return result

    return None


def _resolve_relative(
    module_name: str,
    importer_path: str,
    module_index: dict[str, str],
) -> str | None:
    """Resolve a relative import.

    Handles:
      Python: from .utils import X, from ..bar import X, from .sub.mod import X
      JS/TS: import { X } from "./utils", import { X } from "../lib/helpers"
    """
    importer = PurePosixPath(importer_path)
    base_dir = importer.parent

    # Separate leading dots/slashes from the module path
    # Python: ".utils" → dots=1, remainder="utils"
    #         "..bar" → dots=2, remainder="bar"
    #         ".sub.mod" → dots=1, remainder="sub.mod"
    # JS/TS: "./utils" → dots=1, remainder="utils" (after stripping ./)
    #         "./utils.js" → dots=1, remainder="utils.js"
    #         "../lib/helpers" → dots=2, remainder="lib/helpers"

    # Handle JS/TS path-style: "./" and "../"
    if "/" in module_name:
        return _resolve_path_relative(module_name, importer_path, module_index)

    # Python dotted-style: count leading dots
    stripped = module_name.lstrip(".")
    dots = len(module_name) - len(stripped)

    # Go up (dots - 1) levels
    for _ in range(dots - 1):
        base_dir = base_dir.parent

    if not stripped:
        # `from . import X` → current package's __init__.py
        init_path = str(base_dir / "__init__.py")
        if init_path.startswith("./"):
            init_path = init_path[2:]
        all_paths = set(module_index.values())
        return init_path if init_path in all_paths else None

    # Convert dotted remainder to path: "sub.mod" → "sub/mod"
    rel_parts = stripped.replace(".", "/")
    candidate_base = str(base_dir / rel_parts)
    if candidate_base.startswith("./"):
        candidate_base = candidate_base[2:]

    all_paths = set(module_index.values())
    all_paths.discard(_AMBIGUOUS)

    # Try with common extensions — collect all matches for ambiguity check
    matches: list[str] = []
    for ext in (".py", ".js", ".ts", ".tsx", ".go", ".java", ".rs", ""):
        candidate = candidate_base + ext
        if candidate in all_paths:
            matches.append(candidate)

    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        # Prefer importer's extension
        importer_ext = PurePosixPath(importer_path).suffix.lower()
        for m in matches:
            if m.endswith(importer_ext):
                return m
        return None  # ambiguous

    # Try as a package: sub/mod/__init__.py
    init_candidate = candidate_base + "/__init__.py"
    if init_candidate in all_paths:
        return init_candidate

    # NO global stem fallback — that creates false positives when
    # a relative import like `from .nonexistent` matches an unrelated
    # `other/nonexistent.py` elsewhere in the repo.
    return None


def _resolve_path_relative(
    module_name: str,
    importer_path: str,
    module_index: dict[str, str],
) -> str | None:
    """Resolve a path-style relative import (JS/TS).

    "./utils" or "./utils.js" or "../lib/helpers"
    """
    importer = PurePosixPath(importer_path)
    base_dir = importer.parent

    # Count ../ levels
    remaining = module_name
    ups = 0
    while remaining.startswith("../"):
        ups += 1
        remaining = remaining[3:]
    if remaining.startswith("./"):
        remaining = remaining[2:]

    for _ in range(ups):
        base_dir = base_dir.parent

    candidate_base = str(base_dir / remaining)
    if candidate_base.startswith("./"):
        candidate_base = candidate_base[2:]

    all_paths = set(module_index.values())
    # Remove ambiguous sentinel from the lookup set
    all_paths.discard(_AMBIGUOUS)

    # Try exact path (with extension already included, e.g., "./utils.js")
    if candidate_base in all_paths:
        return candidate_base

    # Try adding extensions — but collect ALL matches to detect ambiguity.
    # Prefer the importer's own extension first (main.ts importing ./utils
    # should prefer utils.ts over utils.js), but if multiple matches exist,
    # treat as ambiguous → return None.
    importer_ext = PurePosixPath(importer_path).suffix.lower()
    all_extensions = [".js", ".mjs", ".cjs", ".ts", ".tsx", ".py", ".go", ".java", ".rs"]

    matches: list[str] = []
    for ext in all_extensions:
        candidate = candidate_base + ext
        if candidate in all_paths:
            matches.append(candidate)

    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        # Multiple matches — try importer's extension first
        for m in matches:
            if m.endswith(importer_ext):
                return m
        # Still ambiguous — no false positives
        return None

    # Try as index file: ./utils → utils/index.js
    index_matches: list[str] = []
    for idx_name in ("index.js", "index.ts", "index.tsx", "__init__.py"):
        candidate = candidate_base + "/" + idx_name
        if candidate in all_paths:
            index_matches.append(candidate)

    if len(index_matches) == 1:
        return index_matches[0]
    elif len(index_matches) > 1:
        for m in index_matches:
            if PurePosixPath(m).suffix.lower() == importer_ext:
                return m
        return None

    return None


# ---------------------------------------------------------------------------
# Test file detection
# ---------------------------------------------------------------------------

_TEST_PREFIXES = ("test_",)
_TEST_SUFFIXES = ("_test",)
_TEST_DIRS = frozenset({"tests", "test", "spec", "specs"})


def _is_test_file(file_path: str) -> bool:
    """Detect if a file is a test file by naming convention."""
    p = PurePosixPath(file_path)
    stem = p.stem.lower()

    if any(stem.startswith(prefix) for prefix in _TEST_PREFIXES):
        return True
    if any(stem.endswith(suffix) for suffix in _TEST_SUFFIXES):
        return True

    for part in p.parts[:-1]:
        if part.lower() in _TEST_DIRS:
            return True

    return False


def _infer_tested_file(
    test_path: str,
    imports: list[dict],
    module_index: dict[str, str],
) -> list[str]:
    """Infer which source files a test file is testing."""
    tested: list[str] = []
    for imp in imports:
        module = imp.get("module", "")
        resolved = _resolve_module(module, module_index, test_path)
        if resolved and not _is_test_file(resolved):
            tested.append(resolved)
    return tested


# ---------------------------------------------------------------------------
# Graph building
# ---------------------------------------------------------------------------


@dataclass
class GraphEdge:
    source: str
    target: str
    kind: str  # "imports", "calls", "tests"
    detail: str = ""
    line: int = 0
    confidence: float = 1.0


def build_graph(
    extractions: list[FileExtraction],
) -> dict:
    """Build the cross-file graph from per-file extractions.

    Returns a dict with nodes, edges, and external_imports.
    """
    module_index = _build_module_index(extractions)

    symbols_by_file: dict[str, set[str]] = {}
    # Track the kind of each symbol by (file, name) for callable checking
    symbol_kinds: dict[str, dict[str, str]] = {}  # file → {name: kind}
    # Track which files have a callable default export (function/method).
    # Only callable defaults justify a call edge from a default import.
    has_callable_default_export: set[str] = set()
    _CALLABLE_KINDS = frozenset({"function", "method"})

    for ext in extractions:
        symbols_by_file[ext.file_path] = {s.name for s in ext.symbols}
        symbol_kinds[ext.file_path] = {s.name: s.kind for s in ext.symbols}
        for exp in ext.exports:
            if exp.kind == "default":
                # Check if the exported symbol is function-like
                sym_kind = symbol_kinds[ext.file_path].get(exp.name)
                if sym_kind in _CALLABLE_KINDS:
                    has_callable_default_export.add(ext.file_path)

    # Track imported names AND aliases for cross-file call resolution.
    # file_path → {local_name: (source_file_path, original_name, is_default)}
    # For non-aliased imports: local_name == original_name, is_default=False.
    # For named aliases: local_name is alias, original_name is the real name.
    # For default imports (alias only, no names): is_default=True, and we
    #   skip the symbol-existence check in pass 2 because the actual
    #   exported symbol name may differ from the local alias.
    imported_names: dict[str, dict[str, tuple[str, str, bool]]] = {
        e.file_path: {} for e in extractions
    }

    edges: list[GraphEdge] = []
    external_imports: list[dict] = []

    # --- Pass 1: Import edges ---
    for ext in extractions:
        for imp in ext.imports:
            resolved = _resolve_module(imp.module, module_index, ext.file_path)
            if resolved and resolved != ext.file_path:
                edges.append(GraphEdge(
                    source=ext.file_path,
                    target=resolved,
                    kind="imports",
                    detail=imp.module + (f" ({', '.join(imp.names)})" if imp.names else ""),
                    line=imp.line,
                ))
                # Track imported names for call resolution
                for name in imp.names:
                    if name and name != "*":
                        imported_names[ext.file_path][name] = (resolved, name, False)
                # Track alias
                if imp.alias and imp.alias != "_":
                    if imp.names:
                        # Named alias: `from utils import helper as h`
                        # h → (utils.py, helper, False)
                        original = imp.names[0]
                        imported_names[ext.file_path][imp.alias] = (resolved, original, False)
                    else:
                        # Default/namespace import: `import foo from './utils'`
                        # foo → (utils.js, foo, True=default)
                        # We can't know the actual exported symbol name.
                        imported_names[ext.file_path][imp.alias] = (resolved, imp.alias, True)
            elif not resolved:
                external_imports.append({
                    "file": ext.file_path,
                    "module": imp.module,
                    "names": imp.names,
                    "line": imp.line,
                })

    # --- Pass 2: Cross-file call edges ---
    for ext in extractions:
        for call in ext.call_edges:
            callee = call.callee
            entry = imported_names.get(ext.file_path, {}).get(callee)
            if entry:
                source_file, original_name, is_default = entry
                if source_file != ext.file_path:
                    if is_default:
                        # Default import: verify the target has a CALLABLE
                        # default export (function or method). Non-callable
                        # defaults (classes, constants) don't justify a call
                        # edge — `foo()` on a class is a constructor, not a
                        # function call in the dependency-graph sense; on a
                        # constant it's a runtime error.
                        if source_file in has_callable_default_export:
                            edges.append(GraphEdge(
                                source=ext.file_path,
                                target=source_file,
                                kind="calls",
                                detail=f"{call.caller} → {callee} (default import)",
                                line=call.line,
                                confidence=0.8,
                            ))
                    elif original_name in symbols_by_file.get(source_file, set()):
                        # Named import: verify the symbol exists in the target
                        edges.append(GraphEdge(
                            source=ext.file_path,
                            target=source_file,
                            kind="calls",
                            detail=f"{call.caller} → {original_name}",
                            line=call.line,
                            confidence=call.confidence,
                        ))

    # --- Pass 3: Test→source mapping ---
    for ext in extractions:
        if _is_test_file(ext.file_path):
            imp_dicts = [{"module": i.module, "names": i.names} for i in ext.imports]
            tested = _infer_tested_file(ext.file_path, imp_dicts, module_index)
            # Deduplicate: multiple Import records for the same module
            # (from aliased specifier splitting) should not create
            # duplicate test edges.
            for target in sorted(set(tested)):
                edges.append(GraphEdge(
                    source=ext.file_path,
                    target=target,
                    kind="tests",
                    detail=f"{ext.file_path} tests {target}",
                ))

    # --- Deduplicate import and test edges ---
    # Multiple Import records from the same import statement (due to
    # aliased specifier splitting) can produce duplicate import/test
    # edges to the same target. Dedup those by (source, target, kind).
    #
    # Call edges are NOT deduped: each represents a distinct
    # caller→callee relationship with its own detail/line/confidence.
    # Collapsing them loses graph fidelity.
    seen_import_test: set[tuple[str, str, str]] = set()
    deduped_edges: list[GraphEdge] = []
    for e in edges:
        if e.kind in ("imports", "tests"):
            key = (e.source, e.target, e.kind)
            if key not in seen_import_test:
                seen_import_test.add(key)
                deduped_edges.append(e)
        else:
            # calls edges: keep all
            deduped_edges.append(e)

    # --- Build nodes ---
    nodes = []
    for ext in extractions:
        # import_count = unique import statements (unique modules),
        # not Import records (which can be split for aliases).
        unique_modules = {i.module for i in ext.imports}
        nodes.append({
            "file_path": ext.file_path,
            "language": ext.language,
            "symbol_count": len(ext.symbols),
            "import_count": len(unique_modules),
            "is_test": _is_test_file(ext.file_path),
        })

    return {
        "nodes": nodes,
        "edges": [
            {
                "source": e.source,
                "target": e.target,
                "kind": e.kind,
                "detail": e.detail,
                "line": e.line,
                "confidence": e.confidence,
            }
            for e in deduped_edges
        ],
        "external_imports": external_imports,
    }
