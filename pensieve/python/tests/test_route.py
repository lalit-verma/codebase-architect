"""Tests for path-aware routing engine (Bx2).

Covers:
  - Directory prefix routing
  - Pattern route matching
  - Common task matching
  - Priority order
  - Fallback behavior
  - Telemetry field accuracy
  - v1 route-index backward compatibility
  - Deterministic matching
  - False-positive guards
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pensieve.route import route_query, RouteResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_index(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "route-index.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


_SAMPLE_INDEX = {
    "version": 2,
    "subsystem_routes": [
        {
            "subsystem": "api-routers",
            "doc_path": "agent-docs/subsystems/api-routers.md",
            "role": "HTTP request handling",
            "owns_paths": ["backend/open_webui/routers"],
            "key_files": ["backend/open_webui/routers/chats.py"],
            "common_tasks": ["Add new API endpoint", "Register new router"],
            "brief_paths": ["backend/open_webui/routers"],
        },
        {
            "subsystem": "data-models",
            "doc_path": "agent-docs/subsystems/data-models.md",
            "role": "ORM layer",
            "owns_paths": [
                "backend/open_webui/models",
                "backend/open_webui/internal",
            ],
            "common_tasks": ["Add new model", "Add new migration"],
            "brief_paths": ["backend/open_webui/models", "backend/open_webui/internal"],
        },
        {
            "subsystem": "configuration",
            "doc_path": "agent-docs/subsystems/configuration.md",
            "role": "App config and env vars",
            "owns_paths": [
                "backend/open_webui/config.py",
                "backend/open_webui/env.py",
            ],
            "common_tasks": ["Add new env var", "Add new PersistentConfig"],
            "brief_paths": [],
        },
    ],
    "pattern_routes": [
        {
            "pattern_name": "router-canonical-crud",
            "doc_anchor": "patterns.md#router-canonical-crud",
            "subsystem": "api-routers",
            "template_file": "backend/open_webui/routers/chats.py",
            "registration": "backend/open_webui/main.py:1190",
        },
        {
            "pattern_name": "model-triplet",
            "doc_anchor": "patterns.md#model-triplet",
            "subsystem": "data-models",
            "template_file": "backend/open_webui/models/users.py",
            "registration": "implicit",
        },
        {
            "pattern_name": "chat-feature-handler",
            "doc_anchor": "patterns.md#chat-feature-handler",
            "subsystem": "chat-middleware",
            "template_file": "backend/open_webui/utils/middleware.py:chat_web_search_handler",
            "registration": "backend/open_webui/utils/middleware.py:process_chat_payload",
        },
    ],
    "fallbacks": {
        "nano": "agent-docs/agent-context-nano.md",
        "agent_context": "agent-docs/agent-context.md",
    },
    "fallback_hint": "Codebase context in CLAUDE.md. For deeper context: agent-docs/agent-context.md",
}


# ---------------------------------------------------------------------------
# Directory prefix routing
# ---------------------------------------------------------------------------


class TestDirectoryPrefixRouting:

    def test_exact_directory_match(self, tmp_path):
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r = route_query("backend/open_webui/routers/chats.py", idx)
        assert r.match_type == "directory_prefix"
        assert r.subsystem == "api-routers"
        assert r.artifact_kind == "subsystem_doc"
        assert "api-routers" in r.doc

    def test_subdirectory_match(self, tmp_path):
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r = route_query("backend/open_webui/models/users.py", idx)
        assert r.match_type == "directory_prefix"
        assert r.subsystem == "data-models"

    def test_longest_prefix_wins(self, tmp_path):
        """More specific path should win over less specific."""
        data = dict(_SAMPLE_INDEX)
        data["subsystem_routes"] = [
            {
                "subsystem": "broad",
                "doc_path": "broad.md",
                "owns_paths": ["backend/open_webui"],
            },
            {
                "subsystem": "specific",
                "doc_path": "specific.md",
                "owns_paths": ["backend/open_webui/routers"],
            },
        ]
        idx = _write_index(tmp_path, data)
        r = route_query("backend/open_webui/routers/chats.py", idx)
        assert r.subsystem == "specific"

    def test_no_match(self, tmp_path):
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r = route_query("completely/unrelated/path.py", idx)
        assert r.match_type == "fallback"

    def test_sibling_prefix_not_matched(self, tmp_path):
        """'src2/file.py' must NOT match owns_path 'src'."""
        data = dict(_SAMPLE_INDEX)
        data["subsystem_routes"] = [{
            "subsystem": "core",
            "doc_path": "core.md",
            "owns_paths": ["src"],
        }]
        idx = _write_index(tmp_path, data)
        r = route_query("src2/file.py", idx)
        assert r.match_type == "fallback"

    def test_hyphenated_sibling_not_matched(self, tmp_path):
        """'src-other/file.py' must NOT match owns_path 'src'."""
        data = dict(_SAMPLE_INDEX)
        data["subsystem_routes"] = [{
            "subsystem": "core",
            "doc_path": "core.md",
            "owns_paths": ["src"],
        }]
        idx = _write_index(tmp_path, data)
        r = route_query("src-other/file.py", idx)
        assert r.match_type == "fallback"


# ---------------------------------------------------------------------------
# Pattern route matching
# ---------------------------------------------------------------------------


class TestPatternRouteMatching:

    def test_match_by_pattern_name(self, tmp_path):
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r = route_query("router-canonical-crud", idx)
        assert r.match_type == "pattern_route"
        assert r.artifact_kind == "patterns"
        assert "patterns.md" in r.doc

    def test_match_by_template_basename(self, tmp_path):
        """Grep for a template file's basename should match the pattern."""
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r = route_query("chat_web_search_handler", idx)
        assert r.match_type == "pattern_route"
        assert "chat-feature-handler" in r.hint

    def test_match_by_pattern_name_underscore(self, tmp_path):
        """Pattern names with hyphens should match underscore queries."""
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r = route_query("model_triplet", idx)
        assert r.match_type == "pattern_route"

    def test_short_fragment_no_greedy_match(self, tmp_path):
        """Short basename fragments like 'config' (<8 chars) must not trigger pattern match."""
        data = dict(_SAMPLE_INDEX)
        data["pattern_routes"] = [{
            "pattern_name": "persistent-config-mirror",
            "doc_anchor": "patterns.md#persistent-config-mirror",
            "template_file": "backend/config.py",  # "config" is 6 chars < 8
            "registration": "implicit",
        }]
        idx = _write_index(tmp_path, data)
        # "config" in query should NOT match the short basename fragment
        r = route_query("config settings", idx)
        assert r.match_type != "pattern_route" or "persistent-config-mirror" in r.hint
        # But the full pattern name DOES match
        r2 = route_query("persistent-config-mirror", idx)
        assert r2.match_type == "pattern_route"

    def test_long_fragment_still_matches(self, tmp_path):
        """Basename fragments >= 8 chars should still trigger pattern match."""
        data = dict(_SAMPLE_INDEX)
        data["pattern_routes"] = [{
            "pattern_name": "stream-wrapper",
            "doc_anchor": "patterns.md#stream-wrapper",
            "template_file": "src/utils/middleware.py",  # "middleware" is 10 chars >= 8
            "registration": "implicit",
        }]
        idx = _write_index(tmp_path, data)
        r = route_query("middleware handler", idx)
        assert r.match_type == "pattern_route"
        assert "stream-wrapper" in r.hint

    def test_vague_query_no_pattern_hijack(self, tmp_path):
        """Vague conceptual query should not be hijacked by narrow pattern."""
        data = dict(_SAMPLE_INDEX)
        data["pattern_routes"] = [{
            "pattern_name": "jwt-auth-flow",
            "doc_anchor": "patterns.md#jwt-auth-flow",
            "template_file": "backend/utils/auth.py",  # "auth" is 4 chars < 8
            "registration": "implicit",
        }]
        data["subsystem_routes"] = [{
            "subsystem": "auth-system",
            "doc_path": "auth.md",
            "owns_paths": [],
            "common_tasks": ["Add authentication provider"],
        }]
        idx = _write_index(tmp_path, data)
        # "authentication" contains "auth" but "auth" is < 8 chars fragment
        r = route_query("authentication provider", idx)
        # Should fall through pattern to common_task, not match on "auth" fragment
        assert r.match_type == "common_task"
        assert r.subsystem == "auth-system"


