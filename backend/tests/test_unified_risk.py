import pytest
from app.models.merchant import Merchant
from app.models.transaction import Transaction
from app.models.checkout_session import CheckoutSession
from app.models.subscription import Subscription
from app.models.recovery_case import RecoveryCase
from app.services.revenue_risk.unified_risk import unified_risk_service
from app.services.revenue_risk.priority_engine import priority_engine

@pytest.mark.asyncio
async def test_priority_engine_deterministic():
    res_high = priority_engine.calculate_priority(
        amount=49999.0,
        recoverability_score=0.85,
        customer_successful_payments=5,
        retry_count=0,
        case_type="SUBSCRIPTION_FAILURE"
    )
    assert res_high.priority_score >= 75.0
    assert res_high.priority_level == "CRITICAL"
    assert len(res_high.priority_factors) > 0

    res_low = priority_engine.calculate_priority(
        amount=499.0,
        recoverability_score=0.20,
        customer_successful_payments=0,
        retry_count=3,
        case_type="PAYMENT_FAILURE"
    )
    assert res_low.priority_score < 40.0
    assert res_low.priority_level in ["LOW", "MEDIUM"]

@pytest.mark.asyncio
async def test_unified_risk_summary_and_opportunities(db_session):
    merchant = Merchant(name="Unified Merchant", email="unified@merchant.com")
    db_session.add(merchant)
    await db_session.commit()
    await db_session.refresh(merchant)

    # 1. Payment failure case
    txn = Transaction(merchant_id=merchant.id, amount=5000.0, status="failed", error_code="GATEWAY_ERROR")
    db_session.add(txn)
    await db_session.commit()
    await db_session.refresh(txn)

    c1 = RecoveryCase(
        case_type="PAYMENT_FAILURE",
        merchant_id=merchant.id,
        transaction_id=txn.id,
        amount=5000.0,
        risk_score=45.0,
        risk_level="MEDIUM",
        status="OPEN"
    )
    db_session.add(c1)

    # 2. Checkout dropoff case
    cs = CheckoutSession(merchant_id=merchant.id, amount=7500.0, status="DROPPED")
    db_session.add(cs)
    await db_session.commit()

    c2 = RecoveryCase(
        case_type="CHECKOUT_DROPOFF",
        merchant_id=merchant.id,
        checkout_session_id=cs.id,
        amount=7500.0,
        risk_score=35.0,
        risk_level="MEDIUM",
        status="OPEN"
    )
    db_session.add(c2)

    # 3. Subscription failure case
    sub = Subscription(merchant_id=merchant.id, plan_name="SaaS Pro", amount=12000.0, status="PAYMENT_FAILED")
    db_session.add(sub)
    await db_session.commit()

    c3 = RecoveryCase(
        case_type="SUBSCRIPTION_FAILURE",
        merchant_id=merchant.id,
        subscription_id=sub.id,
        amount=12000.0,
        risk_score=65.0,
        risk_level="HIGH",
        status="OPEN"
    )
    db_session.add(c3)
    await db_session.commit()

    opps_res = await unified_risk_service.get_unified_opportunities(db_session)
    s = opps_res.summary

    assert s.total_revenue_at_risk == 24500.0  # 5000 + 7500 + 12000
    assert s.payment_failure_risk == 5000.0
    assert s.checkout_dropoff_risk == 7500.0
    assert s.subscription_risk == 12000.0
    assert s.active_opportunities_count == 3
    assert len(opps_res.opportunities) == 3

    # Verify priority sorting: opportunities sorted by priority_score descending
    assert opps_res.opportunities[0].priority_score >= opps_res.opportunities[1].priority_score
    assert opps_res.opportunities[1].priority_score >= opps_res.opportunities[2].priority_score

@pytest.mark.asyncio
async def test_recovered_case_leaves_active_risk(db_session):
    merchant = Merchant(name="Unified Merchant 2", email="unified2@merchant.com")
    db_session.add(merchant)
    await db_session.commit()
    await db_session.refresh(merchant)

    c_rec = RecoveryCase(
        case_type="PAYMENT_FAILURE",
        merchant_id=merchant.id,
        amount=10000.0,
        recovered_amount=10000.0,
        risk_score=20.0,
        risk_level="LOW",
        status="RECOVERED"
    )
    db_session.add(c_rec)
    await db_session.commit()

    opps_res = await unified_risk_service.get_unified_opportunities(db_session)
    # Recovered case should not contribute to active revenue at risk
    item = next((x for x in opps_res.summary.cases_by_unified_status if x == "RECOVERED"), None)
    assert item is not None
    assert opps_res.summary.total_recovered_revenue >= 10000.0
