"""Directory profiler and subsystem boundary detection (B14a, B14b).

B14a — Directory profiler:
  Reads structure.json + graph.json and computes per-directory profiles.
  Deterministic — same inputs produce same outputs.

B14b — Subsystem proposer:
  Feeds directory profiles to an LLM which proposes subsystem boundaries
  with names, directory assignments, and rationale. Uses structured
  output (JSON schema) for reliable parsing.
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
    subsystem boundaries.
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
    timeout_seconds: int = 120,
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
    timeout_seconds: int = 120,
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
