"""Per-file structural extraction schema (milestone B3).

This is the canonical schema for what each language extractor (B4-B9)
outputs per file. Every extractor produces a `FileExtraction` instance
that captures the structural landmarks in a source file without
storing the raw code. Downstream consumers (structure.json, graph.json,
the LLM orchestration layer, the cache) all read this schema.

The schema is designed around these principles:

1. **Flat symbol list with `parent` for containment.** Methods inside
   classes are separate Symbol entries with `parent` pointing at the
   class. This is easier to iterate, query, and serialize than nested
   class-containing-methods.

2. **Continuous confidence scores (0.0-1.0).** Call edges and inferred
   relationships use floats, not categorical labels. 1.0 = extracted
   directly from AST; <1.0 = inferred via heuristic.

3. **Extractor version in output.** Cache invalidation when extractor
   logic changes (not just when the source file changes).

4. **No raw code stored.** The `signature` field captures the
   declaration line; the `docstring` field captures documentation.
   Bodies are not stored — the LLM reads selected raw files for
   interpretation (B14), while the extraction provides the structural
   skeleton.

Serialization: `dataclasses.asdict(extraction)` → dict → `json.dumps`.
Deserialization: `FileExtraction.from_dict(d)`.
Validation: `validate_extraction(extraction)` raises `SchemaError` on
invalid data.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

from pensieve._version import EXTRACTOR_HASH

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

SymbolKind = Literal[
    "function",
    "class",
    "method",
    "interface",
    "trait",
    "struct",
    "enum",
    "type_alias",
    "constant",
]

Language = Literal[
    "python",
    "javascript",
    "typescript",
    "go",
    "java",
    "rust",
]

Visibility = Literal[
    "public",
    "private",
    "protected",
    "package",
    "unknown",
]

CommentTag = Literal[
    "WHY",
    "NOTE",
    "IMPORTANT",
    "HACK",
    "TODO",
    "FIXME",
]

VALID_SYMBOL_KINDS: frozenset[str] = frozenset(SymbolKind.__args__)  # type: ignore[attr-defined]
VALID_LANGUAGES: frozenset[str] = frozenset(Language.__args__)  # type: ignore[attr-defined]
VALID_VISIBILITIES: frozenset[str] = frozenset(Visibility.__args__)  # type: ignore[attr-defined]
VALID_COMMENT_TAGS: frozenset[str] = frozenset(CommentTag.__args__)  # type: ignore[attr-defined]

VALID_IMPORT_KINDS: frozenset[str] = frozenset({
    "import",        # Python `import X`, JS/TS ESM, Go, Java
    "from_import",   # Python `from X import Y`
    "require",       # JS CommonJS `require('X')`
    "use",           # Rust `use X`
    "static_import", # Java `import static X`
    "import_type",   # TS `import type { X }`
})

VALID_EXPORT_KINDS: frozenset[str] = frozenset({
    "default",       # JS/TS `export default X`
    "named",         # JS/TS `export { X }` or `export function X`
    "type",          # TS `export type X`
    "re_export",     # JS/TS `export { X } from 'Y'`
})

# ---------------------------------------------------------------------------
# Schema dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Parameter:
    """A function/method parameter."""

    name: str
    type: str | None = None  # type annotation if available
    default: str | None = None  # default value if available


@dataclass
class Symbol:
    """A structural landmark in a source file.

    Functions, classes, methods, interfaces, traits, structs, enums,
    type aliases, and constants are all Symbols. Methods have a
    `parent` field pointing at their containing class/struct/impl.
    """

    name: str
    kind: SymbolKind
    line_start: int
    line_end: int
    signature: str  # the declaration line (no body)
    visibility: Visibility = "unknown"
    parent: str | None = None  # containing symbol name (for methods)
    docstring: str | None = None
    parameters: list[Parameter] = field(default_factory=list)
    return_type: str | None = None


@dataclass
class Import:
    """An import/use/require statement."""

    module: str  # what's being imported ("os", "react", "fmt")
    names: list[str] = field(default_factory=list)  # specific names; empty for whole-module
    alias: str | None = None  # import numpy as np → alias="np"
    line: int = 0
    kind: str = "import"  # import, from_import, use, require


@dataclass
class Export:
    """An explicit export (JS/TS named/default exports).

    For Go/Rust/Java, visibility is on the Symbol itself; Export
    entries are only generated for JS/TS where exports are explicit
    statements separate from declarations.

    For anonymous default exports (``export default function() {}`` or
    ``export default () => {}``), the name is the reserved sentinel
    ``"<default>"``. This is NOT a source identifier — it signals to
    the graph layer that the default export is an anonymous callable.
    No corresponding Symbol entry exists for this name.
    """

    name: str
    kind: str = "named"  # default, named, type, re_export
    line: int = 0


@dataclass
class CallEdge:
    """A function/method call detected within a single file.

    Cross-file call edges are computed in B13 by resolving imports
    against the per-file symbol tables.
    """

    caller: str  # containing function/method name
    callee: str  # called function/method name
    line: int = 0
    confidence: float = 1.0  # 1.0 = AST-extracted, <1.0 = inferred


@dataclass
class RationaleComment:
    """A tagged comment (# WHY:, // NOTE:, /* HACK: */, etc.).

    These are the comments that carry design rationale — the "why"
    that the LLM needs for decisions.md and the nano-digest.
    """

    tag: CommentTag
    text: str
    line: int = 0
    context: str | None = None  # containing function/class name


@dataclass
class FileExtraction:
    """Complete structural extraction for a single source file.

    This is the top-level schema. Each language extractor (B4-B9)
    produces one of these per file. The SHA256 cache (B11) stores
    these keyed by file hash. `structure.json` (B12) aggregates
    all of these for one repo.
    """

    file_path: str  # path as provided by the caller; scan_repo() normalizes to repo-relative
    language: Language
    sha256: str  # hash of file content at extraction time
    file_size_bytes: int
    line_count: int

    symbols: list[Symbol] = field(default_factory=list)
    imports: list[Import] = field(default_factory=list)
    exports: list[Export] = field(default_factory=list)
    call_edges: list[CallEdge] = field(default_factory=list)
    rationale_comments: list[RationaleComment] = field(default_factory=list)

    extraction_errors: list[str] = field(default_factory=list)
    extractor_version: str = field(default_factory=lambda: EXTRACTOR_HASH)

    # --- Serialization ---

    def to_dict(self) -> dict:
        """Convert to a plain dict suitable for JSON serialization."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialize to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, d: dict) -> FileExtraction:
        """Deserialize from a plain dict (e.g., loaded from JSON)."""
        return cls(
            file_path=d["file_path"],
            language=d["language"],
            sha256=d["sha256"],
            file_size_bytes=d["file_size_bytes"],
            line_count=d["line_count"],
            symbols=[Symbol(**s) if isinstance(s, dict) else s for s in d.get("symbols", [])],
            imports=[Import(**i) if isinstance(i, dict) else i for i in d.get("imports", [])],
            exports=[Export(**e) if isinstance(e, dict) else e for e in d.get("exports", [])],
            call_edges=[CallEdge(**c) if isinstance(c, dict) else c for c in d.get("call_edges", [])],
            rationale_comments=[
                RationaleComment(**r) if isinstance(r, dict) else r
                for r in d.get("rationale_comments", [])
            ],
            extraction_errors=d.get("extraction_errors", []),
            extractor_version=d.get("extractor_version", "unknown"),
        )

    @classmethod
    def from_json(cls, s: str) -> FileExtraction:
        """Deserialize from a JSON string."""
        return cls.from_dict(json.loads(s))

    def save(self, path: Path) -> None:
        """Write to a JSON file."""
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> FileExtraction:
        """Load from a JSON file."""
        return cls.from_json(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Nested Parameter deserialization in from_dict
# ---------------------------------------------------------------------------
# The Symbol dataclass has `parameters: list[Parameter]`. When loading
# from JSON, these come back as dicts. We handle this in from_dict above
# for the top-level lists, but Symbol.parameters also needs it. Override
# Symbol's __post_init__ to handle this.

_original_symbol_init = Symbol.__init__


def _symbol_init_with_param_deser(self, *args, **kwargs):
    _original_symbol_init(self, *args, **kwargs)
    self.parameters = [
        Parameter(**p) if isinstance(p, dict) else p
        for p in self.parameters
    ]


Symbol.__init__ = _symbol_init_with_param_deser  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class SchemaError(Exception):
    """Raised when a FileExtraction fails validation."""


def validate_extraction(extraction: FileExtraction) -> list[str]:
    """Validate a FileExtraction instance.

    Returns a list of error messages. Empty list means valid.
    Raises SchemaError if there are critical structural problems
    (missing required fields). Non-critical issues (e.g., unknown
    visibility value) are returned as warnings.
    """
    errors: list[str] = []

    if not extraction.file_path:
        errors.append("file_path is empty")

    if extraction.language not in VALID_LANGUAGES:
        errors.append(
            f"language '{extraction.language}' not in {sorted(VALID_LANGUAGES)}"
        )

    if not extraction.sha256:
        errors.append("sha256 is empty")

    if extraction.file_size_bytes < 0:
        errors.append(f"file_size_bytes is negative: {extraction.file_size_bytes}")

    if extraction.line_count < 0:
        errors.append(f"line_count is negative: {extraction.line_count}")

    for i, sym in enumerate(extraction.symbols):
        if not sym.name:
            errors.append(f"symbols[{i}].name is empty")
        if not sym.signature:
            errors.append(f"symbols[{i}].signature is empty")
        if sym.kind not in VALID_SYMBOL_KINDS:
            errors.append(
                f"symbols[{i}].kind '{sym.kind}' not in {sorted(VALID_SYMBOL_KINDS)}"
            )
        if sym.visibility not in VALID_VISIBILITIES:
            errors.append(
                f"symbols[{i}].visibility '{sym.visibility}' not in "
                f"{sorted(VALID_VISIBILITIES)}"
            )
        if sym.line_start < 0:
            errors.append(f"symbols[{i}].line_start is negative")
        if sym.line_end < sym.line_start:
            errors.append(
                f"symbols[{i}].line_end ({sym.line_end}) < "
                f"line_start ({sym.line_start})"
            )
        for j, param in enumerate(sym.parameters):
            if not param.name:
                errors.append(f"symbols[{i}].parameters[{j}].name is empty")

    for i, imp in enumerate(extraction.imports):
        if not imp.module:
            errors.append(f"imports[{i}].module is empty")
        if imp.line < 0:
            errors.append(f"imports[{i}].line is negative: {imp.line}")
        if not imp.kind:
            errors.append(f"imports[{i}].kind is empty")
        elif imp.kind not in VALID_IMPORT_KINDS:
            errors.append(
                f"imports[{i}].kind '{imp.kind}' not in {sorted(VALID_IMPORT_KINDS)}"
            )
        if imp.alias is not None and not imp.alias:
            errors.append(f"imports[{i}].alias is empty string (use None instead)")

    for i, exp in enumerate(extraction.exports):
        if not exp.name:
            errors.append(f"exports[{i}].name is empty")
        if not exp.kind:
            errors.append(f"exports[{i}].kind is empty")
        elif exp.kind not in VALID_EXPORT_KINDS:
            errors.append(
                f"exports[{i}].kind '{exp.kind}' not in {sorted(VALID_EXPORT_KINDS)}"
            )
        if exp.line < 0:
            errors.append(f"exports[{i}].line is negative: {exp.line}")

    for i, edge in enumerate(extraction.call_edges):
        if not edge.caller:
            errors.append(f"call_edges[{i}].caller is empty")
        if not edge.callee:
            errors.append(f"call_edges[{i}].callee is empty")
        if not 0.0 <= edge.confidence <= 1.0:
            errors.append(
                f"call_edges[{i}].confidence {edge.confidence} not in [0.0, 1.0]"
            )
        if edge.line < 0:
            errors.append(f"call_edges[{i}].line is negative: {edge.line}")

    for i, rc in enumerate(extraction.rationale_comments):
        if rc.tag not in VALID_COMMENT_TAGS:
            errors.append(
                f"rationale_comments[{i}].tag '{rc.tag}' not in "
                f"{sorted(VALID_COMMENT_TAGS)}"
            )
        if not rc.text:
            errors.append(f"rationale_comments[{i}].text is empty")
        if rc.line < 0:
            errors.append(f"rationale_comments[{i}].line is negative: {rc.line}")

    if errors:
        raise SchemaError(
            f"FileExtraction for '{extraction.file_path}' has "
            f"{len(errors)} error(s):\n" + "\n".join(f"  - {e}" for e in errors)
        )

    return errors
