"""
Lightweight additive schema upgrades for SQLite/dev databases.

SQLAlchemy create_all does not add columns to existing tables, so we apply
safe ALTER TABLE statements for new nullable fields.
"""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    if "requests" in table_names:
        columns = {column["name"] for column in inspector.get_columns("requests")}
        _add_column_if_missing(engine, "requests", columns, "urgency", "VARCHAR")
        _add_column_if_missing(engine, "requests", columns, "learning_style", "VARCHAR")

    if "knowledge_entries" in table_names:
        columns = {
            column["name"] for column in inspector.get_columns("knowledge_entries")
        }
        _add_column_if_missing(
            engine, "knowledge_entries", columns, "learning_style", "VARCHAR"
        )
        _add_column_if_missing(
            engine, "knowledge_entries", columns, "drafter_backend", "VARCHAR"
        )


def _add_column_if_missing(
    engine: Engine,
    table: str,
    columns: set[str],
    column_name: str,
    column_type: str,
) -> None:
    if column_name in columns:
        return
    with engine.begin() as connection:
        connection.execute(
            text(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}")
        )
