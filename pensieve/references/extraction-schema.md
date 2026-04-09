# Extraction Schema Reference

> Authoritative source: `pensieve/python/src/pensieve/schema.py`
> This document is a human-readable summary. When in doubt, the code wins.

## What this schema captures

Each language extractor (B4–B9) produces a `FileExtraction` per source
file. It captures the structural landmarks without storing raw code:

| Field | What it is |
|---|---|
| `file_path` | Relative to repo root |
| `language` | python, javascript, typescript, go, java, rust |
| `sha256` | Hash of file content at extraction time (cache key) |
| `file_size_bytes` | For scale decisions |
| `line_count` | For scale decisions |
| `symbols` | Functions, classes, methods, interfaces, traits, structs, enums, type aliases, constants |
| `imports` | Import/use/require statements |
| `exports` | Explicit exports (JS/TS only; other languages use visibility on symbols) |
| `call_edges` | Within-file function calls (cross-file calls computed in B13) |
| `rationale_comments` | Tagged comments: WHY, NOTE, IMPORTANT, HACK, TODO, FIXME |
| `extraction_errors` | Any errors encountered during extraction |
| `extractor_version` | For cache invalidation when extractor logic changes |

## Symbol kinds

| Kind | Languages where it appears |
|---|---|
| `function` | Python, JS, TS, Go, Rust |
| `class` | Python, JS, TS, Java |
| `method` | Python, JS, TS, Go (receiver methods), Java, Rust (impl methods) |
| `interface` | TS, Go, Java |
| `trait` | Rust |
| `struct` | Go, Rust |
| `enum` | Python, TS, Java, Rust |
| `type_alias` | TS, Go, Rust |
| `constant` | JS, TS, Go, Java, Rust |

## Symbol containment

Methods are stored as separate Symbol entries with a `parent` field
pointing at the containing class/struct/impl. This flat-with-parent
representation is easier to iterate and query than nested
class-containing-methods.

Example:
```json
{"name": "Calculator", "kind": "class", "parent": null, ...}
{"name": "add", "kind": "method", "parent": "Calculator", ...}
```

## Confidence scores

Call edges use continuous 0.0–1.0 scores:

| Score | Meaning |
|---|---|
| 1.0 | Direct call found in AST (e.g., `foo()` inside `bar()`) |
| 0.5–0.9 | Inferred via heuristic (e.g., string-based dispatch, dynamic call) |
| < 0.5 | Weak inference, flagged for review |

## Rationale comment tags

| Tag | Typical prefix | What it captures |
|---|---|---|
| `WHY` | `# WHY:` / `// WHY:` | Design rationale |
| `NOTE` | `# NOTE:` / `// NOTE:` | Important context |
| `IMPORTANT` | `# IMPORTANT:` / `// IMPORTANT:` | Critical constraints |
| `HACK` | `# HACK:` / `// HACK:` | Known workarounds |
| `TODO` | `# TODO:` / `// TODO:` | Planned work |
| `FIXME` | `# FIXME:` / `// FIXME:` | Known bugs |

## JSON example (abbreviated)

```json
{
  "file_path": "src/calculator.py",
  "language": "python",
  "sha256": "e3b0c44298fc1c149afbf4c8996fb924",
  "file_size_bytes": 2048,
  "line_count": 85,
  "symbols": [
    {
      "name": "Calculator",
      "kind": "class",
      "line_start": 10,
      "line_end": 80,
      "signature": "class Calculator:",
      "visibility": "public",
      "parent": null,
      "docstring": "A simple calculator.",
      "parameters": [],
      "return_type": null
    },
    {
      "name": "add",
      "kind": "method",
      "line_start": 15,
      "line_end": 20,
      "signature": "def add(self, a: int, b: int) -> int:",
      "visibility": "public",
      "parent": "Calculator",
      "docstring": null,
      "parameters": [
        {"name": "self", "type": null, "default": null},
        {"name": "a", "type": "int", "default": null},
        {"name": "b", "type": "int", "default": null}
      ],
      "return_type": "int"
    }
  ],
  "imports": [
    {"module": "math", "names": ["sqrt", "pi"], "alias": null, "line": 1, "kind": "from_import"}
  ],
  "exports": [],
  "call_edges": [
    {"caller": "add", "callee": "sqrt", "line": 18, "confidence": 1.0}
  ],
  "rationale_comments": [
    {"tag": "WHY", "text": "Using sqrt here for distance calculation", "line": 18, "context": "add"}
  ],
  "extraction_errors": [],
  "extractor_version": "0.0.1"
}
```

## Validation

`pensieve.schema.validate_extraction(ext)` checks:
- Required fields non-empty (`file_path`, `sha256`)
- `language` is one of the 6 supported values
- `kind` is one of the 9 valid symbol kinds
- `visibility` is one of: public, private, protected, package, unknown
- `line_end >= line_start` for every symbol
- `confidence` in [0.0, 1.0] for every call edge
- `tag` is one of the 6 valid comment tags
- Caller/callee non-empty on call edges
- Module non-empty on imports

Raises `SchemaError` with all errors listed if any check fails.
