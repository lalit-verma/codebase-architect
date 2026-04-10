"""Layer 2 LLM orchestration pipeline (B14).

B14a — Directory profiler (deterministic)
B14b — Subsystem proposer (LLM)
B14c — Per-subsystem structural brief + file selection (LLM)
B14d — Deep-dive documentation generation (LLM)
B14e — Synthesis: subsystem docs → patterns.md, agent-context.md,
       agent-context-nano.md (LLM)
"""

from __future__ import annotations

import json
import subprocess
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath


# Directories that are typically auto-generated, not architectural
_AUTO_GENERATED_DIRS = frozenset({
    "migrations", "versions", "vendor", "node_modules", "dist",
    "build", "__pycache__", ".cache", "generated", "gen",
    "static", "assets", "public",
})


@dataclass
class DirectoryProfile:
    """Profile of a single directory for subsystem detection."""

    path: str
    file_count: int = 0
    languages: dict[str, int] = field(default_factory=dict)

    # Symbols
    symbol_count: int = 0
    top_symbols: list[str] = field(default_factory=list)  # most-referenced

    # Edge analysis
    internal_edges: int = 0  # edges between files in this directory
    outgoing_edges: int = 0  # edges from this dir to other dirs
    incoming_edges: int = 0  # edges from other dirs to this dir
    edge_density: float = 0.0  # internal / (internal + outgoing), 0-1

    # Top directories this one imports from / is imported by
    top_outgoing_targets: list[tuple[str, int]] = field(default_factory=list)
    top_incoming_sources: list[tuple[str, int]] = field(default_factory=list)

    # Flags
    is_test: bool = False
    is_auto_generated: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


