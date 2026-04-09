"""Tests for the JavaScript structural extractor (milestone B5).

Covers: function declarations, classes + methods, arrow functions,
ESM imports, CommonJS require, exports (default + named), constants,
call edges, JSDoc docstrings, rationale comments, and a realistic
integration test.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from pensieve.extractors.javascript import extract_javascript
from pensieve.schema import validate_extraction


def _write_js(tmp_path: Path, content: str, name: str = "test.js") -> Path:
    p = tmp_path / name
    p.write_text(dedent(content))
    return p


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


class TestFunctions:

    def test_function_declaration(self, tmp_path):
        p = _write_js(tmp_path, '''\
        function greet(name) {
          return `hello ${name}`;
        }
        ''')
        ext = extract_javascript(p)
        funcs = [s for s in ext.symbols if s.kind == "function"]
        assert len(funcs) == 1
        assert funcs[0].name == "greet"
        assert funcs[0].parent is None
        validate_extraction(ext)

    def test_arrow_function(self, tmp_path):
        p = _write_js(tmp_path, '''\
        const add = (a, b) => a + b;
        ''')
        ext = extract_javascript(p)
        funcs = [s for s in ext.symbols if s.kind == "function"]
        assert len(funcs) == 1
        assert funcs[0].name == "add"
        assert len(funcs[0].parameters) == 2

    def test_arrow_function_with_body(self, tmp_path):
        p = _write_js(tmp_path, '''\
        const process = (items) => {
          return items.map(x => x * 2);
        };
        ''')
        ext = extract_javascript(p)
        funcs = [s for s in ext.symbols if s.kind == "function"]
        assert len(funcs) == 1
        assert funcs[0].name == "process"

    def test_function_parameters(self, tmp_path):
        p = _write_js(tmp_path, '''\
        function calc(a, b = 10, ...rest) {
          return a + b;
        }
        ''')
        ext = extract_javascript(p)
        func = ext.symbols[0]
        param_names = [p.name for p in func.parameters]
        assert "a" in param_names
        assert "b" in param_names
        assert any("rest" in p.name for p in func.parameters)


# ---------------------------------------------------------------------------
# Classes and methods
# ---------------------------------------------------------------------------


class TestClassesAndMethods:

    def test_class_with_methods(self, tmp_path):
        p = _write_js(tmp_path, '''\
        class Calculator {
          add(a, b) {
            return a + b;
          }
          subtract(a, b) {
            return a - b;
          }
        }
        ''')
        ext = extract_javascript(p)
        classes = [s for s in ext.symbols if s.kind == "class"]
        methods = [s for s in ext.symbols if s.kind == "method"]
        assert len(classes) == 1
        assert classes[0].name == "Calculator"
        assert len(methods) == 2
        assert all(m.parent == "Calculator" for m in methods)

    def test_constructor(self, tmp_path):
        p = _write_js(tmp_path, '''\
        class Foo {
          constructor(x) {
            this.x = x;
          }
        }
        ''')
        ext = extract_javascript(p)
        methods = [s for s in ext.symbols if s.kind == "method"]
        assert any(m.name == "constructor" for m in methods)

    def test_static_method(self, tmp_path):
        p = _write_js(tmp_path, '''\
        class Factory {
          static create(config) {
            return new Factory(config);
          }
        }
        ''')
        ext = extract_javascript(p)
        methods = [s for s in ext.symbols if s.kind == "method"]
        assert len(methods) == 1
        assert methods[0].name == "create"
        assert methods[0].parent == "Factory"

    def test_async_method(self, tmp_path):
        p = _write_js(tmp_path, '''\
        class Api {
          async fetch(url) {
            return await fetch(url);
          }
        }
        ''')
        ext = extract_javascript(p)
        methods = [s for s in ext.symbols if s.kind == "method"]
        assert len(methods) == 1
        assert methods[0].name == "fetch"


# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------


class TestImports:

    def test_esm_named_import(self, tmp_path):
        p = _write_js(tmp_path, "import { useState, useEffect } from 'react';\n")
        ext = extract_javascript(p)
        assert len(ext.imports) == 1
        assert ext.imports[0].module == "react"
        assert "useState" in ext.imports[0].names
        assert "useEffect" in ext.imports[0].names

    def test_esm_default_import(self, tmp_path):
        p = _write_js(tmp_path, "import path from 'path';\n")
        ext = extract_javascript(p)
        assert len(ext.imports) == 1
        assert ext.imports[0].module == "path"
        assert ext.imports[0].alias == "path"

    def test_esm_namespace_import(self, tmp_path):
        p = _write_js(tmp_path, "import * as fs from 'fs';\n")
        ext = extract_javascript(p)
        assert len(ext.imports) == 1
        assert ext.imports[0].module == "fs"
        assert ext.imports[0].alias == "fs"

    def test_commonjs_require(self, tmp_path):
        p = _write_js(tmp_path, "const axios = require('axios');\n")
        ext = extract_javascript(p)
        assert len(ext.imports) == 1
        assert ext.imports[0].module == "axios"
        assert ext.imports[0].kind == "require"


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------


class TestExports:

    def test_default_export(self, tmp_path):
        p = _write_js(tmp_path, '''\
        class Foo {}
        export default Foo;
        ''')
        ext = extract_javascript(p)
        defaults = [e for e in ext.exports if e.kind == "default"]
        assert len(defaults) == 1
        assert defaults[0].name == "Foo"

    def test_named_exports(self, tmp_path):
        p = _write_js(tmp_path, '''\
        function a() {}
        function b() {}
        export { a, b };
        ''')
        ext = extract_javascript(p)
        named = [e for e in ext.exports if e.kind == "named"]
        assert len(named) == 2
        assert {e.name for e in named} == {"a", "b"}

    def test_export_function_declaration(self, tmp_path):
        p = _write_js(tmp_path, '''\
        export function helper() {
          return 42;
        }
        ''')
        ext = extract_javascript(p)
        assert any(e.name == "helper" for e in ext.exports)
        assert any(s.name == "helper" and s.kind == "function" for s in ext.symbols)

    def test_exported_symbol_visibility_is_public(self, tmp_path):
        p = _write_js(tmp_path, '''\
        function internal() {}
        function external() {}
        export { external };
        ''')
        ext = extract_javascript(p)
        internal = next(s for s in ext.symbols if s.name == "internal")
        external = next(s for s in ext.symbols if s.name == "external")
        assert external.visibility == "public"
        assert internal.visibility != "public"  # not exported


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:

    def test_uppercase_constant(self, tmp_path):
        p = _write_js(tmp_path, "const MAX_RETRIES = 3;\n")
        ext = extract_javascript(p)
        consts = [s for s in ext.symbols if s.kind == "constant"]
        assert len(consts) == 1
        assert consts[0].name == "MAX_RETRIES"

    def test_lowercase_not_constant(self, tmp_path):
        p = _write_js(tmp_path, "const myVar = 42;\n")
        ext = extract_javascript(p)
        consts = [s for s in ext.symbols if s.kind == "constant"]
        assert len(consts) == 0

    def test_require_not_constant(self, tmp_path):
        p = _write_js(tmp_path, "const AXIOS = require('axios');\n")
        ext = extract_javascript(p)
        consts = [s for s in ext.symbols if s.kind == "constant"]
        assert len(consts) == 0  # require is an import, not a constant


# ---------------------------------------------------------------------------
# Call edges
# ---------------------------------------------------------------------------


class TestCallEdges:

    def test_simple_call(self, tmp_path):
        p = _write_js(tmp_path, '''\
        function caller() {
          callee();
        }
        function callee() {}
        ''')
        ext = extract_javascript(p)
        edges = [e for e in ext.call_edges if e.caller == "caller"]
        assert any(e.callee == "callee" for e in edges)

    def test_this_call_stripped(self, tmp_path):
        p = _write_js(tmp_path, '''\
        class Foo {
          bar() {
            this.baz();
          }
          baz() {}
        }
        ''')
        ext = extract_javascript(p)
        edges = [e for e in ext.call_edges if e.caller == "bar"]
        assert any(e.callee == "baz" for e in edges)

    def test_arrow_function_calls(self, tmp_path):
        p = _write_js(tmp_path, '''\
        const process = (data) => {
          return transform(data);
        };
        function transform(x) { return x; }
        ''')
        ext = extract_javascript(p)
        edges = [e for e in ext.call_edges if e.caller == "process"]
        assert any(e.callee == "transform" for e in edges)


# ---------------------------------------------------------------------------
# JSDoc docstrings
# ---------------------------------------------------------------------------


class TestJSDoc:

    def test_jsdoc_on_function(self, tmp_path):
        p = _write_js(tmp_path, '''\
        /**
         * Adds two numbers.
         */
        function add(a, b) {
          return a + b;
        }
        ''')
        ext = extract_javascript(p)
        func = ext.symbols[0]
        assert func.docstring is not None
        assert "Adds two numbers" in func.docstring

    def test_jsdoc_on_class(self, tmp_path):
        p = _write_js(tmp_path, '''\
        /**
         * A user service.
         */
        class UserService {
          find(id) {}
        }
        ''')
        ext = extract_javascript(p)
        cls = next(s for s in ext.symbols if s.kind == "class")
        assert cls.docstring is not None
        assert "user service" in cls.docstring.lower()

    def test_regular_comment_not_docstring(self, tmp_path):
        p = _write_js(tmp_path, '''\
        // This is a regular comment
        function foo() {}
        ''')
        ext = extract_javascript(p)
        assert ext.symbols[0].docstring is None


# ---------------------------------------------------------------------------
# Rationale comments
# ---------------------------------------------------------------------------


class TestRationaleComments:

    def test_single_line_comment(self, tmp_path):
        p = _write_js(tmp_path, '''\
        function foo() {
          // WHY: Performance optimization
          return 42;
        }
        ''')
        ext = extract_javascript(p)
        assert len(ext.rationale_comments) == 1
        rc = ext.rationale_comments[0]
        assert rc.tag == "WHY"
        assert "Performance" in rc.text
        assert rc.context == "foo"

    def test_multiple_tags(self, tmp_path):
        p = _write_js(tmp_path, '''\
        function messy() {
          // HACK: Workaround for issue #42
          // TODO: Clean this up
          return null;
        }
        ''')
        ext = extract_javascript(p)
        tags = {rc.tag for rc in ext.rationale_comments}
        assert "HACK" in tags
        assert "TODO" in tags


# ---------------------------------------------------------------------------
# Integration: realistic file
# ---------------------------------------------------------------------------


class TestRealisticFile:

    def test_realistic_js_module(self, tmp_path):
        p = _write_js(tmp_path, '''\
        import { EventEmitter } from 'events';
        const lodash = require('lodash');

        const MAX_LISTENERS = 100;

        /**
         * An event-driven notification service.
         */
        class NotificationService extends EventEmitter {
          constructor(config) {
            super();
            this.config = config;
          }

          /**
           * Send a notification to a user.
           */
          async send(userId, message) {
            // WHY: Rate limiting prevents abuse
            const user = await this.findUser(userId);
            lodash.template(message)({ user });
            this.emit('sent', { userId, message });
          }

          findUser(id) {
            // HACK: Hardcoded for now
            return { id, name: 'test' };
          }
        }

        const formatMessage = (template, data) => {
          // NOTE: Uses lodash templates internally
          return lodash.template(template)(data);
        };

        export default NotificationService;
        export { formatMessage, MAX_LISTENERS };
        ''')

        ext = extract_javascript(p)
        validate_extraction(ext)

        # Symbols
        sym_names = {s.name for s in ext.symbols}
        assert "NotificationService" in sym_names
        assert "send" in sym_names
        assert "findUser" in sym_names
        assert "constructor" in sym_names
        assert "formatMessage" in sym_names
        assert "MAX_LISTENERS" in sym_names

        # Kinds
        assert any(s.kind == "class" for s in ext.symbols)
        assert any(s.kind == "method" and s.parent == "NotificationService" for s in ext.symbols)
        assert any(s.kind == "function" and s.name == "formatMessage" for s in ext.symbols)
        assert any(s.kind == "constant" for s in ext.symbols)

        # Imports
        assert len(ext.imports) == 2
        modules = {i.module for i in ext.imports}
        assert "events" in modules
        assert "lodash" in modules

        # Exports
        assert any(e.kind == "default" and e.name == "NotificationService" for e in ext.exports)
        assert any(e.kind == "named" and e.name == "formatMessage" for e in ext.exports)

        # Visibility from exports
        ns = next(s for s in ext.symbols if s.name == "NotificationService")
        assert ns.visibility == "public"  # default exported
        fm = next(s for s in ext.symbols if s.name == "formatMessage")
        assert fm.visibility == "public"  # named exported

        # Call edges
        assert len(ext.call_edges) > 0

        # Rationale comments
        tags = {rc.tag for rc in ext.rationale_comments}
        assert "WHY" in tags
        assert "HACK" in tags
        assert "NOTE" in tags

        # JSDoc
        cls = next(s for s in ext.symbols if s.kind == "class")
        assert cls.docstring is not None
        assert "notification" in cls.docstring.lower()