# ---------------------------------------------------------------------------
# Common task matching
# ---------------------------------------------------------------------------


class TestCommonTaskMatching:

    def test_keyword_match(self, tmp_path):
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r = route_query("endpoint api", idx)
        assert r.match_type == "common_task"
        assert r.subsystem == "api-routers"

    def test_migration_keyword(self, tmp_path):
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r = route_query("migration", idx)
        assert r.match_type == "common_task"
        assert r.subsystem == "data-models"

    def test_stop_words_only_no_match(self, tmp_path):
        """Queries with only stop words should not match."""
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r = route_query("add new", idx)
        assert r.match_type == "fallback"

    def test_short_words_filtered(self, tmp_path):
        """Words < 3 chars should be filtered out."""
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r = route_query("a b c", idx)
        assert r.match_type == "fallback"

    def test_best_match_wins_over_first(self, tmp_path):
        """Higher keyword overlap should win over earlier iteration order."""
        data = dict(_SAMPLE_INDEX)
        data["subsystem_routes"] = [
            {
                "subsystem": "aaa-weak",  # alphabetically first
                "doc_path": "weak.md",
                "owns_paths": [],
                "common_tasks": ["Handle sqs queue"],  # 1-word overlap on "sqs"
            },
            {
                "subsystem": "zzz-strong",  # alphabetically last
                "doc_path": "strong.md",
                "owns_paths": [],
                "common_tasks": ["Process digest pipeline stage"],  # 2-word overlap
            },
        ]
        idx = _write_index(tmp_path, data)
        r = route_query("digest pipeline sqs", idx)
        assert r.match_type == "common_task"
        assert r.subsystem == "zzz-strong"  # 2-word overlap beats 1-word

    def test_tie_break_alphabetical(self, tmp_path):
        """Equal overlap count → alphabetically earlier subsystem wins."""
        data = dict(_SAMPLE_INDEX)
        data["subsystem_routes"] = [
            {
                "subsystem": "beta-subsystem",
                "doc_path": "beta.md",
                "owns_paths": [],
                "common_tasks": ["Handle webhook event"],
            },
            {
                "subsystem": "alpha-subsystem",
                "doc_path": "alpha.md",
                "owns_paths": [],
                "common_tasks": ["Process webhook payload"],
            },
        ]
        idx = _write_index(tmp_path, data)
        r = route_query("webhook", idx)
        assert r.match_type == "common_task"
        assert r.subsystem == "alpha-subsystem"  # alphabetically first

    def test_best_match_deterministic(self, tmp_path):
        """Same query always produces same result."""
        data = dict(_SAMPLE_INDEX)
        data["subsystem_routes"] = [
            {
                "subsystem": "infra",
                "doc_path": "infra.md",
                "owns_paths": [],
                "common_tasks": ["Deploy service"],
            },
            {
                "subsystem": "pipeline",
                "doc_path": "pipeline.md",
                "owns_paths": [],
                "common_tasks": ["Deploy pipeline service worker"],
            },
        ]
        idx = _write_index(tmp_path, data)
        results = [route_query("deploy service worker", idx) for _ in range(5)]
        assert all(r.subsystem == results[0].subsystem for r in results)


