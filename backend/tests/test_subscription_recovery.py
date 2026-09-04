import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from app.models.merchant import Merchant
from app.models.subscription import Subscription, SubscriptionPaymentAttempt
from app.models.transaction import Transaction
from app.models.recovery_case import RecoveryCase
from app.services.revenue_risk.subscription_recovery import subscription_recovery_service, MAX_SUBSCRIPTION_RETRIES
from app.services.policy import policy_engine

@pytest.mark.asyncio
async def test_subscription_creation(db_session):
    merchant = Merchant(name="Sub Merchant", email="submerchant@test.com")
    db_session.add(merchant)
    await db_session.commit()
    await db_session.refresh(merchant)

    sub = await subscription_recovery_service.create_subscription(
        db=db_session,
        merchant_id=merchant.id,
        plan_name="Pro SaaS Monthly",
        amount=4999.0,
        billing_interval="monthly"
    )
    assert sub.id is not None
    assert sub.status == "ACTIVE"
    assert sub.plan_name == "Pro SaaS Monthly"
    assert float(sub.amount) == 4999.0

@pytest.mark.asyncio
async def test_failed_subscription_payment_links_correctly(db_session):
    merchant = Merchant(name="Sub Merchant 2", email="submerchant2@test.com")
    db_session.add(merchant)
    await db_session.commit()
    await db_session.refresh(merchant)

    sub = await subscription_recovery_service.create_subscription(
        db=db_session,
        merchant_id=merchant.id,
        plan_name="Enterprise Plan",
        amount=12500.0,
        billing_interval="monthly"
    )

    txn = Transaction(
        merchant_id=merchant.id,
        amount=12500.0,
        currency="INR",
        status="failed",
        error_code="BAD_REQUEST_ERROR",
        error_description="Card limit exceeded during recurring billing",
        error_source="bank",
        error_step="payment_authorization",
        error_reason="card_limit_exceeded"
    )
    db_session.add(txn)
    await db_session.commit()
    await db_session.refresh(txn)

    attempt, case = await subscription_recovery_service.handle_failed_subscription_payment(
        db=db_session,
        subscription_id=sub.id,
        txn=txn,
        attempt_number=1
    )

    assert attempt.id is not None
    assert attempt.attempt_number == 1
    assert case.case_type == "SUBSCRIPTION_FAILURE"
    assert case.subscription_id == sub.id
    assert case.subscription_attempt_id == attempt.id

    await db_session.refresh(sub)
    assert sub.status == "PAYMENT_FAILED"

@pytest.mark.asyncio
async def test_subscription_retry_limit_policy_enforcement(db_session):
    # Retry #1 allowed
    res1 = policy_engine.evaluate_action(
        proposed_action="RECOVERY_LINK",
        case_status="OPEN",
        amount=4999.0,
        retry_count=1,
        ai_confidence=0.85
    )
    assert res1.allowed is True

    # Retry #4 blocked by max retries limit
    res4 = policy_engine.evaluate_action(
        proposed_action="RECOVERY_LINK",
        case_status="OPEN",
        amount=4999.0,
        retry_count=4,
        ai_confidence=0.85
    )
    assert res4.allowed is False
    assert "retry limit" in (res4.reason or "").lower() or "retries" in (res4.reason or "").lower()
