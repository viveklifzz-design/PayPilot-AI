import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.merchant import Merchant
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.models.recovery_case import RecoveryCase
from app.models.recovery_action import RecoveryAction
from app.models.audit_log import AuditLog
from app.models.webhook_event import WebhookEvent

@pytest.mark.asyncio
async def test_create_merchant_and_customer(db_session: AsyncSession):
    merchant = Merchant(
        name="Acme E-Commerce",
        email="support@acme.com",
        razorpay_key_id="rzp_test_123456"
    )
    db_session.add(merchant)
    await db_session.commit()
    await db_session.refresh(merchant)

    assert merchant.id is not None

    customer = Customer(
        merchant_id=merchant.id,
        name="John Doe",
        email="john@example.com",
        phone="+919876543210"
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)

    assert customer.id is not None
    assert customer.merchant_id == merchant.id

@pytest.mark.asyncio
async def test_create_transaction_and_recovery_case(db_session: AsyncSession):
    # Setup merchant
    merchant = Merchant(name="Test Shop", email="shop@test.com")
    db_session.add(merchant)
    await db_session.commit()

    # Create transaction
    txn = Transaction(
        merchant_id=merchant.id,
        razorpay_payment_id="pay_123456",
        amount=1500.50,
        status="failed",
        error_code="BAD_REQUEST_PAYMENT_TIMED_OUT",
        error_description="Payment timed out from bank server"
    )
    db_session.add(txn)
    await db_session.commit()
    await db_session.refresh(txn)

    assert txn.id is not None
    assert float(txn.amount) == 1500.50

    # Create Recovery Case
    case = RecoveryCase(
        merchant_id=merchant.id,
        transaction_id=txn.id,
        amount=txn.amount,
        risk_score=75.5,
        risk_level="HIGH",
        status="OPEN"
    )
    db_session.add(case)
    await db_session.commit()
    await db_session.refresh(case)

    assert case.id is not None
    assert case.status == "OPEN"
    assert case.policy_passed is False

@pytest.mark.asyncio
async def test_webhook_event_idempotency_constraint(db_session: AsyncSession):
    evt1 = WebhookEvent(
        event_id="evt_001",
        event_type="payment.failed",
        payload={"payment_id": "pay_100"}
    )
    db_session.add(evt1)
    await db_session.commit()

    evt2 = WebhookEvent(
        event_id="evt_001",
        event_type="payment.failed",
        payload={"payment_id": "pay_100"}
    )
    db_session.add(evt2)
    
    with pytest.raises(Exception):
        await db_session.commit()
    await db_session.rollback()
