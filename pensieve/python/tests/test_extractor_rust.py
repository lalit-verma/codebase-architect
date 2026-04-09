"""Tests for the Rust structural extractor (milestone B9).

Covers: functions, impl blocks (inherent + trait impls), trait
definitions with method signatures, structs, enums, type aliases,
constants, use declarations (simple + nested + glob), pub/private
visibility, /// doc comments, parameters (including &self), return
types, call edges, rationale comments, and a realistic integration test.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from pensieve.extractors.rust import extract_rust
from pensieve.schema import validate_extraction


def _write_rs(tmp_path: Path, content: str, name: str = "test.rs") -> Path:
    p = tmp_path / name
    p.write_text(dedent(content))
    return p


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


class TestFunctions:

    def test_simple_function(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        fn add(a: i32, b: i32) -> i32 {
            a + b
        }
        ''')
        ext = extract_rust(p)
        funcs = [s for s in ext.symbols if s.kind == "function"]
        assert len(funcs) == 1
        assert funcs[0].name == "add"
        assert funcs[0].visibility == "private"  # no pub
        validate_extraction(ext)

    def test_pub_function(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        pub fn create() -> Self {
            Self {}
        }
        ''')
        ext = extract_rust(p)
        assert ext.symbols[0].visibility == "public"

    def test_function_parameters(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        fn process(name: &str, count: usize, flag: bool) -> Result<(), Error> {
            Ok(())
        }
        ''')
        ext = extract_rust(p)
        func = ext.symbols[0]
        param_names = [p.name for p in func.parameters]
        assert "name" in param_names
        assert "count" in param_names
        assert "flag" in param_names

    def test_function_return_type(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        fn get_name() -> String {
            String::from("hello")
        }
        ''')
        ext = extract_rust(p)
        assert ext.symbols[0].return_type == "String"

    def test_function_no_return_type(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        fn side_effect() {
            println!("done");
        }
        ''')
        ext = extract_rust(p)
        assert ext.symbols[0].return_type is None


# ---------------------------------------------------------------------------
# Impl blocks and methods
# ---------------------------------------------------------------------------


class TestImplMethods:

    def test_inherent_impl(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        struct Foo;

        impl Foo {
            pub fn new() -> Self {
                Self
            }
            fn internal(&self) {}
        }
        ''')
        ext = extract_rust(p)
        methods = [s for s in ext.symbols if s.kind == "method"]
        assert len(methods) == 2
        assert all(m.parent == "Foo" for m in methods)
        pub_method = next(m for m in methods if m.name == "new")
        assert pub_method.visibility == "public"
        priv_method = next(m for m in methods if m.name == "internal")
        assert priv_method.visibility == "private"

    def test_trait_impl(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        struct Bar;

        trait Greet {
            fn hello(&self) -> String;
        }

        impl Greet for Bar {
            fn hello(&self) -> String {
                String::from("hi")
            }
        }
        ''')
        ext = extract_rust(p)
        methods = [s for s in ext.symbols if s.kind == "method" and s.parent == "Bar"]
        assert any(m.name == "hello" for m in methods)

    def test_self_parameter(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        struct Foo;
        impl Foo {
            fn method(&self, x: i32) -> i32 { x }
            fn mut_method(&mut self) {}
            fn consuming(self) {}
        }
        ''')
        ext = extract_rust(p)
        methods = [s for s in ext.symbols if s.kind == "method"]
        assert len(methods) == 3
        # All should have self as first param
        for m in methods:
            assert len(m.parameters) >= 1
            assert "self" in m.parameters[0].name


# ---------------------------------------------------------------------------
# Structs and traits
# ---------------------------------------------------------------------------


class TestStructsAndTraits:

    def test_struct(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        pub struct User {
            pub id: u64,
            pub name: String,
            email: String,
        }
        ''')
        ext = extract_rust(p)
        structs = [s for s in ext.symbols if s.kind == "struct"]
        assert len(structs) == 1
        assert structs[0].name == "User"
        assert structs[0].visibility == "public"

    def test_trait_with_methods(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        pub trait Repository<T> {
            fn find_by_id(&self, id: &str) -> Option<&T>;
            fn save(&mut self, entity: T);
        }
        ''')
        ext = extract_rust(p)
        traits = [s for s in ext.symbols if s.kind == "trait"]
        assert len(traits) == 1
        assert traits[0].name == "Repository"
        methods = [s for s in ext.symbols if s.kind == "method" and s.parent == "Repository"]
        assert len(methods) == 2

    def test_private_struct(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        struct Internal {
            data: Vec<u8>,
        }
        ''')
        ext = extract_rust(p)
        assert ext.symbols[0].visibility == "private"


# ---------------------------------------------------------------------------
# Enums and type aliases
# ---------------------------------------------------------------------------


class TestEnumsAndTypeAliases:

    def test_enum(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        pub enum Role {
            Admin,
            User,
            Guest,
        }
        ''')
        ext = extract_rust(p)
        enums = [s for s in ext.symbols if s.kind == "enum"]
        assert len(enums) == 1
        assert enums[0].name == "Role"
        assert enums[0].visibility == "public"

    def test_type_alias(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        type UserId = String;
        ''')
        ext = extract_rust(p)
        aliases = [s for s in ext.symbols if s.kind == "type_alias"]
        assert len(aliases) == 1
        assert aliases[0].name == "UserId"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:

    def test_const_item(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        const MAX_RETRIES: u32 = 5;
        ''')
        ext = extract_rust(p)
        consts = [s for s in ext.symbols if s.kind == "constant"]
        assert len(consts) == 1
        assert consts[0].name == "MAX_RETRIES"

    def test_pub_const(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        pub const VERSION: &str = "1.0.0";
        ''')
        ext = extract_rust(p)
        assert ext.symbols[0].visibility == "public"


# ---------------------------------------------------------------------------
# Use declarations (imports)
# ---------------------------------------------------------------------------


class TestUseDeclarations:

    def test_simple_use(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        use std::collections::HashMap;
        ''')
        ext = extract_rust(p)
        assert len(ext.imports) == 1
        assert ext.imports[0].module == "std::collections"
        assert "HashMap" in ext.imports[0].names

    def test_nested_use(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        use std::io::{self, Read, Write};
        ''')
        ext = extract_rust(p)
        assert len(ext.imports) == 1
        assert ext.imports[0].module == "std::io"
        assert "Read" in ext.imports[0].names
        assert "Write" in ext.imports[0].names

    def test_multiple_use(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        use std::collections::HashMap;
        use std::sync::Arc;
        ''')
        ext = extract_rust(p)
        assert len(ext.imports) == 2


# ---------------------------------------------------------------------------
# Doc comments (///)
# ---------------------------------------------------------------------------


class TestDocComments:

    def test_function_doc(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        /// Creates a new instance.
        pub fn create() {}
        ''')
        ext = extract_rust(p)
        assert ext.symbols[0].docstring is not None
        assert "Creates a new instance" in ext.symbols[0].docstring

    def test_struct_doc(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        /// A user in the system.
        pub struct User {
            pub id: u64,
        }
        ''')
        ext = extract_rust(p)
        assert ext.symbols[0].docstring is not None
        assert "user in the system" in ext.symbols[0].docstring.lower()

    def test_multiline_doc(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        /// Processes input data.
        /// Returns the result or an error.
        pub fn process() {}
        ''')
        ext = extract_rust(p)
        doc = ext.symbols[0].docstring
        assert doc is not None
        assert "Processes" in doc
        assert "Returns" in doc

    def test_no_doc_comment(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        fn no_doc() {}
        ''')
        ext = extract_rust(p)
        assert ext.symbols[0].docstring is None

    def test_regular_comment_not_doc(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        // This is a regular comment, not doc
        fn foo() {}
        ''')
        ext = extract_rust(p)
        assert ext.symbols[0].docstring is None


# ---------------------------------------------------------------------------
# Call edges
# ---------------------------------------------------------------------------


class TestCallEdges:

    def test_function_call(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        fn caller() {
            callee();
        }
        fn callee() {}
        ''')
        ext = extract_rust(p)
        edges = [e for e in ext.call_edges if e.caller == "caller"]
        assert any(e.callee == "callee" for e in edges)

    def test_self_call_stripped(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        struct Foo;
        impl Foo {
            fn bar(&self) {
                self.baz();
            }
            fn baz(&self) {}
        }
        ''')
        ext = extract_rust(p)
        edges = [e for e in ext.call_edges if e.caller == "bar"]
        assert any(e.callee == "baz" for e in edges)

    def test_method_chain(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        fn process() {
            HashMap::new();
        }
        ''')
        ext = extract_rust(p)
        edges = [e for e in ext.call_edges if e.caller == "process"]
        assert any("HashMap::new" in e.callee for e in edges)


# ---------------------------------------------------------------------------
# Rationale comments
# ---------------------------------------------------------------------------


class TestRationaleComments:

    def test_why_comment(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        fn foo() {
            // WHY: Performance optimization
        }
        ''')
        ext = extract_rust(p)
        assert len(ext.rationale_comments) == 1
        assert ext.rationale_comments[0].tag == "WHY"
        assert "Performance" in ext.rationale_comments[0].text

    def test_doc_comment_not_rationale(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        /// This is documentation, not a rationale tag.
        fn foo() {}
        ''')
        ext = extract_rust(p)
        assert len(ext.rationale_comments) == 0


# ---------------------------------------------------------------------------
# Integration: realistic file
# ---------------------------------------------------------------------------


class TestRealisticFile:

    def test_realistic_rust_module(self, tmp_path):
        p = _write_rs(tmp_path, '''\
        use std::collections::HashMap;
        use std::sync::{Arc, Mutex};

        /// Maximum cache entries.
        const MAX_ENTRIES: usize = 1000;

        /// Type alias for the cache key.
        type CacheKey = String;

        /// An in-memory cache.
        pub struct Cache {
            store: Arc<Mutex<HashMap<CacheKey, Vec<u8>>>>,
        }

        /// Cache operations trait.
        pub trait CacheOps {
            fn get(&self, key: &str) -> Option<Vec<u8>>;
            fn set(&mut self, key: CacheKey, value: Vec<u8>);
        }

        impl Cache {
            /// Create a new empty cache.
            pub fn new() -> Self {
                Self {
                    store: Arc::new(Mutex::new(HashMap::new())),
                }
            }

            fn is_full(&self) -> bool {
                // WHY: Prevent unbounded memory growth
                let guard = self.store.lock().unwrap();
                guard.len() >= MAX_ENTRIES
            }
        }

        impl CacheOps for Cache {
            fn get(&self, key: &str) -> Option<Vec<u8>> {
                let guard = self.store.lock().unwrap();
                guard.get(key).cloned()
            }

            fn set(&mut self, key: CacheKey, value: Vec<u8>) {
                // HACK: Evict randomly when full
                let mut guard = self.store.lock().unwrap();
                guard.insert(key, value);
            }
        }

        // NOTE: Consider using an LRU eviction policy
        pub fn create_cache() -> Cache {
            Cache::new()
        }

        pub enum EvictionPolicy {
            Lru,
            Lfu,
            Random,
        }
        ''')

        ext = extract_rust(p)
        validate_extraction(ext)

        # Check symbol names
        sym_names = {s.name for s in ext.symbols}
        assert "Cache" in sym_names
        assert "CacheOps" in sym_names
        assert "new" in sym_names
        assert "is_full" in sym_names
        assert "get" in sym_names
        assert "set" in sym_names
        assert "create_cache" in sym_names
        assert "MAX_ENTRIES" in sym_names
        assert "CacheKey" in sym_names
        assert "EvictionPolicy" in sym_names

        # Check kinds
        kinds = {s.kind for s in ext.symbols}
        assert "struct" in kinds
        assert "trait" in kinds
        assert "method" in kinds
        assert "function" in kinds
        assert "constant" in kinds
        assert "type_alias" in kinds
        assert "enum" in kinds

        # Check parents
        new_method = next(s for s in ext.symbols if s.name == "new" and s.kind == "method")
        assert new_method.parent == "Cache"
        get_methods = [s for s in ext.symbols if s.name == "get"]
        assert any(m.parent == "CacheOps" for m in get_methods)  # trait signature
        assert any(m.parent == "Cache" for m in get_methods)  # impl

        # Check visibility
        cache_struct = next(s for s in ext.symbols if s.name == "Cache" and s.kind == "struct")
        assert cache_struct.visibility == "public"
        is_full = next(s for s in ext.symbols if s.name == "is_full")
        assert is_full.visibility == "private"

        # Check imports
        assert len(ext.imports) == 2
        modules = {i.module for i in ext.imports}
        assert "std::collections" in modules
        assert "std::sync" in modules

        # Check doc comments
        assert cache_struct.docstring is not None
        assert "in-memory cache" in cache_struct.docstring.lower()

        # Check rationale comments
        tags = {rc.tag for rc in ext.rationale_comments}
        assert "WHY" in tags
        assert "HACK" in tags
        assert "NOTE" in tags

        # Check call edges
        assert len(ext.call_edges) > 0
