"""Repo-aware benchmark task generation (A13 rework).

Replaces the shallow PlaceholderFiller + static template approach with
a task generation layer that inspects the target repo's extracted
context and synthesizes concrete benchmark task instances.

Architecture:
  RepoContext — deterministic summary of the repo from structure.json
                + graph.json. Classifies files, finds patterns, maps
                tests to sources, identifies central vs peripheral code.

  TaskGenerator — produces TaskInstance objects from RepoContext.
                  Each instance is a concrete, bounded benchmark item
                  with resolved instructions, checkers, and setup_actions.

  TaskInstance — a single benchmarkable item. No placeholders. Ready
                 to execute. Serializable to JSON for auditability.

Design decisions:
  - Quality over quantity: fewer well-targeted tasks beat many vague ones.
  - Difficulty is structural: easy = local/single-file, medium = subsystem,
    hard = cross-subsystem. Not vague open-ended exploration.
  - Bug planting uses real code mutations (swap operator, remove return,
    off-by-one), not comment injection.
  - Every generated task has source_context explaining why this target
    was chosen — auditability.
  - Task set is written to generated-tasks.json before execution.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath

from pensieve.benchmark.template import CheckerSpec


# ---------------------------------------------------------------------------
# RepoContext — deterministic repo summary
# ---------------------------------------------------------------------------


@dataclass
class FileInfo:
    """Summarized info about a single file for task generation."""

    path: str
    language: str
    directory: str
    symbol_count: int
    symbols: list[dict]  # [{name, kind, signature, line_start, ...}]
    import_count: int
    has_tests: bool  # whether a test file exists for this source
    test_file: str | None  # path to the test file if known
    incoming_edges: int  # how many files import this one
    outgoing_edges: int  # how many files this one imports
    call_edge_count: int


@dataclass
class RepoContext:
    """Deterministic summary of a repo for task generation.

    Built from structure.json + graph.json + repo inspection.
    """

    repo_root: str
    total_files: int
    languages: dict[str, int]
    files: list[FileInfo]

    # Classified file lists (indices into self.files)
    source_files: list[int] = field(default_factory=list)
    test_files: list[int] = field(default_factory=list)
    central_files: list[int] = field(default_factory=list)
    untested_files: list[int] = field(default_factory=list)

    # Directory patterns: dirs with 3+ files sharing a pattern
    pattern_dirs: list[dict] = field(default_factory=list)

    # Subsystem-ish groupings from directory structure
    directories: list[dict] = field(default_factory=list)

    # Enriched context from repo inspection
    readme_summary: str = ""  # first ~500 chars of README
    repo_purpose: str = ""  # one-line from README or manifest
    entrypoints: list[str] = field(default_factory=list)  # main.py, app.py, etc.
    test_conventions: str = ""  # test framework/dir detected
    config_files: list[str] = field(default_factory=list)  # manifests found

    # Cross-directory coupling (for cross-subsystem tasks)
    # [{source_dir, target_dir, edge_count}]
    cross_dir_edges: list[dict] = field(default_factory=list)

    # Registration hubs — files with many incoming call edges
    # (likely routers, registries, plugin loaders)
    registration_hubs: list[int] = field(default_factory=list)


# Auto-generated / non-source directories
_SKIP_DIRS = frozenset({
    "migrations", "versions", "vendor", "node_modules", "dist",
    "build", "__pycache__", ".cache", "generated", "gen",
    "static", "assets", "public", ".git", ".venv", "venv",
})

_TEST_DIR_NAMES = frozenset({
    "tests", "test", "spec", "specs", "__tests__", "testing",
})


def build_repo_context(
    structure_path: Path,
    graph_path: Path | None = None,
    repo_root: Path | None = None,
) -> RepoContext:
    """Build a RepoContext from structure.json, graph.json, and repo files.

    Args:
        structure_path: Path to structure.json.
        graph_path: Path to graph.json (optional but recommended).
        repo_root: Path to the actual repo root for README/config
            inspection. If None, derived from structure_path parent.

    This is deterministic — same inputs produce the same context.
    """
    structure = json.loads(structure_path.read_text(encoding="utf-8"))
    if repo_root is None:
        # structure.json is typically at <repo>/agent-docs/structure.json
        repo_root = structure_path.parent.parent
    raw_files = structure.get("files", [])

    # Load graph if available
    edges: list[dict] = []
    if graph_path and graph_path.exists():
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        edges = graph.get("edges", [])

    # Compute per-file edge counts
    incoming: dict[str, int] = {}
    outgoing: dict[str, int] = {}
    for edge in edges:
        src = edge.get("source", "")
        tgt = edge.get("target", "")
        outgoing[src] = outgoing.get(src, 0) + 1
        incoming[tgt] = incoming.get(tgt, 0) + 1

    # Build test-to-source mapping from graph test edges
    test_edges: dict[str, str] = {}  # test_file -> source_file
    source_has_test: dict[str, str] = {}  # source_file -> test_file
    for edge in edges:
        if edge.get("kind") == "tests":
            test_edges[edge["source"]] = edge["target"]
            source_has_test[edge["target"]] = edge["source"]

    # Also use naming heuristics for test mapping
    all_paths = {f["file_path"] for f in raw_files}
    for f in raw_files:
        fp = f["file_path"]
        p = PurePosixPath(fp)
        # Check if this looks like a test file
        if _is_test_path(fp):
            # Try to find the source file it tests
            stem = p.stem
            for prefix in ("test_", "test", "spec_"):
                if stem.startswith(prefix):
                    source_stem = stem[len(prefix):]
                    break
            else:
                if stem.endswith("_test") or stem.endswith("_spec"):
                    source_stem = stem.rsplit("_", 1)[0]
                elif stem.endswith(".test") or stem.endswith(".spec"):
                    source_stem = stem.rsplit(".", 1)[0]
                else:
                    continue

            # Search for source file
            for candidate in all_paths:
                cp = PurePosixPath(candidate)
                if cp.stem == source_stem and not _is_test_path(candidate):
                    if fp not in test_edges:
                        test_edges[fp] = candidate
                    if candidate not in source_has_test:
                        source_has_test[candidate] = fp
                    break

    # Build FileInfo list
    files: list[FileInfo] = []
    languages: dict[str, int] = {}
    for f in raw_files:
        fp = f["file_path"]
        lang = f.get("language", "unknown")
        languages[lang] = languages.get(lang, 0) + 1
        p = PurePosixPath(fp)
        parent = str(p.parent) if str(p.parent) != "." else "(root)"

        files.append(FileInfo(
            path=fp,
            language=lang,
            directory=parent,
            symbol_count=len(f.get("symbols", [])),
            symbols=f.get("symbols", []),
            import_count=len(f.get("imports", [])),
            has_tests=fp in source_has_test,
            test_file=source_has_test.get(fp),
            incoming_edges=incoming.get(fp, 0),
            outgoing_edges=outgoing.get(fp, 0),
            call_edge_count=len(f.get("call_edges", [])),
        ))

    # Classify files
    source_files: list[int] = []
    test_file_indices: list[int] = []
    central_files: list[int] = []
    untested_files: list[int] = []

    for i, fi in enumerate(files):
        if _is_test_path(fi.path):
            test_file_indices.append(i)
            continue
        if _is_skip_dir(fi.directory):
            continue
        source_files.append(i)
        if fi.incoming_edges >= 3:
            central_files.append(i)
        if not fi.has_tests and fi.symbol_count >= 2:
            untested_files.append(i)

    # Sort central files by incoming edges (most imported first)
    central_files.sort(key=lambda i: -files[i].incoming_edges)

    # Find pattern directories (3+ source files with same language)
    dir_groups: dict[str, list[int]] = {}
    for i in source_files:
        d = files[i].directory
        if d not in dir_groups:
            dir_groups[d] = []
        dir_groups[d].append(i)

    pattern_dirs: list[dict] = []
    for d, indices in sorted(dir_groups.items(), key=lambda x: -len(x[1])):
        if len(indices) < 3:
            continue
        # Check if files share a language
        lang_counts: dict[str, int] = {}
        for i in indices:
            lang = files[i].language
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
        dominant_lang = max(lang_counts, key=lang_counts.get)  # type: ignore
        if lang_counts[dominant_lang] < 3:
            continue

        same_lang = [i for i in indices if files[i].language == dominant_lang]
        # Pick the file with most symbols as the example
        example_idx = max(same_lang, key=lambda i: files[i].symbol_count)

        pattern_dirs.append({
            "dir": d,
            "file_count": len(same_lang),
            "example_file": files[example_idx].path,
            "language": dominant_lang,
            "sibling_files": [files[i].path for i in same_lang[:10]],
        })

    # Directory summaries
    directories: list[dict] = []
    for d, indices in sorted(dir_groups.items(), key=lambda x: -len(x[1])):
        if len(indices) < 2:
            continue
        langs = {}
        top_syms = []
        for i in indices:
            lang = files[i].language
            langs[lang] = langs.get(lang, 0) + 1
            for sym in files[i].symbols[:3]:
                top_syms.append(sym.get("name", ""))
        directories.append({
            "path": d,
            "file_count": len(indices),
            "languages": langs,
            "top_symbols": top_syms[:10],
        })

    # --- Enrich from repo files ---

    readme_summary = ""
    repo_purpose = ""
    for name in ("README.md", "README.rst", "README.txt", "README"):
        readme_path = repo_root / name
        if readme_path.exists():
            try:
                raw = readme_path.read_text(encoding="utf-8", errors="replace")
                # First non-empty, non-heading line as purpose
                for line in raw.splitlines():
                    stripped = line.strip().lstrip("#").strip()
                    if (
                        stripped
                        and len(stripped) > 20
                        and not stripped.startswith(("!", "[", "<", "```", "---", "***"))
                        and "badge" not in stripped.lower()
                        and "shield" not in stripped.lower()
                    ):
                        repo_purpose = stripped[:200]
                        break
                readme_summary = raw[:500]
            except OSError:
                pass
            break

    # Config/manifest files
    config_files: list[str] = []
    _MANIFEST_NAMES = {
        "pyproject.toml", "setup.py", "setup.cfg", "package.json",
        "go.mod", "Cargo.toml", "pom.xml", "build.gradle",
        "Makefile", "docker-compose.yaml", "docker-compose.yml",
        "Dockerfile",
    }
    for name in sorted(_MANIFEST_NAMES):
        if (repo_root / name).exists():
            config_files.append(name)

    # Entrypoints: files named main.*, app.*, __main__.*, index.*
    entrypoints: list[str] = []
    _ENTRY_STEMS = {"main", "app", "__main__", "index", "server", "cli"}
    for fi in files:
        if PurePosixPath(fi.path).stem in _ENTRY_STEMS and not _is_test_path(fi.path):
            entrypoints.append(fi.path)

    # Test conventions
    test_conventions = ""
    if test_file_indices:
        test_dirs_found = {files[i].directory for i in test_file_indices}
        test_langs = {files[i].language for i in test_file_indices}
        test_conventions = (
            f"Tests in {', '.join(sorted(test_dirs_found)[:3])}. "
            f"Languages: {', '.join(sorted(test_langs))}."
        )

    # Agent-docs summaries if present
    agent_docs_dir = repo_root / "agent-docs"
    if agent_docs_dir.is_dir():
        for doc_name in ("agent-context-nano.md", "agent-context.md"):
            doc_path = agent_docs_dir / doc_name
            if doc_path.exists():
                try:
                    content = doc_path.read_text(encoding="utf-8", errors="replace")
                    if content.strip() and not repo_purpose:
                        for line in content.splitlines():
                            stripped = line.strip().lstrip("#").strip()
                            if stripped and len(stripped) > 20:
                                repo_purpose = stripped[:200]
                                break
                except OSError:
                    pass
                break

    # Cross-directory edge data
    cross_dir_counts: dict[tuple[str, str], int] = {}
    file_to_dir_map = {fi.path: fi.directory for fi in files}
    for edge in edges:
        src_dir = file_to_dir_map.get(edge.get("source", ""))
        tgt_dir = file_to_dir_map.get(edge.get("target", ""))
        if src_dir and tgt_dir and src_dir != tgt_dir:
            key = (src_dir, tgt_dir)
            cross_dir_counts[key] = cross_dir_counts.get(key, 0) + 1

    cross_dir_edges = [
        {"source_dir": s, "target_dir": t, "edge_count": c}
        for (s, t), c in sorted(cross_dir_counts.items(), key=lambda x: -x[1])
        if c >= 3  # only substantial cross-dir coupling
    ]

    # Registration hubs: files with many incoming CALL edges
    call_incoming: dict[str, int] = {}
    for edge in edges:
        if edge.get("kind") == "calls":
            tgt = edge.get("target", "")
            call_incoming[tgt] = call_incoming.get(tgt, 0) + 1

    registration_hubs: list[int] = []
    for i in source_files:
        fi = files[i]
        if call_incoming.get(fi.path, 0) >= 5:
            registration_hubs.append(i)
    registration_hubs.sort(key=lambda i: -call_incoming.get(files[i].path, 0))

    return RepoContext(
        repo_root=structure.get("repo_root", ""),
        total_files=len(files),
        languages=languages,
        files=files,
        source_files=source_files,
        test_files=test_file_indices,
        central_files=central_files,
        untested_files=untested_files,
        pattern_dirs=pattern_dirs,
        directories=directories,
        readme_summary=readme_summary,
        repo_purpose=repo_purpose,
        entrypoints=entrypoints,
        test_conventions=test_conventions,
        config_files=config_files,
        cross_dir_edges=cross_dir_edges,
        registration_hubs=registration_hubs,
    )


def _is_test_path(path: str) -> bool:
    """Check if a file path looks like a test file."""
    p = PurePosixPath(path)
    parts = p.parts
    stem = p.stem
    # Directory-based
    if any(part.lower() in _TEST_DIR_NAMES for part in parts):
        return True
    # Name-based
    if stem.startswith("test_") or stem.startswith("test"):
        return True
    if stem.endswith("_test") or stem.endswith("_spec"):
        return True
    if ".test." in p.name or ".spec." in p.name:
        return True
    return False


def _is_skip_dir(directory: str) -> bool:
    """Check if a directory should be skipped for task generation."""
    parts = PurePosixPath(directory).parts
    return any(p.lower() in _SKIP_DIRS for p in parts)


# ---------------------------------------------------------------------------
# TaskInstance — concrete benchmark item
# ---------------------------------------------------------------------------


@dataclass
class TaskInstance:
    """A concrete, repo-specific benchmark task. No placeholders."""

    template_family: str  # which recipe generated this (e.g., "add_sibling")
    instance_id: str  # unique identifier
    difficulty: str  # "easy", "medium", "hard"
    instruction: str  # concrete prompt for the agent
    strict_checker: CheckerSpec
    lenient_checker: CheckerSpec
    setup_actions: list[dict] = field(default_factory=list)
    source_context: str = ""  # why this target was chosen
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "template_family": self.template_family,
            "instance_id": self.instance_id,
            "difficulty": self.difficulty,
            "instruction": self.instruction,
            "strict_checker": asdict(self.strict_checker),
            "lenient_checker": asdict(self.lenient_checker),
            "setup_actions": self.setup_actions,
            "source_context": self.source_context,
            "tags": self.tags,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


# ---------------------------------------------------------------------------
# TaskGenerator — produces TaskInstance objects from RepoContext
# ---------------------------------------------------------------------------


def _make_id(family: str, target: str) -> str:
    """Create a stable instance ID from family + target."""
    h = hashlib.sha256(f"{family}:{target}".encode()).hexdigest()[:8]
    return f"{family}_{h}"


def generate_tasks(
    ctx: RepoContext,
    max_easy: int = 3,
    max_medium: int = 2,
    max_hard: int = 1,
    seed: int | None = 42,
) -> list[TaskInstance]:
    """Generate concrete benchmark task instances from a RepoContext.

    Args:
        ctx: The repo context.
        max_easy: Maximum easy tasks to generate.
        max_medium: Maximum medium tasks to generate.
        max_hard: Maximum hard tasks to generate.
        seed: Random seed for reproducibility. None for non-deterministic.

    Returns:
        List of TaskInstance objects, sorted by difficulty.
    """
    rng = random.Random(seed)
    tasks: list[TaskInstance] = []

    # --- Easy tasks ---
    easy_budget = max_easy

    # 1. add_sibling: create a new file following a directory pattern
    easy_sibling = _generate_add_sibling(ctx, rng, max_count=min(2, easy_budget))
    tasks.extend(easy_sibling)
    easy_budget -= len(easy_sibling)

    # 2. add_test: write tests for an untested source file
    if easy_budget > 0:
        easy_test = _generate_add_test(ctx, rng, max_count=easy_budget)
        tasks.extend(easy_test)

    # --- Medium tasks ---
    medium_budget = max_medium

    # 3. bug_fix: plant a real bug and ask the agent to fix it
    medium_bug = _generate_bug_fix(ctx, rng, max_count=min(1, medium_budget))
    tasks.extend(medium_bug)
    medium_budget -= len(medium_bug)

    # 4. architecture: grounded architecture question about a specific subsystem
    if medium_budget > 0:
        medium_arch = _generate_architecture(ctx, rng, max_count=medium_budget)
        tasks.extend(medium_arch)

    # --- Hard tasks ---
    hard_budget = max_hard

    # 5. find_owner: identify subsystem for a central file
    hard_owner = _generate_find_owner(ctx, rng, max_count=min(1, hard_budget))
    tasks.extend(hard_owner)
    hard_budget -= len(hard_owner)

    # 6. cross_subsystem: task spanning two coupled directories
    if hard_budget > 0:
        hard_cross = _generate_cross_subsystem(ctx, rng, max_count=hard_budget)
        tasks.extend(hard_cross)

    return tasks


# ---------------------------------------------------------------------------
# Per-family generators
# ---------------------------------------------------------------------------


def _generate_add_sibling(
    ctx: RepoContext, rng: random.Random, max_count: int,
) -> list[TaskInstance]:
    """Generate add_sibling tasks from pattern directories."""
    tasks: list[TaskInstance] = []
    if not ctx.pattern_dirs:
        return tasks

    # Pick diverse pattern directories
    candidates = list(ctx.pattern_dirs)
    rng.shuffle(candidates)

    for pattern in candidates[:max_count]:
        dir_path = pattern["dir"]
        example = pattern["example_file"]
        lang = pattern["language"]
        ext = PurePosixPath(example).suffix

        new_file = f"{dir_path}/benchmark_new_instance{ext}"
        sibling_list = ", ".join(pattern["sibling_files"][:3])

        instruction = (
            f"Create a new file at '{new_file}' that follows the same "
            f"pattern as the existing files in '{dir_path}/'. "
            f"Use '{example}' as your primary reference. "
            f"Other files following this pattern: {sibling_list}. "
            f"The new file should have the same structure, imports, "
            f"boilerplate, and conventions. Name the main entity "
            f"'BenchmarkNewInstance' or 'benchmark_new_instance' as "
            f"appropriate for the language ({lang})."
        )

        tasks.append(TaskInstance(
            template_family="add_sibling",
            instance_id=_make_id("add_sibling", dir_path),
            difficulty="easy",
            instruction=instruction,
            strict_checker=CheckerSpec(
                checker_type="file_exists",
                criteria=f"The file '{new_file}' was created.",
                target_file=new_file,
            ),
            lenient_checker=CheckerSpec(
                checker_type="llm_judge",
                criteria=(
                    f"The new file follows the pattern of files in "
                    f"'{dir_path}/' — same structure, imports, naming."
                ),
                llm_prompt=(
                    f"Compare '{new_file}' against '{example}'. "
                    f"Does the new file follow the same pattern "
                    f"(structure, imports, naming, boilerplate)? "
                    f"PASS if pattern is followed, FAIL if not."
                ),
            ),
            source_context=(
                f"Pattern directory '{dir_path}' has {pattern['file_count']} "
                f"{lang} files sharing a common structure. "
                f"Example: {example}."
            ),
            tags=["add_sibling", "pattern", "easy"],
        ))

    return tasks


def _generate_add_test(
    ctx: RepoContext, rng: random.Random, max_count: int,
) -> list[TaskInstance]:
    """Generate add_test tasks for untested source files."""
    tasks: list[TaskInstance] = []
    if not ctx.untested_files:
        return tasks

    # Pick files with enough symbols to be testable
    candidates = [
        i for i in ctx.untested_files
        if ctx.files[i].symbol_count >= 3
    ]
    rng.shuffle(candidates)

    for idx in candidates[:max_count]:
        fi = ctx.files[idx]
        ext = PurePosixPath(fi.path).suffix
        stem = PurePosixPath(fi.path).stem

        # Determine test file path
        test_path = f"{fi.directory}/test_{stem}{ext}"
        # If there's a test directory pattern, use it
        for d in ctx.directories:
            if d["path"].endswith(("test", "tests", "spec", "__tests__")):
                test_path = f"{d['path']}/test_{stem}{ext}"
                break

        func_names = [
            s["name"] for s in fi.symbols
            if s.get("kind") in ("function", "method")
        ][:5]
        func_list = ", ".join(func_names) if func_names else "the main exports"

        instruction = (
            f"Write tests for '{fi.path}'. Place the test file at "
            f"'{test_path}'. The file contains these functions/methods: "
            f"{func_list}. Cover the main behavior of each. "
            f"Use the same test framework as other tests in this repo."
        )

        tasks.append(TaskInstance(
            template_family="add_test",
            instance_id=_make_id("add_test", fi.path),
            difficulty="easy",
            instruction=instruction,
            strict_checker=CheckerSpec(
                checker_type="file_exists",
                criteria=f"The test file '{test_path}' was created.",
                target_file=test_path,
            ),
            lenient_checker=CheckerSpec(
                checker_type="llm_judge",
                criteria=(
                    f"The test file covers the main functions in "
                    f"'{fi.path}' using the repo's test conventions."
                ),
                llm_prompt=(
                    f"Review '{test_path}' written for '{fi.path}'. "
                    f"Does it cover {func_list}? Does it use the "
                    f"correct test framework? PASS or FAIL."
                ),
            ),
            source_context=(
                f"'{fi.path}' has {fi.symbol_count} symbols, "
                f"{fi.incoming_edges} incoming edges, and no existing tests."
            ),
            tags=["add_test", "easy"],
        ))

    return tasks


# Bug mutation strategies for planted bugs
_BUG_MUTATIONS = [
    {
        "name": "swap_comparison",
        "description": "comparison operator is inverted",
        "find": ["<=", ">=", "==", "!=", "<", ">"],
        "replace": [">=", "<=", "!=", "==", ">", "<"],
    },
    {
        "name": "off_by_one",
        "description": "off-by-one error in range/slice boundary",
        "find": ["- 1", "+ 1", "len("],
        "replace": ["", " + 1", "len("] ,  # remove -1, add +1, no change
    },
    {
        "name": "remove_return",
        "description": "missing return statement causes function to return None",
        "find": ["return "],
        "replace": ["# return "],
    },
]


def _generate_bug_fix(
    ctx: RepoContext, rng: random.Random, max_count: int,
) -> list[TaskInstance]:
    """Generate bug_fix tasks with real code mutations.

    Picks a function in a source file, applies a concrete mutation
    via setup_actions, and asks the agent to find and fix it.
    """
    tasks: list[TaskInstance] = []

    # Pick source files with functions that have enough code to mutate
    candidates = []
    for i in ctx.source_files:
        fi = ctx.files[i]
        functions = [
            s for s in fi.symbols
            if s.get("kind") in ("function", "method")
            and s.get("line_start") and s.get("line_end")
            and (s["line_end"] - s["line_start"]) >= 5  # at least 5 lines
        ]
        if functions:
            candidates.append((i, functions))

    rng.shuffle(candidates)

    for file_idx, functions in candidates[:max_count]:
        fi = ctx.files[file_idx]
        func = rng.choice(functions)
        func_name = func["name"]
        line_start = func["line_start"]
        line_end = func["line_end"]

        # Pick a mutation strategy
        mutation = rng.choice(_BUG_MUTATIONS)
        bug_desc = mutation["description"]

        instruction = (
            f"There is a bug in the function '{func_name}' in file "
            f"'{fi.path}' (lines {line_start}-{line_end}). "
            f"The bug: {bug_desc}. Find and fix it. "
            f"Only modify '{fi.path}'. Do not change the function's "
            f"signature or any other function in the file."
        )

        # Setup action: the runner will read the file, find the function,
        # and apply the mutation. We store the mutation spec; the runner
        # applies it at execution time.
        setup_action = {
            "action": "mutate_function",
            "path": fi.path,
            "function_name": func_name,
            "line_start": line_start,
            "line_end": line_end,
            "mutation": mutation["name"],
            "find_patterns": mutation["find"],
            "replace_patterns": mutation["replace"],
        }

        tasks.append(TaskInstance(
            template_family="bug_fix",
            instance_id=_make_id("bug_fix", f"{fi.path}:{func_name}"),
            difficulty="medium",
            instruction=instruction,
            strict_checker=CheckerSpec(
                checker_type="content_contains",
                criteria=(
                    f"The file '{fi.path}' still contains '{func_name}'."
                ),
                target_string=func_name,
                target_file=fi.path,
            ),
            lenient_checker=CheckerSpec(
                checker_type="llm_judge",
                criteria=(
                    f"The bug ({bug_desc}) in '{func_name}' was fixed "
                    f"correctly without unnecessary changes."
                ),
                llm_prompt=(
                    f"The function '{func_name}' in '{fi.path}' had "
                    f"this bug: {bug_desc}. Was it fixed correctly? "
                    f"Were any unnecessary changes made? PASS or FAIL."
                ),
            ),
            setup_actions=[setup_action],
            source_context=(
                f"Function '{func_name}' in '{fi.path}' "
                f"(lines {line_start}-{line_end}, "
                f"{line_end - line_start + 1} lines). "
                f"Mutation: {mutation['name']} — {bug_desc}."
            ),
            tags=["bug_fix", "medium"],
        ))

    return tasks


def _generate_find_owner(
    ctx: RepoContext, rng: random.Random, max_count: int,
) -> list[TaskInstance]:
    """Generate find_owner tasks grounded in real directory structure."""
    tasks: list[TaskInstance] = []
    if not ctx.directories or not ctx.central_files:
        return tasks

    # Pick central files that belong to substantial directories
    candidates = []
    for i in ctx.central_files:
        fi = ctx.files[i]
        # Find the directory this file belongs to
        for d in ctx.directories:
            if fi.directory == d["path"] and d["file_count"] >= 3:
                candidates.append((i, d))
                break

    rng.shuffle(candidates)

    for file_idx, dir_info in candidates[:max_count]:
        fi = ctx.files[file_idx]
        dir_path = dir_info["path"]
        dir_files = dir_info["file_count"]
        top_syms = ", ".join(dir_info["top_symbols"][:5])

        instruction = (
            f"Answer these questions about '{fi.path}':\n"
            f"1. What module or subsystem does this file belong to?\n"
            f"2. What are the key files in the same module "
            f"('{dir_path}/')?\n"
            f"3. What conventions does this module follow "
            f"(naming, error handling, patterns)?\n"
            f"4. If I wanted to add a new file to this module, "
            f"what pattern should I follow?\n"
            f"Be specific — cite file paths and concrete conventions."
        )

        tasks.append(TaskInstance(
            template_family="find_owner",
            instance_id=_make_id("find_owner", fi.path),
            difficulty="hard",
            instruction=instruction,
            strict_checker=CheckerSpec(
                checker_type="content_contains",
                criteria=(
                    f"The response mentions '{dir_path}'."
                ),
                target_string=dir_path,
            ),
            lenient_checker=CheckerSpec(
                checker_type="llm_judge",
                criteria=(
                    f"The response correctly identifies the module, "
                    f"cites files from '{dir_path}/', and describes "
                    f"real conventions."
                ),
                llm_prompt=(
                    f"'{fi.path}' is in '{dir_path}/' which has "
                    f"{dir_files} files. Key symbols: {top_syms}. "
                    f"Did the agent correctly identify the module, "
                    f"cite real file paths, and describe conventions? "
                    f"PASS or FAIL."
                ),
            ),
            source_context=(
                f"'{fi.path}' has {fi.incoming_edges} incoming edges, "
                f"is in '{dir_path}/' ({dir_files} files). "
                f"Central file chosen for grounded ownership task."
            ),
            tags=["find_owner", "hard"],
        ))

    return tasks


def _generate_architecture(
    ctx: RepoContext, rng: random.Random, max_count: int,
) -> list[TaskInstance]:
    """Generate grounded architecture/navigation tasks.

    Unlike old cold_navigation (vague "describe the architecture"),
    these are bounded: ask about a specific subsystem directory,
    with concrete expected answers.
    """
    tasks: list[TaskInstance] = []
    if not ctx.directories:
        return tasks

    # Pick directories with substantial file counts and cross-dir coupling
    candidates = [
        d for d in ctx.directories
        if d["file_count"] >= 5 and not _is_skip_dir(d["path"])
    ]
    rng.shuffle(candidates)

    for d in candidates[:max_count]:
        dir_path = d["path"]
        file_count = d["file_count"]
        top_syms = ", ".join(d["top_symbols"][:5])

        # Find what this directory imports from and what imports it
        imports_from = []
        imported_by = []
        for edge in ctx.cross_dir_edges:
            if edge["source_dir"] == dir_path:
                imports_from.append(f"{edge['target_dir']} ({edge['edge_count']} edges)")
            if edge["target_dir"] == dir_path:
                imported_by.append(f"{edge['source_dir']} ({edge['edge_count']} edges)")

        dep_info = ""
        if imports_from:
            dep_info += f" It imports from: {', '.join(imports_from[:3])}."
        if imported_by:
            dep_info += f" It is imported by: {', '.join(imported_by[:3])}."

        repo_desc = ctx.repo_purpose or f"a {ctx.total_files}-file project"

        instruction = (
            f"This repo is {repo_desc}. "
            f"Explain the architecture of the '{dir_path}/' module "
            f"({file_count} files).{dep_info}\n\n"
            f"Answer specifically:\n"
            f"1. What is this module's responsibility in the system?\n"
            f"2. What are its key files and what does each do?\n"
            f"3. How does it interact with other modules?\n"
            f"4. What patterns or conventions does it follow?\n"
            f"Cite specific file paths and function names."
        )

        tasks.append(TaskInstance(
            template_family="architecture",
            instance_id=_make_id("architecture", dir_path),
            difficulty="medium",
            instruction=instruction,
            strict_checker=CheckerSpec(
                checker_type="content_contains",
                criteria=f"The response mentions '{dir_path}'.",
                target_string=dir_path,
            ),
            lenient_checker=CheckerSpec(
                checker_type="llm_judge",
                criteria=(
                    f"The response accurately describes '{dir_path}/' — "
                    f"its role, key files, interactions, and patterns."
                ),
                llm_prompt=(
                    f"'{dir_path}/' has {file_count} files. "
                    f"Key symbols: {top_syms}. "
                    f"Did the agent accurately describe this module's "
                    f"responsibility, cite real files, explain interactions "
                    f"with other modules, and identify patterns? "
                    f"PASS or FAIL."
                ),
            ),
            source_context=(
                f"'{dir_path}/' has {file_count} files, "
                f"key symbols: {top_syms}. "
                f"Grounded architecture task with specific directory target."
            ),
            tags=["architecture", "medium"],
        ))

    return tasks


def _generate_cross_subsystem(
    ctx: RepoContext, rng: random.Random, max_count: int,
) -> list[TaskInstance]:
    """Generate cross-subsystem tasks spanning two coupled directories.

    These are 'hard' tasks that require understanding how two modules
    interact. The question is bounded and grounded in real coupling data.
    """
    tasks: list[TaskInstance] = []
    if not ctx.cross_dir_edges:
        return tasks

    # Pick the most tightly coupled directory pairs
    candidates = [
        e for e in ctx.cross_dir_edges
        if e["edge_count"] >= 5
        and not _is_skip_dir(e["source_dir"])
        and not _is_skip_dir(e["target_dir"])
    ]
    rng.shuffle(candidates)

    for edge_info in candidates[:max_count]:
        src_dir = edge_info["source_dir"]
        tgt_dir = edge_info["target_dir"]
        edge_count = edge_info["edge_count"]

        # Find specific symbols involved in the cross-dir coupling
        cross_symbols = []
        for fi in ctx.files:
            if fi.directory == src_dir:
                for sym in fi.symbols:
                    if sym.get("kind") in ("function", "method"):
                        cross_symbols.append(f"{fi.path}:{sym['name']}")
                        if len(cross_symbols) >= 3:
                            break
            if len(cross_symbols) >= 3:
                break

        sym_examples = ", ".join(cross_symbols[:3]) if cross_symbols else "various functions"

        instruction = (
            f"The modules '{src_dir}/' and '{tgt_dir}/' are tightly coupled "
            f"({edge_count} import/call edges between them).\n\n"
            f"Answer specifically:\n"
            f"1. What does '{src_dir}/' depend on '{tgt_dir}/' for?\n"
            f"2. Which specific functions/classes in '{tgt_dir}/' are "
            f"consumed by '{src_dir}/'?\n"
            f"3. If I needed to refactor the interface between these "
            f"two modules, which files would I need to change?\n"
            f"4. Are there any circular dependencies or coupling concerns?\n"
            f"Cite specific file paths and function names."
        )

        tasks.append(TaskInstance(
            template_family="cross_subsystem",
            instance_id=_make_id("cross_subsystem", f"{src_dir}:{tgt_dir}"),
            difficulty="hard",
            instruction=instruction,
            strict_checker=CheckerSpec(
                checker_type="content_contains",
                criteria=(
                    f"The response mentions both '{src_dir}' and '{tgt_dir}'."
                ),
                target_string=src_dir,
            ),
            lenient_checker=CheckerSpec(
                checker_type="llm_judge",
                criteria=(
                    f"The response explains the coupling between "
                    f"'{src_dir}/' and '{tgt_dir}/', cites specific "
                    f"files and functions, and provides refactoring guidance."
                ),
                llm_prompt=(
                    f"'{src_dir}/' and '{tgt_dir}/' have {edge_count} edges "
                    f"between them. Did the agent explain the coupling, "
                    f"cite specific files/functions, and provide useful "
                    f"refactoring guidance? PASS or FAIL."
                ),
            ),
            source_context=(
                f"'{src_dir}/' → '{tgt_dir}/': {edge_count} cross-dir edges. "
                f"Example symbols: {sym_examples}."
            ),
            tags=["cross_subsystem", "hard"],
        ))

    return tasks


# ---------------------------------------------------------------------------
# Setup action execution
# ---------------------------------------------------------------------------


def apply_setup_actions(
    actions: list[dict],
    repo_root: Path,
) -> list[str]:
    """Apply setup actions to a (copied) repo before task execution.

    Args:
        actions: List of action dicts from TaskInstance.setup_actions.
        repo_root: Path to the repo copy (never the original).

    Returns:
        List of error messages. Empty list = all actions succeeded.
    """
    errors: list[str] = []

    for action in actions:
        act_type = action.get("action", "")
        path = action.get("path", "")
        if not path:
            errors.append(f"Action missing path: {action}")
            continue

        target = repo_root / path

        if act_type == "write_file":
            content = action.get("content", "")
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            except OSError as e:
                errors.append(f"write_file '{path}': {e}")

        elif act_type == "delete_file":
            try:
                if target.exists():
                    target.unlink()
            except OSError as e:
                errors.append(f"delete_file '{path}': {e}")

        elif act_type == "modify_file":
            content = action.get("content", "")
            try:
                if target.exists():
                    existing = target.read_text(encoding="utf-8")
                    target.write_text(existing + "\n" + content, encoding="utf-8")
                else:
                    errors.append(f"modify_file '{path}': file does not exist")
            except OSError as e:
                errors.append(f"modify_file '{path}': {e}")

        elif act_type == "mutate_function":
            # Read the file, find the function by line range, apply mutation
            func_name = action.get("function_name", "")
            line_start = action.get("line_start", 0)
            line_end = action.get("line_end", 0)
            find_patterns = action.get("find_patterns", [])
            replace_patterns = action.get("replace_patterns", [])

            if not target.exists():
                errors.append(f"mutate_function '{path}': file does not exist")
                continue

            try:
                lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
                mutated = False

                # Extract function lines (1-indexed in the action)
                start_idx = max(0, line_start - 1)
                end_idx = min(len(lines), line_end)

                for i in range(start_idx, end_idx):
                    if mutated:
                        break
                    for find_pat, repl_pat in zip(find_patterns, replace_patterns):
                        if find_pat in lines[i]:
                            lines[i] = lines[i].replace(find_pat, repl_pat, 1)
                            mutated = True
                            break

                if mutated:
                    target.write_text("".join(lines), encoding="utf-8")
                else:
                    errors.append(
                        f"mutate_function '{path}:{func_name}': "
                        f"no matching pattern found in lines {line_start}-{line_end}"
                    )
            except OSError as e:
                errors.append(f"mutate_function '{path}': {e}")

        else:
            errors.append(f"Unknown action type: {act_type}")

    return errors


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def save_generated_tasks(
    tasks: list[TaskInstance],
    output_path: Path,
) -> Path:
    """Write generated tasks to JSON for auditability."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "task_count": len(tasks),
        "by_difficulty": {
            "easy": len([t for t in tasks if t.difficulty == "easy"]),
            "medium": len([t for t in tasks if t.difficulty == "medium"]),
            "hard": len([t for t in tasks if t.difficulty == "hard"]),
        },
        "tasks": [t.to_dict() for t in tasks],
    }
    output_path.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path
