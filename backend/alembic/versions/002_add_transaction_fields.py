"""Add updated_at and raw_payload to transactions

Revision ID: 002_add_transaction_fields
Revises: 001_initial_schema
Create Date: 2026-08-23 13:42:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_add_transaction_fields'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('transactions', sa.Column('raw_payload', sa.JSON(), nullable=True))
    op.add_column('transactions', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')))

def downgrade() -> None:
    op.drop_column('transactions', 'updated_at')
    op.drop_column('transactions', 'raw_payload')
