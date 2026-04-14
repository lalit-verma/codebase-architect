"""Tests for route-index v2 builder (Bx1a).

Covers:
  - Parsing routing-map.md YAML block
  - Subsystem route extraction
  - Pattern route extraction
  - Recursive subsystem metadata from .analysis-state.md
  - Deterministic output ordering
  - Malformed routing-map failure behavior
  - pensieve wire refreshes route-index
  - pensieve wire warns when routing-map is missing
  - Expanded telemetry fields in hook script
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest

from pensieve.routing import (
    RouteIndex,
    SubsystemRoute,
    PatternRoute,
    build_route_index,
    save_route_index,
    _extract_yaml_block,
    _parse_routing_map,
    _parse_recursion_from_analysis_state,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_SAMPLE_ROUTING_MAP = """\
# Routing Map

> Machine-readable routing.

```yaml
subsystem_routing:
  - name: api-routers
    doc: agent-docs/subsystems/api-routers.md
    role: HTTP request handling
    owns_paths:
      - backend/open_webui/routers
    key_files:
      - backend/open_webui/routers/chats.py
    common_tasks:
      - "Add new API endpoint"

  - name: data-models
    doc: agent-docs/subsystems/data-models.md
    role: ORM layer
    owns_paths:
      - backend/open_webui/models
      - backend/open_webui/internal
    key_files:
      - backend/open_webui/internal/db.py
    common_tasks:
      - "Add new model"

pattern_routing:
  - pattern: router-canonical-crud
    subsystem: api-routers
    template_file: backend/open_webui/routers/chats.py
    registration: backend/open_webui/main.py:1190
    test_template: backend/open_webui/test/apps/webui/routers/test_chats.py
    file_count: 31

  - pattern: model-triplet
    subsystem: data-models
    template_file: backend/open_webui/models/users.py
    registration: implicit
    file_count: 23
```
"""

_SAMPLE_ANALYSIS_STATE = """\
---
phase_completed: 2
subsystems_completed:
  - api-routers
  - data-models
  - frontend-sveltekit (recursive: chat-ui, app-shell, admin)
---

