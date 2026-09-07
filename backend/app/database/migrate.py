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
        for column_name, column_type in (
            ("student_name", "VARCHAR"),
            ("course", "VARCHAR"),
            ("code_snippet", "TEXT"),
            ("oracle_category", "VARCHAR"),
            ("oracle_difficulty", "VARCHAR"),
            ("oracle_estimated_minutes", "INTEGER"),
            ("oracle_tags", "TEXT"),
            ("assigned_ta", "VARCHAR"),
            ("alternative_ta", "VARCHAR"),
            ("estimated_wait_minutes", "INTEGER"),
            ("student_hint", "TEXT"),
            ("oracle_trace_json", "TEXT"),
            ("course_id", "INTEGER"),
            ("sensitive", "BOOLEAN"),
            ("help_mode", "VARCHAR"),
            ("work_status", "VARCHAR"),
            ("claimed_by", "VARCHAR"),
            ("claimed_by_user_id", "INTEGER"),
            ("created_by_user_id", "INTEGER"),
            ("claimed_at", "DATETIME"),
            ("helped_at", "DATETIME"),
            ("ta_reply", "TEXT"),
            ("ta_replied_at", "DATETIME"),
        ):
            _add_column_if_missing(engine, "requests", columns, column_name, column_type)

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
        _add_column_if_missing(
            engine, "knowledge_entries", columns, "course_id", "INTEGER"
        )
        _add_column_if_missing(
            engine, "knowledge_entries", columns, "material_source", "VARCHAR"
        )
        _add_column_if_missing(
            engine, "knowledge_entries", columns, "ta_resolution", "VARCHAR"
        )

    if "courses" in table_names:
        columns = {column["name"] for column in inspector.get_columns("courses")}
        _add_column_if_missing(
            engine, "courses", columns, "canvas_course_id", "VARCHAR"
        )

    if "help_posts" in table_names:
        columns = {column["name"] for column in inspector.get_columns("help_posts")}
        _add_column_if_missing(
            engine, "help_posts", columns, "flair", "VARCHAR DEFAULT 'stuck'"
        )
        _add_column_if_missing(
            engine, "help_posts", columns, "room_type", "VARCHAR DEFAULT 'problem'"
        )
        _add_column_if_missing(
            engine, "help_posts", columns, "status", "VARCHAR DEFAULT 'open'"
        )
        _add_column_if_missing(engine, "help_posts", columns, "tags_json", "TEXT")

    if "help_replies" in table_names:
        columns = {column["name"] for column in inspector.get_columns("help_replies")}
        _add_column_if_missing(
            engine, "help_replies", columns, "parent_reply_id", "INTEGER"
        )
        _add_column_if_missing(
            engine, "help_replies", columns, "accepted", "BOOLEAN DEFAULT 0"
        )

    if "help_post_votes" in table_names:
        columns = {column["name"] for column in inspector.get_columns("help_post_votes")}
        _add_column_if_missing(
            engine, "help_post_votes", columns, "value", "INTEGER DEFAULT 1"
        )

    if "users" in table_names:
        columns = {column["name"] for column in inspector.get_columns("users")}
        _add_column_if_missing(engine, "users", columns, "handle", "VARCHAR")
        _add_column_if_missing(engine, "users", columns, "bio", "VARCHAR")
        _add_column_if_missing(engine, "users", columns, "country", "VARCHAR")
        _add_column_if_missing(engine, "users", columns, "skills_json", "TEXT")
        _add_column_if_missing(
            engine, "users", columns, "profile_views", "INTEGER DEFAULT 0"
        )

    _ensure_indexes(engine)


def _add_column_if_missing(
    engine: Engine,
    table: str,
    columns: set[str],
    column_name: str,
    column_type: str,
) -> None:
    if column_name in columns:
        return
    mapped = column_type
    if engine.dialect.name == "postgresql":
        mapped = {
            "VARCHAR": "VARCHAR",
            "TEXT": "TEXT",
            "INTEGER": "INTEGER",
            "BOOLEAN": "BOOLEAN",
            "BOOLEAN DEFAULT 0": "BOOLEAN DEFAULT FALSE",
            "INTEGER DEFAULT 0": "INTEGER DEFAULT 0",
            "DATETIME": "TIMESTAMP WITH TIME ZONE",
            "VARCHAR DEFAULT 'stuck'": "VARCHAR DEFAULT 'stuck'",
            "VARCHAR DEFAULT 'problem'": "VARCHAR DEFAULT 'problem'",
            "VARCHAR DEFAULT 'open'": "VARCHAR DEFAULT 'open'",
        }.get(column_type, column_type)
    with engine.begin() as connection:
        connection.execute(
            text(f"ALTER TABLE {table} ADD COLUMN {column_name} {mapped}")
        )


def _ensure_indexes(engine: Engine) -> None:
    """Best-effort indexes for hot filters (SQLite/Postgres)."""
    statements = [
        "CREATE INDEX IF NOT EXISTS ix_requests_course_created ON requests (course_id, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_requests_course_author ON requests (course_id, created_by_user_id)",
        "CREATE INDEX IF NOT EXISTS ix_knowledge_course_status ON knowledge_entries (course_id, status)",
        "CREATE INDEX IF NOT EXISTS ix_help_posts_course ON help_posts (course_id)",
        "CREATE INDEX IF NOT EXISTS ix_auth_sessions_token ON auth_sessions (token)",
    ]
    with engine.begin() as connection:
        for sql in statements:
            try:
                connection.execute(text(sql))
            except Exception:
                # Table may not exist yet on a fresh partial migrate — ignore.
                pass


# Append index ensure to ensure_schema by wrapping — call at end of ensure_schema
