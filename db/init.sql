-- Grand Contract v1.0 — PostgreSQL schema bootstrap
-- Runs once on first container start via docker-entrypoint-initdb.d

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- for fuzzy name search

-- ── Enums ────────────────────────────────────────────────────────
CREATE TYPE user_role AS ENUM ('ADMIN', 'MANAGER', 'ANALYST', 'VIEWER');
CREATE TYPE video_status AS ENUM (
    'PENDING', 'QUEUED', 'PROCESSING', 'PROCESSED', 'ERROR'
);
CREATE TYPE audit_action AS ENUM (
    'WORKSPACE_CREATED',
    'PROJECT_CREATED',
    'VIDEO_UPLOADED',
    'VIDEO_PROCESSING_STARTED',
    'VIDEO_PROCESSING_COMPLETED',
    'VIDEO_MARKUP_STARTED',
    'VIDEO_MARKUP_COMPLETED',
    'LINE_DRAWN',
    'RESULTS_DOWNLOADED',
    'QUEUE_CONTROLLED',
    'WORKER_SCALED'
);

-- ── Users ─────────────────────────────────────────────────────────
CREATE TABLE users (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    oauth_provider  TEXT        NOT NULL,  -- 'google' | 'yandex'
    oauth_id        TEXT        NOT NULL,
    email           TEXT        NOT NULL UNIQUE,
    display_name    TEXT        NOT NULL,
    avatar_url      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (oauth_provider, oauth_id)
);

-- ── Workspaces ────────────────────────────────────────────────────
CREATE TABLE workspaces (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT        NOT NULL,
    owner_id    UUID        NOT NULL REFERENCES users(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by  UUID        NOT NULL REFERENCES users(id)
);

CREATE TABLE workspace_members (
    workspace_id    UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id         UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role            user_role   NOT NULL DEFAULT 'VIEWER',
    assigned_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_by     UUID        REFERENCES users(id),
    PRIMARY KEY (workspace_id, user_id)
);

-- ── Projects ──────────────────────────────────────────────────────
CREATE TABLE projects (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID        NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name            TEXT        NOT NULL,
    location_label  TEXT,           -- intersection node description
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by      UUID        NOT NULL REFERENCES users(id)
);

-- ── Videos ────────────────────────────────────────────────────────
CREATE TABLE videos (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    filename        TEXT        NOT NULL,
    filepath        TEXT        NOT NULL UNIQUE,     -- absolute inside container
    resolution_w    INT,
    resolution_h    INT,
    duration_s      FLOAT,
    size_bytes      BIGINT,
    fps             FLOAT,
    status          video_status NOT NULL DEFAULT 'PENDING',
    error_message   TEXT,
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    uploaded_by     UUID        REFERENCES users(id),
    processing_started_at  TIMESTAMPTZ,
    processed_at    TIMESTAMPTZ,
    frame_count     INT,         -- actual extracted JPEG count
    parquet_path    TEXT         -- path to trajectory parquet file
);

-- ── Counting Lines ────────────────────────────────────────────────
CREATE TABLE counting_lines (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id    UUID        NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    name        TEXT        NOT NULL,
    -- GeoJSON LineString points: [[x1,y1],[x2,y2]] in pixel coords
    points      JSONB       NOT NULL,
    color       TEXT        NOT NULL DEFAULT '#FF0000',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by  UUID        REFERENCES users(id)
);

-- Counting results stored per line after server-side intersection calculation
CREATE TABLE counting_results (
    id              UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    counting_line_id UUID   NOT NULL REFERENCES counting_lines(id) ON DELETE CASCADE,
    count_in        INT     NOT NULL DEFAULT 0,
    count_out       INT     NOT NULL DEFAULT 0,
    total           INT     GENERATED ALWAYS AS (count_in + count_out) STORED,
    vehicle_pct     JSONB,  -- {"car": 60.5, "truck": 20.0, "motorcycle": 19.5}
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Audit Log ─────────────────────────────────────────────────────
CREATE TABLE audit_logs (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    action          audit_action NOT NULL,
    user_id         UUID        REFERENCES users(id),
    resource_type   TEXT,       -- 'workspace' | 'project' | 'video' | 'line'
    resource_id     UUID,
    metadata        JSONB,      -- arbitrary extra context
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Indexes ───────────────────────────────────────────────────────
CREATE INDEX idx_videos_project_id     ON videos(project_id);
CREATE INDEX idx_videos_status         ON videos(status);
CREATE INDEX idx_counting_lines_video  ON counting_lines(video_id);
CREATE INDEX idx_audit_user            ON audit_logs(user_id);
CREATE INDEX idx_audit_resource        ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_created         ON audit_logs(created_at DESC);
