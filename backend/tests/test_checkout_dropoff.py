import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from app.models.checkout_session import CheckoutSession
from app.models.recovery_case import RecoveryCase
from app.models.merchant import Merchant
from app.models.customer import Customer
from app.models.base import utc_now
from app.services.revenue_risk.dropoff_detector import dropoff_detector, CHECKOUT_DROPOFF_WINDOW_MINUTES

@pytest.mark.asyncio
async def test_checkout_session_creation(db_session):
    merchant = Merchant(name="Test Merchant", email="merchant@test.com")
    db_session.add(merchant)
    await db_session.commit()
    await db_session.refresh(merchant)

    session = await dropoff_detector.create_checkout_session(
        db=db_session,
        merchant_id=merchant.id,
        amount=2500.0,
        currency="INR"
    )
    assert session.id is not None
    assert session.status == "CREATED"
    assert float(session.amount) == 2500.0

@pytest.mark.asyncio
async def test_active_checkout_not_marked_dropped(db_session):
    merchant = Merchant(name="Test Merchant 2", email="merchant2@test.com")
    db_session.add(merchant)
    await db_session.commit()
    await db_session.refresh(merchant)

    # Fresh checkout created just now
    session = await dropoff_detector.create_checkout_session(
        db=db_session,
        merchant_id=merchant.id,
        amount=1500.0
    )

    created_cases = await dropoff_detector.detect_and_process_dropoffs(db_session, window_minutes=30)
    assert len(created_cases) == 0

    await db_session.refresh(session)
    assert session.status == "CREATED"

@pytest.mark.asyncio
async def test_inactive_checkout_marked_dropped_and_case_created(db_session):
    merchant = Merchant(name="Test Merchant 3", email="merchant3@test.com")
    db_session.add(merchant)
    await db_session.commit()
    await db_session.refresh(merchant)

    # Checkout created 45 minutes ago
    old_time = utc_now() - timedelta(minutes=45)
    session = CheckoutSession(
        merchant_id=merchant.id,
        amount=3500.0,
        currency="INR",
        status="CREATED",
        created_at=old_time
    )
    db_session.add(session)
    await db_session.commit()

    created_cases = await dropoff_detector.detect_and_process_dropoffs(db_session, window_minutes=30)
    assert len(created_cases) == 1
    case = created_cases[0]

    assert case.case_type == "CHECKOUT_DROPOFF"
    assert case.checkout_session_id == session.id
    assert float(case.amount) == 3500.0

    await db_session.refresh(session)
    assert session.status == "DROPPED"

@pytest.mark.asyncio
async def test_dropoff_detection_idempotency(db_session):
    merchant = Merchant(name="Test Merchant 4", email="merchant4@test.com")
    db_session.add(merchant)
    await db_session.commit()
    await db_session.refresh(merchant)

    old_time = utc_now() - timedelta(minutes=50)
    session = CheckoutSession(
        merchant_id=merchant.id,
        amount=4500.0,
        currency="INR",
        status="CREATED",
        created_at=old_time
    )
    db_session.add(session)
    await db_session.commit()

    # First run
    cases1 = await dropoff_detector.detect_and_process_dropoffs(db_session, window_minutes=30)
    assert len(cases1) == 1

    # Second run (should be idempotent)
    cases2 = await dropoff_detector.detect_and_process_dropoffs(db_session, window_minutes=30)
    assert len(cases2) == 0

    all_cases = await db_session.execute(
        select(RecoveryCase).where(RecoveryCase.checkout_session_id == session.id)
    )
    assert len(all_cases.scalars().all()) == 1
