import pytest
from datetime import datetime, timezone, timedelta
from app.models.subscription import Subscription, SubscriptionPaymentAttempt
from app.models.transaction import Transaction
from app.models.recovery_case import RecoveryCase
from app.models.merchant import Merchant
from app.services.revenue_risk.subscription_recovery import (
    subscription_recovery_service,
    classify_subscription_failure,
    SUBSCRIPTION_MAX_RETRY_ATTEMPTS,
    SUBSCRIPTION_GRACE_PERIOD_HOURS
)

@pytest.mark.asyncio
async def test_subscription_creation_defaults(db_session):
    sub = await subscription_recovery_service.create_subscription(
        db=db_session,
        merchant_id="m_sub_01",
        plan_name="Growth SaaS",
        amount=1999.0,
        billing_interval="monthly"
    )
    assert sub.id is not None
    assert sub.status == "ACTIVE"
    assert sub.recovery_status == "ACTIVE"
    assert sub.retry_count == 0
    assert sub.max_retry_attempts == 3

@pytest.mark.asyncio
async def test_failure_taxonomy_classification():
    assert classify_subscription_failure(error_reason="card_expired") == "PAYMENT_METHOD_EXPIRED"
    assert classify_subscription_failure(error_reason="insufficient_funds") == "INSUFFICIENT_FUNDS"
    assert classify_subscription_failure(error_reason="card_declined") == "CARD_DECLINED"
    assert classify_subscription_failure(error_code="BAD_REQUEST_ERROR") == "PAYMENT_METHOD_INVALID"
    assert classify_subscription_failure(error_reason="bank_error") == "BANK_DECLINED"
    assert classify_subscription_failure(error_description="network gateway timeout") == "NETWORK_FAILURE"
    assert classify_subscription_failure(error_description="unknown error") == "UNKNOWN"

@pytest.mark.asyncio
async def test_handle_failed_subscription_payment(db_session):
    sub = await subscription_recovery_service.create_subscription(
        db=db_session, merchant_id="m_sub_02", plan_name="Pro Monthly", amount=4999.0
    )
    txn = Transaction(
        merchant_id="m_sub_02",
        amount=4999.0,
        currency="INR",
        status="failed",
        error_code="BAD_REQUEST_ERROR",
        error_reason="insufficient_funds",
        error_description="Account balance insufficient for recurring debit"
    )
    db_session.add(txn)
    await db_session.commit()

    attempt, case = await subscription_recovery_service.handle_failed_subscription_payment(
        db=db_session, subscription_id=sub.id, txn=txn, attempt_number=1
    )
    assert attempt.subscription_id == sub.id
    assert case.case_type == "SUBSCRIPTION_FAILURE"
    assert sub.status == "PAYMENT_FAILED"
    assert sub.recovery_status == "GRACE_PERIOD"
    assert sub.failure_reason == "INSUFFICIENT_FUNDS"
    assert sub.grace_period_until is not None

@pytest.mark.asyncio
async def test_get_subscription_recovery_status(db_session):
    sub = await subscription_recovery_service.create_subscription(
        db=db_session, merchant_id="m_sub_03", plan_name="Scale Plan", amount=9999.0
    )
    status_resp = await subscription_recovery_service.get_subscription_recovery_status(db_session, sub.id)
    assert status_resp.subscription_id == sub.id
    assert status_resp.status == "ACTIVE"
    assert status_resp.retry_allowed is True
    assert len(status_resp.lineage) >= 1

@pytest.mark.asyncio
async def test_evaluate_and_execute_subscription_retry(db_session):
    sub = await subscription_recovery_service.create_subscription(
        db=db_session, merchant_id="m_sub_04", plan_name="Starter Plan", amount=999.0
    )
    retry_resp = await subscription_recovery_service.evaluate_and_execute_subscription_retry(db_session, sub.id)
    assert retry_resp.status == "RETRY_INITIATED"
    assert retry_resp.retry_count == 1
    assert retry_resp.razorpay_order_id.startswith("order_sub_rec_")

@pytest.mark.asyncio
async def test_retry_blocked_when_already_recovered(db_session):
    sub = await subscription_recovery_service.create_subscription(
        db=db_session, merchant_id="m_sub_05", plan_name="Enterprise Plan", amount=15000.0
    )
    sub.status = "PAYMENT_RECOVERED"
    db_session.add(sub)
    await db_session.commit()

    retry_resp = await subscription_recovery_service.evaluate_and_execute_subscription_retry(db_session, sub.id)
    assert retry_resp.status == "ALREADY_RECOVERED"

@pytest.mark.asyncio
async def test_retry_blocked_when_max_retries_reached(db_session):
    sub = await subscription_recovery_service.create_subscription(
        db=db_session, merchant_id="m_sub_06", plan_name="Basic Plan", amount=499.0
    )
    sub.retry_count = 3
    db_session.add(sub)
    await db_session.commit()

    case = RecoveryCase(
        case_type="SUBSCRIPTION_FAILURE",
        merchant_id="m_sub_06",
        subscription_id=sub.id,
        amount=499.0,
        risk_level="LOW",
        retry_count=3,
        status="OPEN"
    )
    db_session.add(case)
    await db_session.commit()

    retry_resp = await subscription_recovery_service.evaluate_and_execute_subscription_retry(db_session, sub.id)
    assert retry_resp.status in ["BLOCKED", "REVIEW_REQUIRED"]