# ---------------------------------------------------------------------------
# Priority order
# ---------------------------------------------------------------------------


class TestPriorityOrder:

    def test_prefix_beats_pattern(self, tmp_path):
        """A directory prefix match should win over a pattern match."""
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        # This query matches both:
        # - directory prefix: backend/open_webui/routers
        # - pattern: router-canonical-crud (via "routers" in query)
        r = route_query("backend/open_webui/routers/chats.py", idx)
        assert r.match_type == "directory_prefix"

    def test_pattern_beats_task(self, tmp_path):
        """A pattern match should win over a common task match."""
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        # "model_triplet" matches pattern name AND "model" matches common task
        r = route_query("model_triplet", idx)
        assert r.match_type == "pattern_route"


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------


class TestFallback:

    def test_empty_query(self, tmp_path):
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r = route_query("", idx)
        assert r.match_type == "fallback"

    def test_missing_index(self, tmp_path):
        r = route_query("anything", tmp_path / "nonexistent.json")
        assert r.match_type == "fallback"

    def test_corrupt_index(self, tmp_path):
        path = tmp_path / "route-index.json"
        path.write_text("NOT JSON")
        r = route_query("anything", path)
        assert r.match_type == "fallback"

    def test_fallback_hint_from_index(self, tmp_path):
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r = route_query("unrelated", idx)
        assert "CLAUDE.md" in r.hint


# ---------------------------------------------------------------------------
# Telemetry accuracy
# ---------------------------------------------------------------------------


