"""Path-aware routing engine for the PreToolUse hook (Bx2).

Takes a query string (from Glob pattern or Grep query) and a
route-index.json, returns the best routing hint.

Priority order:
  1. directory_prefix — query path starts with a subsystem's owns_paths
  2. pattern_route — query contains a pattern's template/registration basename
  3. common_task — query contains keywords from a subsystem's common_tasks
  4. fallback — generic context hint

Design:
  - Conservative matching — prefer false negatives over false positives
  - Deterministic — same query + same index → same result
  - Single best hint — one line, one doc pointer
  - Longest-prefix-wins for directory matching

This module is the canonical routing file. It contains both the library
API (route_query) and a stdlib-only template (_HOOK_ROUTING_TEMPLATE)
that is rendered into the installed hook via render_hook_routing_script().
Constants (_STOP_WORDS, _SKIP_REG) are shared; the algorithm template
mirrors the library logic. Changes to routing policy must be reflected
in both route_query() and the template.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass
class RouteResult:
    """Result of routing a query."""
    hint: str
    doc: str
    subsystem: str
    match_type: str  # directory_prefix, pattern_route, common_task, fallback
    artifact_kind: str  # subsystem_doc, patterns, fallback


# ---------------------------------------------------------------------------
# Canonical constants — shared between library API and hook script
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset({
    "a", "an", "the", "add", "new", "create", "update", "delete",
    "remove", "get", "set", "find", "list", "change", "modify",
    "in", "to", "for", "of", "from", "with", "on", "at", "by",
})

_SKIP_REG = frozenset({
    "implicit", "per_dispatch_site", "per_provider_router",
    "per_llm_proxy_handler", "env_vars", "aiocache_decorator",
    "implicit_import", "per_service_container",
    "backend_and_frontend_each",
})


# ---------------------------------------------------------------------------
# Library API — canonical routing logic
# ---------------------------------------------------------------------------


def route_query(query: str, index_path: Path) -> RouteResult:
    """Route a query against a route-index.json.

    Args:
        query: The Glob pattern or Grep query string.
        index_path: Path to route-index.json.

    Returns:
        RouteResult with the best hint, doc, and match metadata.
    """
    fallback = RouteResult(
        hint="Codebase context in CLAUDE.md. For deeper context: agent-docs/agent-context.md",
        doc="agent-docs/agent-context.md",
        subsystem="",
        match_type="fallback",
        artifact_kind="fallback",
    )

    if not query or not index_path.exists():
        return fallback

    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback

    version = data.get("version", 1)
    if version < 2:
        # v1 fallback — use old routes[] format
        return _route_v1(query, data, fallback)

    # Update fallback hint from index
    fb_hint = data.get("fallback_hint", fallback.hint)
    fallback = RouteResult(
        hint=fb_hint, doc="agent-docs/agent-context.md",
        subsystem="", match_type="fallback", artifact_kind="fallback",
    )

    subsystem_routes = data.get("subsystem_routes", [])
    pattern_routes = data.get("pattern_routes", [])

    # --- Priority 1: directory_prefix ---
    result = _match_directory_prefix(query, subsystem_routes)
    if result:
        return result

    # --- Priority 2: pattern_route ---
    result = _match_pattern_route(query, pattern_routes)
    if result:
        return result

    # --- Priority 3: common_task ---
    result = _match_common_task(query, subsystem_routes)
    if result:
        return result

    return fallback


def _match_directory_prefix(
    query: str, subsystem_routes: list[dict],
) -> RouteResult | None:
    """Match query against subsystem owns_paths. Longest prefix wins."""
    best_match: tuple[int, dict] | None = None  # (prefix_len, route)

    for route in subsystem_routes:
        for path in route.get("owns_paths", []):
            p = path.rstrip("/")
            if not p:
                continue
            # Match: query starts with the path (exact or as a prefix)
            if query == p or query.startswith(p + "/"):
                match_len = len(p)
                if best_match is None or match_len > best_match[0]:
                    best_match = (match_len, route)

    if best_match:
        route = best_match[1]
        name = route.get("subsystem", "")
        doc = route.get("doc_path", "")
        role = route.get("role", name)
        return RouteResult(
            hint=f"Subsystem: {name}. {role}. See {doc}.",
            doc=doc,
            subsystem=name,
            match_type="directory_prefix",
            artifact_kind="subsystem_doc",
        )

    return None


def _match_pattern_route(
    query: str, pattern_routes: list[dict],
) -> RouteResult | None:
    """Match query against pattern template/registration basenames."""
    query_lower = query.lower()

    for route in pattern_routes:
        pattern_name = route.get("pattern_name", "")
        template = route.get("template_file", "")
        registration = route.get("registration", "")

        # Collect matchable fragments from the pattern
        fragments: list[str] = []

        # Pattern name (hyphenated → check as-is and with underscores)
        if pattern_name:
            fragments.append(pattern_name.lower())
            fragments.append(pattern_name.lower().replace("-", "_"))

        # Template file: extract both basename and function name if present
        # Format: "path/to/file.py:function_name" or just "path/to/file.py"
        if template:
            parts = template.split(":")
            basename = PurePosixPath(parts[0]).stem
            if len(basename) >= 4:
                fragments.append(basename.lower())
            # Function name after colon (e.g., "middleware.py:chat_web_search_handler")
            if len(parts) > 1 and len(parts[1]) >= 4:
                fragments.append(parts[1].lower())

        # Registration: extract basename and function name
        if registration:
            reg_parts = registration.split(":")
            reg_base = PurePosixPath(reg_parts[0]).stem
            if len(reg_base) >= 4 and reg_base.lower() not in _SKIP_REG:
                fragments.append(reg_base.lower())
            if len(reg_parts) > 1 and len(reg_parts[1]) >= 4:
                fragments.append(reg_parts[1].lower())

        # Check if query contains any fragment
        for frag in fragments:
            if frag in query_lower:
                doc_anchor = route.get("doc_anchor", f"patterns.md#{pattern_name}")
                subsystem = route.get("subsystem", "")
                return RouteResult(
                    hint=f"Pattern: {pattern_name}. See agent-docs/{doc_anchor}.",
                    doc=f"agent-docs/{doc_anchor}",
                    subsystem=subsystem,
                    match_type="pattern_route",
                    artifact_kind="patterns",
                )

    return None


def _match_common_task(
    query: str, subsystem_routes: list[dict],
) -> RouteResult | None:
    """Match query against subsystem common_tasks using keyword overlap."""
    query_lower = query.lower()
    query_words = set(re.findall(r"[a-z]{3,}", query_lower))
    # Remove stop words
    query_words -= _STOP_WORDS

    if not query_words:
        return None

    for route in subsystem_routes:
        for task in route.get("common_tasks", []):
            task_lower = task.lower()
            task_words = set(re.findall(r"[a-z]{3,}", task_lower))
            task_words -= _STOP_WORDS

            # Require at least one meaningful keyword overlap
            overlap = query_words & task_words
            if overlap:
                name = route.get("subsystem", "")
                doc = route.get("doc_path", "")
                return RouteResult(
                    hint=f"Subsystem: {name}. See {doc}.",
                    doc=doc,
                    subsystem=name,
                    match_type="common_task",
                    artifact_kind="subsystem_doc",
                )

    return None


def _route_v1(query: str, data: dict, fallback: RouteResult) -> RouteResult:
    """Fallback routing for v1 route-index format."""
    for route in data.get("routes", []):
        if route.get("match_type") == "directory_prefix":
            pattern = route.get("pattern", "")
            if query.startswith(pattern):
                return RouteResult(
                    hint=route.get("hint", ""),
                    doc=route.get("doc_path", ""),
                    subsystem=route.get("subsystem", ""),
                    match_type="directory_prefix",
                    artifact_kind="subsystem_doc",
                )
    return fallback


# ---------------------------------------------------------------------------
# Hook script generation — canonical source for the installed hook
# ---------------------------------------------------------------------------

# Template for the self-contained stdlib-only routing script embedded in the
# bash hook. %%STOP_WORDS%% and %%SKIP_REG%% are replaced with the canonical
# constants above by render_hook_routing_script().
#
# This template mirrors the algorithm in route_query() above but uses only
# stdlib (json, re, sys, os.path) so the installed hook works without
# pensieve being importable. This is co-located duplication with generated
# delivery — not a single implementation. Changes to routing policy must
# be reflected in both route_query() and this template.
_HOOK_ROUTING_TEMPLATE = '''\
import json, re, sys, os.path
query = sys.argv[1] if len(sys.argv) > 1 else ''
if not query:
    print(json.dumps({'hint':'','doc':'','subsystem':'','match_type':'fallback','artifact_kind':'fallback'}))
    sys.exit(0)
try:
    with open('agent-docs/route-index.json') as f:
        idx = json.load(f)
except Exception:
    print(json.dumps({'hint':'','doc':'','subsystem':'','match_type':'fallback','artifact_kind':'fallback'}))
    sys.exit(0)

v = idx.get('version', 1)
ql = query.lower()
result = None

# --- Priority 1: directory_prefix (longest match wins) ---
if v >= 2:
    best = None
    for r in idx.get('subsystem_routes', []):
        for p in r.get('owns_paths', []):
            p = p.rstrip('/')
            if p and (query == p or query.startswith(p + '/')):
                if best is None or len(p) > best[0]:
                    best = (len(p), r)
    if best:
        r = best[1]
        nm = r.get('subsystem','')
        role = r.get('role', nm)
        doc = r.get('doc_path','')
        result = {'hint': f'Subsystem: {nm}. {role}. See {doc}.', 'doc': doc, 'subsystem': nm, 'match_type': 'directory_prefix', 'artifact_kind': 'subsystem_doc'}

# --- Priority 2: pattern_route (fragment match) ---
if not result and v >= 2:
    skip = %%SKIP_REG%%
    for pr in idx.get('pattern_routes', []):
        pn = pr.get('pattern_name','')
        frags = []
        if pn:
            frags.append(pn.lower())
            frags.append(pn.lower().replace('-','_'))
        tf = pr.get('template_file','')
        if tf:
            parts = tf.split(':')
            stem = os.path.splitext(os.path.basename(parts[0]))[0]
            if len(stem) >= 4:
                frags.append(stem.lower())
            if len(parts) > 1 and len(parts[1]) >= 4:
                frags.append(parts[1].lower())
        rg = pr.get('registration','')
        if rg:
            rp = rg.split(':')
            rs = os.path.splitext(os.path.basename(rp[0]))[0]
            if len(rs) >= 4 and rs.lower() not in skip:
                frags.append(rs.lower())
            if len(rp) > 1 and len(rp[1]) >= 4:
                frags.append(rp[1].lower())
        for fg in frags:
            if fg in ql:
                da = pr.get('doc_anchor', f'patterns.md#{pn}')
                result = {'hint': f'Pattern: {pn}. See agent-docs/{da}.', 'doc': f'agent-docs/{da}', 'subsystem': pr.get('subsystem',''), 'match_type': 'pattern_route', 'artifact_kind': 'patterns'}
                break
        if result:
            break

# --- Priority 3: common_task (keyword overlap) ---
if not result and v >= 2:
    stops = %%STOP_WORDS%%
    qw = set(w for w in re.findall(r'[a-z]{3,}', ql) if w not in stops)
    if qw:
        for r in idx.get('subsystem_routes', []):
            for task in r.get('common_tasks', []):
                tw = set(w for w in re.findall(r'[a-z]{3,}', task.lower()) if w not in stops)
                if qw & tw:
                    nm = r.get('subsystem','')
                    doc = r.get('doc_path','')
                    result = {'hint': f'Subsystem: {nm}. See {doc}.', 'doc': doc, 'subsystem': nm, 'match_type': 'common_task', 'artifact_kind': 'subsystem_doc'}
                    break
            if result:
                break

# --- v1 fallback ---
if not result and v < 2:
    for r in idx.get('routes', []):
        if r.get('match_type') == 'directory_prefix':
            p = r.get('pattern','')
            if p and (query == p or query.startswith(p + '/')):
                result = {'hint': r.get('hint',''), 'doc': r.get('doc_path',''), 'subsystem': r.get('subsystem',''), 'match_type': 'directory_prefix', 'artifact_kind': 'subsystem_doc'}
                break

if not result:
    fb = idx.get('fallback_hint', '')
    result = {'hint': fb, 'doc': 'agent-docs/agent-context.md', 'subsystem': '', 'match_type': 'fallback', 'artifact_kind': 'fallback'}

print(json.dumps(result))
'''


def _set_literal(s: frozenset) -> str:
    """Render a frozenset as a deterministic Python set literal string."""
    return '{' + ', '.join(repr(w) for w in sorted(s)) + '}'


def render_hook_routing_script() -> str:
    """Render the self-contained stdlib-only routing script for the bash hook.

    Returns a Python script string that:
    - Uses only stdlib (json, re, sys, os.path)
    - Implements the same priority order as route_query()
    - Embeds canonical constants (_STOP_WORDS, _SKIP_REG) from this module

    This is the ONLY way the hook routing script should be produced.
    Do not hand-maintain a separate copy in hooks.py or elsewhere.
    """
    return (_HOOK_ROUTING_TEMPLATE
        .replace('%%STOP_WORDS%%', _set_literal(_STOP_WORDS))
        .replace('%%SKIP_REG%%', _set_literal(_SKIP_REG)))
