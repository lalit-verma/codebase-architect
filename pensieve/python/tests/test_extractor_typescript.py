"""Tests for the TypeScript structural extractor (milestone B6).

Covers TS-specific constructs: interfaces, type aliases, enums,
accessibility modifiers (public/private/protected), type annotations
on parameters and return types, import type, TSX parsing, plus all
the JS-compatible constructs (functions, classes, methods, arrow fns,
imports, exports, constants, call edges, JSDoc, rationale comments).
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from pensieve.extractors.typescript import extract_typescript
from pensieve.schema import validate_extraction


def _write_ts(tmp_path: Path, content: str, name: str = "test.ts") -> Path:
    p = tmp_path / name
    p.write_text(dedent(content))
    return p


# ---------------------------------------------------------------------------
# Interfaces
# ---------------------------------------------------------------------------


class TestInterfaces:

    def test_interface_extracted(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        interface User {
          id: string;
          name: string;
        }
        ''')
        ext = extract_typescript(p)
        ifaces = [s for s in ext.symbols if s.kind == "interface"]
        assert len(ifaces) == 1
        assert ifaces[0].name == "User"
        validate_extraction(ext)

    def test_generic_interface(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        interface Repository<T> {
          findById(id: string): Promise<T | null>;
          save(entity: T): Promise<void>;
        }
        ''')
        ext = extract_typescript(p)
        ifaces = [s for s in ext.symbols if s.kind == "interface"]
        assert len(ifaces) == 1
        assert ifaces[0].name == "Repository"

    def test_exported_interface(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        export interface Config {
          port: number;
          host: string;
        }
        ''')
        ext = extract_typescript(p)
        ifaces = [s for s in ext.symbols if s.kind == "interface"]
        assert len(ifaces) == 1
        assert ifaces[0].name == "Config"
        assert ifaces[0].visibility == "public"


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------


class TestTypeAliases:

    def test_type_alias_extracted(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        type Result<T> = { ok: true; value: T } | { ok: false; error: Error };
        ''')
        ext = extract_typescript(p)
        aliases = [s for s in ext.symbols if s.kind == "type_alias"]
        assert len(aliases) == 1
        assert aliases[0].name == "Result"
        validate_extraction(ext)

    def test_exported_type_alias(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        export type Handler = (req: Request, res: Response) => void;
        ''')
        ext = extract_typescript(p)
        aliases = [s for s in ext.symbols if s.kind == "type_alias"]
        assert len(aliases) == 1
        assert aliases[0].visibility == "public"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestEnums:

    def test_enum_extracted(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        enum Status {
          Active = "active",
          Inactive = "inactive",
        }
        ''')
        ext = extract_typescript(p)
        enums = [s for s in ext.symbols if s.kind == "enum"]
        assert len(enums) == 1
        assert enums[0].name == "Status"
        validate_extraction(ext)

    def test_exported_enum(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        export enum Direction {
          Up,
          Down,
          Left,
          Right,
        }
        ''')
        ext = extract_typescript(p)
        enums = [s for s in ext.symbols if s.kind == "enum"]
        assert len(enums) == 1
        assert enums[0].visibility == "public"


# ---------------------------------------------------------------------------
# Visibility (accessibility modifiers)
# ---------------------------------------------------------------------------


class TestVisibility:

    def test_public_method(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        class Foo {
          public bar(): void {}
        }
        ''')
        ext = extract_typescript(p)
        methods = [s for s in ext.symbols if s.kind == "method"]
        assert methods[0].visibility == "public"

    def test_private_method(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        class Foo {
          private secret(): string { return "hidden"; }
        }
        ''')
        ext = extract_typescript(p)
        methods = [s for s in ext.symbols if s.kind == "method"]
        assert methods[0].visibility == "private"

    def test_protected_method(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        class Base {
          protected init(): void {}
        }
        ''')
        ext = extract_typescript(p)
        methods = [s for s in ext.symbols if s.kind == "method"]
        assert methods[0].visibility == "protected"

    def test_no_modifier_defaults_public(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        class Foo {
          bar(): void {}
        }
        ''')
        ext = extract_typescript(p)
        methods = [s for s in ext.symbols if s.kind == "method"]
        assert methods[0].visibility == "public"


# ---------------------------------------------------------------------------
# Type annotations
# ---------------------------------------------------------------------------


class TestTypeAnnotations:

    def test_parameter_types(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        function greet(name: string, age: number): string {
          return `${name} is ${age}`;
        }
        ''')
        ext = extract_typescript(p)
        func = ext.symbols[0]
        assert any(p.type == "string" for p in func.parameters)
        assert any(p.type == "number" for p in func.parameters)

    def test_return_type(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        function add(a: number, b: number): number {
          return a + b;
        }
        ''')
        ext = extract_typescript(p)
        assert ext.symbols[0].return_type == "number"

    def test_async_return_type(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        async function fetch(url: string): Promise<Response> {
          return new Response();
        }
        ''')
        ext = extract_typescript(p)
        ret = ext.symbols[0].return_type
        assert ret is not None
        assert "Promise" in ret

    def test_method_return_type(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        class Foo {
          async findById(id: string): Promise<User | null> {
            return null;
          }
        }
        ''')
        ext = extract_typescript(p)
        method = [s for s in ext.symbols if s.kind == "method"][0]
        assert method.return_type is not None
        assert "Promise" in method.return_type


# ---------------------------------------------------------------------------
# Import type
# ---------------------------------------------------------------------------


class TestImportType:

    def test_import_type(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        import type { Config } from "./config";
        ''')
        ext = extract_typescript(p)
        assert len(ext.imports) == 1
        assert ext.imports[0].kind == "import_type"
        assert ext.imports[0].module == "./config"
        assert "Config" in ext.imports[0].names

    def test_regular_import(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        import { useState } from "react";
        ''')
        ext = extract_typescript(p)
        assert ext.imports[0].kind == "import"


# ---------------------------------------------------------------------------
# TSX
# ---------------------------------------------------------------------------


class TestTSX:

    def test_tsx_file_parses(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        import React from "react";

        interface Props {
          name: string;
        }

        const Greeting: React.FC<Props> = ({ name }) => {
          return <div>Hello, {name}!</div>;
        };

        export default Greeting;
        ''', name="component.tsx")
        ext = extract_typescript(p)
        validate_extraction(ext)
        assert ext.language == "typescript"
        sym_names = {s.name for s in ext.symbols}
        assert "Props" in sym_names
        assert "Greeting" in sym_names


# ---------------------------------------------------------------------------
# JS-compatible constructs (should still work)
# ---------------------------------------------------------------------------


class TestJSCompatible:

    def test_function_declaration(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        function helper(): void {}
        ''')
        ext = extract_typescript(p)
        assert any(s.kind == "function" for s in ext.symbols)

    def test_arrow_function(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        const process = (data: string[]): string[] => {
          return data;
        };
        ''')
        ext = extract_typescript(p)
        assert any(s.kind == "function" and s.name == "process" for s in ext.symbols)

    def test_class_with_methods(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        class Calc {
          add(a: number, b: number): number { return a + b; }
        }
        ''')
        ext = extract_typescript(p)
        assert any(s.kind == "class" for s in ext.symbols)
        assert any(s.kind == "method" and s.parent == "Calc" for s in ext.symbols)

    def test_constants(self, tmp_path):
        p = _write_ts(tmp_path, "const MAX_SIZE = 100;\n")
        ext = extract_typescript(p)
        assert any(s.kind == "constant" and s.name == "MAX_SIZE" for s in ext.symbols)

    def test_jsdoc(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        /** Adds numbers. */
        function add(a: number, b: number): number { return a + b; }
        ''')
        ext = extract_typescript(p)
        assert ext.symbols[0].docstring is not None
        assert "Adds" in ext.symbols[0].docstring

    def test_rationale_comments(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        function foo(): void {
          // WHY: Performance optimization
          // HACK: Temporary fix
        }
        ''')
        ext = extract_typescript(p)
        tags = {rc.tag for rc in ext.rationale_comments}
        assert "WHY" in tags
        assert "HACK" in tags

    def test_call_edges(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        function caller(): void {
          callee();
        }
        function callee(): void {}
        ''')
        ext = extract_typescript(p)
        assert any(e.caller == "caller" and e.callee == "callee" for e in ext.call_edges)

    def test_exports(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        function a(): void {}
        export { a };
        export default a;
        ''')
        ext = extract_typescript(p)
        assert any(e.kind == "named" for e in ext.exports)
        assert any(e.kind == "default" for e in ext.exports)


# ---------------------------------------------------------------------------
# Integration: realistic TS file
# ---------------------------------------------------------------------------


class TestRealisticFile:

    def test_realistic_ts_service(self, tmp_path):
        p = _write_ts(tmp_path, '''\
        import { Pool } from "pg";
        import type { QueryResult } from "pg";

        export const MAX_CONNECTIONS = 20;

        export type UserId = string;

        export enum Role {
          Admin = "admin",
          User = "user",
          Guest = "guest",
        }

        export interface UserRepository {
          findById(id: UserId): Promise<User | null>;
          findByEmail(email: string): Promise<User | null>;
          save(user: User): Promise<void>;
        }

        /**
         * PostgreSQL-backed user repository.
         */
        export class PgUserRepository implements UserRepository {
          private pool: Pool;

          constructor(pool: Pool) {
            this.pool = pool;
          }

          public async findById(id: UserId): Promise<User | null> {
            // WHY: Parameterized query prevents SQL injection
            const result = await this.pool.query("SELECT * FROM users WHERE id = $1", [id]);
            return result.rows[0] || null;
          }

          public async findByEmail(email: string): Promise<User | null> {
            const result = await this.pool.query("SELECT * FROM users WHERE email = $1", [email]);
            return result.rows[0] || null;
          }

          public async save(user: User): Promise<void> {
            // HACK: Upsert pattern until we add proper conflict handling
            await this.pool.query(
              "INSERT INTO users (id, email, role) VALUES ($1, $2, $3) ON CONFLICT (id) DO UPDATE SET email = $2",
              [user.id, user.email, user.role]
            );
          }

          private validate(user: User): boolean {
            // NOTE: Schema validation handled at API layer
            return !!user.id && !!user.email;
          }
        }

        export function createRepository(connectionString: string): PgUserRepository {
          const pool = new Pool({ connectionString });
          return new PgUserRepository(pool);
        }
        ''')

        ext = extract_typescript(p)
        validate_extraction(ext)

        # Check all symbol types present
        kinds = {s.kind for s in ext.symbols}
        assert "class" in kinds
        assert "method" in kinds
        assert "function" in kinds
        assert "interface" in kinds
        assert "type_alias" in kinds
        assert "enum" in kinds
        assert "constant" in kinds

        # Check names
        sym_names = {s.name for s in ext.symbols}
        assert "PgUserRepository" in sym_names
        assert "UserRepository" in sym_names
        assert "UserId" in sym_names
        assert "Role" in sym_names
        assert "MAX_CONNECTIONS" in sym_names
        assert "findById" in sym_names
        assert "validate" in sym_names
        assert "createRepository" in sym_names

        # Check visibility
        validate_method = next(s for s in ext.symbols if s.name == "validate")
        assert validate_method.visibility == "private"
        find_method = next(s for s in ext.symbols if s.name == "findById")
        assert find_method.visibility == "public"

        # Check return types on methods
        assert find_method.return_type is not None
        assert "Promise" in find_method.return_type

        # Check imports (regular + type)
        assert len(ext.imports) == 2
        kinds_set = {i.kind for i in ext.imports}
        assert "import" in kinds_set
        assert "import_type" in kinds_set

        # Check exports
        exported_names = {e.name for e in ext.exports}
        assert "PgUserRepository" in exported_names
        assert "UserRepository" in exported_names
        assert "createRepository" in exported_names

        # Check rationale comments
        tags = {rc.tag for rc in ext.rationale_comments}
        assert "WHY" in tags
        assert "HACK" in tags
        assert "NOTE" in tags

        # Check call edges
        assert len(ext.call_edges) > 0
