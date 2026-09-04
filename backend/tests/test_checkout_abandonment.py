import pytest
from app.models.recovery_case import RecoveryCase
from app.models.checkout_session import CheckoutSession
from app.services.recovery.checkout_abandonment import checkout_abandonment_service, CheckoutAbandonmentMetrics

@pytest.mark.asyncio
async def test_get_checkout_status(db_session):
    case = RecoveryCase(
        id="c_ab_status_01",
        merchant_id="m_test",
        amount=100.0,
        risk_level="LOW",
        status="OPEN",
        case_type="CHECKOUT_DROPOFF"
    )
    db_session.add(case)
    await db_session.commit()

    status_resp = await checkout_abandonment_service.get_checkout_status(db_session, case.id)
    assert status_resp.case_id == case.id
    assert status_resp.state == "CHECKOUT_ABANDONED"
    assert status_resp.retry_allowed is True
    assert len(status_resp.lineage) >= 3

@pytest.mark.asyncio
async def test_evaluate_and_execute_retry_allowed(db_session):
    case = RecoveryCase(
        id="c_ab_retry_01",
        merchant_id="m_test",
        amount=50.0,
        risk_score=10.0,
        risk_level="LOW",
        status="OPEN",
        retry_count=0
    )
    db_session.add(case)
    await db_session.commit()

    retry_resp = await checkout_abandonment_service.evaluate_and_execute_retry(db_session, case.id)
    assert retry_resp.status == "RETRY_INITIATED"
    assert retry_resp.retry_count == 1
    assert retry_resp.razorpay_order_id.startswith("order_rec_")

@pytest.mark.asyncio
async def test_retry_blocked_when_already_recovered(db_session):
    case = RecoveryCase(
        id="c_ab_rec_01",
        merchant_id="m_test",
        amount=20.0,
        recovered_amount=20.0,
        risk_level="LOW",
        status="RECOVERED"
    )
    db_session.add(case)
    await db_session.commit()

    retry_resp = await checkout_abandonment_service.evaluate_and_execute_retry(db_session, case.id)
    assert retry_resp.status == "ALREADY_RECOVERED"

@pytest.mark.asyncio
async def test_retry_blocked_by_stopping_rules(db_session):
    case = RecoveryCase(
        id="c_ab_stop_01",
        merchant_id="m_test",
        amount=50.0,
        risk_level="LOW",
        status="OPEN",
        retry_count=3
    )
    db_session.add(case)
    await db_session.commit()

    retry_resp = await checkout_abandonment_service.evaluate_and_execute_retry(db_session, case.id)
    assert retry_resp.status in ["BLOCKED", "REVIEW_REQUIRED"]

@pytest.mark.asyncio
async def test_get_abandonment_metrics(db_session):
    metrics = await checkout_abandonment_service.get_abandonment_metrics(db_session)
    assert isinstance(metrics, CheckoutAbandonmentMetrics)
    assert metrics.abandonment_rate >= 0.0
    assert metrics.completion_rate >= 0.0

@pytest.mark.asyncio
async def test_endpoint_checkout_abandonment(async_client):
    res = await async_client.get("/api/v1/analytics/checkout-abandonment")
    assert res.status_code == 200
    data = res.json()
    assert "abandonment_rate" in data
    assert "completion_rate" in data

@pytest.mark.asyncio
async def test_endpoint_checkout_status(async_client, db_session):
    case = RecoveryCase(
        id="c_ep_chk_01",
        merchant_id="m_test",
        amount=30.0,
        risk_level="LOW",
        status="OPEN"
    )
    db_session.add(case)
    await db_session.commit()

    res = await async_client.get(f"/api/v1/cases/{case.id}/checkout-status")
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == case.id
    assert "state" in data

@pytest.mark.asyncio
async def test_endpoint_checkout_retry(async_client, db_session):
    case = RecoveryCase(
        id="c_ep_retry_01",
        merchant_id="m_test",
        amount=30.0,
        risk_score=10.0,
        risk_level="LOW",
        status="OPEN",
        retry_count=0
    )
    db_session.add(case)
    await db_session.commit()

    res = await async_client.post(f"/api/v1/cases/{case.id}/checkout-retry")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "RETRY_INITIATED"

@pytest.mark.asyncio
async def test_step_1_ai_decision_regression():
    from app.services.recovery.ai_decision_service import ai_decision_service
    case = RecoveryCase(id="c_reg_s1_ab", merchant_id="m_test", amount=10.0, risk_level="LOW", status="OPEN")
    eval_res = ai_decision_service.assess_case(case)
    assert eval_res.case_id == "c_reg_s1_ab"

@pytest.mark.asyncio
async def test_step_2_policy_gate_regression():
    from app.services.recovery.policy_gate import policy_gate
    case = RecoveryCase(id="c_reg_s2_ab", merchant_id="m_test", amount=10.0, risk_score=10.0, risk_level="LOW", status="OPEN")
    pol = policy_gate.assess_case(case)
    assert pol.decision in ["ALLOW_RECOVERY", "REVIEW_REQUIRED", "BLOCK_RECOVERY"]

@pytest.mark.asyncio
async def test_step_3_stopping_rules_regression():
    from app.services.recovery.stopping_rules import stopping_rules
    case = RecoveryCase(id="c_reg_s3_ab", merchant_id="m_test", amount=10.0, retry_count=0, risk_level="LOW", status="OPEN")
    stp = stopping_rules.evaluate_case(case)
    assert stp.decision in ["CONTINUE", "STOP"]

@pytest.mark.asyncio
async def test_step_4_human_escalation_regression():
    from app.services.recovery.human_escalation import human_escalation
    case = RecoveryCase(id="c_reg_s4_ab", merchant_id="m_test", amount=10.0, risk_level="LOW", status="ESCALATED")
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
        db_session, type="CHECKOUT_ABANDONED", severity="WARNING", title="Checkout Abandoned", message="Abandoned", case_id="c_reg_s8_ab"
    )
    assert n.type == "CHECKOUT_ABANDONED"
