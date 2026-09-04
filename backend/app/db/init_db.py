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
    try:
        await seed_demo_data_if_empty()
    except Exception as e:
        logger.warning(f"Initial demo seeding skipped or failed: {e}")

async def seed_demo_data_if_empty():
    from app.db.session import AsyncSessionLocal
    from app.models.merchant import Merchant
    from app.models.customer import Customer
    from app.models.transaction import Transaction
    from app.models.recovery_case import RecoveryCase
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(RecoveryCase))
        existing_cases = res.scalars().all()
        if existing_cases:
            logger.info(f"Database already contains {len(existing_cases)} recovery cases. Skipping demo seeding.")
            return

        logger.info("Database empty; initializing initial demo recovery cases and transactions...")
        
        merchant_id = "m_default_merchant"
        m_res = await db.execute(select(Merchant).where(Merchant.id == merchant_id))
        merchant = m_res.scalar_one_or_none()
        if not merchant:
            merchant = Merchant(
                id=merchant_id,
                name="Acme Technologies Pvt Ltd",
                email="merchant@acme.corp"
            )
            db.add(merchant)
            await db.flush()

        cust_acme = Customer(
            id="cust_acme_corp",
            merchant_id=merchant_id,
            name="Acme Corp",
            email="finance@acme.corp",
            phone="+919876543210"
        )
        cust_globex = Customer(
            id="cust_globex",
            merchant_id=merchant_id,
            name="Globex Inc",
            email="accounts@globex.io",
            phone="+919876543211"
        )
        cust_soylent = Customer(
            id="cust_soylent",
            merchant_id=merchant_id,
            name="Soylent Ltd",
            email="billing@soylent.com",
            phone="+919876543212"
        )
        db.add_all([cust_acme, cust_globex, cust_soylent])
        await db.flush()

        t1 = Transaction(
            id="txn_001",
            merchant_id=merchant_id,
            customer_id="cust_acme_corp",
            amount=15000.00,
            currency="INR",
            status="failed",
            error_code="BAD_REQUEST_ERROR",
            error_reason="insufficient_funds",
            error_description="Mandate execution failed: Insufficient funds"
        )
        t2 = Transaction(
            id="txn_002",
            merchant_id=merchant_id,
            customer_id="cust_globex",
            amount=45000.00,
            currency="INR",
            status="failed",
            error_code="BAD_REQUEST_ERROR",
            error_reason="card_expired",
            error_description="Card expired during auto-debit"
        )
        t3 = Transaction(
            id="txn_003",
            merchant_id=merchant_id,
            customer_id="cust_soylent",
            amount=500.00,
            currency="INR",
            status="failed",
            error_code="BAD_REQUEST_ERROR",
            error_reason="authentication_failed",
            error_description="Customer failed 2FA verification"
        )
        db.add_all([t1, t2, t3])
        await db.flush()

        c1 = RecoveryCase(
            id="case_rec_001",
            case_type="PAYMENT_FAILURE",
            merchant_id=merchant_id,
            customer_id="cust_acme_corp",
            transaction_id="txn_001",
            amount=15000.00,
            risk_score=45.0,
            risk_level="MEDIUM",
            priority_score=60.0,
            priority_level="MEDIUM",
            status="ENGAGED",
            ai_root_cause="INSUFFICIENT_FUNDS",
            ai_recommended_action="SEND_PAYMENT_LINK",
            ai_confidence=0.92,
            ai_reasoning="High probability of recovery via payment link; customer has good payment history.",
            policy_passed=True,
            retry_count=1,
            recovered_amount=0.0
        )
        c2 = RecoveryCase(
            id="case_rec_002",
            case_type="PAYMENT_FAILURE",
            merchant_id=merchant_id,
            customer_id="cust_globex",
            transaction_id="txn_002",
            amount=45000.00,
            risk_score=15.0,
            risk_level="LOW",
            priority_score=85.0,
            priority_level="HIGH",
            status="RECOVERED",
            ai_root_cause="CARD_EXPIRED",
            ai_recommended_action="TRIGGER_MANDATE_RETRY",
            ai_confidence=0.97,
            ai_reasoning="Card details updated; auto-debit retry successful.",
            policy_passed=True,
            retry_count=1,
            recovered_amount=45000.00,
            actual_action_taken="MANDATE_RETRY_SUCCESSFUL"
        )
        c3 = RecoveryCase(
            id="case_rec_003",
            case_type="PAYMENT_FAILURE",
            merchant_id=merchant_id,
            customer_id="cust_soylent",
            transaction_id="txn_003",
            amount=500.00,
            risk_score=85.0,
            risk_level="HIGH",
            priority_score=30.0,
            priority_level="LOW",
            status="ESCALATED",
            ai_root_cause="AUTHENTICATION_FAILED",
            ai_recommended_action="OFFER_DISCOUNT_INCENTIVE",
            ai_confidence=0.78,
            ai_reasoning="Multiple authentication failures; escalated for manual operator review.",
            policy_passed=False,
            policy_failure_reason="Maximum retry limit reached for high-risk customer.",
            retry_count=3,
            recovered_amount=0.0
        )
        db.add_all([c1, c2, c3])
        await db.commit()
        logger.info("Successfully seeded demo recovery cases and transactions into database.")






