"""Initial schema setup

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-23 13:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Merchants Table
    op.create_table(
        'merchants',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('razorpay_key_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_merchants_email'), 'merchants', ['email'], unique=True)

    # 2. Customers Table
    op.create_table(
        'customers',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('merchant_id', sa.String(length=36), nullable=False),
        sa.Column('razorpay_customer_id', sa.String(length=255), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('total_successful_payments', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_failed_payments', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_customers_merchant_id'), 'customers', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_customers_razorpay_customer_id'), 'customers', ['razorpay_customer_id'], unique=False)

    # 3. Transactions Table
    op.create_table(
        'transactions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('merchant_id', sa.String(length=36), nullable=False),
        sa.Column('customer_id', sa.String(length=36), nullable=True),
        sa.Column('razorpay_payment_id', sa.String(length=255), nullable=True),
        sa.Column('razorpay_order_id', sa.String(length=255), nullable=True),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('error_code', sa.String(length=100), nullable=True),
        sa.Column('error_description', sa.Text(), nullable=True),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('razorpay_payment_id')
    )
    op.create_index(op.f('ix_transactions_merchant_id'), 'transactions', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_transactions_customer_id'), 'transactions', ['customer_id'], unique=False)
    op.create_index(op.f('ix_transactions_razorpay_payment_id'), 'transactions', ['razorpay_payment_id'], unique=True)
    op.create_index(op.f('ix_transactions_status'), 'transactions', ['status'], unique=False)

    # 4. Recovery Cases Table
    op.create_table(
        'recovery_cases',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('merchant_id', sa.String(length=36), nullable=False),
        sa.Column('transaction_id', sa.String(length=36), nullable=False),
        sa.Column('customer_id', sa.String(length=36), nullable=True),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('risk_score', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.00'),
        sa.Column('risk_level', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('ai_root_cause', sa.String(length=100), nullable=True),
        sa.Column('ai_recommended_action', sa.String(length=50), nullable=True),
        sa.Column('ai_confidence', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('ai_reasoning', sa.Text(), nullable=True),
        sa.Column('policy_passed', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('policy_failure_reason', sa.Text(), nullable=True),
        sa.Column('actual_action_taken', sa.String(length=50), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('recovered_amount', sa.Numeric(precision=12, scale=2), nullable=False, server_default='0.00'),
        sa.Column('stop_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recovery_cases_merchant_id'), 'recovery_cases', ['merchant_id'], unique=False)
    op.create_index(op.f('ix_recovery_cases_transaction_id'), 'recovery_cases', ['transaction_id'], unique=False)
    op.create_index(op.f('ix_recovery_cases_risk_level'), 'recovery_cases', ['risk_level'], unique=False)
    op.create_index(op.f('ix_recovery_cases_status'), 'recovery_cases', ['status'], unique=False)

    # 5. Recovery Actions Table
    op.create_table(
        'recovery_actions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('case_id', sa.String(length=36), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('razorpay_payment_link_id', sa.String(length=255), nullable=True),
        sa.Column('short_url', sa.Text(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('response', sa.JSON(), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['recovery_cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recovery_actions_case_id'), 'recovery_actions', ['case_id'], unique=False)

    # 6. Audit Logs Table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('case_id', sa.String(length=36), nullable=False),
        sa.Column('actor', sa.String(length=50), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['recovery_cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_case_id'), 'audit_logs', ['case_id'], unique=False)

    # 7. Webhook Events Table
    op.create_table(
        'webhook_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('event_id', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('processed', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id')
    )
    op.create_index(op.f('ix_webhook_events_event_id'), 'webhook_events', ['event_id'], unique=True)

    # 8. Evaluation Runs Table
    op.create_table(
        'evaluation_runs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('run_name', sa.String(length=255), nullable=False),
        sa.Column('total_cases', sa.Integer(), nullable=False),
        sa.Column('revenue_at_risk', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('recoverable_revenue', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('total_recovered', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('recovery_rate', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('precision_rate', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('false_intervention_rate', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('escalation_rate', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('safe_stop_rate', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('metrics', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('evaluation_runs')
    op.drop_table('webhook_events')
    op.drop_table('audit_logs')
    op.drop_table('recovery_actions')
    op.drop_table('recovery_cases')
    op.drop_table('transactions')
    op.drop_table('customers')
    op.drop_table('merchants')
