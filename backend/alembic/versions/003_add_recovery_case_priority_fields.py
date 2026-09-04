"""Add priority_score, priority_level, risk_factors to recovery_cases

Revision ID: 003_add_recovery_case_priority_fields
Revises: 002_add_transaction_fields
Create Date: 2026-08-23 13:46:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_add_recovery_case_priority_fields'
down_revision: Union[str, None] = '002_add_transaction_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('recovery_cases', sa.Column('priority_score', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.00'))
    op.add_column('recovery_cases', sa.Column('priority_level', sa.String(length=20), nullable=False, server_default='MEDIUM'))
    op.add_column('recovery_cases', sa.Column('risk_factors', sa.JSON(), nullable=True))
    op.create_index(op.f('ix_recovery_cases_priority_level'), 'recovery_cases', ['priority_level'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_recovery_cases_priority_level'), table_name='recovery_cases')
    op.drop_column('recovery_cases', 'risk_factors')
    op.drop_column('recovery_cases', 'priority_level')
    op.drop_column('recovery_cases', 'priority_score')
