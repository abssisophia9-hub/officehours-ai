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
        if "urgency" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE requests ADD COLUMN urgency VARCHAR"))