@pytest.mark.asyncio
async def test_get_subscription_analytics(db_session):
    analytics = await subscription_recovery_service.get_subscription_analytics(db_session)
    assert analytics.total_subscriptions >= 0
    assert analytics.failure_rate >= 0.0
    assert analytics.recovery_rate >= 0.0

@pytest.mark.asyncio
async def test_endpoint_list_subscriptions(async_client):
    res = await async_client.get("/api/v1/subscriptions")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

@pytest.mark.asyncio
async def test_endpoint_failed_subscriptions_analytics(async_client):
    res = await async_client.get("/api/v1/analytics/failed-subscriptions")
    assert res.status_code == 200
    data = res.json()
    assert "total_subscriptions" in data
    assert "subscription_risk_amount" in data

@pytest.mark.asyncio
async def test_endpoint_subscription_detail_and_recovery(async_client, db_session):
    sub = await subscription_recovery_service.create_subscription(
        db=db_session, merchant_id="m_ep_sub", plan_name="API Plan", amount=2999.0
    )
    res1 = await async_client.get(f"/api/v1/subscriptions/{sub.id}")
    assert res1.status_code == 200
    assert res1.json()["id"] == sub.id

    res2 = await async_client.get(f"/api/v1/subscriptions/{sub.id}/recovery")
    assert res2.status_code == 200
    assert res2.json()["subscription_id"] == sub.id

@pytest.mark.asyncio
async def test_endpoint_subscription_retry_and_stop(async_client, db_session):
    sub = await subscription_recovery_service.create_subscription(
        db=db_session, merchant_id="m_ep_retry", plan_name="API Retry Plan", amount=3999.0
    )
    res_retry = await async_client.post(f"/api/v1/subscriptions/{sub.id}/retry")
    assert res_retry.status_code == 200
    assert res_retry.json()["status"] == "RETRY_INITIATED"

    res_stop = await async_client.post(f"/api/v1/subscriptions/{sub.id}/stop")
    assert res_stop.status_code == 200
    assert res_stop.json()["status"] == "STOPPED"

@pytest.mark.asyncio
async def test_step_1_ai_decision_regression():
    from app.services.recovery.ai_decision_service import ai_decision_service
    case = RecoveryCase(id="c_reg_s1_sub", merchant_id="m_test", amount=10.0, risk_level="LOW", status="OPEN")
    eval_res = ai_decision_service.assess_case(case)
    assert eval_res.case_id == "c_reg_s1_sub"

@pytest.mark.asyncio
async def test_step_2_policy_gate_regression():
    from app.services.recovery.policy_gate import policy_gate
    case = RecoveryCase(id="c_reg_s2_sub", merchant_id="m_test", amount=10.0, risk_score=10.0, risk_level="LOW", status="OPEN")
    pol = policy_gate.assess_case(case)
    assert pol.decision in ["ALLOW_RECOVERY", "REVIEW_REQUIRED", "BLOCK_RECOVERY"]

@pytest.mark.asyncio
async def test_step_3_stopping_rules_regression():
    from app.services.recovery.stopping_rules import stopping_rules
    case = RecoveryCase(id="c_reg_s3_sub", merchant_id="m_test", amount=10.0, retry_count=0, risk_level="LOW", status="OPEN")
    stp = stopping_rules.evaluate_case(case)
    assert stp.decision in ["CONTINUE", "STOP"]

@pytest.mark.asyncio
async def test_step_4_human_escalation_regression():
    from app.services.recovery.human_escalation import human_escalation
    case = RecoveryCase(id="c_reg_s4_sub", merchant_id="m_test", amount=10.0, risk_level="LOW", status="ESCALATED")
    esc = human_escalation.evaluate_case(case)
    assert esc.should_escalate is True

@pytest.mark.asyncio
async def test_step_7_failure_fallback_regression(db_session):
    from app.services.recovery.failure_fallback import failure_fallback, SimulateFailureRequest
    req = SimulateFailureRequest(scenario_key="RAZORPAY_ORDER_FAILURE")
    f_res = await failure_fallback.simulate_failure(req, db_session)
    assert f_res.case_state_preserved == "OPEN"

@pytest.mark.asyncio
async def test_step_8_notifications_regression(db_session):
    from app.services.notification_service import notification_service
    n = await notification_service.create_notification(
        db_session, type="SUBSCRIPTION_PAYMENT_FAILED", severity="WARNING", title="Sub Failed", message="Failed", case_id="c_reg_s8_sub"
    )
    assert n.type == "SUBSCRIPTION_PAYMENT_FAILED"

@pytest.mark.asyncio
async def test_step_9_checkout_abandonment_regression(db_session):
    from app.services.recovery.checkout_abandonment import checkout_abandonment_service
    case = RecoveryCase(id="c_reg_s9_sub", merchant_id="m_test", amount=10.0, risk_level="LOW", status="OPEN", case_type="CHECKOUT_DROPOFF")
    db_session.add(case)
    await db_session.commit()
    chk = await checkout_abandonment_service.get_checkout_status(db_session, case.id)
    assert chk.state == "CHECKOUT_ABANDONED"