Checkpoint content here.
"""


def _write_routing_map(tmp_path: Path, content: str = _SAMPLE_ROUTING_MAP) -> Path:
    path = tmp_path / "routing-map.md"
    path.write_text(content, encoding="utf-8")
    return path


def _write_analysis_state(tmp_path: Path, content: str = _SAMPLE_ANALYSIS_STATE) -> Path:
    path = tmp_path / ".analysis-state.md"
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# YAML extraction
# ---------------------------------------------------------------------------


class TestYAMLExtraction:

    def test_extracts_yaml_block(self):
        content = "# Title\n\n```yaml\nfoo: bar\n```\n\nMore text."
        result = _extract_yaml_block(content)
        assert result is not None
        assert "foo: bar" in result

    def test_no_yaml_block(self):
        result = _extract_yaml_block("# No yaml here\nJust text.")
        assert result is None

    def test_multiple_yaml_blocks_takes_first(self):
        content = "```yaml\nfirst: 1\n```\n\n```yaml\nsecond: 2\n```"
        result = _extract_yaml_block(content)
        assert "first" in result


# ---------------------------------------------------------------------------
# Routing-map parsing
# ---------------------------------------------------------------------------


class TestParseRoutingMap:

    def test_parses_subsystems(self, tmp_path):
        path = _write_routing_map(tmp_path)
        subs, pats, errors = _parse_routing_map(path)
        assert len(subs) == 2
        assert subs[0]["name"] == "api-routers"
        assert subs[1]["name"] == "data-models"

    def test_parses_patterns(self, tmp_path):
        path = _write_routing_map(tmp_path)
        subs, pats, errors = _parse_routing_map(path)
        assert len(pats) == 2
        assert pats[0]["pattern"] == "router-canonical-crud"

    def test_missing_file(self, tmp_path):
        subs, pats, errors = _parse_routing_map(tmp_path / "nonexistent.md")
        assert len(errors) == 1
        assert "not found" in errors[0].lower()

    def test_no_yaml_block(self, tmp_path):
        path = tmp_path / "routing-map.md"
        path.write_text("# No yaml\nJust text.")
        subs, pats, errors = _parse_routing_map(path)
        assert len(errors) == 1
        assert "No ```yaml```" in errors[0]

    def test_malformed_yaml(self, tmp_path):
        path = tmp_path / "routing-map.md"
        path.write_text("```yaml\n{{{invalid yaml\n```")
        subs, pats, errors = _parse_routing_map(path)
        assert len(errors) == 1
        assert "YAML parse error" in errors[0]


# ---------------------------------------------------------------------------
# Recursion from analysis-state
# ---------------------------------------------------------------------------


class TestParseRecursion:

    def test_extracts_children(self, tmp_path):
        path = _write_analysis_state(tmp_path)
        result = _parse_recursion_from_analysis_state(path)
        assert "frontend-sveltekit" in result
        assert result["frontend-sveltekit"] == ["chat-ui", "app-shell", "admin"]

    def test_missing_file(self, tmp_path):
        result = _parse_recursion_from_analysis_state(tmp_path / "nope.md")
        assert result == {}

    def test_inline_recursion_format(self, tmp_path):
        """The real format: 'name (recursive: child1, child2)' in subsystems_completed."""
        path = tmp_path / ".analysis-state.md"
        path.write_text(
            "---\n"
            "phase_completed: 2\n"
            "subsystems_completed:\n"
            "  - api-routers\n"
            "  - retrieval-rag (recursive: vector, web-search, loaders, rerankers)\n"
            "  - frontend-sveltekit (recursive: app-shell, chat-ui, admin)\n"
            "---\n"
        )
        result = _parse_recursion_from_analysis_state(path)
        assert "retrieval-rag" in result
        assert result["retrieval-rag"] == ["vector", "web-search", "loaders", "rerankers"]
        assert "frontend-sveltekit" in result
        assert result["frontend-sveltekit"] == ["app-shell", "chat-ui", "admin"]

    def test_no_recursion_data(self, tmp_path):
        path = tmp_path / ".analysis-state.md"
        path.write_text("---\nphase_completed: 1\n---\nNo recursion.")
        result = _parse_recursion_from_analysis_state(path)
        assert result == {}


# ---------------------------------------------------------------------------
# Route-index building
# ---------------------------------------------------------------------------


class TestBuildRouteIndex:

    def test_builds_complete_index(self, tmp_path):
        rm = _write_routing_map(tmp_path)
        idx = build_route_index(rm)
        assert idx.version == 2
        assert len(idx.subsystem_routes) == 2
        assert len(idx.pattern_routes) == 2
        assert len(idx.errors) == 0

    def test_subsystem_fields(self, tmp_path):
        rm = _write_routing_map(tmp_path)
        idx = build_route_index(rm)
        api = [r for r in idx.subsystem_routes if r.subsystem == "api-routers"][0]
        assert api.doc_path == "agent-docs/subsystems/api-routers.md"
        assert api.role == "HTTP request handling"
        assert "backend/open_webui/routers" in api.owns_paths
        assert "backend/open_webui/routers/chats.py" in api.key_files
        assert "Add new API endpoint" in api.common_tasks
        # brief_paths initialized from owns_paths
        assert api.brief_paths == api.owns_paths
        assert "backend/open_webui/routers" in api.brief_paths

    def test_pattern_fields(self, tmp_path):
        rm = _write_routing_map(tmp_path)
        idx = build_route_index(rm)
        crud = [p for p in idx.pattern_routes if p.pattern_name == "router-canonical-crud"][0]
        assert crud.subsystem == "api-routers"
        assert crud.template_file == "backend/open_webui/routers/chats.py"
        assert crud.registration == "backend/open_webui/main.py:1190"
        assert "router-canonical-crud" in crud.doc_anchor

    def test_deterministic_ordering(self, tmp_path):
        rm = _write_routing_map(tmp_path)
        idx1 = build_route_index(rm)
        idx2 = build_route_index(rm)
        assert idx1.to_json() == idx2.to_json()

    def test_subsystems_sorted_by_name(self, tmp_path):
        rm = _write_routing_map(tmp_path)
        idx = build_route_index(rm)
        names = [r.subsystem for r in idx.subsystem_routes]
        assert names == sorted(names)

    def test_patterns_sorted_by_name(self, tmp_path):
        rm = _write_routing_map(tmp_path)
        idx = build_route_index(rm)
        names = [r.pattern_name for r in idx.pattern_routes]
        assert names == sorted(names)

    def test_fallbacks_present(self, tmp_path):
        rm = _write_routing_map(tmp_path)
        idx = build_route_index(rm)
        assert "nano" in idx.fallbacks
        assert "agent_context" in idx.fallbacks
        assert idx.fallback_hint != ""

    def test_recursive_children_from_analysis_state(self, tmp_path):
        rm = _write_routing_map(tmp_path)
        # Add a subsystem matching the recursion parent
        content = _SAMPLE_ROUTING_MAP.replace(
            "  - name: api-routers",
            "  - name: frontend-sveltekit\n"
            "    owns_paths:\n"
            "      - src/\n"
            "    common_tasks:\n"
            "      - Add component\n\n"
            "  - name: api-routers",
        )
        rm.write_text(content)
        state = _write_analysis_state(tmp_path)
        idx = build_route_index(rm, state)
        fe = [r for r in idx.subsystem_routes if r.subsystem == "frontend-sveltekit"]
        assert len(fe) == 1
        assert "chat-ui" in fe[0].recursive_children

    def test_malformed_routing_map_returns_errors(self, tmp_path):
        path = tmp_path / "routing-map.md"
        path.write_text("no yaml here")
        idx = build_route_index(path)
        assert len(idx.errors) > 0
        assert len(idx.subsystem_routes) == 0

    def test_generated_from_field(self, tmp_path):
        rm = _write_routing_map(tmp_path)
        idx = build_route_index(rm)
        assert "routing_map" in idx.generated_from


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------


class TestSaveRouteIndex:

    def test_writes_valid_json(self, tmp_path):
        rm = _write_routing_map(tmp_path)
        idx = build_route_index(rm)
        path = save_route_index(idx, tmp_path / "route-index.json")
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["version"] == 2
        assert len(data["subsystem_routes"]) == 2


# ---------------------------------------------------------------------------
# Wire integration
# ---------------------------------------------------------------------------


class TestWireRefreshesRouteIndex:

    def test_wire_generates_route_index(self, tmp_path):
        from pensieve.cli import main

        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()
        (ad / "agent-context-nano.md").write_text("# Nano\n")
        _write_routing_map(ad)

        result = main(["wire", "--repo", str(repo)])
        assert result == 0

        ri = ad / "route-index.json"
        assert ri.exists()
        data = json.loads(ri.read_text())
        assert data["version"] == 2
        assert len(data["subsystem_routes"]) == 2

    def test_wire_warns_without_routing_map(self, capsys, tmp_path):
        from pensieve.cli import main

        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()
        (ad / "agent-context-nano.md").write_text("# Nano\n")
        # No routing-map.md

        result = main(["wire", "--repo", str(repo)])
        assert result == 0  # wire still succeeds
        captured = capsys.readouterr()
        assert "routing-map.md not found" in captured.out


# ---------------------------------------------------------------------------
# Telemetry schema
# ---------------------------------------------------------------------------


class TestExpandedTelemetry:

    def test_hook_script_has_expanded_fields(self):
        from pensieve.hooks import HOOK_SCRIPT
        assert "'artifact_kind'" in HOOK_SCRIPT
        assert "'route_match_type'" in HOOK_SCRIPT
        assert "'target_subsystem'" in HOOK_SCRIPT
        assert "'target_doc'" in HOOK_SCRIPT
        assert "'session_id'" in HOOK_SCRIPT
        assert "'brief_suggested'" in HOOK_SCRIPT
        assert "'brief_mode'" in HOOK_SCRIPT

    def test_hook_script_has_self_contained_routing(self):
        """Hook script embeds routing logic inline (no pensieve import needed)."""
        from pensieve.hooks import HOOK_SCRIPT
        assert "subsystem_routes" in HOOK_SCRIPT
        assert "owns_paths" in HOOK_SCRIPT
        assert "pattern_routes" in HOOK_SCRIPT
        assert "directory_prefix" in HOOK_SCRIPT
        # Must NOT import pensieve (system python may not have it)
        assert "from pensieve" not in HOOK_SCRIPT
        assert "import pensieve" not in HOOK_SCRIPT

    def test_hook_script_derived_from_canonical_source(self):
        """HOOK_SCRIPT routing section is generated from route.py, not hand-maintained."""
        from pensieve.hooks import HOOK_SCRIPT
        from pensieve.route import render_hook_routing_script
        rendered = render_hook_routing_script()
        # The rendered routing script must appear verbatim in HOOK_SCRIPT
        assert rendered in HOOK_SCRIPT

    def test_render_contains_canonical_stop_words(self):
        """Rendered hook script contains all canonical stop words from route.py."""
        from pensieve.route import render_hook_routing_script, _STOP_WORDS
        rendered = render_hook_routing_script()
        for word in _STOP_WORDS:
            assert repr(word) in rendered, f"Stop word {word!r} missing from rendered script"

    def test_render_contains_canonical_skip_reg(self):
        """Rendered hook script contains all canonical skip registrations from route.py."""
        from pensieve.route import render_hook_routing_script, _SKIP_REG
        rendered = render_hook_routing_script()
        for reg in _SKIP_REG:
            assert repr(reg) in rendered, f"Skip registration {reg!r} missing from rendered script"

    def test_render_no_pensieve_import(self):
        """Rendered routing script must not import pensieve."""
        from pensieve.route import render_hook_routing_script
        rendered = render_hook_routing_script()
        assert "from pensieve" not in rendered
        assert "import pensieve" not in rendered

    def test_render_no_placeholders_remaining(self):
        """Rendered script must not contain unsubstituted placeholders."""
        from pensieve.route import render_hook_routing_script
        rendered = render_hook_routing_script()
        assert "%%" not in rendered


# ---------------------------------------------------------------------------
# Routing Lock
# ---------------------------------------------------------------------------


from pensieve.routing import (
    load_routing_lock,
    derive_lock_from_index,
    save_routing_lock,
    merge_candidate_with_lock,
    update_lock_with_new_entries,
    ReconciliationReport,
)


class TestRoutingLockFirstRun:
    """First run: no lock exists, derive from candidate."""

    def test_first_run_creates_lock(self, tmp_path):
        rm = _write_routing_map(tmp_path)
        idx = build_route_index(rm)
        lock = derive_lock_from_index(idx)

        assert lock["version"] == 1
        assert "api-routers" in lock["subsystems"]
        assert "data-models" in lock["subsystems"]
        assert "router-canonical-crud" in lock["patterns"]
        assert "model-triplet" in lock["patterns"]

    def test_lock_contains_semantic_fields_only(self, tmp_path):
        rm = _write_routing_map(tmp_path)
        idx = build_route_index(rm)
        lock = derive_lock_from_index(idx)

        api = lock["subsystems"]["api-routers"]
        assert "role" in api
        assert "common_tasks" in api
        assert "brief_paths" in api
        # Structural fields must NOT be in the lock
        assert "owns_paths" not in api
        assert "key_files" not in api
        assert "doc_path" not in api

    def test_lock_preserves_values(self, tmp_path):
        rm = _write_routing_map(tmp_path)
        idx = build_route_index(rm)
        lock = derive_lock_from_index(idx)

        api = lock["subsystems"]["api-routers"]
        assert api["role"] == "HTTP request handling"
        assert api["common_tasks"] == ["Add new API endpoint"]
        assert api["brief_paths"] == ["backend/open_webui/routers"]

    def test_save_and_load_roundtrip(self, tmp_path):
        rm = _write_routing_map(tmp_path)
        idx = build_route_index(rm)
        lock = derive_lock_from_index(idx)

        lock_path = tmp_path / "routing-lock.yaml"
        save_routing_lock(lock, lock_path)
        status, loaded = load_routing_lock(lock_path)

        assert status == "ok"
        assert loaded is not None
        assert loaded["version"] == 1
        assert loaded["subsystems"]["api-routers"]["role"] == "HTTP request handling"
        assert loaded["patterns"]["model-triplet"]["pattern_name"] == "model-triplet"

    def test_save_is_deterministic(self, tmp_path):
        rm = _write_routing_map(tmp_path)
        idx = build_route_index(rm)
        lock = derive_lock_from_index(idx)

        p1 = tmp_path / "lock1.yaml"
        p2 = tmp_path / "lock2.yaml"
        save_routing_lock(lock, p1)
        save_routing_lock(lock, p2)
        assert p1.read_text() == p2.read_text()


class TestRoutingLockMerge:
    """Rerun: merge candidate with existing lock."""

    def _make_lock(self) -> dict:
        """A lock with known stable values."""
        return {
            "version": 1,
            "subsystems": {
                "api-routers": {
                    "role": "HTTP request handling",
                    "common_tasks": ["Add new API endpoint", "Register new router"],
                    "brief_paths": ["backend/open_webui/routers"],
                },
                "data-models": {
                    "role": "ORM layer",
                    "common_tasks": ["Add new model"],
                    "brief_paths": ["backend/open_webui/models"],
                },
            },
            "patterns": {
                "router-canonical-crud": {
                    "pattern_name": "router-canonical-crud",
                },
                "model-triplet": {
                    "pattern_name": "model-triplet",
                },
            },
        }

    def test_locked_role_preserved_over_drifted_candidate(self, tmp_path):
        """Lock's role wins when candidate has different role text."""
        # Candidate has drifted role
        drifted_map = _SAMPLE_ROUTING_MAP.replace(
            "role: HTTP request handling",
            "role: API endpoint handlers",
        )
        rm = _write_routing_map(tmp_path, drifted_map)
        candidate = build_route_index(rm)
        lock = self._make_lock()

        merged, report = merge_candidate_with_lock(candidate, lock)

        api = [r for r in merged.subsystem_routes if r.subsystem == "api-routers"][0]
        assert api.role == "HTTP request handling"  # Lock wins
        assert report.locked_role_overrides == 1

    def test_locked_common_tasks_preserved(self, tmp_path):
        """Lock's common_tasks wins when candidate has different wording."""
        # Candidate has drifted common_tasks
        drifted_map = _SAMPLE_ROUTING_MAP.replace(
            '"Add new API endpoint"',
            '"Create a new REST endpoint"',
        )
        rm = _write_routing_map(tmp_path, drifted_map)
        candidate = build_route_index(rm)
        lock = self._make_lock()

        merged, report = merge_candidate_with_lock(candidate, lock)

        api = [r for r in merged.subsystem_routes if r.subsystem == "api-routers"][0]
        assert "Add new API endpoint" in api.common_tasks
        assert "Register new router" in api.common_tasks
        assert report.locked_common_tasks_overrides == 1

    def test_locked_brief_paths_preserved(self, tmp_path):
        """Lock's brief_paths wins over candidate's owns_paths fallback."""
        rm = _write_routing_map(tmp_path)
        candidate = build_route_index(rm)
        lock = self._make_lock()

        merged, report = merge_candidate_with_lock(candidate, lock)

        api = [r for r in merged.subsystem_routes if r.subsystem == "api-routers"][0]
        assert api.brief_paths == ["backend/open_webui/routers"]

    def test_fresh_structural_fields_from_candidate(self, tmp_path):
        """Structural fields always come from candidate, not lock."""
        # Candidate has updated key_files
        updated_map = _SAMPLE_ROUTING_MAP.replace(
            "backend/open_webui/routers/chats.py",
            "backend/open_webui/routers/new_file.py",
        )
        rm = _write_routing_map(tmp_path, updated_map)
        candidate = build_route_index(rm)
        lock = self._make_lock()

        merged, _ = merge_candidate_with_lock(candidate, lock)

        api = [r for r in merged.subsystem_routes if r.subsystem == "api-routers"][0]
        # key_files should be from candidate (fresh)
        assert "backend/open_webui/routers/new_file.py" in api.key_files

    def test_new_subsystem_included(self, tmp_path):
        """Subsystem in candidate but not lock is included as new."""
        # Add a subsystem to the candidate
        extended_map = _SAMPLE_ROUTING_MAP.replace(
            "pattern_routing:",
            "  - name: new-subsystem\n"
            "    role: Brand new\n"
            "    owns_paths:\n"
            "      - src/new/\n"
            "    common_tasks:\n"
            "      - Do new thing\n\n"
            "pattern_routing:",
        )
        rm = _write_routing_map(tmp_path, extended_map)
        candidate = build_route_index(rm)
        lock = self._make_lock()

        merged, report = merge_candidate_with_lock(candidate, lock)

        assert report.subsystems_new == 1
        assert "new-subsystem" in report.new_subsystems
        new = [r for r in merged.subsystem_routes if r.subsystem == "new-subsystem"]
        assert len(new) == 1
        assert new[0].role == "Brand new"

    def test_stale_subsystem_excluded(self, tmp_path):
        """Subsystem in lock but not candidate is excluded from route-index."""
        rm = _write_routing_map(tmp_path)
        candidate = build_route_index(rm)
        # Lock has an extra subsystem that candidate doesn't
        lock = self._make_lock()
        lock["subsystems"]["old-removed"] = {
            "role": "Deprecated",
            "common_tasks": ["Legacy task"],
            "brief_paths": [],
        }

        merged, report = merge_candidate_with_lock(candidate, lock)

        assert report.subsystems_stale == 1
        assert "old-removed" in report.stale_subsystems
        # Stale entry must NOT be in route-index
        names = [r.subsystem for r in merged.subsystem_routes]
        assert "old-removed" not in names

    def test_stale_pattern_excluded(self, tmp_path):
        """Pattern in lock but not candidate is excluded from route-index."""
        rm = _write_routing_map(tmp_path)
        candidate = build_route_index(rm)
        lock = self._make_lock()
        lock["patterns"]["old-pattern"] = {"pattern_name": "old-pattern"}

        merged, report = merge_candidate_with_lock(candidate, lock)

        assert report.patterns_stale == 1
        assert "old-pattern" in report.stale_patterns
        names = [p.pattern_name for p in merged.pattern_routes]
        assert "old-pattern" not in names

    def test_new_entries_auto_appended_to_lock(self, tmp_path):
        """New subsystems and patterns are auto-appended to the lock."""
        extended_map = _SAMPLE_ROUTING_MAP.replace(
            "pattern_routing:",
            "  - name: fresh-subsystem\n"
            "    role: Fresh\n"
            "    owns_paths:\n"
            "      - src/fresh/\n"
            "    common_tasks:\n"
            "      - Fresh task\n\n"
            "pattern_routing:",
        )
        rm = _write_routing_map(tmp_path, extended_map)
        candidate = build_route_index(rm)
        lock = self._make_lock()

        merged, report = merge_candidate_with_lock(candidate, lock)
        updated = update_lock_with_new_entries(lock, merged, report)

        assert "fresh-subsystem" in updated["subsystems"]
        assert updated["subsystems"]["fresh-subsystem"]["role"] == "Fresh"

    def test_deterministic_output(self, tmp_path):
        """Same inputs produce same merged output."""
        rm = _write_routing_map(tmp_path)
        candidate = build_route_index(rm)
        lock = self._make_lock()

        merged1, _ = merge_candidate_with_lock(candidate, lock)
        merged2, _ = merge_candidate_with_lock(candidate, lock)
        assert merged1.to_json() == merged2.to_json()


