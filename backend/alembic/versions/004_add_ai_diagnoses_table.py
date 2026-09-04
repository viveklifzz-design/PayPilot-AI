"""Add ai_diagnoses table

Revision ID: 004_add_ai_diagnoses_table
Revises: 003_add_recovery_case_priority_fields
Create Date: 2026-08-23 13:57:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004_add_ai_diagnoses_table'
down_revision: Union[str, None] = '003_add_recovery_case_priority_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'ai_diagnoses',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('case_id', sa.String(length=36), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False, server_default='gemini'),
        sa.Column('model', sa.String(length=50), nullable=False, server_default='gemini-2.5-flash'),
        sa.Column('prompt_version', sa.String(length=20), nullable=False, server_default='v1.0.0'),
        sa.Column('risk_level', sa.String(length=20), nullable=False),
        sa.Column('recoverability_score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('failure_category', sa.String(length=50), nullable=False),
        sa.Column('root_cause', sa.String(length=100), nullable=False),
        sa.Column('recommended_action', sa.String(length=50), nullable=False),
        sa.Column('confidence', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('raw_response', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['recovery_cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_diagnoses_case_id'), 'ai_diagnoses', ['case_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_ai_diagnoses_case_id'), table_name='ai_diagnoses')
    op.drop_table('ai_diagnoses')
