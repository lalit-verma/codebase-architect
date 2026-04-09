"""Tests for the Python structural extractor (milestone B4).

Tests the reference extractor against real-world Python patterns:
functions, classes, methods, imports, constants, call edges, rationale
comments, decorated functions, async functions, docstrings, parameters,
return types, and visibility.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from pensieve.extractors.python import extract_python
from pensieve.schema import validate_extraction


def _write_py(tmp_path: Path, content: str, name: str = "test.py") -> Path:
    """Write Python source to a temp file and return its path."""
    p = tmp_path / name
    p.write_text(dedent(content))
    return p


# ---------------------------------------------------------------------------
# Basic extraction
# ---------------------------------------------------------------------------


class TestBasicExtraction:

    def test_empty_file(self, tmp_path):
        p = _write_py(tmp_path, "")
        ext = extract_python(p)
        assert ext.language == "python"
        assert ext.symbols == []
        assert ext.imports == []
        validate_extraction(ext)

    def test_file_metadata(self, tmp_path):
        p = _write_py(tmp_path, "x = 1\n")
        ext = extract_python(p)
        assert ext.file_path == str(p)
        assert ext.language == "python"
        assert ext.sha256  # non-empty
        assert ext.file_size_bytes > 0
        assert ext.line_count >= 1
        assert ext.extractor_version

    def test_extraction_is_schema_valid(self, tmp_path):
        source = '''\
        import os
        from pathlib import Path

        MAX_RETRIES = 3

        class Processor:
            """A processor."""
            def run(self, data: list) -> bool:
                # WHY: Validate before processing
                os.path.exists(".")
                return True

        def helper(x: int) -> int:
            return x + 1
        '''
        p = _write_py(tmp_path, source)
        ext = extract_python(p)
        validate_extraction(ext)  # should not raise


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


class TestFunctions:

    def test_simple_function(self, tmp_path):
        p = _write_py(tmp_path, '''\
        def greet(name: str) -> str:
            return f"hello {name}"
        ''')
        ext = extract_python(p)
        funcs = [s for s in ext.symbols if s.kind == "function"]
        assert len(funcs) == 1
        assert funcs[0].name == "greet"
        assert funcs[0].parent is None
        assert funcs[0].visibility == "public"

    def test_function_parameters(self, tmp_path):
        p = _write_py(tmp_path, '''\
        def calc(a: int, b: float = 0.5, *args, **kwargs) -> float:
            pass
        ''')
        ext = extract_python(p)
        func = ext.symbols[0]
        param_names = [p.name for p in func.parameters]
        assert "a" in param_names
        assert "b" in param_names
        assert any("*" in p.name for p in func.parameters)  # *args
        assert any("**" in p.name for p in func.parameters)  # **kwargs

    def test_function_return_type(self, tmp_path):
        p = _write_py(tmp_path, '''\
        def add(a: int, b: int) -> int:
            return a + b
        ''')
        ext = extract_python(p)
        assert ext.symbols[0].return_type == "int"

    def test_function_no_return_type(self, tmp_path):
        p = _write_py(tmp_path, '''\
        def side_effect():
            pass
        ''')
        ext = extract_python(p)
        assert ext.symbols[0].return_type is None

    def test_async_function(self, tmp_path):
        p = _write_py(tmp_path, '''\
        async def fetch(url: str) -> str:
            pass
        ''')
        ext = extract_python(p)
        assert len(ext.symbols) == 1
        assert ext.symbols[0].name == "fetch"
        assert "async" in ext.symbols[0].signature

    def test_function_docstring(self, tmp_path):
        p = _write_py(tmp_path, '''\
        def documented():
            """This function has a docstring."""
            pass
        ''')
        ext = extract_python(p)
        assert ext.symbols[0].docstring == "This function has a docstring."

    def test_function_signature(self, tmp_path):
        p = _write_py(tmp_path, '''\
        def process(data: list[int], verbose: bool = False) -> dict:
            pass
        ''')
        ext = extract_python(p)
        sig = ext.symbols[0].signature
        assert "def process" in sig
        assert "data" in sig

    def test_private_function(self, tmp_path):
        p = _write_py(tmp_path, '''\
        def _internal_helper():
            pass
        ''')
        ext = extract_python(p)
        assert ext.symbols[0].visibility == "private"

    def test_decorated_function(self, tmp_path):
        p = _write_py(tmp_path, '''\
        @app.route("/health")
        def health_check():
            return "ok"
        ''')
        ext = extract_python(p)
        assert len(ext.symbols) == 1
        assert ext.symbols[0].name == "health_check"
        assert "@app.route" in ext.symbols[0].signature


# ---------------------------------------------------------------------------
# Classes and methods
# ---------------------------------------------------------------------------


class TestClassesAndMethods:

    def test_class_with_methods(self, tmp_path):
        p = _write_py(tmp_path, '''\
        class Calculator:
            """A calculator."""
            def add(self, a: int, b: int) -> int:
                return a + b
            def subtract(self, a: int, b: int) -> int:
                return a - b
        ''')
        ext = extract_python(p)
        classes = [s for s in ext.symbols if s.kind == "class"]
        methods = [s for s in ext.symbols if s.kind == "method"]

        assert len(classes) == 1
        assert classes[0].name == "Calculator"
        assert classes[0].docstring == "A calculator."

        assert len(methods) == 2
        assert all(m.parent == "Calculator" for m in methods)
        assert {m.name for m in methods} == {"add", "subtract"}

    def test_static_method(self, tmp_path):
        p = _write_py(tmp_path, '''\
        class Validator:
            @staticmethod
            def validate(value):
                return value >= 0
        ''')
        ext = extract_python(p)
        methods = [s for s in ext.symbols if s.kind == "method"]
        assert len(methods) == 1
        assert methods[0].name == "validate"
        assert methods[0].parent == "Validator"

    def test_class_method(self, tmp_path):
        p = _write_py(tmp_path, '''\
        class Factory:
            @classmethod
            def create(cls, config: dict):
                return cls()
        ''')
        ext = extract_python(p)
        methods = [s for s in ext.symbols if s.kind == "method"]
        assert len(methods) == 1
        assert methods[0].name == "create"

    def test_dunder_method_is_public(self, tmp_path):
        p = _write_py(tmp_path, '''\
        class Foo:
            def __init__(self):
                pass
            def __repr__(self):
                return "Foo()"
        ''')
        ext = extract_python(p)
        methods = [s for s in ext.symbols if s.kind == "method"]
        assert all(m.visibility == "public" for m in methods)

    def test_private_method(self, tmp_path):
        p = _write_py(tmp_path, '''\
        class Foo:
            def _internal(self):
                pass
        ''')
        ext = extract_python(p)
        method = [s for s in ext.symbols if s.kind == "method"][0]
        assert method.visibility == "private"

    def test_class_line_range(self, tmp_path):
        p = _write_py(tmp_path, '''\
        class Foo:
            def bar(self):
                pass

            def baz(self):
                pass
        ''')
        ext = extract_python(p)
        cls = [s for s in ext.symbols if s.kind == "class"][0]
        assert cls.line_start == 1
        assert cls.line_end >= 5


# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------


class TestImports:

    def test_simple_import(self, tmp_path):
        p = _write_py(tmp_path, "import os\n")
        ext = extract_python(p)
        assert len(ext.imports) == 1
        assert ext.imports[0].module == "os"
        assert ext.imports[0].kind == "import"

    def test_from_import(self, tmp_path):
        p = _write_py(tmp_path, "from pathlib import Path\n")
        ext = extract_python(p)
        assert len(ext.imports) == 1
        assert ext.imports[0].module == "pathlib"
        assert "Path" in ext.imports[0].names
        assert ext.imports[0].kind == "from_import"

    def test_multiple_from_import(self, tmp_path):
        p = _write_py(tmp_path, "from typing import Optional, List, Dict\n")
        ext = extract_python(p)
        assert len(ext.imports) == 1
        assert len(ext.imports[0].names) == 3

    def test_aliased_import(self, tmp_path):
        p = _write_py(tmp_path, "import numpy as np\n")
        ext = extract_python(p)
        assert len(ext.imports) == 1
        assert ext.imports[0].module == "numpy"
        assert ext.imports[0].alias == "np"

    def test_dotted_import(self, tmp_path):
        p = _write_py(tmp_path, "import os.path\n")
        ext = extract_python(p)
        assert ext.imports[0].module == "os.path"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:

    def test_uppercase_constant(self, tmp_path):
        p = _write_py(tmp_path, "MAX_RETRIES = 3\n")
        ext = extract_python(p)
        consts = [s for s in ext.symbols if s.kind == "constant"]
        assert len(consts) == 1
        assert consts[0].name == "MAX_RETRIES"

    def test_lowercase_not_constant(self, tmp_path):
        p = _write_py(tmp_path, "my_var = 42\n")
        ext = extract_python(p)
        consts = [s for s in ext.symbols if s.kind == "constant"]
        assert len(consts) == 0

    def test_dunder_not_constant(self, tmp_path):
        p = _write_py(tmp_path, '__version__ = "1.0.0"\n')
        ext = extract_python(p)
        consts = [s for s in ext.symbols if s.kind == "constant"]
        assert len(consts) == 0  # dunders start with __


# ---------------------------------------------------------------------------
# Call edges
# ---------------------------------------------------------------------------


class TestCallEdges:

    def test_simple_call(self, tmp_path):
        p = _write_py(tmp_path, '''\
        def caller():
            callee()
        def callee():
            pass
        ''')
        ext = extract_python(p)
        assert len(ext.call_edges) >= 1
        edge = ext.call_edges[0]
        assert edge.caller == "caller"
        assert edge.callee == "callee"
        assert edge.confidence == 1.0

    def test_method_call_strips_self(self, tmp_path):
        p = _write_py(tmp_path, '''\
        class Foo:
            def bar(self):
                self.baz()
            def baz(self):
                pass
        ''')
        ext = extract_python(p)
        edges = [e for e in ext.call_edges if e.caller == "bar"]
        assert any(e.callee == "baz" for e in edges)

    def test_attribute_call_preserved(self, tmp_path):
        p = _write_py(tmp_path, '''\
        import os
        def check():
            os.path.exists(".")
        ''')
        ext = extract_python(p)
        edges = [e for e in ext.call_edges if e.caller == "check"]
        assert any("os.path.exists" in e.callee for e in edges)

    def test_no_calls_in_nested_functions(self, tmp_path):
        """Nested function calls should not leak into the parent."""
        p = _write_py(tmp_path, '''\
        def outer():
            def inner():
                deep_call()
            top_call()
        ''')
        ext = extract_python(p)
        outer_edges = [e for e in ext.call_edges if e.caller == "outer"]
        callees = [e.callee for e in outer_edges]
        assert "top_call" in callees
        assert "deep_call" not in callees


# ---------------------------------------------------------------------------
# Rationale comments
# ---------------------------------------------------------------------------


class TestRationaleComments:

    def test_why_comment(self, tmp_path):
        p = _write_py(tmp_path, '''\
        def foo():
            # WHY: Performance optimization
            pass
        ''')
        ext = extract_python(p)
        assert len(ext.rationale_comments) == 1
        rc = ext.rationale_comments[0]
        assert rc.tag == "WHY"
        assert "Performance optimization" in rc.text
        assert rc.context == "foo"

    def test_multiple_tags(self, tmp_path):
        p = _write_py(tmp_path, '''\
        # TODO: Refactor this
        def messy():
            # HACK: Workaround for bug #123
            # NOTE: Revisit after v2
            pass
        ''')
        ext = extract_python(p)
        tags = {rc.tag for rc in ext.rationale_comments}
        assert "TODO" in tags
        assert "HACK" in tags
        assert "NOTE" in tags

    def test_comment_context_is_containing_function(self, tmp_path):
        p = _write_py(tmp_path, '''\
        def outer():
            # WHY: reason in outer
            pass

        class MyClass:
            def method(self):
                # NOTE: reason in method
                pass
        ''')
        ext = extract_python(p)
        by_tag = {rc.tag: rc for rc in ext.rationale_comments}
        assert by_tag["WHY"].context == "outer"
        assert by_tag["NOTE"].context == "method"

    def test_case_insensitive_tags(self, tmp_path):
        p = _write_py(tmp_path, '''\
        # why: lowercase tag
        # Why: mixed case
        # WHY: uppercase
        def f():
            pass
        ''')
        ext = extract_python(p)
        assert len(ext.rationale_comments) == 3
        assert all(rc.tag == "WHY" for rc in ext.rationale_comments)

    def test_non_tagged_comments_ignored(self, tmp_path):
        p = _write_py(tmp_path, '''\
        # This is a regular comment
        # Another regular comment
        def f():
            pass
        ''')
        ext = extract_python(p)
        assert len(ext.rationale_comments) == 0


# ---------------------------------------------------------------------------
# Integration: realistic file
# ---------------------------------------------------------------------------


class TestRealisticFile:

    def test_realistic_python_module(self, tmp_path):
        """A realistic Python module exercises all extraction paths."""
        p = _write_py(tmp_path, '''\
        """User authentication module."""

        import hashlib
        from datetime import datetime, timedelta
        from typing import Optional

        MAX_ATTEMPTS = 5
        TOKEN_EXPIRY_HOURS = 24

        class AuthService:
            """Handles user authentication."""

            def __init__(self, secret: str, db):
                self.secret = secret
                self.db = db

            def authenticate(self, username: str, password: str) -> Optional[str]:
                """Authenticate a user and return a token."""
                # WHY: Hash comparison prevents timing attacks
                user = self.db.find_user(username)
                if user and self._verify_password(password, user.hash):
                    return self._generate_token(user)
                return None

            def _verify_password(self, password: str, stored_hash: str) -> bool:
                # HACK: Using SHA256 for now, switch to bcrypt
                computed = hashlib.sha256(password.encode()).hexdigest()
                return computed == stored_hash

            @staticmethod
            def _generate_token(user) -> str:
                # NOTE: Token format is subject to change
                return f"token_{user.id}_{datetime.now().isoformat()}"

        def create_auth_service(config: dict) -> AuthService:
            """Factory function for AuthService."""
            return AuthService(
                secret=config["secret"],
                db=config["db"],
            )
        ''')

        ext = extract_python(p)
        validate_extraction(ext)

        # Check symbols
        sym_names = {s.name for s in ext.symbols}
        assert "AuthService" in sym_names
        assert "authenticate" in sym_names
        assert "_verify_password" in sym_names
        assert "_generate_token" in sym_names
        assert "create_auth_service" in sym_names
        assert "MAX_ATTEMPTS" in sym_names
        assert "TOKEN_EXPIRY_HOURS" in sym_names

        # Check kinds
        assert any(s.kind == "class" and s.name == "AuthService" for s in ext.symbols)
        assert any(s.kind == "method" and s.name == "authenticate" for s in ext.symbols)
        assert any(s.kind == "function" and s.name == "create_auth_service" for s in ext.symbols)
        assert any(s.kind == "constant" and s.name == "MAX_ATTEMPTS" for s in ext.symbols)

        # Check parent relationships
        auth_method = next(s for s in ext.symbols if s.name == "authenticate")
        assert auth_method.parent == "AuthService"

        # Check visibility
        verify = next(s for s in ext.symbols if s.name == "_verify_password")
        assert verify.visibility == "private"

        # Check imports
        assert len(ext.imports) == 3
        modules = {i.module for i in ext.imports}
        assert "hashlib" in modules
        assert "datetime" in modules
        assert "typing" in modules

        # Check docstrings
        cls = next(s for s in ext.symbols if s.name == "AuthService")
        assert cls.docstring == "Handles user authentication."
        auth = next(s for s in ext.symbols if s.name == "authenticate")
        assert "Authenticate" in (auth.docstring or "")

        # Check call edges
        assert len(ext.call_edges) > 0
        callers = {e.caller for e in ext.call_edges}
        assert "authenticate" in callers

        # Check rationale comments
        assert len(ext.rationale_comments) >= 3
        tags = {rc.tag for rc in ext.rationale_comments}
        assert "WHY" in tags
        assert "HACK" in tags
        assert "NOTE" in tags

        # Check no extraction errors
        assert ext.extraction_errors == []
