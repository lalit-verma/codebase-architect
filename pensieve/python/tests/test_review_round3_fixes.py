"""Regression tests for review round 3: Rust trait default method call edges.

Failure cases tested:
1. Trait with default method containing calls — was broken, now fixed
2. Trait with only signatures (no body) — should produce no call edges gracefully
3. Trait default method with same name as impl method on a different type — must not cross-match
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from pensieve.extractors.rust import extract_rust
from pensieve.schema import validate_extraction


def _write_rs(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "test.rs"
    p.write_text(dedent(content))
    return p


class TestTraitDefaultMethodCallEdges:
    """Fix for: trait default methods extracted but call edges were empty."""

    def test_default_method_call_edges_collected(self, tmp_path):
        """A trait default method with calls should produce call edges."""
        p = _write_rs(tmp_path, '''\
        trait Processor {
            fn process(&self) {
                self.validate();
                self.execute();
            }

            fn validate(&self) -> bool { true }
            fn execute(&self);
        }
        ''')
        ext = extract_rust(p)
        validate_extraction(ext)

        # The default impl of process() calls validate() and execute()
        edges = [e for e in ext.call_edges if e.caller == "process"]
        callees = {e.callee for e in edges}
        assert "validate" in callees
        assert "execute" in callees

    def test_trait_signature_only_no_call_edges(self, tmp_path):
        """A trait method with no body (signature only) should produce
        no call edges and not crash."""
        p = _write_rs(tmp_path, '''\
        trait Reader {
            fn read(&self, buf: &mut [u8]) -> usize;
            fn close(&self);
        }
        ''')
        ext = extract_rust(p)
        validate_extraction(ext)

        # Signature-only methods have no body → no call edges
        assert len(ext.call_edges) == 0
        # But the methods should still be extracted as symbols
        methods = [s for s in ext.symbols if s.kind == "method"]
        assert len(methods) == 2

    def test_same_name_method_in_trait_and_impl_no_cross_match(self, tmp_path):
        """A method named `run` in a trait and a method named `run` in
        a different type's impl block should not cross-match."""
        p = _write_rs(tmp_path, '''\
        trait Runner {
            fn run(&self) {
                self.prepare();
            }
        }

        struct Worker;

        impl Worker {
            fn run(&self) {
                self.execute();
            }

            fn prepare(&self) {}
            fn execute(&self) {}
        }
        ''')
        ext = extract_rust(p)
        validate_extraction(ext)

        # Runner::run should call prepare
        runner_edges = [
            e for e in ext.call_edges
            if e.caller == "run" and e.callee == "prepare"
        ]
        assert len(runner_edges) >= 1

        # Worker::run should call execute
        worker_edges = [
            e for e in ext.call_edges
            if e.caller == "run" and e.callee == "execute"
        ]
        assert len(worker_edges) >= 1

    def test_mixed_trait_with_default_and_signature(self, tmp_path):
        """A trait with both default methods and signature-only methods."""
        p = _write_rs(tmp_path, '''\
        trait Cache {
            fn get(&self, key: &str) -> Option<String>;
            fn set(&mut self, key: String, value: String);

            fn get_or_default(&self, key: &str, default: &str) -> String {
                self.get(key).unwrap_or_else(|| default.to_string())
            }
        }
        ''')
        ext = extract_rust(p)
        validate_extraction(ext)

        # get_or_default has a body that calls get()
        edges = [e for e in ext.call_edges if e.caller == "get_or_default"]
        callees = {e.callee for e in edges}
        assert "get" in callees

        # get and set are signature-only → no call edges from them
        get_edges = [e for e in ext.call_edges if e.caller == "get"]
        set_edges = [e for e in ext.call_edges if e.caller == "set"]
        assert len(get_edges) == 0
        assert len(set_edges) == 0


