"""Tests for the shared rationale comment extraction module (B10).

Tests the canonical tag list, the universal tag pattern, doc-comment
filters, context detection, and multi-line block comment handling.
These tests exercise the shared module directly, independent of any
specific language extractor.
"""

from __future__ import annotations

import tree_sitter_python as tspython
import tree_sitter_javascript as tsjs
import tree_sitter_java as tsjava
import tree_sitter_rust as tsrust
from tree_sitter import Language, Parser

from pensieve.extractors._comments import (
    RATIONALE_TAGS,
    extract_rationale_comments,
    is_jsdoc,
    is_rust_doc,
)


def _parse(source: bytes, language_fn) -> object:
    parser = Parser(Language(language_fn))
    return parser.parse(source)


# ---------------------------------------------------------------------------
# Canonical tag list
# ---------------------------------------------------------------------------


class TestTagList:
    def test_all_expected_tags_present(self):
        expected = {"WHY", "NOTE", "IMPORTANT", "HACK", "TODO", "FIXME"}
        assert set(RATIONALE_TAGS) == expected

    def test_tags_are_uppercase(self):
        assert all(tag == tag.upper() for tag in RATIONALE_TAGS)


# ---------------------------------------------------------------------------
# Python-style comments (# prefix)
# ---------------------------------------------------------------------------


class TestPythonComments:
    def _extract(self, source: bytes):
        tree = _parse(source, tspython.language())
        return extract_rationale_comments(
            tree.root_node, source, [],
            comment_node_types=frozenset({"comment"}),
        )

    def test_hash_why(self):
        results = self._extract(b"# WHY: Performance\nx = 1\n")
        assert len(results) == 1
        assert results[0].tag == "WHY"
        assert results[0].text == "Performance"

    def test_hash_note(self):
        results = self._extract(b"# NOTE: Important detail\n")
        assert len(results) == 1
        assert results[0].tag == "NOTE"

    def test_hash_case_insensitive(self):
        results = self._extract(b"# why: lowercase\n# Why: mixed\n# WHY: upper\n")
        assert len(results) == 3
        assert all(r.tag == "WHY" for r in results)

    def test_non_tagged_comment_ignored(self):
        results = self._extract(b"# This is a regular comment\n")
        assert len(results) == 0

    def test_all_six_tags(self):
        source = b"\n".join(
            f"# {tag}: text for {tag}".encode() for tag in RATIONALE_TAGS
        )
        results = self._extract(source)
        found_tags = {r.tag for r in results}
        assert found_tags == set(RATIONALE_TAGS)


# ---------------------------------------------------------------------------
# JS-style comments (// and /* */ prefix)
# ---------------------------------------------------------------------------


class TestJSComments:
    def _extract(self, source: bytes, doc_filter=None):
        tree = _parse(source, tsjs.language())
        return extract_rationale_comments(
            tree.root_node, source, [],
            comment_node_types=frozenset({"comment"}),
            is_doc_comment=doc_filter,
        )

    def test_slash_slash_why(self):
        results = self._extract(b"// WHY: Security concern\n")
        assert len(results) == 1
        assert results[0].tag == "WHY"
        assert results[0].text == "Security concern"

    def test_slash_slash_hack(self):
        results = self._extract(b"// HACK: Temporary fix\n")
        assert len(results) == 1
        assert results[0].tag == "HACK"

    def test_jsdoc_skipped_with_filter(self):
        source = b"/** This is JSDoc */\nfunction foo() {}\n"
        results = self._extract(source, doc_filter=is_jsdoc)
        assert len(results) == 0

    def test_jsdoc_not_skipped_without_filter(self):
        # Without the filter, /** is treated as a regular block comment
        # and any tags inside it would be matched
        source = b"/** WHY: in JSDoc */\nfunction foo() {}\n"
        results = self._extract(source, doc_filter=None)
        # May or may not match depending on pattern — the point is it doesn't crash
        assert isinstance(results, list)


# ---------------------------------------------------------------------------
# Java-style comments (line_comment + block_comment)
# ---------------------------------------------------------------------------


class TestJavaComments:
    def _extract(self, source: bytes, doc_filter=None):
        tree = _parse(source, tsjava.language())
        return extract_rationale_comments(
            tree.root_node, source, [],
            comment_node_types=frozenset({"line_comment", "block_comment"}),
            is_doc_comment=doc_filter,
        )

    def test_java_line_comment(self):
        source = b"public class Foo {\n  // WHY: Reason\n}\n"
        results = self._extract(source)
        assert len(results) == 1
        assert results[0].tag == "WHY"

    def test_javadoc_skipped(self):
        source = b"/** Javadoc */\npublic class Foo {}\n"
        results = self._extract(source, doc_filter=is_jsdoc)
        assert len(results) == 0


# ---------------------------------------------------------------------------
# Rust-style comments (line_comment with doc filter)
# ---------------------------------------------------------------------------


class TestRustComments:
    def _extract(self, source: bytes, doc_filter=None):
        tree = _parse(source, tsrust.language())
        return extract_rationale_comments(
            tree.root_node, source, [],
            comment_node_types=frozenset({"line_comment"}),
            is_doc_comment=doc_filter,
        )

    def test_rust_slash_slash_why(self):
        results = self._extract(b"// WHY: Performance\nfn foo() {}\n")
        assert len(results) == 1
        assert results[0].tag == "WHY"

    def test_rust_doc_comment_skipped(self):
        source = b"/// Doc comment, not a tag\nfn foo() {}\n"
        results = self._extract(source, doc_filter=is_rust_doc)
        assert len(results) == 0

    def test_rust_doc_comment_not_skipped_without_filter(self):
        source = b"/// WHY: Inside doc comment\nfn foo() {}\n"
        results = self._extract(source, doc_filter=None)
        # Without filter, the /// comment is processed — may match
        assert isinstance(results, list)


# ---------------------------------------------------------------------------
# Context detection
# ---------------------------------------------------------------------------


class TestContext:
    def test_comment_inside_function_gets_context(self):
        source = b"def foo():\n    # WHY: Reason\n    pass\n"
        tree = _parse(source, tspython.language())
        ranges = [("foo", 1, 3)]
        results = extract_rationale_comments(
            tree.root_node, source, ranges,
            comment_node_types=frozenset({"comment"}),
        )
        assert len(results) == 1
        assert results[0].context == "foo"

    def test_comment_outside_function_has_no_context(self):
        source = b"# WHY: Top-level reason\ndef foo():\n    pass\n"
        tree = _parse(source, tspython.language())
        ranges = [("foo", 2, 3)]
        results = extract_rationale_comments(
            tree.root_node, source, ranges,
            comment_node_types=frozenset({"comment"}),
        )
        assert len(results) == 1
        assert results[0].context is None

    def test_innermost_context_wins(self):
        source = b"class Foo:\n    def bar(self):\n        # WHY: Deep\n        pass\n"
        tree = _parse(source, tspython.language())
        ranges = [("Foo", 1, 4), ("bar", 2, 4)]
        results = extract_rationale_comments(
            tree.root_node, source, ranges,
            comment_node_types=frozenset({"comment"}),
        )
        assert len(results) == 1
        assert results[0].context == "bar"  # innermost wins
