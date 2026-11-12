-- OfficeHours AI core schema represented by diagrams/database_erd.png.
--
-- Only solid ER relationships are enforced as foreign keys. Dashed logical
-- relationships remain plain INTEGER columns so the database does not enforce
-- cross-module lifecycle coupling.

PRAGMA foreign_keys = ON;

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    student_id VARCHAR(64),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_users_email UNIQUE (email)
);

CREATE TABLE courses (
    id INTEGER PRIMARY KEY,
    code VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    term VARCHAR(64),
    canvas_course_id VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE course_memberships (
    id INTEGER PRIMARY KEY,
    course_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role VARCHAR(32) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_course_memberships_course_user UNIQUE (course_id, user_id),
    CONSTRAINT fk_course_memberships_course
        FOREIGN KEY (course_id) REFERENCES courses (id),
    CONSTRAINT fk_course_memberships_user
        FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE requests (
    id INTEGER PRIMARY KEY,
    text TEXT NOT NULL,
    anonymous BOOLEAN NOT NULL DEFAULT TRUE,
    student_id VARCHAR(64),
    student_name VARCHAR(255),
    help_mode VARCHAR(32) NOT NULL DEFAULT 'message',
    category VARCHAR(255),
    urgency VARCHAR(64),
    learning_style VARCHAR(64),
    cluster_id INTEGER,
    recommended_action TEXT,
    assigned_ta VARCHAR(255),
    course_id INTEGER,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE knowledge_entries (
    id INTEGER PRIMARY KEY,
    status VARCHAR(32) NOT NULL DEFAULT 'pending_review',
    question_text TEXT NOT NULL,
    answer_draft TEXT NOT NULL,
    student_hint TEXT NOT NULL,
    course_id INTEGER,
    source_request_id INTEGER,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME
);

CREATE TABLE ta_roster (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    expertise_tags TEXT NOT NULL DEFAULT '[]',
    queue_depth INTEGER NOT NULL DEFAULT 0,
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_ta_roster_name UNIQUE (name)
);

CREATE TABLE auth_sessions (
    id INTEGER PRIMARY KEY,
    token VARCHAR(255) NOT NULL,
    user_id INTEGER NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    CONSTRAINT uq_auth_sessions_token UNIQUE (token),
    CONSTRAINT fk_auth_sessions_user
        FOREIGN KEY (user_id) REFERENCES users (id)
);
