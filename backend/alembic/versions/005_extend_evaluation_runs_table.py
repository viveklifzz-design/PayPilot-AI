"""Extend evaluation_runs table for Phase 6 batch metrics

Revision ID: 005_extend_evaluation_runs_table
Revises: 004_add_ai_diagnoses_table
Create Date: 2026-08-23 17:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '005_extend_evaluation_runs_table'
down_revision: Union[str, None] = '004_add_ai_diagnoses_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('evaluation_runs', sa.Column('seed', sa.Integer(), nullable=False, server_default='42'))
    op.add_column('evaluation_runs', sa.Column('batch_size', sa.Integer(), nullable=False, server_default='100'))
    op.add_column('evaluation_runs', sa.Column('mode', sa.String(length=50), nullable=False, server_default='simulation'))
    op.add_column('evaluation_runs', sa.Column('diagnosed_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('evaluation_runs', sa.Column('policy_allowed_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('evaluation_runs', sa.Column('policy_blocked_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('evaluation_runs', sa.Column('escalated_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('evaluation_runs', sa.Column('recovery_attempt_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('evaluation_runs', sa.Column('recovered_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('evaluation_runs', sa.Column('failed_recovery_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('evaluation_runs', sa.Column('stopped_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('evaluation_runs', sa.Column('remaining_revenue_at_risk', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'))
    op.add_column('evaluation_runs', sa.Column('recovery_success_rate', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.00'))
    op.add_column('evaluation_runs', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    op.drop_column('evaluation_runs', 'completed_at')
    op.drop_column('evaluation_runs', 'recovery_success_rate')
    op.drop_column('evaluation_runs', 'remaining_revenue_at_risk')
    op.drop_column('evaluation_runs', 'stopped_count')
    op.drop_column('evaluation_runs', 'failed_recovery_count')
    op.drop_column('evaluation_runs', 'recovered_count')
    op.drop_column('evaluation_runs', 'recovery_attempt_count')
    op.drop_column('evaluation_runs', 'escalated_count')
    op.drop_column('evaluation_runs', 'policy_blocked_count')
    op.drop_column('evaluation_runs', 'policy_allowed_count')
    op.drop_column('evaluation_runs', 'diagnosed_count')
    op.drop_column('evaluation_runs', 'mode')
    op.drop_column('evaluation_runs', 'batch_size')
    op.drop_column('evaluation_runs', 'seed')
