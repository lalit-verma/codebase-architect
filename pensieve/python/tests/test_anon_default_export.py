"""Integration tests for anonymous callable default exports.

Tests the full pipeline: real extractors → build_graph → call edges.
Verifies that anonymous default functions and arrows produce call edges,
while non-callable defaults (class, constant) do not.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from pensieve.graph import build_graph


def _make_repo(tmp_path, files):
    repo = tmp_path / "repo"
    repo.mkdir()
    for rel, content in files.items():
        f = repo / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(dedent(content))
    return repo


def _scan_and_graph(repo):
    from pensieve.scan import scan_repo
    result = scan_repo(repo)
    import json
    return json.loads(result.graph_path.read_text())


# ---------------------------------------------------------------------------
# JS anonymous default exports — integration
# ---------------------------------------------------------------------------


class TestJSAnonymousDefaults:

    def test_anon_function_default_creates_call_edge(self, tmp_path):
        """export default function() {} + import foo; foo() → call edge."""
        repo = _make_repo(tmp_path, {
            "utils.js": "export default function() { return 42; }\n",
            "main.js": dedent("""\
                import foo from './utils.js';
                function run() { foo(); }
            """),
        })
        graph = _scan_and_graph(repo)
        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) >= 1
        assert any(e["target"] == "utils.js" for e in call_edges)

    def test_arrow_default_creates_call_edge(self, tmp_path):
        """export default () => 1 + import foo; foo() → call edge."""
        repo = _make_repo(tmp_path, {
            "utils.js": "export default () => 1;\n",
            "main.js": dedent("""\
                import foo from './utils.js';
                function run() { foo(); }
            """),
        })
        graph = _scan_and_graph(repo)
        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) >= 1
        assert any(e["target"] == "utils.js" for e in call_edges)

    def test_named_function_default_still_works(self, tmp_path):
        """export default function helper() {} → call edge (regression)."""
        repo = _make_repo(tmp_path, {
            "utils.js": "export default function helper() { return 1; }\n",
            "main.js": dedent("""\
                import foo from './utils.js';
                function run() { foo(); }
            """),
        })
        graph = _scan_and_graph(repo)
        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) >= 1

    def test_class_default_no_call_edge(self, tmp_path):
        """export default class Foo {} + import foo; foo() → NO call edge."""
        repo = _make_repo(tmp_path, {
            "utils.js": "export default class Foo { bar() { return 1; } }\n",
            "main.js": dedent("""\
                import foo from './utils.js';
                function run() { foo(); }
            """),
        })
        graph = _scan_and_graph(repo)
        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) == 0

    def test_constant_default_no_call_edge(self, tmp_path):
        """const x = 42; export default x; + import foo; foo() → NO call edge."""
        repo = _make_repo(tmp_path, {
            "utils.js": "const x = 42;\nexport default x;\n",
            "main.js": dedent("""\
                import foo from './utils.js';
                function run() { foo(); }
            """),
        })
        graph = _scan_and_graph(repo)
        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) == 0


# ---------------------------------------------------------------------------
# TS anonymous default exports — integration
# ---------------------------------------------------------------------------


class TestTSAnonymousDefaults:

    def test_ts_anon_function_default_creates_call_edge(self, tmp_path):
        """TS: export default function() {} → call edge."""
        repo = _make_repo(tmp_path, {
            "utils.ts": "export default function(): number { return 42; }\n",
            "main.ts": dedent("""\
                import foo from './utils';
                function run(): void { foo(); }
            """),
        })
        graph = _scan_and_graph(repo)
        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) >= 1
        assert any(e["target"] == "utils.ts" for e in call_edges)

    def test_ts_arrow_default_creates_call_edge(self, tmp_path):
        """TS: export default () => 1 → call edge."""
        repo = _make_repo(tmp_path, {
            "utils.ts": "export default (): number => 1;\n",
            "main.ts": dedent("""\
                import foo from './utils';
                function run(): void { foo(); }
            """),
        })
        graph = _scan_and_graph(repo)
        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) >= 1

    def test_ts_class_default_no_call_edge(self, tmp_path):
        """TS: export default class Foo {} → NO call edge."""
        repo = _make_repo(tmp_path, {
            "utils.ts": "export default class Foo {}\n",
            "main.ts": dedent("""\
                import foo from './utils';
                function run(): void { foo(); }
            """),
        })
        graph = _scan_and_graph(repo)
        call_edges = [e for e in graph["edges"] if e["kind"] == "calls"]
        assert len(call_edges) == 0
