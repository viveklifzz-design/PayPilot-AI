from sqlalchemy import text
from app.db.session import engine, Base
from app.db.base import *  # ensure all models registered
from app.core.logging import logger

async def init_db():
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # SQLite column migration for new subscription recovery fields
        for col_def in [
            ("failure_reason", "VARCHAR(100) DEFAULT 'UNKNOWN' NOT NULL"),
            ("retry_count", "INTEGER DEFAULT 0 NOT NULL"),
            ("max_retry_attempts", "INTEGER DEFAULT 3 NOT NULL"),
            ("grace_period_until", "DATETIME"),
            ("recovery_status", "VARCHAR(50) DEFAULT 'NOT_STARTED' NOT NULL")
        ]:
            try:
                await conn.execute(text(f"ALTER TABLE subscriptions ADD COLUMN {col_def[0]} {col_def[1]}"))
            except Exception:
                pass  # Column already exists

        # Mandate table column migrations
        for col_def in [
            ("failure_reason", "VARCHAR(255)"),
            ("escalation_reason", "VARCHAR(255)"),
            ("provider_mandate_id", "VARCHAR(100)"),
            ("next_retry_date", "DATETIME"),
            ("last_retry_at", "DATETIME"),
        ]:
            try:
                await conn.execute(text(f"ALTER TABLE mandates ADD COLUMN {col_def[0]} {col_def[1]}"))
            except Exception:
                pass  # Column already exists
    logger.info("Database tables initialized successfully.")


