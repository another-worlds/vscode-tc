"""Initial schema: users, workspaces, projects, audit logs, jobs

Revision ID: 001_initial
Revises: 
Create Date: 2026-05-17 02:23:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create extension for UUID
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('username', sa.String(50), nullable=False, unique=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('roles', postgresql.JSON, nullable=False, server_default='[]'),
        sa.Column('debug_override', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    
    # Workspaces table
    op.create_table(
        'workspaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('storage_quota_gb', sa.Float, nullable=False, server_default='100.0'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE')
    )
    
    # Projects table
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('video_path', sa.String(1024), nullable=False),
        sa.Column('file_hash', sa.String(64), nullable=True, unique=True),
        sa.Column('resolution', sa.String(20), nullable=True),
        sa.Column('duration_sec', sa.Integer, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='uploaded'),
        sa.Column('line_config', postgresql.JSON, nullable=True, server_default='{}'),
        sa.Column('od_matrix', postgresql.JSON, nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.CheckConstraint("status IN ('uploaded', 'processing', 'done', 'failed')")
    )
    
    # Audit Logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('target_type', sa.String(50), nullable=False),
        sa.Column('details', postgresql.JSON, nullable=True, server_default='{}'),
        sa.Column('timestamp', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.Index('ix_audit_logs_user_id', 'user_id'),
        sa.Index('ix_audit_logs_timestamp', 'timestamp'),
        sa.Index('ix_audit_logs_action', 'action')
    )
    
    # Jobs table (for processing queue state)
    op.create_table(
        'jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('video_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('worker_id', sa.String(255), nullable=True),
        sa.Column('progress_percent', sa.Integer, nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('parquet_path', sa.String(1024), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['video_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.CheckConstraint("status IN ('pending', 'processing', 'done', 'failed')"),
        sa.Index('ix_jobs_status', 'status'),
        sa.Index('ix_jobs_video_id', 'video_id')
    )
    
    # Create indexes for performance
    op.create_index('ix_workspaces_owner_id', 'workspaces', ['owner_id'])
    op.create_index('ix_projects_workspace_id', 'projects', ['workspace_id'])
    op.create_index('ix_projects_status', 'projects', ['status'])


def downgrade() -> None:
    # Drop all tables
    op.drop_table('jobs')
    op.drop_table('audit_logs')
    op.drop_table('projects')
    op.drop_table('workspaces')
    op.drop_table('users')
    
    # Drop extension
    op.execute('DROP EXTENSION IF NOT EXISTS "uuid-ossp"')
