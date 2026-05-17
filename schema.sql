-- Traffic Count MVP Database Schema
-- PostgreSQL 15+
-- Generated from Alembic migrations (alembic/versions/001_initial.py)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    roles JSON NOT NULL DEFAULT '[]'::json,
    debug_override BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Workspaces table
CREATE TABLE IF NOT EXISTS workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    storage_quota_gb FLOAT NOT NULL DEFAULT 100.0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_workspaces_owner_id ON workspaces(owner_id);

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    video_path VARCHAR(1024) NOT NULL,
    file_hash VARCHAR(64) UNIQUE,
    resolution VARCHAR(20),
    duration_sec INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'uploaded'
        CHECK (status IN ('uploaded', 'processing', 'done', 'failed')),
    line_config JSON NOT NULL DEFAULT '{}'::json,
    od_matrix JSON NOT NULL DEFAULT '{}'::json,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_projects_workspace_id ON projects(workspace_id);
CREATE INDEX IF NOT EXISTS ix_projects_status ON projects(status);

-- Audit Logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    target_id UUID,
    target_type VARCHAR(50) NOT NULL,
    details JSON NOT NULL DEFAULT '{}'::json,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    ip_address VARCHAR(45)
);

CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs(action);

-- Jobs table (processing queue state)
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'done', 'failed')),
    worker_id VARCHAR(255),
    progress_percent INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    parquet_path VARCHAR(1024),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS ix_jobs_video_id ON jobs(video_id);

-- Views for common queries (optional but helpful)

-- View: Workspace usage statistics
CREATE OR REPLACE VIEW workspace_stats AS
SELECT
    w.id,
    w.name,
    w.owner_id,
    COUNT(DISTINCT p.id) AS project_count,
    COUNT(DISTINCT j.id) AS job_count,
    SUM(COALESCE(j.progress_percent, 0)) / COUNT(DISTINCT j.id) AS avg_progress
FROM workspaces w
LEFT JOIN projects p ON w.id = p.workspace_id
LEFT JOIN jobs j ON w.id = j.workspace_id
GROUP BY w.id, w.name, w.owner_id;

-- View: Project processing status
CREATE OR REPLACE VIEW project_status_view AS
SELECT
    p.id,
    p.name,
    p.status,
    j.status AS job_status,
    j.progress_percent,
    j.worker_id,
    p.created_at,
    j.started_at,
    j.completed_at
FROM projects p
LEFT JOIN jobs j ON p.id = j.video_id
ORDER BY p.updated_at DESC;