@dataclass
class RepoProfile:
    """Complete directory profile of a repository."""

    repo_root: str
    total_files: int
    total_edges: int
    directories: list[DirectoryProfile]

    def to_dict(self) -> dict:
        return {
            "repo_root": self.repo_root,
            "total_files": self.total_files,
            "total_edges": self.total_edges,
            "directories": [d.to_dict() for d in self.directories],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def profile_directories(
    structure_path: Path,
    graph_path: Path,
    min_files: int = 2,
    depth: int | None = None,
) -> RepoProfile:
    """Build directory profiles from structure.json + graph.json.

    Args:
        structure_path: Path to structure.json.
        graph_path: Path to graph.json.
        min_files: Minimum files for a directory to be profiled.
        depth: If set, profile directories at this depth from repo root.
            None = auto-detect: use the deepest level where directories
            have meaningful file counts (>= min_files).

    Returns:
        RepoProfile with per-directory profiles.
    """
    structure = json.loads(structure_path.read_text(encoding="utf-8"))
    graph = json.loads(graph_path.read_text(encoding="utf-8"))

    files = structure.get("files", [])
    edges = graph.get("edges", [])

    # --- Map files to directories ---
    file_to_dir: dict[str, str] = {}
    dir_files: dict[str, list[dict]] = defaultdict(list)

    for f in files:
        fp = f["file_path"]
        p = PurePosixPath(fp)
        parts = p.parts

        if depth is not None:
            # Use exact depth
            if len(parts) > depth:
                d = "/".join(parts[:depth])
            else:
                d = str(p.parent) if str(p.parent) != "." else "(root)"
        else:
            # Auto-detect: use the directory containing the file
            d = str(p.parent) if str(p.parent) != "." else "(root)"

        file_to_dir[fp] = d
        dir_files[d].append(f)

    # --- If no depth specified, collapse directories to a meaningful level ---
    if depth is None:
        dir_files, file_to_dir = _collapse_directories(
            dir_files, file_to_dir, files, min_files,
        )

    # --- Compute edge stats per directory ---
    dir_internal: Counter[str] = Counter()
    dir_outgoing: dict[str, Counter[str]] = defaultdict(Counter)
    dir_incoming: dict[str, Counter[str]] = defaultdict(Counter)

    for edge in edges:
        src = edge.get("source", "")
        tgt = edge.get("target", "")
        src_dir = file_to_dir.get(src)
        tgt_dir = file_to_dir.get(tgt)

        if src_dir is None or tgt_dir is None:
            continue

        if src_dir == tgt_dir:
            dir_internal[src_dir] += 1
        else:
            dir_outgoing[src_dir][tgt_dir] += 1
            dir_incoming[tgt_dir][src_dir] += 1

    # --- Compute symbol popularity (how often each symbol is imported) ---
    symbol_refs: dict[str, Counter[str]] = defaultdict(Counter)
    for edge in edges:
        if edge.get("kind") == "calls":
            tgt = edge.get("target", "")
            tgt_dir = file_to_dir.get(tgt)
            detail = edge.get("detail", "")
            # detail format: "callerFunc -> calleeFunc"
            if " -> " in detail:
                callee = detail.split(" -> ")[-1].strip()
                if tgt_dir:
                    symbol_refs[tgt_dir][callee] += 1

    # Also count import-level references
    for edge in edges:
        if edge.get("kind") == "imports":
            tgt = edge.get("target", "")
            tgt_dir = file_to_dir.get(tgt)
            detail = edge.get("detail", "")
            # detail often contains the imported names
            if tgt_dir and detail:
                # Extract names from detail like "module (name1, name2)"
                if "(" in detail:
                    names_part = detail.split("(", 1)[1].rstrip(")")
                    for name in names_part.split(","):
                        name = name.strip()
                        if name:
                            symbol_refs[tgt_dir][name] += 1

    # --- Build profiles ---
    profiles: list[DirectoryProfile] = []

    for d, d_files in sorted(dir_files.items()):
        if len(d_files) < min_files:
            continue

        # Language breakdown
        langs: Counter[str] = Counter()
        total_symbols = 0
        for f in d_files:
            lang = f.get("language", "unknown")
            langs[lang] += 1
            total_symbols += len(f.get("symbols", []))

        internal = dir_internal.get(d, 0)
        outgoing_total = sum(dir_outgoing.get(d, {}).values())
        incoming_total = sum(dir_incoming.get(d, {}).values())

        total_dir_edges = internal + outgoing_total
        density = internal / total_dir_edges if total_dir_edges > 0 else 0.0

        # Top outgoing/incoming
        out_targets = sorted(
            dir_outgoing.get(d, {}).items(),
            key=lambda x: -x[1],
        )[:5]
        in_sources = sorted(
            dir_incoming.get(d, {}).items(),
            key=lambda x: -x[1],
        )[:5]

        # Top symbols
        top_syms = [
            name for name, _ in symbol_refs.get(d, Counter()).most_common(10)
        ]

        # Flags
        dir_name = PurePosixPath(d).name
        is_auto = dir_name.lower() in _AUTO_GENERATED_DIRS
        is_test = dir_name.lower() in {"test", "tests", "spec", "__tests__", "testing"}

        profiles.append(DirectoryProfile(
            path=d,
            file_count=len(d_files),
            languages=dict(langs),
            symbol_count=total_symbols,
            top_symbols=top_syms,
            internal_edges=internal,
            outgoing_edges=outgoing_total,
            incoming_edges=incoming_total,
            edge_density=round(density, 3),
            top_outgoing_targets=out_targets,
            top_incoming_sources=in_sources,
            is_test=is_test,
            is_auto_generated=is_auto,
        ))

    return RepoProfile(
        repo_root=structure.get("repo_root", ""),
        total_files=len(files),
        total_edges=len(edges),
        directories=profiles,
    )


def _collapse_directories(
    dir_files: dict[str, list[dict]],
    file_to_dir: dict[str, str],
    files: list[dict],
    min_files: int,
) -> tuple[dict[str, list[dict]], dict[str, str]]:
    """Collapse directory tree to a meaningful profiling level.

    Strategy: if a directory has only one subdirectory with all the files
    (e.g., backend/ → backend/open_webui/), collapse down. Stop when
    directories have multiple children with >= min_files each.
    """
    # Find directories where all files share a common deeper prefix
    # e.g., backend/ has 245 files but they're all in backend/open_webui/
    collapsed = True
    while collapsed:
        collapsed = False
        new_dir_files: dict[str, list[dict]] = defaultdict(list)
        new_file_to_dir: dict[str, str] = {}

        for d, d_files in dir_files.items():
            if d == "(root)" or len(d_files) < min_files:
                for f in d_files:
                    new_dir_files[d].append(f)
                    new_file_to_dir[f["file_path"]] = d
                continue

            # Check children at one level deeper
            children: dict[str, list[dict]] = defaultdict(list)
            direct_files: list[dict] = []
            for f in d_files:
                p = PurePosixPath(f["file_path"])
                rel = str(p.relative_to(d)) if str(p).startswith(d + "/") else str(p)
                parts = PurePosixPath(rel).parts
                if len(parts) > 1:
                    child_dir = d + "/" + parts[0]
                    children[child_dir].append(f)
                else:
                    direct_files.append(f)

            # If there's exactly one dominant child with almost all files,
            # collapse into that child
            if len(children) == 1 and len(direct_files) <= 2:
                child_d = list(children.keys())[0]
                for f in d_files:
                    new_dir_files[child_d].append(f)
                    new_file_to_dir[f["file_path"]] = child_d
                collapsed = True
            elif len(children) > 1:
                # Multiple children — profile at child level
                for child_d, child_files in children.items():
                    for f in child_files:
                        new_dir_files[child_d].append(f)
                        new_file_to_dir[f["file_path"]] = child_d
                for f in direct_files:
                    new_dir_files[d].append(f)
                    new_file_to_dir[f["file_path"]] = d
                collapsed = True
            else:
                # No children or all direct files — keep as is
                for f in d_files:
                    new_dir_files[d].append(f)
                    new_file_to_dir[f["file_path"]] = d

        dir_files = dict(new_dir_files)
        file_to_dir = new_file_to_dir

    return dir_files, file_to_dir


def format_profiles_for_llm(profile: RepoProfile) -> str:
    """Format directory profiles as a concise text for LLM consumption.

    This is the structural brief the LLM reads before proposing
    subsystem boundaries. Used internally by propose_subsystems().
    """
    lines: list[str] = []
    lines.append(f"# Repository Structure: {profile.total_files} files, {profile.total_edges} edges\n")

    for d in sorted(profile.directories, key=lambda x: -x.file_count):
        flags = []
        if d.is_test:
            flags.append("TEST")
        if d.is_auto_generated:
            flags.append("AUTO-GENERATED")
        flag_str = f" [{', '.join(flags)}]" if flags else ""

        lines.append(f"## {d.path}/{flag_str}")
        lines.append(f"  Files: {d.file_count} ({', '.join(f'{v} {k}' for k, v in sorted(d.languages.items()))})")
        lines.append(f"  Symbols: {d.symbol_count}")
        lines.append(f"  Edge density: {d.edge_density:.0%} internal ({d.internal_edges} internal, {d.outgoing_edges} outgoing, {d.incoming_edges} incoming)")

        if d.top_outgoing_targets:
            targets = ", ".join(f"{t} ({c})" for t, c in d.top_outgoing_targets)
            lines.append(f"  Imports from: {targets}")

        if d.top_incoming_sources:
            sources = ", ".join(f"{s} ({c})" for s, c in d.top_incoming_sources)
            lines.append(f"  Imported by: {sources}")

        if d.top_symbols:
            lines.append(f"  Key symbols: {', '.join(d.top_symbols[:8])}")

        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM-optimized structural profiles (XML-tagged, layered)
# ---------------------------------------------------------------------------


def format_structural_profiles(
    structure_path: Path,
    graph_path: Path,
    max_signatures_per_dir: int = 5,
) -> str:
    """Format structural data as an LLM-optimized XML-tagged profile.

    Four layers designed for how LLMs process architectural information:

    1. <architecture> — hierarchical tree with one-line descriptions and
       dependant counts. Gives the LLM the spatial layout.
    2. <signatures> — key file signatures per directory (top files by
       centrality). Gives the LLM what each file exports without reading it.
    3. <dependencies> — edge lists grouped by coupling strength
       (HIGH/MODERATE/LOW). LLMs reason better about edge lists than
       adjacency matrices or percentages (ICLR 2025).
    4. <entry_points> — application entry files (main, app, server, cli).
       Tells the LLM where the application begins.
    5. <external_dependencies> — top third-party packages by import count.
       Tells the LLM the framework and conventions to expect.
    6. <rationale_comments> — developer-annotated WHY/NOTE/HACK/IMPORTANT
       comments. Design intent that pure structure can't capture.
    7. <flags> — auto-generated, test directories to ignore.

    Design grounded in:
    - Aider repo map: tree-sitter signatures + PageRank (aider.chat)
    - RIG paper: descriptive field names > terse encoding (+12.2% accuracy)
    - ICLR 2025: edge lists > adjacency matrices for LLM graph reasoning
    - Anthropic: XML tags for Claude section parsing
    - Code Maps: signatures capture ~90% of architecture at ~5% token cost
    """
    try:
        structure = json.loads(structure_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return f"<repository error=\"Failed to read structure.json: {e}\">\n</repository>"
    files = structure.get("files", [])
    if not files:
        return '<repository files="0" edges="0" languages="">\n<architecture>\n  (no files found)\n</architecture>\n</repository>'

    graph_data: dict = {}
    if graph_path.exists():
        try:
            graph_data = json.loads(graph_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass  # proceed without graph data
    edges = graph_data.get("edges", [])

    # Compute directory profiles for the tree
    try:
        profile = profile_directories(structure_path, graph_path)
    except Exception:
        # Fallback: minimal profile with no directory data
        profile = RepoProfile(
            repo_root=structure.get("repo_root", ""),
            total_files=len(files),
            total_edges=len(edges),
            directories=[],
        )

    # Build file-level data indices
    file_by_path: dict[str, dict] = {f["file_path"]: f for f in files}
    incoming_count: dict[str, int] = {}
    for edge in edges:
        tgt = edge.get("target", "")
        incoming_count[tgt] = incoming_count.get(tgt, 0) + 1

    # Detect languages
    langs = set()
    for f in files:
        langs.add(f.get("language", "unknown"))

    lines: list[str] = []

    # --- Layer 1: Architecture tree ---
    lines.append(f'<repository files="{len(files)}" edges="{len(edges)}" languages="{", ".join(sorted(langs))}">')
    lines.append("")
    lines.append("<architecture>")

    # Group directories into a hierarchy for cleaner presentation
    source_dirs = [
        d for d in profile.directories
        if not d.is_test and not d.is_auto_generated and d.file_count >= 2
    ]
    # Sort by incoming edges (most depended-on first)
    source_dirs.sort(key=lambda d: -d.incoming_edges)

    for d in source_dirs:
        dep_str = f" — {d.incoming_edges} dependents" if d.incoming_edges > 0 else ""
        sym_hint = ""
        if d.top_symbols:
            sym_hint = f" ({', '.join(d.top_symbols[:4])})"
        lang_str = "/".join(sorted(d.languages.keys()))
        lines.append(f"  {d.path}/  [{d.file_count} {lang_str} files]{dep_str}{sym_hint}")

    # Show flagged dirs separately
    test_dirs = [d for d in profile.directories if d.is_test and d.file_count >= 2]
    auto_dirs = [d for d in profile.directories if d.is_auto_generated and d.file_count >= 2]
    if test_dirs or auto_dirs:
        lines.append("")
        for d in auto_dirs:
            lines.append(f"  {d.path}/  [AUTO-GENERATED, {d.file_count} files]")
        for d in test_dirs:
            lines.append(f"  {d.path}/  [TEST, {d.file_count} files]")

    lines.append("</architecture>")
    lines.append("")

    # --- Layer 2: Signatures (top files per directory) ---
    lines.append("<signatures>")

    for d in source_dirs:
        # Get files in this directory, sorted by incoming edges (most central first)
        dir_files = [
            f for f in files
            if str(PurePosixPath(f["file_path"]).parent) == d.path
            and f.get("symbols")
        ]
        dir_files.sort(key=lambda f: -incoming_count.get(f["file_path"], 0))

        shown = 0
        for f in dir_files[:max_signatures_per_dir]:
            symbols = f.get("symbols", [])
            # Show only public top-level symbols (not methods inside classes)
            top_level = [
                s for s in symbols
                if s.get("visibility") == "public" and not s.get("parent")
            ]
            if not top_level:
                continue

            dep_note = ""
            ic = incoming_count.get(f["file_path"], 0)
            if ic > 0:
                dep_note = f"  ({ic} dependents)"

            lines.append(f"  {f['file_path']}:{dep_note}")
            for s in top_level[:8]:  # cap at 8 symbols per file
                sig = s.get("signature", s["name"])
                # Truncate long signatures
                if len(sig) > 100:
                    sig = sig[:97] + "..."
                kind = s.get("kind", "")
                if kind in ("class", "interface", "trait", "struct", "enum"):
                    lines.append(f"    {sig}")
                else:
                    lines.append(f"    {sig}")
            shown += 1

        if shown > 0:
            lines.append("")

    lines.append("</signatures>")
    lines.append("")

    # --- Layer 3: Dependencies (edge lists by coupling strength) ---
    lines.append("<dependencies>")

    # Aggregate edges by directory pair
    dir_edges: dict[tuple[str, str], list[dict]] = {}
    file_to_dir: dict[str, str] = {}
    for f in files:
        parent = str(PurePosixPath(f["file_path"]).parent)
        file_to_dir[f["file_path"]] = parent

    for edge in edges:
        src_dir = file_to_dir.get(edge.get("source", ""))
        tgt_dir = file_to_dir.get(edge.get("target", ""))
        if src_dir and tgt_dir and src_dir != tgt_dir:
            key = (src_dir, tgt_dir)
            if key not in dir_edges:
                dir_edges[key] = []
            dir_edges[key].append(edge)

    # Sort by edge count, group by strength
    sorted_pairs = sorted(dir_edges.items(), key=lambda x: -len(x[1]))

    high = [(k, v) for k, v in sorted_pairs if len(v) >= 50]
    moderate = [(k, v) for k, v in sorted_pairs if 10 <= len(v) < 50]
    low = [(k, v) for k, v in sorted_pairs if 5 <= len(v) < 10]

    if high:
        lines.append("  HIGH COUPLING (50+ edges):")
        for (src, tgt), edge_list in high:
            # Extract key imported names
            names = set()
            for e in edge_list[:10]:
                detail = e.get("detail", "")
                if "(" in detail:
                    name_part = detail.split("(", 1)[1].rstrip(")")
                    for n in name_part.split(",")[:3]:
                        n = n.strip()
                        if n:
                            names.add(n)
            name_hint = f" — key: {', '.join(sorted(names)[:5])}" if names else ""
            lines.append(f"    {src}/ -> {tgt}/ ({len(edge_list)} edges){name_hint}")
        lines.append("")

    if moderate:
        lines.append("  MODERATE COUPLING (10-49 edges):")
        for (src, tgt), edge_list in moderate:
            lines.append(f"    {src}/ -> {tgt}/ ({len(edge_list)} edges)")
        lines.append("")

    if low:
        lines.append("  NOTABLE COUPLING (5-9 edges):")
        for (src, tgt), edge_list in low:
            lines.append(f"    {src}/ -> {tgt}/ ({len(edge_list)} edges)")
        lines.append("")

    # Detect potential circular dependencies
    all_pairs = set(dir_edges.keys())
    circular = []
    seen = set()
    for (a, b) in all_pairs:
        if (b, a) in all_pairs and (b, a) not in seen:
            circular.append((a, b, len(dir_edges[(a, b)]), len(dir_edges[(b, a)])))
            seen.add((a, b))

    if circular:
        lines.append("  CIRCULAR DEPENDENCIES:")
        for a, b, ab_count, ba_count in sorted(circular, key=lambda x: -(x[2] + x[3])):
            lines.append(f"    {a}/ <-> {b}/ ({ab_count} + {ba_count} edges)")
        lines.append("")

    lines.append("</dependencies>")
    lines.append("")

    # --- Layer 4: Entry points ---
    # Entry points: main/app/server/cli files (not index.ts barrel exports)
    _ENTRY_STEMS = {"main", "app", "__main__", "server", "cli", "wsgi", "asgi"}
    entry_files = []
    for f in files:
        p = PurePosixPath(f["file_path"])
        if p.stem in _ENTRY_STEMS and f.get("symbols"):
            sym_names = [s["name"] for s in f.get("symbols", [])[:5]]
            hint = ", ".join(sym_names[:3]) if sym_names else ""
            ic = incoming_count.get(f["file_path"], 0)
            entry_files.append((f["file_path"], hint, ic))

    if entry_files:
        entry_files.sort(key=lambda x: -x[2])
        lines.append("<entry_points>")
        for fp, hint, ic in entry_files[:10]:  # cap at 10
            hint_str = f" — {hint}" if hint else ""
            dep_str = f" ({ic} dependents)" if ic > 0 else ""
            lines.append(f"  {fp}{hint_str}{dep_str}")
        lines.append("</entry_points>")
        lines.append("")

    # --- Layer 5: External dependencies ---
    ext_imports = graph_data.get("external_imports", [])
    if ext_imports:
        from collections import Counter as _Counter
        pkg_counts: _Counter[str] = _Counter()
        for ei in ext_imports:
            module = ei.get("module", "")
            # Use top-level package name
            pkg = module.split(".")[0] if module else ""
            if pkg:
                pkg_counts[pkg] += 1

        # Filter stdlib — keep only likely third-party
        _STDLIB = {
            "os", "sys", "json", "typing", "pathlib", "datetime",
            "collections", "dataclasses", "abc", "enum", "re",
            "logging", "hashlib", "functools", "itertools", "io",
            "time", "math", "random", "copy", "uuid", "base64",
            "urllib", "http", "email", "html", "xml", "csv",
            "contextlib", "inspect", "importlib", "pkgutil",
            "threading", "multiprocessing", "asyncio", "concurrent",
            "subprocess", "shutil", "tempfile", "glob", "fnmatch",
            "struct", "codecs", "string", "textwrap", "unicodedata",
            "socket", "ssl", "select", "signal", "warnings",
            "traceback", "types", "operator", "secrets",
            "__future__", "builtins",
        }
        third_party = [
            (pkg, count) for pkg, count in pkg_counts.most_common(15)
            if pkg not in _STDLIB
        ]

        if third_party:
            lines.append("<external_dependencies>")
            for pkg, count in third_party[:10]:
                lines.append(f"  {pkg} ({count} imports)")
            lines.append("</external_dependencies>")
            lines.append("")

    # --- Layer 6: Rationale comments ---
    rationale = []
    for f in files:
        for c in f.get("comments", []):
            tag = c.get("tag", "")
            text = c.get("text", "")
            line = c.get("line", 0)
            if tag in ("WHY", "HACK", "IMPORTANT", "NOTE") and text:
                rationale.append((f["file_path"], line, tag, text[:120]))

    if rationale:
        # Show top 15, prioritize WHY and HACK over NOTE
        priority = {"WHY": 0, "HACK": 1, "IMPORTANT": 2, "NOTE": 3}
        rationale.sort(key=lambda x: (priority.get(x[2], 9), -x[1]))
        lines.append("<rationale_comments>")
        for fp, line_num, tag, text in rationale[:15]:
            lines.append(f"  {fp}:{line_num} — {tag}: {text}")
        lines.append("</rationale_comments>")
        lines.append("")

    # --- Layer 7: Flags ---
    if auto_dirs or test_dirs:
        lines.append("<flags>")
        if auto_dirs:
            auto_names = ", ".join(d.path for d in auto_dirs)
            lines.append(f"  AUTO-GENERATED: {auto_names}")
        if test_dirs:
            test_names = ", ".join(d.path for d in test_dirs)
            lines.append(f"  TEST: {test_names}")
        lines.append("</flags>")
        lines.append("")

    lines.append("</repository>")
    return "\n".join(lines)


def validate_structural_profile(content: str) -> list[str]:
    """Validate a structural profile for well-formedness.

    Returns list of errors. Empty list = valid.
    """
    errors: list[str] = []

    if "<repository" not in content:
        errors.append("Missing <repository> opening tag")
    if "</repository>" not in content:
        errors.append("Missing </repository> closing tag")

    # Required sections (always present)
    for tag in ("architecture", "signatures", "dependencies"):
        if f"<{tag}>" not in content:
            errors.append(f"Missing <{tag}> section")
        if f"</{tag}>" not in content:
            errors.append(f"Missing </{tag}> closing tag")

    # Check for error attribute (format function reports errors this way)
    if 'error="' in content:
        errors.append("Profile contains an error attribute — generation failed")

    return errors


def validate_subsystem_brief(content: str) -> list[str]:
    """Validate a subsystem brief for well-formedness.

    Returns list of errors. Empty list = valid.
    """
    errors: list[str] = []

    if "<subsystem_brief" not in content:
        errors.append("Missing <subsystem_brief> opening tag")
    if "</subsystem_brief>" not in content:
        errors.append("Missing </subsystem_brief> closing tag")

    # Signatures section is always present
    if "<signatures>" not in content:
        errors.append("Missing <signatures> section")

    if 'error="' in content:
        errors.append("Brief contains an error attribute — generation failed")

    return errors


def format_subsystem_brief(
    subsystem_dirs: list[str],
    structure_path: Path,
    graph_path: Path,
) -> str:
    """Format a detailed brief for one subsystem's directories.

    Like format_structural_profiles but zoomed into specific directories
    with FULL file-level signatures (not just top-N). Used by deep-dive
    prompts to understand a subsystem without reading every file.

    Args:
        subsystem_dirs: List of directory paths belonging to the subsystem.
        structure_path: Path to structure.json.
        graph_path: Path to graph.json.
    """
    try:
        structure = json.loads(structure_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        dir_list = ", ".join(subsystem_dirs)
        return f'<subsystem_brief dirs="{dir_list}" error="Failed to read structure.json: {e}">\n</subsystem_brief>'
    files = structure.get("files", [])

    graph_data: dict = {}
    if graph_path.exists():
        try:
            graph_data = json.loads(graph_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass  # proceed without graph data
    edges = graph_data.get("edges", [])

    # Normalize dirs
    dirs = {d.rstrip("/") for d in subsystem_dirs}

    # Filter files in this subsystem
    subsystem_files = []
    for f in files:
        parent = str(PurePosixPath(f["file_path"]).parent)
        if parent in dirs or any(parent.startswith(d + "/") for d in dirs):
            subsystem_files.append(f)

    if not subsystem_files:
        return f"<subsystem_brief dirs=\"{', '.join(dirs)}\">\n  No files found.\n</subsystem_brief>\n"

    # Compute per-file incoming edge count
    incoming_count: dict[str, int] = {}
    for edge in edges:
        tgt = edge.get("target", "")
        incoming_count[tgt] = incoming_count.get(tgt, 0) + 1

    # File-to-dir mapping for dependency analysis
    file_to_dir: dict[str, str] = {}
    for f in files:
        file_to_dir[f["file_path"]] = str(PurePosixPath(f["file_path"]).parent)

    lines: list[str] = []
    dir_list = ", ".join(sorted(dirs))
    lines.append(f'<subsystem_brief dirs="{dir_list}" files="{len(subsystem_files)}">')
    lines.append("")

    # --- Signatures: ALL files, ALL public symbols ---
    lines.append("<signatures>")

    # Sort files by incoming edges (most central first)
    subsystem_files.sort(key=lambda f: -incoming_count.get(f["file_path"], 0))

    for f in subsystem_files:
        symbols = f.get("symbols", [])
        if not symbols:
            lines.append(f"  {f['file_path']}: (no symbols)")
            continue

        ic = incoming_count.get(f["file_path"], 0)
        dep_note = f"  ({ic} dependents)" if ic > 0 else ""
        lines.append(f"  {f['file_path']}:{dep_note}")

        for s in symbols:
            sig = s.get("signature", s["name"])
            if len(sig) > 120:
                sig = sig[:117] + "..."
            parent = s.get("parent")
            indent = "      " if parent else "    "
            lines.append(f"{indent}{sig}")

        # Show rationale comments if any
        comments = f.get("comments", [])
        if comments:
            for c in comments[:3]:
                tag = c.get("tag", "")
                text = c.get("text", "")[:100]
                lines.append(f"    # {tag}: {text}")

        lines.append("")

    lines.append("</signatures>")
    lines.append("")

    # --- Internal dependencies ---
    lines.append("<internal_dependencies>")

    # Edges within the subsystem
    internal_edges = []
    external_in = []  # edges from outside into this subsystem
    external_out = []  # edges from this subsystem to outside

    subsystem_file_set = {f["file_path"] for f in subsystem_files}

    for edge in edges:
        src = edge.get("source", "")
        tgt = edge.get("target", "")
        src_in = src in subsystem_file_set
        tgt_in = tgt in subsystem_file_set

        if src_in and tgt_in:
            internal_edges.append(edge)
        elif src_in and not tgt_in:
            external_out.append(edge)
        elif not src_in and tgt_in:
            external_in.append(edge)

    if internal_edges:
        # Group by source -> target file
        from collections import defaultdict
        grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
        for e in internal_edges:
            key = (e["source"], e["target"])
            detail = e.get("detail", "")
            if detail:
                grouped[key].append(detail[:80])

        lines.append("  Within subsystem:")
        for (src, tgt), details in sorted(grouped.items()):
            detail_str = f" — {details[0]}" if details else ""
            lines.append(f"    {src} -> {tgt}{detail_str}")
        lines.append("")

    if external_out:
        # Group by target directory
        out_by_dir: dict[str, int] = {}
        for e in external_out:
            tgt_dir = file_to_dir.get(e["target"], "?")
            out_by_dir[tgt_dir] = out_by_dir.get(tgt_dir, 0) + 1

        lines.append("  Depends on (external):")
        for d, count in sorted(out_by_dir.items(), key=lambda x: -x[1]):
            lines.append(f"    -> {d}/ ({count} edges)")
        lines.append("")

    if external_in:
        in_by_dir: dict[str, int] = {}
        for e in external_in:
            src_dir = file_to_dir.get(e["source"], "?")
            in_by_dir[src_dir] = in_by_dir.get(src_dir, 0) + 1

        lines.append("  Depended on by (external):")
        for d, count in sorted(in_by_dir.items(), key=lambda x: -x[1]):
            lines.append(f"    <- {d}/ ({count} edges)")
        lines.append("")

    lines.append("</internal_dependencies>")
    lines.append("")

    # --- Test mapping ---
    test_edges = [e for e in edges if e.get("kind") == "tests"]
    subsystem_tests = [e for e in test_edges if e.get("target") in subsystem_file_set]
    if subsystem_tests:
        lines.append("<test_mapping>")
        for e in subsystem_tests:
            lines.append(f"  {e['source']} tests {e['target']}")
        lines.append("</test_mapping>")
        lines.append("")

    # --- Entry points within subsystem ---
    _ENTRY_STEMS = {"main", "app", "__main__", "index", "server", "cli", "wsgi", "asgi"}
    entry_files = [
        f for f in subsystem_files
        if PurePosixPath(f["file_path"]).stem in _ENTRY_STEMS
    ]
    if entry_files:
        lines.append("<entry_points>")
        for f in entry_files:
            syms = [s["name"] for s in f.get("symbols", [])[:3]]
            hint = f" — {', '.join(syms)}" if syms else ""
            lines.append(f"  {f['file_path']}{hint}")
        lines.append("</entry_points>")
        lines.append("")

    # --- Consolidated rationale comments (WHY/HACK/IMPORTANT) ---
    all_rationale = []
    for f in subsystem_files:
        for c in f.get("comments", []):
            tag = c.get("tag", "")
            text = c.get("text", "")
            line_num = c.get("line", 0)
            if tag in ("WHY", "HACK", "IMPORTANT") and text:
                all_rationale.append((f["file_path"], line_num, tag, text[:120]))

    if all_rationale:
        priority = {"WHY": 0, "HACK": 1, "IMPORTANT": 2}
        all_rationale.sort(key=lambda x: priority.get(x[2], 9))
        lines.append("<rationale_comments>")
        for fp, ln, tag, text in all_rationale[:20]:
            lines.append(f"  {fp}:{ln} — {tag}: {text}")
        lines.append("</rationale_comments>")
        lines.append("")

    lines.append("</subsystem_brief>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# B14b: LLM subsystem proposal
# ---------------------------------------------------------------------------


_SUBSYSTEM_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "subsystems": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Human-readable subsystem name (e.g., 'API Routers', 'Data Models', 'Auth & Access Control').",
                    },
                    "directories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of directory paths that belong to this subsystem.",
                    },
                    "role": {
                        "type": "string",
                        "description": "One-line description of what this subsystem does in the architecture.",
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Why these directories are grouped together (shared responsibility, tight coupling, etc.).",
                    },
                },
                "required": ["name", "directories", "role", "rationale"],
            },
        },
        "excluded": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["directory", "reason"],
            },
            "description": "Directories intentionally excluded from subsystems (auto-generated, config-only, etc.).",
        },
    },
    "required": ["subsystems", "excluded"],
})

