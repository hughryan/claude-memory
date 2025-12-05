"""Initial schema - captures existing tables

Revision ID: 001
Revises:
Create Date: 2025-12-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if table already exists."""
    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # Decisions table
    if not table_exists('decisions'):
        op.create_table(
            'decisions',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('decision', sa.Text(), nullable=False),
            sa.Column('rationale', sa.Text(), nullable=False),
            sa.Column('context', sa.JSON(), default=dict),
            sa.Column('alternatives_considered', sa.JSON(), default=list),
            sa.Column('expected_impact', sa.Text(), nullable=True),
            sa.Column('risk_level', sa.String(), default='medium'),
            sa.Column('tags', sa.JSON(), default=list),
            sa.Column('timestamp', sa.DateTime()),
            sa.Column('outcome', sa.Text(), nullable=True),
            sa.Column('actual_impact', sa.Text(), nullable=True),
            sa.Column('lessons_learned', sa.Text(), nullable=True),
            sa.Column('updated_at', sa.DateTime()),
        )
        op.create_index('ix_decisions_id', 'decisions', ['id'])

    # Thought Sessions table
    if not table_exists('thought_sessions'):
        op.create_table(
            'thought_sessions',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('context', sa.JSON(), default=dict),
            sa.Column('started_at', sa.DateTime()),
            sa.Column('ended_at', sa.DateTime(), nullable=True),
            sa.Column('summary', sa.Text(), nullable=True),
            sa.Column('outcomes', sa.JSON(), default=list),
            sa.Column('status', sa.String(), default='active'),
        )

    # Thoughts table
    if not table_exists('thoughts'):
        op.create_table(
            'thoughts',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('thought', sa.Text(), nullable=False),
            sa.Column('category', sa.String(), nullable=False),
            sa.Column('reasoning', sa.Text(), nullable=True),
            sa.Column('related_to', sa.JSON(), default=list),
            sa.Column('confidence', sa.Float(), nullable=True),
            sa.Column('timestamp', sa.DateTime()),
            sa.Column('session_id', sa.String(), sa.ForeignKey('thought_sessions.id'), nullable=True),
        )
        op.create_index('ix_thoughts_id', 'thoughts', ['id'])

    # Insights table
    if not table_exists('insights'):
        op.create_table(
            'insights',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('insight', sa.Text(), nullable=False),
            sa.Column('source', sa.String(), nullable=True),
            sa.Column('applicability', sa.Text(), nullable=True),
            sa.Column('session_id', sa.String(), sa.ForeignKey('thought_sessions.id'), nullable=True),
            sa.Column('timestamp', sa.DateTime()),
        )
        op.create_index('ix_insights_id', 'insights', ['id'])

    # Changes table
    if not table_exists('changes'):
        op.create_table(
            'changes',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('hash', sa.String(), nullable=True),
            sa.Column('file_path', sa.String(), nullable=False),
            sa.Column('change_type', sa.String(), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('rationale', sa.Text(), nullable=True),
            sa.Column('affected_components', sa.JSON(), default=list),
            sa.Column('risk_assessment', sa.JSON(), default=dict),
            sa.Column('rollback_plan', sa.Text(), nullable=True),
            sa.Column('timestamp', sa.DateTime()),
            sa.Column('status', sa.String(), default='planned'),
            sa.Column('actual_impact', sa.Text(), nullable=True),
            sa.Column('issues_encountered', sa.JSON(), default=list),
            sa.Column('updated_at', sa.DateTime()),
        )
        op.create_index('ix_changes_id', 'changes', ['id'])

    # Cascade Events table
    if not table_exists('cascade_events'):
        op.create_table(
            'cascade_events',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('trigger', sa.String(), nullable=False),
            sa.Column('affected_components', sa.JSON(), default=list),
            sa.Column('severity', sa.String(), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('resolution', sa.Text(), nullable=True),
            sa.Column('timestamp', sa.DateTime()),
        )
        op.create_index('ix_cascade_events_id', 'cascade_events', ['id'])

    # Tools table
    if not table_exists('tools'):
        op.create_table(
            'tools',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(), nullable=False, unique=True),
            sa.Column('display_name', sa.String(), nullable=False),
            sa.Column('command', sa.String(), nullable=False),
            sa.Column('args', sa.JSON(), default=list),
            sa.Column('capabilities', sa.JSON(), default=list),
            sa.Column('enabled', sa.Integer(), default=1),
            sa.Column('config', sa.JSON(), default=dict),
            sa.Column('created_at', sa.DateTime()),
            sa.Column('last_used', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_tools_name', 'tools', ['name'])

    # Tool Sessions table
    if not table_exists('tool_sessions'):
        op.create_table(
            'tool_sessions',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('tool_id', sa.Integer(), sa.ForeignKey('tools.id'), nullable=False),
            sa.Column('session_id', sa.String(), nullable=False, unique=True),
            sa.Column('pid', sa.Integer(), nullable=True),
            sa.Column('state', sa.String(), default='idle'),
            sa.Column('started_at', sa.DateTime()),
            sa.Column('last_activity', sa.DateTime()),
            sa.Column('ended_at', sa.DateTime(), nullable=True),
            sa.Column('context', sa.JSON(), default=dict),
        )
        op.create_index('ix_tool_sessions_session_id', 'tool_sessions', ['session_id'])

    # Task Executions table
    if not table_exists('task_executions'):
        op.create_table(
            'task_executions',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('task_description', sa.Text(), nullable=False),
            sa.Column('tool_id', sa.Integer(), sa.ForeignKey('tools.id'), nullable=False),
            sa.Column('session_id', sa.String(), sa.ForeignKey('tool_sessions.session_id'), nullable=False),
            sa.Column('command_sent', sa.Text(), nullable=False),
            sa.Column('response_received', sa.Text(), nullable=True),
            sa.Column('status', sa.String(), default='pending'),
            sa.Column('started_at', sa.DateTime()),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('context', sa.JSON(), default=dict),
        )

    # Workflow Executions table
    if not table_exists('workflow_executions'):
        op.create_table(
            'workflow_executions',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('workflow_name', sa.String(), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('steps', sa.JSON(), default=list),
            sa.Column('status', sa.String(), default='pending'),
            sa.Column('started_at', sa.DateTime()),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('result', sa.JSON(), default=dict),
        )

    # Tasks table
    if not table_exists('tasks'):
        op.create_table(
            'tasks',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('title', sa.String(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('status', sa.String(), default='todo'),
            sa.Column('priority', sa.String(), default='medium'),
            sa.Column('assigned_to', sa.String(), nullable=True),
            sa.Column('tags', sa.JSON(), default=list),
            sa.Column('created_at', sa.DateTime()),
            sa.Column('updated_at', sa.DateTime()),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('parent_id', sa.Integer(), sa.ForeignKey('tasks.id'), nullable=True),
        )
        op.create_index('ix_tasks_status', 'tasks', ['status'])
        op.create_index('ix_tasks_priority', 'tasks', ['priority'])

    # Project Files table
    if not table_exists('project_files'):
        op.create_table(
            'project_files',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('file_path', sa.String(), nullable=False, unique=True),
            sa.Column('file_type', sa.String(), nullable=True),
            sa.Column('size', sa.Integer(), nullable=True),
            sa.Column('last_modified', sa.DateTime(), nullable=True),
            sa.Column('line_count', sa.Integer(), nullable=True),
            sa.Column('hash', sa.String(), nullable=True),
            sa.Column('language', sa.String(), nullable=True),
        )
        op.create_index('ix_project_files_file_path', 'project_files', ['file_path'])

    # File Dependencies table
    if not table_exists('file_dependencies'):
        op.create_table(
            'file_dependencies',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('source_file_id', sa.Integer(), sa.ForeignKey('project_files.id'), nullable=False),
            sa.Column('target_file_id', sa.Integer(), sa.ForeignKey('project_files.id'), nullable=False),
            sa.Column('dependency_type', sa.String(), default='import'),
        )

    # External Dependencies table
    if not table_exists('external_dependencies'):
        op.create_table(
            'external_dependencies',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('source_file_id', sa.Integer(), sa.ForeignKey('project_files.id'), nullable=False),
            sa.Column('package_name', sa.String(), nullable=False),
            sa.Column('version_constraint', sa.String(), nullable=True),
        )
        op.create_index('ix_external_dependencies_package_name', 'external_dependencies', ['package_name'])


def downgrade() -> None:
    # Drop tables in reverse order of dependencies
    op.drop_table('external_dependencies')
    op.drop_table('file_dependencies')
    op.drop_table('project_files')
    op.drop_table('tasks')
    op.drop_table('workflow_executions')
    op.drop_table('task_executions')
    op.drop_table('tool_sessions')
    op.drop_table('tools')
    op.drop_table('cascade_events')
    op.drop_table('changes')
    op.drop_table('insights')
    op.drop_table('thoughts')
    op.drop_table('thought_sessions')
    op.drop_table('decisions')