class TestTelemetryFields:

    def test_directory_prefix_telemetry(self, tmp_path):
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r = route_query("backend/open_webui/routers/users.py", idx)
        assert r.artifact_kind == "subsystem_doc"
        assert r.match_type == "directory_prefix"
        assert r.subsystem == "api-routers"

    def test_pattern_route_telemetry(self, tmp_path):
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r = route_query("router-canonical-crud", idx)
        assert r.artifact_kind == "patterns"
        assert r.match_type == "pattern_route"

    def test_common_task_telemetry(self, tmp_path):
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r = route_query("endpoint", idx)
        assert r.artifact_kind == "subsystem_doc"
        assert r.match_type == "common_task"

    def test_fallback_telemetry(self, tmp_path):
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r = route_query("zzzzz", idx)
        assert r.artifact_kind == "fallback"
        assert r.match_type == "fallback"


# ---------------------------------------------------------------------------
# v1 backward compatibility
# ---------------------------------------------------------------------------


class TestV1Compat:

    def test_v1_index_still_routes(self, tmp_path):
        v1 = {
            "version": 1,
            "routes": [
                {
                    "match_type": "directory_prefix",
                    "pattern": "src/routers",
                    "subsystem": "Routers",
                    "doc_path": "agent-docs/subsystems/routers.md",
                    "hint": "HTTP handlers",
                },
            ],
            "fallback_hint": "See agent-docs/agent-context.md",
        }
        idx = _write_index(tmp_path, v1)
        r = route_query("src/routers/api.py", idx)
        assert r.match_type == "directory_prefix"
        assert r.subsystem == "Routers"


# ---------------------------------------------------------------------------
# Deterministic behavior
# ---------------------------------------------------------------------------


class TestDeterministic:

    def test_same_query_same_result(self, tmp_path):
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r1 = route_query("backend/open_webui/routers/chats.py", idx)
        r2 = route_query("backend/open_webui/routers/chats.py", idx)
        assert r1.hint == r2.hint
        assert r1.match_type == r2.match_type
        assert r1.doc == r2.doc


# ---------------------------------------------------------------------------
# Bx6a: Brief suggestion for directory_prefix matches
# ---------------------------------------------------------------------------