_PROPOSER_SYSTEM_PROMPT = """\
You are a software architect analyzing a codebase to identify its subsystems.

A subsystem is a cohesive group of files that:
- Share a single responsibility (API layer, data models, auth, retrieval, etc.)
- Have high internal coupling (many edges between files in the group)
- Have a clear boundary with other parts of the codebase

Your job:
1. Read the structural brief (directory profiles with edge data).
2. Propose subsystem boundaries by grouping directories.
3. Merge directories that are tightly coupled and share responsibility.
4. Keep directories separate when they have distinct roles even if co-located.
5. Exclude auto-generated directories, test directories, and config-only directories.
6. Name each subsystem with a clear, human-readable name that describes its architectural role.

Be specific. "Backend" is not a subsystem name. "API Routers" or "Data Access Layer" is.
Do not create subsystems with only one small directory unless it has a distinct, important role.
Shared utilities imported by many subsystems should be their own subsystem, not lumped into a consumer.\
"""


@dataclass
class SubsystemProposal:
    """A proposed subsystem boundary from the LLM."""

    name: str
    directories: list[str]
    role: str
    rationale: str


@dataclass
class SubsystemMap:
    """Complete subsystem proposal for a repository."""

    subsystems: list[SubsystemProposal]
    excluded: list[dict]  # [{"directory": str, "reason": str}]
    raw_reasoning: str = ""  # LLM's full reasoning if available
    error: str | None = None


