import pytest
from app.models.recovery_case import RecoveryCase
from app.services.recovery.failure_fallback import (
    failure_fallback,
    FailureCategory,
    RetryPolicy,
    SimulateFailureRequest
)

@pytest.mark.asyncio
async def test_failure_taxonomy_scenarios():
    scenarios = failure_fallback.list_scenarios()
    assert len(scenarios) >= 7
    keys = [s.scenario_key for s in scenarios]
    assert "AI_UNAVAILABLE" in keys
    assert "RAZORPAY_ORDER_FAILURE" in keys
    assert "PAYMENT_VERIFICATION_FAILURE" in keys
    assert "PROVIDER_VERIFICATION_FAILURE" in keys
    assert "POLICY_GATE_FAIL_CLOSED" in keys
    assert "STOPPING_RULES_FAIL_CLOSED" in keys
    assert "HUMAN_ESCALATION_FAILURE" in keys

@pytest.mark.asyncio
async def test_simulate_payment_verification_failure(db_session):
    req = SimulateFailureRequest(scenario_key="PAYMENT_VERIFICATION_FAILURE")
    res = await failure_fallback.simulate_failure(req, db_session)

    assert res.category == FailureCategory.PAYMENT_VERIFICATION_FAILURE
    assert res.retryable is False
    assert res.retry_policy == RetryPolicy.NON_RETRYABLE
    assert res.case_state_preserved == "OPEN"
    assert res.recovered_amount_preserved == 0.0
    assert res.audit_logged is True
    assert len(res.step_by_step_lineage) == 4

@pytest.mark.asyncio
async def test_simulate_ai_unavailable_fallback(db_session):
    req = SimulateFailureRequest(scenario_key="AI_UNAVAILABLE")
    res = await failure_fallback.simulate_failure(req, db_session)

    assert res.category == FailureCategory.AI_SERVICE_FAILURE
    assert res.retryable is True
    assert res.retry_policy == RetryPolicy.RETRYABLE
    assert "AI explanation is temporarily unavailable" in res.user_message

@pytest.mark.asyncio
async def test_simulate_policy_gate_fail_closed(db_session):
    req = SimulateFailureRequest(scenario_key="POLICY_GATE_FAIL_CLOSED")
    res = await failure_fallback.simulate_failure(req, db_session)

    assert res.category == FailureCategory.POLICY_GATE_FAILURE
    assert res.retry_policy == RetryPolicy.REVIEW_REQUIRED
    assert "escalated for human review" in res.user_message

@pytest.mark.asyncio
async def test_authoritative_recovered_case_protection_during_simulation(db_session):
    auth_cid = "d669dce3-b855-4348-b457-f0ef7c34b6b1"
    req = SimulateFailureRequest(scenario_key="PAYMENT_VERIFICATION_FAILURE", target_case_id=auth_cid)
    res = await failure_fallback.simulate_failure(req, db_session)

    # Must redirect away from authoritative recovered case to prevent state corruption
    assert res.case_state_preserved == "OPEN"

    case_res = await db_session.get(RecoveryCase, auth_cid)
    if case_res:
        assert case_res.status == "RECOVERED"
        assert float(case_res.recovered_amount or 0.0) == 10.0

@pytest.mark.asyncio
async def test_endpoint_get_failure_scenarios(async_client):
    res = await async_client.get("/api/v1/health/failure-scenarios")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 7

@pytest.mark.asyncio
async def test_endpoint_simulate_failure(async_client):
    res = await async_client.post(
        "/api/v1/health/simulate-failure",
        json={"scenario_key": "RAZORPAY_ORDER_FAILURE"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["scenario_key"] == "RAZORPAY_ORDER_FAILURE"
    assert data["retry_policy"] == "RETRYABLE"

@pytest.mark.asyncio
async def test_step_1_ai_decision_regression():
    from app.services.recovery.ai_decision_service import ai_decision_service
    case = RecoveryCase(id="c_reg_s1_ff", amount=10.0, status="OPEN")
    eval_res = ai_decision_service.assess_case(case)
    assert eval_res.case_id == "c_reg_s1_ff"

@pytest.mark.asyncio
async def test_step_2_policy_gate_regression():
    from app.services.recovery.policy_gate import policy_gate
    case = RecoveryCase(id="c_reg_s2_ff", amount=10.0, risk_score=20.0, status="OPEN")
    pol = policy_gate.assess_case(case)
    assert pol.decision in ["ALLOW_RECOVERY", "REVIEW_REQUIRED", "BLOCK_RECOVERY"]

@pytest.mark.asyncio
async def test_step_3_stopping_rules_regression():
    from app.services.recovery.stopping_rules import stopping_rules
    case = RecoveryCase(id="c_reg_s3_ff", amount=10.0, retry_count=0, status="OPEN")
    stp = stopping_rules.evaluate_case(case)
    assert stp.decision in ["CONTINUE", "STOP"]

@pytest.mark.asyncio
async def test_step_4_human_escalation_regression():
    from app.services.recovery.human_escalation import human_escalation
    case = RecoveryCase(id="c_reg_s4_ff", amount=10.0, status="ESCALATED")
    esc = human_escalation.evaluate_case(case)
    assert esc.should_escalate is True

@pytest.mark.asyncio
async def test_step_5_funnel_regression(db_session):
    from app.services.analytics.recovery_funnel import recovery_funnel
    f_res = await recovery_funnel.get_funnel_metrics(db_session)
    assert len(f_res.stages) == 8

@pytest.mark.asyncio
async def test_step_6_ai_metrics_regression(db_session):
    from app.services.analytics.ai_metrics import ai_metrics
    m_res = await ai_metrics.get_ai_metrics(db_session)
    assert len(m_res.confidence_analysis) == 5
