from sqlalchemy import text
from app.db.session import engine, Base
from app.db.base import *  # ensure all models registered
from app.core.logging import logger

async def init_db():
    logger.info("Initializing database tables...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Base metadata create_all completed successfully.")
    except Exception as e:
        logger.error(f"Base metadata create_all error: {e}")

    # SQLite / PostgreSQL column migration for new subscription recovery fields
    for col_name, col_type in [
        ("failure_reason", "VARCHAR(100) DEFAULT 'UNKNOWN'"),
        ("retry_count", "INTEGER DEFAULT 0"),
        ("max_retry_attempts", "INTEGER DEFAULT 3"),
        ("grace_period_until", "TIMESTAMP"),
        ("recovery_status", "VARCHAR(50) DEFAULT 'NOT_STARTED'")
    ]:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(f"ALTER TABLE subscriptions ADD COLUMN {col_name} {col_type}"))
        except Exception as e:
            logger.debug(f"Subscription column {col_name} migration note: {e}")

    # Mandate table column migrations
    for col_name, col_type in [
        ("failure_reason", "VARCHAR(255)"),
        ("escalation_reason", "VARCHAR(255)"),
        ("provider_mandate_id", "VARCHAR(100)"),
        ("next_retry_date", "TIMESTAMP"),
        ("last_retry_at", "TIMESTAMP"),
    ]:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(f"ALTER TABLE mandates ADD COLUMN {col_name} {col_type}"))
        except Exception as e:
            logger.debug(f"Mandate column {col_name} migration note: {e}")

    # RecoveryCase table column migrations
    for col_name, col_type in [
        ("case_type", "VARCHAR(50) DEFAULT 'PAYMENT_FAILURE'"),
        ("priority_score", "NUMERIC(5, 2) DEFAULT 0.0"),
        ("priority_level", "VARCHAR(20) DEFAULT 'MEDIUM'"),
        ("risk_factors", "JSON"),
        ("checkout_session_id", "VARCHAR(36)"),
        ("subscription_id", "VARCHAR(36)"),
        ("subscription_attempt_id", "VARCHAR(36)"),
        ("invoice_id", "VARCHAR(36)"),
        ("mandate_id", "VARCHAR(36)"),
        ("stop_reason", "TEXT"),
        ("ai_reasoning", "TEXT"),
        ("policy_failure_reason", "TEXT"),
        ("actual_action_taken", "VARCHAR(50)"),
        ("recovered_amount", "NUMERIC(12, 2) DEFAULT 0.00"),
    ]:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(f"ALTER TABLE recovery_cases ADD COLUMN {col_name} {col_type}"))
        except Exception as e:
            logger.debug(f"RecoveryCase column {col_name} migration note: {e}")

    # Transaction table column migrations
    for col_name, col_type in [
        ("raw_payload", "JSON"),
        ("payment_method", "VARCHAR(50)"),
        ("error_source", "VARCHAR(100)"),
        ("error_step", "VARCHAR(100)"),
        ("error_reason", "VARCHAR(100)"),
    ]:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(f"ALTER TABLE transactions ADD COLUMN {col_name} {col_type}"))
        except Exception as e:
            logger.debug(f"Transaction column {col_name} migration note: {e}")


    logger.info("Database tables initialized successfully.")





