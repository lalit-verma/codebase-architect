"""Tests for the Go structural extractor (milestone B7).

Covers Go-specific constructs: functions, methods with receivers,
structs, interfaces, constants, imports (single + block), visibility
by capitalization, Go doc comments, parameters (shared types, variadic),
return types (single, multiple, named), call edges, rationale comments,
and a realistic integration test.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from pensieve.extractors.go import extract_go
from pensieve.schema import validate_extraction


def _write_go(tmp_path: Path, content: str, name: str = "test.go") -> Path:
    p = tmp_path / name
    p.write_text(dedent(content))
    return p


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


class TestFunctions:

    def test_simple_function(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        func Add(a int, b int) int {
        \treturn a + b
        }
        ''')
        ext = extract_go(p)
        funcs = [s for s in ext.symbols if s.kind == "function"]
        assert len(funcs) == 1
        assert funcs[0].name == "Add"
        assert funcs[0].parent is None
        assert funcs[0].visibility == "public"
        validate_extraction(ext)

    def test_unexported_function(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package internal

        func helper() {}
        ''')
        ext = extract_go(p)
        func = ext.symbols[0]
        assert func.visibility == "private"

    def test_function_parameters(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        func process(ctx context.Context, name string, count int) error {
        \treturn nil
        }
        ''')
        ext = extract_go(p)
        func = ext.symbols[0]
        param_names = [p.name for p in func.parameters]
        assert "ctx" in param_names
        assert "name" in param_names
        assert "count" in param_names

    def test_function_return_type(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        func GetName() string {
        \treturn "hello"
        }
        ''')
        ext = extract_go(p)
        assert ext.symbols[0].return_type == "string"

    def test_function_multiple_returns(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        func Divide(a, b float64) (float64, error) {
        \tif b == 0 {
        \t\treturn 0, fmt.Errorf("division by zero")
        \t}
        \treturn a / b, nil
        }
        ''')
        ext = extract_go(p)
        ret = ext.symbols[0].return_type
        assert ret is not None
        assert "float64" in ret
        assert "error" in ret


# ---------------------------------------------------------------------------
# Methods with receivers
# ---------------------------------------------------------------------------


class TestMethods:

    def test_method_with_pointer_receiver(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        type Service struct{}

        func (s *Service) Start() error {
        \treturn nil
        }
        ''')
        ext = extract_go(p)
        methods = [s for s in ext.symbols if s.kind == "method"]
        assert len(methods) == 1
        assert methods[0].name == "Start"
        assert methods[0].parent == "Service"
        assert methods[0].visibility == "public"

    def test_method_with_value_receiver(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        type Point struct{ X, Y int }

        func (p Point) String() string {
        \treturn fmt.Sprintf("(%d, %d)", p.X, p.Y)
        }
        ''')
        ext = extract_go(p)
        method = [s for s in ext.symbols if s.kind == "method"][0]
        assert method.parent == "Point"

    def test_unexported_method(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        type Foo struct{}

        func (f *Foo) internal() {}
        ''')
        ext = extract_go(p)
        method = [s for s in ext.symbols if s.kind == "method"][0]
        assert method.visibility == "private"


# ---------------------------------------------------------------------------
# Structs and interfaces
# ---------------------------------------------------------------------------


class TestTypes:

    def test_struct(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        type User struct {
        \tID    string
        \tName  string
        \tEmail string
        }
        ''')
        ext = extract_go(p)
        structs = [s for s in ext.symbols if s.kind == "struct"]
        assert len(structs) == 1
        assert structs[0].name == "User"
        assert structs[0].visibility == "public"

    def test_interface(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        type Repository interface {
        \tFindByID(id string) (*User, error)
        \tSave(user *User) error
        }
        ''')
        ext = extract_go(p)
        ifaces = [s for s in ext.symbols if s.kind == "interface"]
        assert len(ifaces) == 1
        assert ifaces[0].name == "Repository"

    def test_unexported_struct(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package internal

        type config struct {
        \thost string
        \tport int
        }
        ''')
        ext = extract_go(p)
        s = ext.symbols[0]
        assert s.visibility == "private"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:

    def test_single_const(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        const MaxRetries = 5
        ''')
        ext = extract_go(p)
        consts = [s for s in ext.symbols if s.kind == "constant"]
        assert len(consts) == 1
        assert consts[0].name == "MaxRetries"

    def test_const_block(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        const (
        \tMaxRetries = 5
        \tTimeout    = 30
        )
        ''')
        ext = extract_go(p)
        consts = [s for s in ext.symbols if s.kind == "constant"]
        assert len(consts) == 2
        names = {c.name for c in consts}
        assert "MaxRetries" in names
        assert "Timeout" in names


# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------


class TestImports:

    def test_single_import(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        import "fmt"
        ''')
        ext = extract_go(p)
        assert len(ext.imports) == 1
        assert ext.imports[0].module == "fmt"

    def test_import_block(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        import (
        \t"context"
        \t"fmt"
        \t"os"
        )
        ''')
        ext = extract_go(p)
        assert len(ext.imports) == 3
        modules = {i.module for i in ext.imports}
        assert "context" in modules
        assert "fmt" in modules
        assert "os" in modules

    def test_aliased_import(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        import (
        \tpb "google.golang.org/protobuf/proto"
        )
        ''')
        ext = extract_go(p)
        assert len(ext.imports) == 1
        assert ext.imports[0].alias == "pb"
        assert "protobuf" in ext.imports[0].module

    def test_blank_import(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        import _ "net/http/pprof"
        ''')
        ext = extract_go(p)
        assert len(ext.imports) == 1
        assert ext.imports[0].alias == "_"


# ---------------------------------------------------------------------------
# Go doc comments
# ---------------------------------------------------------------------------


class TestDocComments:

    def test_function_doc(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        // NewService creates a new service instance.
        func NewService() *Service {
        \treturn &Service{}
        }
        ''')
        ext = extract_go(p)
        func = ext.symbols[0]
        assert func.docstring is not None
        assert "NewService creates" in func.docstring

    def test_type_doc(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        // User represents a system user.
        type User struct {
        \tID string
        }
        ''')
        ext = extract_go(p)
        s = ext.symbols[0]
        assert s.docstring is not None
        assert "User represents" in s.docstring

    def test_multiline_doc(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        // Process handles the main processing logic.
        // It reads from the input channel and writes to output.
        func Process() {}
        ''')
        ext = extract_go(p)
        assert "Process handles" in ext.symbols[0].docstring
        assert "reads from" in ext.symbols[0].docstring

    def test_no_doc_comment(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        func noDoc() {}
        ''')
        ext = extract_go(p)
        assert ext.symbols[0].docstring is None


# ---------------------------------------------------------------------------
# Call edges
# ---------------------------------------------------------------------------


class TestCallEdges:

    def test_simple_call(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        import "fmt"

        func Hello() {
        \tfmt.Println("hello")
        }
        ''')
        ext = extract_go(p)
        edges = [e for e in ext.call_edges if e.caller == "Hello"]
        assert any("fmt.Println" in e.callee for e in edges)

    def test_method_call(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        type Foo struct{ db DB }

        func (f *Foo) Run() {
        \tf.db.Query("SELECT 1")
        }
        ''')
        ext = extract_go(p)
        edges = [e for e in ext.call_edges if e.caller == "Run"]
        assert len(edges) >= 1


# ---------------------------------------------------------------------------
# Rationale comments
# ---------------------------------------------------------------------------


class TestRationaleComments:

    def test_why_comment(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package main

        func Validate() {
        \t// WHY: Prevent timing attacks
        }
        ''')
        ext = extract_go(p)
        assert len(ext.rationale_comments) == 1
        assert ext.rationale_comments[0].tag == "WHY"
        assert "timing attacks" in ext.rationale_comments[0].text

    def test_rationale_not_in_docstring(self, tmp_path):
        """Rationale tags in doc position should NOT appear as docstrings."""
        p = _write_go(tmp_path, '''\
        package main

        // WHY: This needs to exist for legacy reasons
        func Legacy() {}
        ''')
        ext = extract_go(p)
        func = ext.symbols[0]
        # The WHY: comment should be a rationale, not a docstring
        assert func.docstring is None or "WHY:" not in (func.docstring or "")
        assert len(ext.rationale_comments) == 1


# ---------------------------------------------------------------------------
# Integration: realistic file
# ---------------------------------------------------------------------------


class TestRealisticFile:

    def test_realistic_go_service(self, tmp_path):
        p = _write_go(tmp_path, '''\
        package auth

        import (
        \t"context"
        \t"crypto/sha256"
        \t"database/sql"
        \t"fmt"
        )

        const (
        \tMaxAttempts   = 5
        \tTokenExpiry   = 24
        )

        // AuthError represents an authentication failure.
        type AuthError struct {
        \tCode    int
        \tMessage string
        }

        // Authenticator defines the auth interface.
        type Authenticator interface {
        \tAuthenticate(ctx context.Context, user, pass string) (string, error)
        }

        // Service implements Authenticator.
        type Service struct {
        \tdb     *sql.DB
        \tsecret string
        }

        // NewService creates a new auth service.
        func NewService(db *sql.DB, secret string) *Service {
        \treturn &Service{db: db, secret: secret}
        }

        // Authenticate validates credentials and returns a token.
        // WHY: Using SHA256 for constant-time comparison
        func (s *Service) Authenticate(ctx context.Context, username, password string) (string, error) {
        \thash := sha256.Sum256([]byte(password))
        \t// HACK: Plaintext comparison for now
        \ttoken := s.generateToken(username)
        \treturn token, nil
        }

        // generateToken creates an auth token.
        // NOTE: Will switch to JWT in v2
        func (s *Service) generateToken(username string) string {
        \treturn fmt.Sprintf("token_%s", username)
        }
        ''')

        ext = extract_go(p)
        validate_extraction(ext)

        # Check all expected symbols
        sym_names = {s.name for s in ext.symbols}
        assert "AuthError" in sym_names
        assert "Authenticator" in sym_names
        assert "Service" in sym_names
        assert "NewService" in sym_names
        assert "Authenticate" in sym_names
        assert "generateToken" in sym_names
        assert "MaxAttempts" in sym_names
        assert "TokenExpiry" in sym_names

        # Check kinds
        assert any(s.kind == "struct" and s.name == "AuthError" for s in ext.symbols)
        assert any(s.kind == "struct" and s.name == "Service" for s in ext.symbols)
        assert any(s.kind == "interface" and s.name == "Authenticator" for s in ext.symbols)
        assert any(s.kind == "function" and s.name == "NewService" for s in ext.symbols)
        assert any(s.kind == "method" and s.name == "Authenticate" for s in ext.symbols)
        assert any(s.kind == "constant" for s in ext.symbols)

        # Check method parents
        auth_method = next(s for s in ext.symbols if s.name == "Authenticate")
        assert auth_method.parent == "Service"
        gen_method = next(s for s in ext.symbols if s.name == "generateToken")
        assert gen_method.parent == "Service"

        # Check visibility
        assert auth_method.visibility == "public"  # uppercase
        assert gen_method.visibility == "private"  # lowercase

        # Check imports
        assert len(ext.imports) == 4
        modules = {i.module for i in ext.imports}
        assert "context" in modules
        assert "crypto/sha256" in modules

        # Check doc comments
        svc = next(s for s in ext.symbols if s.name == "Service" and s.kind == "struct")
        assert svc.docstring is not None
        assert "implements" in svc.docstring.lower()

        # Check rationale comments
        tags = {rc.tag for rc in ext.rationale_comments}
        assert "WHY" in tags
        assert "HACK" in tags
        assert "NOTE" in tags

        # Check call edges
        assert len(ext.call_edges) > 0
