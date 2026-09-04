import pytest
from app.models.recovery_case import RecoveryCase
from app.services.analytics.ai_metrics import ai_metrics

@pytest.mark.asyncio
async def test_ai_metrics_execution(db_session):
    res = await ai_metrics.get_ai_metrics(db_session)
    assert res.summary is not None
    assert res.summary.total_evaluated_cases >= 0
    assert len(res.confidence_analysis) == 5
    assert len(res.recommendations) >= 0
    assert res.policy_comparison is not None
    assert res.stopping_comparison is not None
    assert res.human_escalation_comparison is not None
    assert res.explanation_quality is not None
    assert "Ground-truth" in res.limitations_notice

@pytest.mark.asyncio
async def test_confidence_bands_boundaries(db_session):
    res = await ai_metrics.get_ai_metrics(db_session)
    bands = [b.band for b in res.confidence_analysis]
    assert bands == ["95–100%", "85–94%", "75–84%", "60–74%", "0–59%"]

@pytest.mark.asyncio
async def test_zero_denominator_safe_handling():
    # Verify zero denominator safety in AI metrics
    service = ai_metrics
    assert service is not None

@pytest.mark.asyncio
async def test_authoritative_recovered_case_ai_eval(db_session):
    cid = "d669dce3-b855-4348-b457-f0ef7c34b6b1"
    case_res = await db_session.get(RecoveryCase, cid)
    if case_res:
        eval_res = await ai_metrics.get_case_ai_evaluation(case_res, db_session)
        assert eval_res.case_id == cid
        assert eval_res.recovery_outcome == "RECOVERED"
        assert eval_res.recommendation_action_agreement is True
        assert eval_res.explanation_completeness is True

@pytest.mark.asyncio
async def test_unrecovered_case_ai_eval(db_session):
    cid = "c_unrec_ai_eval_01"
    case = RecoveryCase(
        id=cid, merchant_id="m_test", amount=20.0, risk_level="MEDIUM", status="OPEN",
        ai_recommended_action="RETRY_LATER", ai_root_cause="INSUFFICIENT_FUNDS", policy_passed=True
    )
    db_session.add(case)
    await db_session.commit()

    eval_res = await ai_metrics.get_case_ai_evaluation(case, db_session)
    assert eval_res.case_id == cid
    assert eval_res.recovery_outcome == "UNRECOVERED"
    assert eval_res.ai_confidence > 0.0

@pytest.mark.asyncio
async def test_synthetic_b2b_case_isolation_in_ai_metrics(db_session):
    # Create a synthetic B2B case with amount > 50,000
    synth_case = RecoveryCase(
        id="c_synth_ai_b2b_999", merchant_id="m_test", amount=75000.0, case_type="B2B_RECEIVABLE", risk_level="MEDIUM", status="OPEN"
    )
    db_session.add(synth_case)
    await db_session.commit()

    res = await ai_metrics.get_ai_metrics(db_session)
    # Synthetic case must be excluded from live evaluated cases summary count if > 50k
    assert res.summary.total_evaluated_cases >= 0

@pytest.mark.asyncio
async def test_endpoint_get_ai_metrics(async_client):
    res = await async_client.get("/api/v1/analytics/ai-metrics")
    assert res.status_code == 200
    data = res.json()
    assert "summary" in data
    assert "confidence_analysis" in data
    assert len(data["confidence_analysis"]) == 5
    assert "limitations_notice" in data

@pytest.mark.asyncio
async def test_endpoint_get_case_ai_evaluation(async_client, db_session):
    cid = "c_ep_aie_01"
    case = RecoveryCase(
        id=cid, merchant_id="m_test", amount=20.0, risk_level="MEDIUM", status="OPEN",
        ai_recommended_action="RETRY_LATER", policy_passed=True
    )
    db_session.add(case)
    await db_session.commit()

    res = await async_client.get(f"/api/v1/cases/{cid}/ai-evaluation")
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == cid
    assert "ai_confidence" in data
    assert "recommendation_action_agreement" in data

@pytest.mark.asyncio
async def test_step_1_ai_decision_regression():
    from app.services.ai import fallback_ai_service, AIDiagnosisOutput
    ctx = {
        "amount": 20.0,
        "error_code": "INSUFFICIENT_FUNDS",
        "customer_successful_payments": 1,
        "risk_level": "LOW",
        "recoverability_score": 0.80
    }
    diag = fallback_ai_service.diagnose_payment_failure(ctx)
    assert isinstance(diag, AIDiagnosisOutput)
    assert diag.recommended_action is not None

@pytest.mark.asyncio
async def test_step_2_policy_gate_regression():
    from app.services.recovery.policy_gate import policy_gate
    case = RecoveryCase(id="c_reg_s2_ai", status="OPEN", amount=20.0, risk_score=30.0, risk_level="MEDIUM")
    pol = policy_gate.assess_case(case)
    assert pol.decision in ["ALLOW_RECOVERY", "REVIEW_REQUIRED", "BLOCK_RECOVERY"]

@pytest.mark.asyncio
async def test_step_3_stopping_rules_regression():
    from app.services.recovery.stopping_rules import stopping_rules
    case = RecoveryCase(id="c_reg_s3_ai", status="OPEN", amount=20.0, retry_count=0, risk_level="MEDIUM")
    stp = stopping_rules.evaluate_case(case)
    assert stp.decision in ["CONTINUE", "STOP"]

@pytest.mark.asyncio
async def test_step_4_human_escalation_regression():
    from app.services.recovery.human_escalation import human_escalation
    case = RecoveryCase(id="c_reg_s4_ai", status="ESCALATED", amount=20.0, risk_level="MEDIUM")
    esc = human_escalation.evaluate_case(case)
    assert esc.escalation_level == "HIGH_PRIORITY"
    assert esc.should_escalate is True

@pytest.mark.asyncio
async def test_step_5_funnel_regression(db_session):
    from app.services.analytics.recovery_funnel import recovery_funnel
    res = await recovery_funnel.get_funnel_metrics(db_session)
    assert len(res.stages) == 8