def propose_subsystems(
    profile: RepoProfile,
    model: str = "sonnet",
    timeout_seconds: int = 300,
) -> SubsystemMap:
    """Ask the LLM to propose subsystem boundaries from directory profiles.

    Args:
        profile: The RepoProfile from profile_directories().
        model: Model to use for the proposal.
        timeout_seconds: Subprocess timeout.

    Returns:
        SubsystemMap with proposed boundaries, or error on failure.
    """
    structural_brief = format_profiles_for_llm(profile)

    user_prompt = (
        f"Analyze this repository's structure and propose subsystem boundaries.\n\n"
        f"{structural_brief}\n\n"
        f"Group directories into subsystems based on architectural role and coupling. "
        f"Explain your reasoning for each grouping."
    )

    cmd = [
        "claude",
        "-p",
        "--output-format", "json",
        "--model", model,
        "--no-session-persistence",
        "--system-prompt", _PROPOSER_SYSTEM_PROMPT,
        "--json-schema", _SUBSYSTEM_SCHEMA,
        user_prompt,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return SubsystemMap(
            subsystems=[], excluded=[],
            error=f"LLM timed out after {timeout_seconds}s",
        )
    except FileNotFoundError:
        return SubsystemMap(
            subsystems=[], excluded=[],
            error="Claude Code CLI not found",
        )

    output = result.stdout.strip()
    if not output:
        return SubsystemMap(
            subsystems=[], excluded=[],
            error=f"Empty stdout. stderr: {result.stderr[:200]}",
        )

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return SubsystemMap(
            subsystems=[], excluded=[],
            error=f"Failed to parse JSON: {output[:200]}",
        )

    if result.returncode != 0:
        return SubsystemMap(
            subsystems=[], excluded=[],
            error=f"LLM exited with code {result.returncode}. stderr: {result.stderr[:200]}",
        )

    if data.get("is_error"):
        return SubsystemMap(
            subsystems=[], excluded=[],
            error=f"LLM error: {data.get('result', 'unknown')}",
        )

    # Extract structured output
    structured = data.get("structured_output") or {}
    if isinstance(structured, str):
        try:
            structured = json.loads(structured)
        except (json.JSONDecodeError, TypeError):
            return SubsystemMap(
                subsystems=[], excluded=[],
                error=f"Unstructured response: {structured[:200]}",
            )

    if not isinstance(structured, dict):
        return SubsystemMap(
            subsystems=[], excluded=[],
            error=f"Response is not a dict: {type(structured).__name__}",
        )

    # Parse subsystems
    subsystems: list[SubsystemProposal] = []
    for entry in structured.get("subsystems", []):
        try:
            subsystems.append(SubsystemProposal(
                name=str(entry.get("name", "Unnamed")),
                directories=[str(d) for d in entry.get("directories", [])],
                role=str(entry.get("role", "")),
                rationale=str(entry.get("rationale", "")),
            ))
        except (TypeError, ValueError, AttributeError):
            continue  # skip malformed entries

    excluded = []
    for entry in structured.get("excluded", []):
        try:
            excluded.append({
                "directory": str(entry.get("directory", "")),
                "reason": str(entry.get("reason", "")),
            })
        except (TypeError, ValueError, AttributeError):
            continue

    return SubsystemMap(
        subsystems=subsystems,
        excluded=excluded,
        raw_reasoning=data.get("result", ""),
    )


def format_subsystem_map(smap: SubsystemMap) -> str:
    """Format a SubsystemMap as readable text for human confirmation."""
    if smap.error:
        return f"Error proposing subsystems: {smap.error}"

    lines: list[str] = []
    lines.append(f"# Proposed Subsystem Map ({len(smap.subsystems)} subsystems)\n")

    for i, s in enumerate(smap.subsystems, 1):
        lines.append(f"## {i}. {s.name}")
        lines.append(f"  Role: {s.role}")
        lines.append(f"  Directories: {', '.join(s.directories)}")
        lines.append(f"  Rationale: {s.rationale}")
        lines.append("")

    if smap.excluded:
        lines.append("## Excluded directories")
        for e in smap.excluded:
            lines.append(f"  - {e['directory']}: {e['reason']}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# B14c: Per-subsystem structural brief + LLM file selection
# ---------------------------------------------------------------------------


def build_subsystem_brief(
    subsystem: SubsystemProposal,
    structure_path: Path,
) -> str:
    """Build a structural brief for one subsystem from structure.json.

    Includes: file list with signatures, imports, call edges, and
    rationale comments for all files in the subsystem's directories.
    This is what the LLM reads before deciding which files to read in full.
    """
    structure = json.loads(structure_path.read_text(encoding="utf-8"))
    files = structure.get("files", [])

    # Normalize directory paths for matching
    dirs = set()
    for d in subsystem.directories:
        d = d.rstrip("/")
        dirs.add(d)

    # Filter files belonging to this subsystem
    subsystem_files = []
    for f in files:
        fp = f["file_path"]
        parent = str(PurePosixPath(fp).parent)
        if parent in dirs or any(parent.startswith(d + "/") for d in dirs):
            subsystem_files.append(f)

    if not subsystem_files:
        return f"# {subsystem.name}\n\nNo files found in directories: {subsystem.directories}\n"

    lines: list[str] = []
    lines.append(f"# {subsystem.name}")
    lines.append(f"Role: {subsystem.role}")
    lines.append(f"Files: {len(subsystem_files)}")
    lines.append("")

    # stdlib modules — not useful for file selection context
    _STDLIB = {
        "os", "sys", "json", "typing", "pathlib", "datetime",
        "collections", "dataclasses", "abc", "enum", "re",
        "logging", "hashlib", "functools", "itertools",
    }

    for f in sorted(subsystem_files, key=lambda x: x["file_path"]):
        fp = f["file_path"]
        lang = f.get("language", "unknown")
        symbols = f.get("symbols", [])
        imports = f.get("imports", [])
        call_edges = f.get("call_edges", [])
        comments = f.get("comments", [])

        lines.append(f"## {fp} ({lang})")

        if symbols:
            for sym in symbols:
                kind = sym.get("kind", "?")
                name = sym.get("name", "?")
                sig = sym.get("signature", "")
                vis = sym.get("visibility", "")
                parent = sym.get("parent")
                parent_str = f" (in {parent})" if parent else ""
                if sig:
                    lines.append(f"  {vis} {kind} {name}{parent_str}: {sig[:120]}")
                else:
                    lines.append(f"  {vis} {kind} {name}{parent_str}")

        internal_imports = [
            imp for imp in imports
            if imp.get("module", "").startswith(".")
            or imp.get("module", "").split(".")[0] not in _STDLIB
        ]
        if internal_imports:
            imp_strs = []
            for imp in internal_imports[:10]:
                mod = imp.get("module", "")
                names = imp.get("names", [])
                if names:
                    imp_strs.append(f"{mod} ({', '.join(names[:5])})")
                else:
                    imp_strs.append(mod)
            lines.append(f"  imports: {'; '.join(imp_strs)}")

        if call_edges:
            lines.append(f"  call edges: {len(call_edges)}")

        if comments:
            for c in comments[:3]:
                tag = c.get("tag", "")
                text = c.get("text", "")[:100]
                lines.append(f"  {tag}: {text}")

        lines.append("")

    return "\n".join(lines)


_FILE_SELECTION_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read in full.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why this file needs full reading for the deep-dive.",
                    },
                },
                "required": ["file_path", "reason"],
            },
        },
    },
    "required": ["files"],
})

