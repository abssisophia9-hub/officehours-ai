from __future__ import annotations

import re
import sqlite3
from pathlib import Path


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "docs" / "database_schema.sql"
SNAKE_CASE = re.compile(r"^[a-z][a-z0-9_]*$")


def _schema_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    return connection


def _unique_column_sets(
    connection: sqlite3.Connection, table: str
) -> set[tuple[str, ...]]:
    unique_sets: set[tuple[str, ...]] = set()
    for _, index_name, is_unique, *_ in connection.execute(
        f"PRAGMA index_list('{table}')"
    ):
        if not is_unique:
            continue
        columns = tuple(
            row[2]
            for row in connection.execute(f"PRAGMA index_info('{index_name}')")
        )
        unique_sets.add(columns)
    return unique_sets


def test_core_ddl_uses_lowercase_snake_case_names() -> None:
    connection = _schema_connection()
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    assert tables == {
        "users",
        "courses",
        "course_memberships",
        "requests",
        "knowledge_entries",
        "ta_roster",
        "auth_sessions",
    }
    for table in tables:
        assert SNAKE_CASE.fullmatch(table)
        columns = [row[1] for row in connection.execute(f"PRAGMA table_info('{table}')")]
        assert columns
        assert all(SNAKE_CASE.fullmatch(column) for column in columns)


def test_core_ddl_declares_only_the_three_solid_relationships() -> None:
    connection = _schema_connection()
    foreign_keys = {
        (table, row[3], row[2], row[4])
        for table in (
            "users",
            "courses",
            "course_memberships",
            "requests",
            "knowledge_entries",
            "ta_roster",
            "auth_sessions",
        )
        for row in connection.execute(f"PRAGMA foreign_key_list('{table}')")
    }
    assert foreign_keys == {
        ("course_memberships", "course_id", "courses", "id"),
        ("course_memberships", "user_id", "users", "id"),
        ("auth_sessions", "user_id", "users", "id"),
    }

    request_columns = {
        row[1]: row[2] for row in connection.execute("PRAGMA table_info('requests')")
    }
    knowledge_columns = {
        row[1]: row[2]
        for row in connection.execute("PRAGMA table_info('knowledge_entries')")
    }
    assert request_columns["course_id"] == "INTEGER"
    assert knowledge_columns["course_id"] == "INTEGER"


def test_core_ddl_preserves_diagram_unique_constraints() -> None:
    connection = _schema_connection()
    assert ("email",) in _unique_column_sets(connection, "users")
    assert ("token",) in _unique_column_sets(connection, "auth_sessions")
    assert ("name",) in _unique_column_sets(connection, "ta_roster")
    assert ("course_id", "user_id") in _unique_column_sets(
        connection, "course_memberships"
    )