class TestRoutingLockMalformed:
    """Malformed lock: warn and do not overwrite."""

    def test_missing_lock_returns_missing(self, tmp_path):
        status, data = load_routing_lock(tmp_path / "nonexistent.yaml")
        assert status == "missing"
        assert data is None

    def test_malformed_yaml_returns_malformed(self, tmp_path):
        lock_path = tmp_path / "lock.yaml"
        lock_path.write_text("{{{not yaml")
        status, data = load_routing_lock(lock_path)
        assert status == "malformed"
        assert data is None

    def test_non_dict_yaml_returns_malformed(self, tmp_path):
        lock_path = tmp_path / "lock.yaml"
        lock_path.write_text("- just\n- a\n- list")
        status, data = load_routing_lock(lock_path)
        assert status == "malformed"
        assert data is None

    def test_malformed_lock_not_overwritten_by_wire(self, capsys, tmp_path):
        """Wire with malformed lock should warn, not silently overwrite."""
        from pensieve.cli import main

        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()
        (ad / "agent-context-nano.md").write_text("# Nano\n")
        _write_routing_map(ad)

        # Create a malformed lock
        (ad / "routing-lock.yaml").write_text("{{{broken yaml")

        result = main(["wire", "--repo", str(repo)])
        assert result == 0

        captured = capsys.readouterr()
        assert "malformed" in captured.out.lower()

        # The malformed lock must NOT be overwritten
        assert "{{{broken yaml" in (ad / "routing-lock.yaml").read_text()