_FILE_SELECTION_SYSTEM_PROMPT = """\
You are a software architect preparing to write detailed documentation for a subsystem.

You have the structural skeleton of every file in the subsystem — signatures, imports, \
exports, call edges, and rationale comments. This gives you the shape of the code without \
the implementation details.

Your job: decide which files you need to read IN FULL to produce excellent documentation \
about this subsystem's architecture, design patterns, design decisions, and modification guide.

Pick files that will reveal:
- How the subsystem is orchestrated (entry points, main flows)
- Design patterns and why they were chosen
- Contracts and invariants that must be preserved
- The most instructive example of the dominant code pattern
- Edge cases, gotchas, or non-obvious behavior

Do NOT pick files just because they are large or have many symbols. Pick files that are \
architecturally revealing. A small config file or a factory function can be more important \
than a 500-line utility.

There is no budget constraint. Pick as many files as you need to produce excellent \
documentation. But every file you pick should have a clear reason.\
"""


@dataclass
class FileSelection:
    """Files selected by the LLM for full reading."""

    files: list[dict]  # [{"file_path": str, "reason": str}]
    error: str | None = None


def select_files_for_subsystem(
    subsystem: SubsystemProposal,
    structure_path: Path,
    model: str = "sonnet",
    timeout_seconds: int = 300,
) -> FileSelection:
    """Ask the LLM which files to read in full for a subsystem deep-dive.

    Args:
        subsystem: The confirmed subsystem proposal.
        structure_path: Path to structure.json.
        model: Model for file selection.
        timeout_seconds: Subprocess timeout.

    Returns:
        FileSelection with file paths and reasons, or error.
    """
    brief = build_subsystem_brief(subsystem, structure_path)

    user_prompt = (
        f"Here is the structural skeleton of the '{subsystem.name}' subsystem.\n\n"
        f"{brief}\n\n"
        f"Which files do you need to read in full to write excellent "
        f"architectural documentation for this subsystem? Explain why for each."
    )

    cmd = [
        "claude",
        "-p",
        "--output-format", "json",
        "--model", model,
        "--no-session-persistence",
        "--system-prompt", _FILE_SELECTION_SYSTEM_PROMPT,
        "--json-schema", _FILE_SELECTION_SCHEMA,
        user_prompt,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return FileSelection(
            files=[],
            error=f"File selection timed out after {timeout_seconds}s",
        )
    except FileNotFoundError:
        return FileSelection(
            files=[],
            error="Claude Code CLI not found",
        )

    output = result.stdout.strip()
    if not output:
        return FileSelection(
            files=[],
            error=f"Empty stdout. stderr: {result.stderr[:200]}",
        )

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return FileSelection(
            files=[],
            error=f"Failed to parse JSON: {output[:200]}",
        )

    if result.returncode != 0:
        return FileSelection(
            files=[],
            error=f"LLM exited with code {result.returncode}. stderr: {result.stderr[:200]}",
        )

    if data.get("is_error"):
        return FileSelection(
            files=[],
            error=f"LLM error: {data.get('result', 'unknown')}",
        )

    structured = data.get("structured_output") or {}
    if isinstance(structured, str):
        try:
            structured = json.loads(structured)
        except (json.JSONDecodeError, TypeError):
            return FileSelection(
                files=[],
                error=f"Unstructured response: {structured[:200]}",
            )

    if not isinstance(structured, dict):
        return FileSelection(
            files=[],
            error=f"Response is not a dict: {type(structured).__name__}",
        )

    selected: list[dict] = []
    for entry in structured.get("files", []):
        try:
            selected.append({
                "file_path": str(entry.get("file_path", "")),
                "reason": str(entry.get("reason", "")),
            })
        except (TypeError, ValueError, AttributeError):
            continue

    return FileSelection(files=selected)


# ---------------------------------------------------------------------------
# B14d: Deep-dive documentation generation
# ---------------------------------------------------------------------------


_DEEPDIVE_SYSTEM_PROMPT = """\
You are a software architect writing internal documentation for a subsystem. \
Your audience is coding agents and developers who need to work in this code.

You have two inputs:
1. A structural skeleton of every file in the subsystem (signatures, imports, \
call edges, rationale comments) — this covers ALL files.
2. The full source code of selected key files — these reveal implementation \
details, patterns, and design decisions that the skeleton alone cannot show.

Write a subsystem document following this exact structure. Every section is \
required. Cite specific file paths and line numbers. Do not write generic \
architecture prose — every claim must be grounded in what you can see.

## Required sections:

### Why This Subsystem Exists
1 paragraph: responsibility, role, why it is separate from adjacent code.

### Boundaries
Path/scope, role tag, inputs, outputs, state owned.

### Internal Structure
For each key file/package: what it does and why it matters.

### Key Contracts and Types
Exported types/classes/functions with file:line, purpose, who uses them.

### Main Flows
Trace each entry point through the subsystem. Show handoffs, error handling.

### Dependencies
Internal (other subsystems) and external (third-party packages). Flag which \
are load-bearing.

### Design Decisions and Trade-offs
2-4 decisions you can identify from the code. What was chosen, what it \
enables, what it costs, credible alternative.

### Modification Guide
THIS IS THE MOST IMPORTANT SECTION FOR CODING AGENTS.
- Invariants to preserve
- Step-by-step pattern for adding new code (cite the cleanest example file)
- Files commonly touched together
- Gotchas: what an agent would likely get wrong on the first attempt

### Detected Patterns
Recurring file structures within this subsystem. Name, example file, count.

### Open Questions
Anything uncertain or that needs human clarification. Label as UNCERTAIN \
or NEEDS CLARIFICATION.\
"""


@dataclass
class SubsystemDoc:
    """Generated subsystem documentation."""

    subsystem_name: str
    markdown: str
    files_read: list[str]
    error: str | None = None


def generate_subsystem_doc(
    subsystem: SubsystemProposal,
    structure_path: Path,
    file_selection: FileSelection,
    repo_root: Path,
    model: str = "sonnet",
    timeout_seconds: int = 300,
) -> SubsystemDoc:
    """Generate a subsystem document from structural brief + selected files.

    Args:
        subsystem: The confirmed subsystem proposal.
        structure_path: Path to structure.json.
        file_selection: Files selected by the LLM in B14c.
        repo_root: Path to the repo for reading file contents.
        model: Model to use for generation.
        timeout_seconds: Subprocess timeout.

    Returns:
        SubsystemDoc with markdown content, or error.
    """
    # Build the structural brief (covers ALL files in the subsystem)
    brief = build_subsystem_brief(subsystem, structure_path)

    # Read the selected files' full content
    file_contents: list[str] = []
    files_read: list[str] = []
    for entry in file_selection.files:
        fp = entry["file_path"]
        full_path = repo_root / fp
        if not full_path.exists():
            file_contents.append(f"## {fp}\n\n[FILE NOT FOUND]\n")
            continue
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
            # Truncate very large files to avoid blowing the context
            if len(content) > 15000:
                content = content[:15000] + f"\n\n[TRUNCATED at 15000 chars — full file is {len(content)} chars]\n"
            file_contents.append(f"## {fp}\n\n```\n{content}\n```\n")
            files_read.append(fp)
        except OSError as e:
            file_contents.append(f"## {fp}\n\n[READ ERROR: {e}]\n")

    files_section = "\n".join(file_contents)

    user_prompt = (
        f"# Subsystem: {subsystem.name}\n"
        f"Role: {subsystem.role}\n"
        f"Directories: {', '.join(subsystem.directories)}\n\n"
        f"## Part 1: Structural skeleton (all files)\n\n"
        f"{brief}\n\n"
        f"## Part 2: Full source of selected key files\n\n"
        f"{files_section}\n\n"
        f"Write the subsystem document now. Follow every required section."
    )

    cmd = [
        "claude",
        "-p",
        "--output-format", "text",
        "--model", model,
        "--no-session-persistence",
        "--system-prompt", _DEEPDIVE_SYSTEM_PROMPT,
        user_prompt,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return SubsystemDoc(
            subsystem_name=subsystem.name,
            markdown="",
            files_read=files_read,
            error=f"Generation timed out after {timeout_seconds}s",
        )
    except FileNotFoundError:
        return SubsystemDoc(
            subsystem_name=subsystem.name,
            markdown="",
            files_read=files_read,
            error="Claude Code CLI not found",
        )

    if result.returncode != 0:
        return SubsystemDoc(
            subsystem_name=subsystem.name,
            markdown="",
            files_read=files_read,
            error=f"Claude Code exited with code {result.returncode}. stderr: {result.stderr[:200]}",
        )

    output = result.stdout.strip()
    if not output:
        return SubsystemDoc(
            subsystem_name=subsystem.name,
            markdown="",
            files_read=files_read,
            error=f"Empty output. stderr: {result.stderr[:200]}",
        )

    return SubsystemDoc(
        subsystem_name=subsystem.name,
        markdown=output,
        files_read=files_read,
    )


def save_subsystem_doc(
    doc: SubsystemDoc,
    output_dir: Path,
) -> Path:
    """Save a subsystem document to agent-docs/subsystems/{name}.md."""
    # Sanitize name for filesystem
    safe_name = doc.subsystem_name.lower().replace(" ", "_").replace("/", "_")
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in ("_", "-"))

    subsystems_dir = output_dir / "subsystems"
    subsystems_dir.mkdir(parents=True, exist_ok=True)

    path = subsystems_dir / f"{safe_name}.md"
    path.write_text(doc.markdown + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# B14e: Synthesis — subsystem docs → top-level artifacts
# ---------------------------------------------------------------------------


def _call_llm_text(
    system_prompt: str,
    user_prompt: str,
    model: str = "sonnet",
    timeout_seconds: int = 300,
) -> tuple[str, str | None]:
    """Call Claude Code in text mode. Returns (output, error_or_none)."""
    cmd = [
        "claude", "-p",
        "--output-format", "text",
        "--model", model,
        "--no-session-persistence",
        "--system-prompt", system_prompt,
        user_prompt,
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return ("", f"Timed out after {timeout_seconds}s")
    except FileNotFoundError:
        return ("", "Claude Code CLI not found")

    if result.returncode != 0:
        return ("", f"Exit code {result.returncode}. stderr: {result.stderr[:200]}")

    output = result.stdout.strip()
    if not output:
        return ("", f"Empty output. stderr: {result.stderr[:200]}")

    return (output, None)


def _build_subsystem_summaries(docs: list[SubsystemDoc]) -> str:
    """Build a condensed summary of all subsystem docs for synthesis.

    Each doc is truncated to its first ~2000 chars to keep the synthesis
    prompt manageable. The full docs are in agent-docs/subsystems/.
    """
    parts: list[str] = []
    for doc in docs:
        if doc.error or not doc.markdown:
            parts.append(f"## {doc.subsystem_name}\n\n[Generation failed: {doc.error}]\n")
            continue
        # Take first 2000 chars — enough to capture Why, Boundaries, Structure
        truncated = doc.markdown[:2000]
        if len(doc.markdown) > 2000:
            truncated += f"\n\n[... truncated, full doc in agent-docs/subsystems/]\n"
        parts.append(truncated)
    return "\n\n---\n\n".join(parts)


@dataclass
class SynthesisResult:
    """Result of the synthesis step."""

    patterns_md: str
    agent_context_md: str
    agent_context_nano_md: str
    errors: list[str] = field(default_factory=list)


def synthesize_docs(
    subsystem_docs: list[SubsystemDoc],
    repo_profile: RepoProfile,
    model: str = "sonnet",
    timeout_seconds: int = 300,
) -> SynthesisResult:
    """Synthesize top-level artifacts from subsystem docs + repo profile.

    Produces three artifacts via three separate LLM calls:
    1. patterns.md — prescriptive recipes
    2. agent-context.md — full compact context (≤120 lines)
    3. agent-context-nano.md — inlined nano-digest (≤40 lines)

    Args:
        subsystem_docs: List of generated SubsystemDoc objects.
        repo_profile: The RepoProfile for directory/edge context.
        model: Model to use.
        timeout_seconds: Per-call timeout.

    Returns:
        SynthesisResult with the three markdown strings.
    """
    summaries = _build_subsystem_summaries(subsystem_docs)
    dir_brief = format_profiles_for_llm(repo_profile)
    errors: list[str] = []

    # --- 1. patterns.md ---
    patterns_md, err = _call_llm_text(
        system_prompt=(
            "You are extracting code patterns from subsystem documentation. "
            "For each pattern you find, produce a prescriptive recipe: "
            "what the pattern is, the cleanest example file, step-by-step "
            "instructions for adding a new instance, conventions to follow, "
            "and anti-patterns to avoid. "
            "Output valid markdown. Be specific — cite file paths."
        ),
        user_prompt=(
            f"# Repository directory structure\n\n{dir_brief}\n\n"
            f"# Subsystem documentation summaries\n\n{summaries}\n\n"
            f"Extract all recurring code patterns into prescriptive recipes. "
            f"For each pattern: name, example file, step-by-step to add a "
            f"new instance, conventions, anti-patterns."
        ),
        model=model,
        timeout_seconds=timeout_seconds,
    )
    if err:
        errors.append(f"patterns.md: {err}")

    # --- 2. agent-context.md ---
    agent_context_md, err = _call_llm_text(
        system_prompt=(
            "You are writing a compact agent context document (≤120 lines). "
            "This is the PRIMARY output — the document a coding agent loads "
            "at session start. No prose. No tables. Every line must be "
            "actionable. Sections: What this repo is (2-3 sentences), "
            "Architecture map (path → purpose), Key patterns (step-by-step "
            "recipes), Conventions, Do NOT list, Key contracts, "
            "For deeper context (pointers to subsystem docs). "
            "Cite specific file paths. Keep under 120 lines."
        ),
        user_prompt=(
            f"# Repository directory structure\n\n{dir_brief}\n\n"
            f"# Subsystem documentation summaries\n\n{summaries}\n\n"
            f"Write agent-context.md. Under 120 lines. Every line actionable."
        ),
        model=model,
        timeout_seconds=timeout_seconds,
    )
    if err:
        errors.append(f"agent-context.md: {err}")

    # --- 3. agent-context-nano.md ---
    agent_context_nano_md, err = _call_llm_text(
        system_prompt=(
            "You are writing a nano-digest (HARD CEILING: 40 lines). "
            "This is inlined directly into CLAUDE.md / AGENTS.md. "
            "It must be the most compressed, highest-signal summary "
            "possible. Sections: What this is (1-2 sentences), "
            "Where things live (5-8 paths), How to add a new [most "
            "common thing] (4 steps), How to add a new [second thing] "
            "(4 steps), Do NOT (2-3 items). "
            "FORBIDDEN: any reference to agent-docs/ paths. "
            "The agent should never need to read deeper docs for "
            "common tasks. Cite specific file paths. "
            "MAXIMUM 40 LINES. Target 25-35."
        ),
        user_prompt=(
            f"# Repository directory structure\n\n{dir_brief}\n\n"
            f"# Subsystem documentation summaries\n\n{summaries}\n\n"
            f"Write agent-context-nano.md. MAXIMUM 40 LINES."
        ),
        model=model,
        timeout_seconds=timeout_seconds,
    )
    if err:
        errors.append(f"agent-context-nano.md: {err}")

    return SynthesisResult(
        patterns_md=patterns_md,
        agent_context_md=agent_context_md,
        agent_context_nano_md=agent_context_nano_md,
        errors=errors,
    )


def save_synthesis(
    result: SynthesisResult,
    output_dir: Path,
) -> list[Path]:
    """Save synthesis artifacts to the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    for name, content in [
        ("patterns.md", result.patterns_md),
        ("agent-context.md", result.agent_context_md),
        ("agent-context-nano.md", result.agent_context_nano_md),
    ]:
        if content:
            path = output_dir / name
            path.write_text(content + "\n", encoding="utf-8")
            paths.append(path)

    return paths


# ---------------------------------------------------------------------------
# Bx1: Route index generation
# ---------------------------------------------------------------------------


def generate_route_index(
    subsystem_map: SubsystemMap,
    output_dir: Path,
) -> Path:
    """Generate agent-docs/route-index.json from a subsystem map.

    The route index maps file paths, directory prefixes, and patterns
    to the relevant agent-docs files. The PreToolUse hook uses this to
    provide path-aware hints when the agent runs Glob/Grep.

    Structure:
      {
        "version": 1,
        "routes": [
          {
            "match_type": "directory_prefix",
            "pattern": "backend/open_webui/routers",
            "subsystem": "API Routers",
            "doc_path": "agent-docs/subsystems/api_routers.md",
            "hint": "API Routers subsystem — see agent-docs/subsystems/api_routers.md"
          },
          ...
        ],
        "fallback_hint": "See agent-docs/agent-context.md for full codebase context."
      }
    """
    routes: list[dict] = []

    for sub in subsystem_map.subsystems:
        # Sanitize name for doc path (must match save_subsystem_doc)
        safe_name = sub.name.lower().replace(" ", "_").replace("/", "_")
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in ("_", "-"))
        doc_path = f"agent-docs/subsystems/{safe_name}.md"

        for directory in sub.directories:
            d = directory.rstrip("/")
            routes.append({
                "match_type": "directory_prefix",
                "pattern": d,
                "subsystem": sub.name,
                "doc_path": doc_path,
                "hint": f"{sub.name}: {sub.role}",
            })

    index = {
        "version": 1,
        "routes": routes,
        "fallback_hint": (
            "Codebase context in CLAUDE.md (nano-digest). "
            "For deeper context: agent-docs/agent-context.md"
        ),
    }

    output_path = output_dir / "route-index.json"
    output_path.write_text(
        json.dumps(index, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path
