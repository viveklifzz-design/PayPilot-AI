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
    from app.models.subscription import Subscription
    from app.models.receivables_and_mandates import Mandate, Invoice
    from app.models.audit_log import AuditLog
    from app.models.notification import Notification
    from app.models.base import utc_now
    from app.services.recovery.reconciliation_service import reconciliation_service
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
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

        # Check if demo case case_rec_001 exists
        c1_res = await db.execute(select(RecoveryCase).where(RecoveryCase.id == "case_rec_001"))
        c1_exists = c1_res.scalar_one_or_none()

        if not c1_exists:
            logger.info("Demo recovery case 'case_rec_001' not found. Populating complete demo data set...")
            
            # Customers
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
            cust_initech = Customer(
                id="cust_test_vip",
                merchant_id=merchant_id,
                name="Initech LLC",
                email="billing@initech.com",
                phone="+919876543213"
            )

            for c_obj in [cust_acme, cust_globex, cust_soylent, cust_initech]:
                existing_c = await db.execute(select(Customer).where(Customer.id == c_obj.id))
                if not existing_c.scalar_one_or_none():
                    db.add(c_obj)
            await db.flush()

            # Transactions
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
            t4 = Transaction(
                id="txn_004",
                merchant_id=merchant_id,
                customer_id="cust_test_vip",
                amount=4999.00,
                currency="INR",
                status="failed",
                error_code="BAD_REQUEST_ISSUER_DECLINED",
                error_reason="issuer_declined",
                error_description="Subscription recurring attempt #1 failed (Growth SaaS Monthly)"
            )
            t5 = Transaction(
                id="txn_005",
                merchant_id=merchant_id,
                customer_id="cust_acme_corp",
                amount=22000.00,
                currency="INR",
                status="failed",
                error_code="BAD_REQUEST_ERROR",
                error_reason="mandate_debit_failed",
                error_description="Mandate maximum retry count (3) exceeded"
            )
            t6 = Transaction(
                id="txn_006",
                merchant_id=merchant_id,
                customer_id="cust_globex",
                amount=115000.00,
                currency="INR",
                status="failed",
                error_code="BAD_REQUEST_ERROR",
                error_reason="overdue_receivable",
                error_description="B2B invoice overdue (INV-P2P-VERIFY-1787594827)"
            )
            t_legacy = Transaction(
                id="txn_legacy_001",
                merchant_id=merchant_id,
                customer_id="cust_acme_corp",
                amount=2500.00,
                currency="INR",
                status="failed",
                error_code="BAD_REQUEST_PAYMENT_TIMED_OUT",
                error_reason="timed_out",
                error_description="Legacy unverified test transaction"
            )

            for t_obj in [t1, t2, t3, t4, t5, t6, t_legacy]:
                existing_t = await db.execute(select(Transaction).where(Transaction.id == t_obj.id))
                if not existing_t.scalar_one_or_none():
                    db.add(t_obj)
            await db.flush()

            # Cases
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
                ai_reasoning="High probability of recovery via payment link; customer has good payment history. Lineage: DEMO / SYNTHETIC",
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
                ai_reasoning="Card details updated; auto-debit retry successful. Lineage: DEMO / SYNTHETIC",
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
                ai_reasoning="Multiple authentication failures; escalated for manual operator review. Lineage: DEMO / SYNTHETIC",
                policy_passed=False,
                policy_failure_reason="Maximum retry limit reached for high-risk customer.",
                retry_count=3,
                recovered_amount=0.0
            )
            c4 = RecoveryCase(
                id="case_rec_004",
                case_type="SUBSCRIPTION_FAILURE",
                merchant_id=merchant_id,
                customer_id="cust_test_vip",
                transaction_id="txn_004",
                amount=4999.00,
                risk_score=36.5,
                risk_level="MEDIUM",
                priority_score=50.0,
                priority_level="MEDIUM",
                status="ENGAGED",
                ai_root_cause="ISSUER_DECLINED",
                ai_recommended_action="SEND_RECOVERY_LINK",
                ai_confidence=0.88,
                ai_reasoning="Subscription recurring charge failed (Growth SaaS Monthly). Lineage: DEMO / SYNTHETIC",
                policy_passed=True,
                retry_count=1,
                recovered_amount=0.0
            )
            c5 = RecoveryCase(
                id="case_rec_005",
                case_type="MANDATE_RETRY",
                merchant_id=merchant_id,
                customer_id="cust_acme_corp",
                transaction_id="txn_005",
                amount=22000.00,
                risk_score=65.0,
                risk_level="HIGH",
                priority_score=75.0,
                priority_level="HIGH",
                status="ESCALATED",
                ai_root_cause="MANDATE_DEBIT_FAILED",
                ai_recommended_action="HUMAN_OPERATOR_REVIEW",
                ai_confidence=0.85,
                ai_reasoning="Mandate retry limit exceeded. Lineage: DEMO / SYNTHETIC",
                policy_passed=False,
                policy_failure_reason="Mandate maximum retry count (3) exceeded",
                retry_count=3,
                recovered_amount=0.0
            )
            c6 = RecoveryCase(
                id="case_rec_006",
                case_type="B2B_RECEIVABLE",
                merchant_id=merchant_id,
                customer_id="cust_globex",
                transaction_id="txn_006",
                amount=115000.00,
                risk_score=70.0,
                risk_level="HIGH",
                priority_score=90.0,
                priority_level="HIGH",
                status="ESCALATED",
                ai_root_cause="OVERDUE_RECEIVABLE",
                ai_recommended_action="SEND_P2P_REMINDER",
                ai_confidence=0.90,
                ai_reasoning="B2B Invoice INV-P2P-VERIFY-1787594827 is overdue. Lineage: DEMO / SYNTHETIC",
                policy_passed=True,
                retry_count=0,
                recovered_amount=0.0
            )
            c_legacy = RecoveryCase(
                id="a802b0cb-06a3-4ba2-b0d5-e1ab37422741",
                case_type="PAYMENT_FAILURE",
                merchant_id=merchant_id,
                customer_id="cust_acme_corp",
                transaction_id="txn_legacy_001",
                amount=2500.00,
                risk_score=11.25,
                risk_level="LOW",
                priority_score=28.0,
                priority_level="LOW",
                status="INVALID_UNRECONCILED",
                ai_root_cause="BAD_REQUEST_PAYMENT_TIMED_OUT",
                ai_recommended_action="RECOVERY_LINK",
                ai_confidence=0.92,
                ai_reasoning="Legacy unverified test record. Lineage: INVALID / UNRECONCILED",
                policy_passed=False,
                retry_count=0,
                recovered_amount=0.0
            )

            for c_obj in [c1, c2, c3, c4, c5, c6, c_legacy]:
                existing_c = await db.execute(select(RecoveryCase).where(RecoveryCase.id == c_obj.id))
                if not existing_c.scalar_one_or_none():
                    db.add(c_obj)
            await db.flush()

            # Subscriptions
            sub1 = Subscription(
                id="22e299a1-fdab-4d21-9560-f4193c607cd4",
                merchant_id=merchant_id,
                customer_id="cust_test_vip",
                provider="RAZORPAY",
                plan_name="Growth SaaS Monthly",
                amount=4999.00,
                currency="INR",
                billing_interval="monthly",
                status="PAYMENT_FAILED",
                failure_reason="BAD_REQUEST_ISSUER_DECLINED",
                retry_count=1,
                max_retry_attempts=3
            )
            existing_sub = await db.execute(select(Subscription).where(Subscription.id == sub1.id))
            if not existing_sub.scalar_one_or_none():
                db.add(sub1)
            await db.flush()

            # Mandates
            m1 = Mandate(
                id="216643bb-a143-4c18-9b75-199f44827064",
                merchant_id=merchant_id,
                customer_id="cust_acme_corp",
                mandate_number="MND-VERIFY-1787594822",
                amount=22000.00,
                currency="INR",
                billing_interval="monthly",
                attempt_count=3,
                max_attempts=3,
                status="CANCELLED"
            )
            m2 = Mandate(
                id="6b66d2b4-da8b-43b3-91d4-0d3f5498c09a",
                merchant_id=merchant_id,
                customer_id="cust_globex",
                mandate_number="MND-6982",
                amount=8500.00,
                currency="INR",
                billing_interval="monthly",
                attempt_count=0,
                max_attempts=3,
                status="ACTIVE"
            )
            m3 = Mandate(
                id="29008464-15a2-4fd0-815a-f78641cca48e",
                merchant_id=merchant_id,
                customer_id="cust_soylent",
                mandate_number="MND-2009",
                amount=8500.00,
                currency="INR",
                billing_interval="monthly",
                attempt_count=1,
                max_attempts=3,
                status="RECOVERED",
                failure_reason="Bank auto-debit failed (Insufficient funds)"
            )
            m4 = Mandate(
                id="f1edca2d-db50-4f19-ae8b-e8f81117b23b",
                merchant_id=merchant_id,
                customer_id="cust_test_vip",
                mandate_number="MND-7385",
                amount=12000.00,
                currency="INR",
                billing_interval="monthly",
                attempt_count=1,
                max_attempts=3,
                status="RECOVERED",
                failure_reason="Bank auto-debit failed (Insufficient funds)"
            )
            for m_obj in [m1, m2, m3, m4]:
                existing_m = await db.execute(select(Mandate).where(Mandate.id == m_obj.id))
                if not existing_m.scalar_one_or_none():
                    db.add(m_obj)
            await db.flush()

            # Invoices
            inv1 = Invoice(
                id="dd1bdea5-57d2-483c-8b31-1841794b19a6",
                merchant_id=merchant_id,
                customer_id="cust_acme_corp",
                invoice_number="INV-VERIFY-1787594805",
                amount=45000.00,
                currency="INR",
                due_date=utc_now(),
                status="ESCALATED",
                days_overdue=13
            )
            inv2 = Invoice(
                id="c64927a9-9fc7-42b4-8555-75c17e408607",
                merchant_id=merchant_id,
                customer_id="cust_globex",
                invoice_number="INV-P2P-VERIFY-1787594827",
                amount=115000.00,
                currency="INR",
                due_date=utc_now(),
                status="ESCALATED",
                days_overdue=2
            )
            inv3 = Invoice(
                id="fede9283-d0f9-4b92-a7c4-6bbf43499068",
                merchant_id=merchant_id,
                customer_id="cust_soylent",
                invoice_number="INV-E2E-9901",
                amount=2500.00,
                currency="INR",
                due_date=utc_now(),
                status="ESCALATED",
                days_overdue=2
            )
            for inv_obj in [inv1, inv2, inv3]:
                existing_inv = await db.execute(select(Invoice).where(Invoice.id == inv_obj.id))
                if not existing_inv.scalar_one_or_none():
                    db.add(inv_obj)
            await db.flush()

            # Notifications
            n1 = Notification(
                id="notif_001",
                case_id="case_rec_001",
                merchant_id=merchant_id,
                type="PAYMENT_RECOVERY_LINK",
                severity="INFO",
                title="Payment Recovery Link Delivered",
                message="PayPilot AI: Your payment of INR 15,000 to Acme Technologies requires re-authorization. Click to recover."
            )
            existing_n = await db.execute(select(Notification).where(Notification.id == n1.id))
            if not existing_n.scalar_one_or_none():
                db.add(n1)

            # Audit Logs
            a1 = AuditLog(
                case_id="case_rec_001",
                actor="SYSTEM_SEEDER",
                event_type="DEMO_FIXTURE_INITIALIZED",
                description="Demo fixture initialized for PayPilot AI recovery evaluation."
            )
            existing_a = await db.execute(select(AuditLog).where(AuditLog.case_id == "case_rec_001"))
            if not existing_a.scalars().first():
                db.add(a1)

            await db.commit()
            logger.info("Successfully seeded complete demo dataset.")

        # Always run Provider Reconciliation for real Razorpay captured payment pay_TU3EQsT63DFVuX
        try:
            logger.info("Running provider reconciliation for pay_TU3EQsT63DFVuX / order_TU2xgzptEfg7rP...")
            recon_res = await reconciliation_service.reconcile_provider_recovery(
                payment_id="pay_TU3EQsT63DFVuX",
                order_id="order_TU2xgzptEfg7rP",
                db=db,
                verification_source="SYSTEM_INITIALIZATION_RECONCILIATION"
            )
            logger.info(f"Provider Reconciliation result: {recon_res}")
        except Exception as recon_err:
            logger.warning(f"Provider reconciliation during init_db skipped/failed: {recon_err}")