class TestWireWithLock:
    """Integration: pensieve wire creates/uses routing lock."""

    def test_wire_creates_lock_on_first_run(self, capsys, tmp_path):
        from pensieve.cli import main

        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()
        (ad / "agent-context-nano.md").write_text("# Nano\n")
        _write_routing_map(ad)

        result = main(["wire", "--repo", str(repo)])
        assert result == 0

        lock_path = ad / "routing-lock.yaml"
        assert lock_path.exists()

        captured = capsys.readouterr()
        assert "Route Lock: created" in captured.out
        assert "Locked: 2 subsystems, 2 patterns" in captured.out

    def test_wire_uses_lock_on_rerun(self, capsys, tmp_path):
        from pensieve.cli import main
        import yaml as yaml_mod

        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()
        (ad / "agent-context-nano.md").write_text("# Nano\n")
        _write_routing_map(ad)

        # First wire — creates lock
        main(["wire", "--repo", str(repo)])

        # Drift the routing-map (change role text)
        drifted = _SAMPLE_ROUTING_MAP.replace(
            "role: HTTP request handling",
            "role: REST API modules",
        )
        (ad / "routing-map.md").write_text(drifted)

        # Second wire — should use lock
        result = main(["wire", "--repo", str(repo)])
        assert result == 0

        captured = capsys.readouterr()
        assert "Route Lock: applied" in captured.out
        assert "matched" in captured.out

        # Route-index should have the LOCKED role, not the drifted one
        ri = json.loads((ad / "route-index.json").read_text())
        api = [s for s in ri["subsystem_routes"] if s["subsystem"] == "api-routers"][0]
        assert api["role"] == "HTTP request handling"  # Lock preserved

    def test_wire_reports_new_and_stale(self, capsys, tmp_path):
        from pensieve.cli import main

        repo = tmp_path / "repo"
        repo.mkdir()
        ad = repo / "agent-docs"
        ad.mkdir()
        (ad / "agent-context-nano.md").write_text("# Nano\n")
        _write_routing_map(ad)

        # First wire
        main(["wire", "--repo", str(repo)])

        # Change routing-map: add a new subsystem, remove data-models
        changed = """\
# Routing Map

```yaml
subsystem_routing:
  - name: api-routers
    role: REST handlers
    owns_paths:
      - backend/open_webui/routers
    common_tasks:
      - "Add new endpoint"
  - name: brand-new
    role: Something new
    owns_paths:
      - src/new/
    common_tasks:
      - "New task"

pattern_routing:
  - pattern: router-canonical-crud
    template_file: backend/open_webui/routers/chats.py
    registration: backend/open_webui/main.py:1190
```
"""
        (ad / "routing-map.md").write_text(changed)

        result = main(["wire", "--repo", str(repo)])
        assert result == 0

        captured = capsys.readouterr()
        assert "1 new" in captured.out
        assert "1 stale" in captured.out
        assert "brand-new" in captured.out
        assert "data-models" in captured.out