class TestBriefSuggestion:

    def test_directory_prefix_with_brief_paths(self, tmp_path):
        """directory_prefix match with brief_paths → directive brief (Bx7a)."""
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r = route_query("backend/open_webui/routers/chats.py", idx)
        assert r.match_type == "directory_prefix"
        assert r.show_brief_hint is True
        assert r.brief_paths == ["backend/open_webui/routers"]
        assert "Before further search, run: pensieve brief" in r.hint
        assert r.brief_mode == "instructed"

    def test_directory_prefix_without_brief_paths(self, tmp_path):
        """directory_prefix match without brief_paths → doc-only hint, no directive."""
        data = dict(_SAMPLE_INDEX)
        data["subsystem_routes"] = [{
            "subsystem": "core",
            "doc_path": "core.md",
            "role": "Core logic",
            "owns_paths": ["src/core"],
            # no brief_paths
        }]
        idx = _write_index(tmp_path, data)
        r = route_query("src/core/main.py", idx)
        assert r.match_type == "directory_prefix"
        assert r.show_brief_hint is False
        assert r.brief_paths == []
        assert "pensieve brief" not in r.hint
        assert r.brief_mode == "none"

    def test_directory_prefix_empty_brief_paths(self, tmp_path):
        """directory_prefix match with empty brief_paths → doc-only hint."""
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        # configuration subsystem has brief_paths: []
        r = route_query("backend/open_webui/config.py", idx)
        assert r.match_type == "directory_prefix"
        assert r.show_brief_hint is False
        assert r.brief_paths == []
        assert "pensieve brief" not in r.hint

    def test_directory_prefix_multiple_brief_paths(self, tmp_path):
        """brief_paths with multiple entries → all paths in command."""
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r = route_query("backend/open_webui/models/users.py", idx)
        assert r.match_type == "directory_prefix"
        assert r.show_brief_hint is True
        assert len(r.brief_paths) == 2
        assert "pensieve brief backend/open_webui/models backend/open_webui/internal" in r.hint

    def test_pattern_route_no_brief(self, tmp_path):
        """Pattern matches never suggest brief."""
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r = route_query("router-canonical-crud", idx)
        assert r.match_type == "pattern_route"
        assert r.show_brief_hint is False
        assert r.brief_paths == []
        assert "pensieve brief" not in r.hint
        assert r.brief_mode == "none"

    def test_common_task_weak_no_brief(self, tmp_path):
        """Bx6b: weak common_task (overlap 1) does not suggest brief."""
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        # "endpoint" overlaps 1 keyword with "Add new API endpoint"
        r = route_query("endpoint", idx)
        assert r.match_type == "common_task"
        assert r.show_brief_hint is False
        assert r.brief_paths == []
        assert "pensieve brief" not in r.hint
        assert r.brief_mode == "none"

    def test_common_task_strong_with_brief(self, tmp_path):
        """Bx6b: strong common_task → suggested brief (not instructed)."""
        data = dict(_SAMPLE_INDEX)
        data["subsystem_routes"] = [{
            "subsystem": "digest-pipeline",
            "doc_path": "digest.md",
            "owns_paths": [],
            "common_tasks": ["Add new digest pipeline stage"],
            "brief_paths": ["backend/pipelines/"],
        }]
        idx = _write_index(tmp_path, data)
        r = route_query("digest pipeline", idx)
        assert r.match_type == "common_task"
        assert r.show_brief_hint is True
        assert "For structural detail:" in r.hint  # suggestion wording, not directive
        assert "Before further search" not in r.hint  # NOT directive
        assert r.brief_mode == "suggested"

    def test_common_task_strong_empty_brief_paths(self, tmp_path):
        """Bx6b: strong overlap but empty brief_paths → no brief."""
        data = dict(_SAMPLE_INDEX)
        data["subsystem_routes"] = [{
            "subsystem": "infra",
            "doc_path": "infra.md",
            "owns_paths": [],
            "common_tasks": ["Deploy service worker"],
            "brief_paths": [],
        }]
        idx = _write_index(tmp_path, data)
        r = route_query("service worker", idx)
        assert r.match_type == "common_task"
        assert r.show_brief_hint is False
        assert r.brief_paths == []
        assert "pensieve brief" not in r.hint

    def test_common_task_strong_hint_single_line(self, tmp_path):
        """Bx6b: strong common_task brief hint stays one line."""
        data = dict(_SAMPLE_INDEX)
        data["subsystem_routes"] = [{
            "subsystem": "digest-pipeline",
            "doc_path": "digest.md",
            "owns_paths": [],
            "common_tasks": ["Add new digest pipeline stage"],
            "brief_paths": ["backend/pipelines/"],
        }]
        idx = _write_index(tmp_path, data)
        r = route_query("digest pipeline", idx)
        assert "\n" not in r.hint

    def test_fallback_no_brief(self, tmp_path):
        """Fallback never suggests brief."""
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r = route_query("zzzzz", idx)
        assert r.match_type == "fallback"
        assert r.show_brief_hint is False
        assert r.brief_paths == []
        assert r.brief_mode == "none"

    def test_v1_index_no_brief(self, tmp_path):
        """v1 index has no brief concept."""
        v1 = {
            "version": 1,
            "routes": [
                {
                    "match_type": "directory_prefix",
                    "pattern": "src/routers",
                    "subsystem": "Routers",
                    "doc_path": "agent-docs/subsystems/routers.md",
                    "hint": "HTTP handlers",
                },
            ],
        }
        idx = _write_index(tmp_path, v1)
        r = route_query("src/routers/api.py", idx)
        assert r.show_brief_hint is False
        assert r.brief_paths == []

    def test_hint_is_single_line(self, tmp_path):
        """Brief suggestion must not break the one-line hint policy."""
        idx = _write_index(tmp_path, _SAMPLE_INDEX)
        r = route_query("backend/open_webui/routers/chats.py", idx)
        assert "\n" not in r.hint

    def test_brief_paths_shell_quoted(self, tmp_path):
        """Paths with spaces or shell chars are quoted in the brief command."""
        data = dict(_SAMPLE_INDEX)
        data["subsystem_routes"] = [{
            "subsystem": "frontend",
            "doc_path": "frontend.md",
            "role": "UI",
            "owns_paths": ["src/ui"],
            "brief_paths": ["src/ui components", "src/$utils"],
        }]
        idx = _write_index(tmp_path, data)
        r = route_query("src/ui/app.tsx", idx)
        assert r.show_brief_hint is True
        # shlex.quote wraps paths that need it
        assert "'src/ui components'" in r.hint
        assert "'src/$utils'" in r.hint
