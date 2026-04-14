"""Tests for the Java structural extractor (milestone B8).

Covers: classes + methods, constructors, interfaces, enums, access
modifiers (public/private/protected/package-private), imports,
constants (static final), Javadoc, parameters with types, return types,
call edges (method_invocation + object_creation), rationale comments,
annotations in signatures, and a realistic integration test.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from pensieve.extractors.java import extract_java
from pensieve.schema import validate_extraction


def _write_java(tmp_path: Path, content: str, name: str = "Test.java") -> Path:
    p = tmp_path / name
    p.write_text(dedent(content))
    return p


# ---------------------------------------------------------------------------
# Classes and methods
# ---------------------------------------------------------------------------


class TestClassesAndMethods:

    def test_class_with_method(self, tmp_path):
        p = _write_java(tmp_path, '''\
        public class Calculator {
            public int add(int a, int b) {
                return a + b;
            }
        }
        ''')
        ext = extract_java(p)
        classes = [s for s in ext.symbols if s.kind == "class"]
        methods = [s for s in ext.symbols if s.kind == "method"]
        assert len(classes) == 1
        assert classes[0].name == "Calculator"
        assert len(methods) == 1
        assert methods[0].name == "add"
        assert methods[0].parent == "Calculator"
        validate_extraction(ext)

    def test_constructor(self, tmp_path):
        p = _write_java(tmp_path, '''\
        public class Foo {
            public Foo(String name) {
                this.name = name;
            }
        }
        ''')
        ext = extract_java(p)
        methods = [s for s in ext.symbols if s.kind == "method"]
        assert any(m.name == "Foo" and m.parent == "Foo" for m in methods)

    def test_multiple_methods(self, tmp_path):
        p = _write_java(tmp_path, '''\
        public class Service {
            public void start() {}
            public void stop() {}
            private void cleanup() {}
        }
        ''')
        ext = extract_java(p)
        methods = [s for s in ext.symbols if s.kind == "method"]
        assert len(methods) == 3
        assert all(m.parent == "Service" for m in methods)


# ---------------------------------------------------------------------------
# Visibility
# ---------------------------------------------------------------------------


class TestVisibility:

    def test_public_class(self, tmp_path):
        p = _write_java(tmp_path, "public class Foo {}\n")
        ext = extract_java(p)
        assert ext.symbols[0].visibility == "public"

    def test_private_method(self, tmp_path):
        p = _write_java(tmp_path, '''\
        public class Foo {
            private void secret() {}
        }
        ''')
        ext = extract_java(p)
        method = [s for s in ext.symbols if s.kind == "method"][0]
        assert method.visibility == "private"

    def test_protected_method(self, tmp_path):
        p = _write_java(tmp_path, '''\
        public class Base {
            protected void init() {}
        }
        ''')
        ext = extract_java(p)
        method = [s for s in ext.symbols if s.kind == "method"][0]
        assert method.visibility == "protected"

    def test_package_private(self, tmp_path):
        p = _write_java(tmp_path, '''\
        class PackageClass {
            void packageMethod() {}
        }
        ''')
        ext = extract_java(p)
        cls = [s for s in ext.symbols if s.kind == "class"][0]
        assert cls.visibility == "package"
        method = [s for s in ext.symbols if s.kind == "method"][0]
        assert method.visibility == "package"


# ---------------------------------------------------------------------------
# Interfaces and enums
# ---------------------------------------------------------------------------


class TestInterfacesAndEnums:

    def test_interface(self, tmp_path):
        p = _write_java(tmp_path, '''\
        public interface Repository {
            User findById(long id);
            void save(User entity);
        }
        ''')
        ext = extract_java(p)
        ifaces = [s for s in ext.symbols if s.kind == "interface"]
        assert len(ifaces) == 1
        assert ifaces[0].name == "Repository"
        methods = [s for s in ext.symbols if s.kind == "method"]
        assert len(methods) == 2
        assert all(m.parent == "Repository" for m in methods)

    def test_enum(self, tmp_path):
        p = _write_java(tmp_path, '''\
        public enum Status {
            ACTIVE,
            INACTIVE
        }
        ''')
        ext = extract_java(p)
        enums = [s for s in ext.symbols if s.kind == "enum"]
        assert len(enums) == 1
        assert enums[0].name == "Status"
        assert enums[0].visibility == "public"


# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------


class TestImports:

    def test_single_import(self, tmp_path):
        p = _write_java(tmp_path, '''\
        import java.util.List;

        public class Foo {}
        ''')
        ext = extract_java(p)
        assert len(ext.imports) == 1
        assert ext.imports[0].module == "java.util"
        assert "List" in ext.imports[0].names

    def test_multiple_imports(self, tmp_path):
        p = _write_java(tmp_path, '''\
        import java.util.List;
        import java.util.Optional;
        import java.io.IOException;

        public class Foo {}
        ''')
        ext = extract_java(p)
        assert len(ext.imports) == 3
        modules = {i.module for i in ext.imports}
        assert "java.util" in modules
        assert "java.io" in modules


# ---------------------------------------------------------------------------
# Parameters and return types
# ---------------------------------------------------------------------------


class TestParamsAndReturnTypes:

    def test_method_parameters(self, tmp_path):
        p = _write_java(tmp_path, '''\
        public class Foo {
            public void process(String name, int count, boolean flag) {}
        }
        ''')
        ext = extract_java(p)
        method = [s for s in ext.symbols if s.kind == "method"][0]
        param_names = [p.name for p in method.parameters]
        assert "name" in param_names
        assert "count" in param_names
        assert "flag" in param_names
        assert any(p.type == "String" for p in method.parameters)
        assert any(p.type == "int" for p in method.parameters)

    def test_method_return_type(self, tmp_path):
        p = _write_java(tmp_path, '''\
        public class Foo {
            public String getName() { return ""; }
        }
        ''')
        ext = extract_java(p)
        method = [s for s in ext.symbols if s.kind == "method"][0]
        assert method.return_type == "String"

    def test_void_return_type(self, tmp_path):
        p = _write_java(tmp_path, '''\
        public class Foo {
            public void doNothing() {}
        }
        ''')
        ext = extract_java(p)
        method = [s for s in ext.symbols if s.kind == "method"][0]
        assert method.return_type == "void"

    def test_generic_return_type(self, tmp_path):
        p = _write_java(tmp_path, '''\
        import java.util.Optional;
        public class Foo {
            public Optional<String> find() { return Optional.empty(); }
        }
        ''')
        ext = extract_java(p)
        method = [s for s in ext.symbols if s.kind == "method"][0]
        assert method.return_type is not None
        assert "Optional" in method.return_type


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:

    def test_static_final_constant(self, tmp_path):
        p = _write_java(tmp_path, '''\
        public class Config {
            public static final int MAX_RETRIES = 5;
        }
        ''')
        ext = extract_java(p)
        consts = [s for s in ext.symbols if s.kind == "constant"]
        assert len(consts) == 1
        assert consts[0].name == "MAX_RETRIES"

    def test_non_static_final_not_constant(self, tmp_path):
        p = _write_java(tmp_path, '''\
        public class Config {
            private final String name = "test";
        }
        ''')
        ext = extract_java(p)
        consts = [s for s in ext.symbols if s.kind == "constant"]
        assert len(consts) == 0  # not static

    def test_lowercase_not_constant(self, tmp_path):
        p = _write_java(tmp_path, '''\
        public class Config {
            public static final String name = "test";
        }
        ''')
        ext = extract_java(p)
        consts = [s for s in ext.symbols if s.kind == "constant"]
        assert len(consts) == 0  # not ALL_CAPS


# ---------------------------------------------------------------------------
# Javadoc
# ---------------------------------------------------------------------------


class TestJavadoc:

    def test_class_javadoc(self, tmp_path):
        p = _write_java(tmp_path, '''\
        /**
         * A service for user management.
         */
        public class UserService {}
        ''')
        ext = extract_java(p)
        cls = ext.symbols[0]
        assert cls.docstring is not None
        assert "user management" in cls.docstring.lower()

    def test_method_javadoc(self, tmp_path):
        p = _write_java(tmp_path, '''\
        public class Foo {
            /**
             * Process the input data.
             * @param data the input
             * @return processed result
             */
            public String process(String data) { return data; }
        }
        ''')
        ext = extract_java(p)
        method = [s for s in ext.symbols if s.kind == "method"][0]
        assert method.docstring is not None
        assert "Process" in method.docstring
        # @param and @return should be stripped
        assert "@param" not in method.docstring

    def test_no_javadoc(self, tmp_path):
        p = _write_java(tmp_path, '''\
        public class Foo {
            public void bar() {}
        }
        ''')
        ext = extract_java(p)
        method = [s for s in ext.symbols if s.kind == "method"][0]
        assert method.docstring is None


# ---------------------------------------------------------------------------
# Call edges
# ---------------------------------------------------------------------------


class TestCallEdges:

    def test_method_invocation(self, tmp_path):
        p = _write_java(tmp_path, '''\
        public class Foo {
            public void caller() {
                callee();
            }
            private void callee() {}
        }
        ''')
        ext = extract_java(p)
        edges = [e for e in ext.call_edges if e.caller == "caller"]
        assert any(e.callee == "callee" for e in edges)

    def test_this_method_call(self, tmp_path):
        p = _write_java(tmp_path, '''\
        public class Foo {
            public void bar() {
                this.baz();
            }
            private void baz() {}
        }
        ''')
        ext = extract_java(p)
        edges = [e for e in ext.call_edges if e.caller == "bar"]
        assert any(e.callee == "baz" for e in edges)

    def test_object_method_call(self, tmp_path):
        p = _write_java(tmp_path, '''\
        public class Foo {
            public void run() {
                db.query("SELECT 1");
            }
        }
        ''')
        ext = extract_java(p)
        edges = [e for e in ext.call_edges if e.caller == "run"]
        assert any("db.query" in e.callee for e in edges)


# ---------------------------------------------------------------------------
# Rationale comments
# ---------------------------------------------------------------------------


class TestRationaleComments:

    def test_line_comment(self, tmp_path):
        p = _write_java(tmp_path, '''\
        public class Foo {
            public void bar() {
                // WHY: Prevent race condition
            }
        }
        ''')
        ext = extract_java(p)
        assert len(ext.rationale_comments) == 1
        assert ext.rationale_comments[0].tag == "WHY"
        assert "race condition" in ext.rationale_comments[0].text

    def test_multiple_tags(self, tmp_path):
        p = _write_java(tmp_path, '''\
        public class Foo {
            public void bar() {
                // HACK: Temporary workaround
                // TODO: Fix this properly
            }
        }
        ''')
        ext = extract_java(p)
        tags = {rc.tag for rc in ext.rationale_comments}
        assert "HACK" in tags
        assert "TODO" in tags


# ---------------------------------------------------------------------------
# Annotations in signatures
# ---------------------------------------------------------------------------


class TestAnnotations:

    def test_annotated_method_signature(self, tmp_path):
        p = _write_java(tmp_path, '''\
        public class Foo {
            @Override
            public String toString() { return ""; }
        }
        ''')
        ext = extract_java(p)
        method = [s for s in ext.symbols if s.kind == "method"][0]
        assert "@Override" in method.signature


# ---------------------------------------------------------------------------
# Integration: realistic file
# ---------------------------------------------------------------------------


class TestRealisticFile:

    def test_realistic_java_service(self, tmp_path):
        p = _write_java(tmp_path, '''\
        import java.util.Optional;
        import java.util.List;
        import javax.inject.Inject;

        /**
         * User authentication service.
         */
        public class AuthService implements Authenticator {

            private static final int MAX_ATTEMPTS = 5;
            private final Database db;

            @Inject
            public AuthService(Database db) {
                this.db = db;
            }

            /**
             * Authenticate a user.
             */
            @Override
            public Optional<String> authenticate(String username, String password) {
                // WHY: Constant-time comparison prevents timing attacks
                User user = db.findByUsername(username);
                if (user != null && verifyPassword(password, user.getHash())) {
                    return Optional.of(generateToken(user));
                }
                return Optional.empty();
            }

            private boolean verifyPassword(String password, String hash) {
                // HACK: Using simple comparison for now
                return password.hashCode() == hash.hashCode();
            }

            // NOTE: Token format subject to change
            private String generateToken(User user) {
                return "token_" + user.getId();
            }
        }

        public interface Authenticator {
            Optional<String> authenticate(String username, String password);
        }

        public enum Role {
            ADMIN,
            USER,
            GUEST
        }
        ''', name="AuthService.java")

        ext = extract_java(p)
        validate_extraction(ext)

        # Check symbol names
        sym_names = {s.name for s in ext.symbols}
        assert "AuthService" in sym_names
        assert "authenticate" in sym_names
        assert "verifyPassword" in sym_names
        assert "generateToken" in sym_names
        assert "Authenticator" in sym_names
        assert "Role" in sym_names
        assert "MAX_ATTEMPTS" in sym_names

        # Check kinds
        kinds = {s.kind for s in ext.symbols}
        assert "class" in kinds
        assert "method" in kinds
        assert "interface" in kinds
        assert "enum" in kinds
        assert "constant" in kinds

        # Check visibility
        verify = next(s for s in ext.symbols if s.name == "verifyPassword")
        assert verify.visibility == "private"
        auth = next(s for s in ext.symbols if s.name == "authenticate")
        assert auth.visibility == "public"
        cls = next(s for s in ext.symbols if s.name == "AuthService")
        assert cls.visibility == "public"

        # Check return types
        assert auth.return_type is not None
        assert "Optional" in auth.return_type
        assert verify.return_type == "boolean"

        # Check imports
        assert len(ext.imports) == 3
        modules = {i.module for i in ext.imports}
        assert "java.util" in modules

        # Check Javadoc
        assert cls.docstring is not None
        assert "authentication" in cls.docstring.lower()
        assert auth.docstring is not None

        # Check rationale
        tags = {rc.tag for rc in ext.rationale_comments}
        assert "WHY" in tags
        assert "HACK" in tags
        assert "NOTE" in tags

        # Check call edges
        assert len(ext.call_edges) > 0
        callers = {e.caller for e in ext.call_edges}
        assert "authenticate" in callers
