import pytest
from app.models.recovery_case import RecoveryCase
from app.models.transaction import Transaction
from app.services.recovery.human_escalation import human_escalation, HumanActionRequest

def test_escalation_eligible_normal_case_none():
    case = RecoveryCase(id="c_norm", status="OPEN", amount=20.0, retry_count=0, risk_score=30.0, ai_confidence=0.95)
    res = human_escalation.evaluate_case(case)
    assert res.escalation_level == "NONE"
    assert res.should_escalate is False
    assert len(res.triggered_rules) == 0

def test_escalation_already_recovered_critical():
    case = RecoveryCase(id="d669dce3-b855-4348-b457-f0ef7c34b6b1", status="RECOVERED", amount=10.0)
    res = human_escalation.evaluate_case(case)
    assert res.escalation_level == "CRITICAL"
    assert res.should_escalate is True
    assert any(r.rule_id == "RULE_CASE_RECOVERED" for r in res.triggered_rules)

def test_escalation_policy_blocked_critical():
    case = RecoveryCase(id="c_pol_blk", status="OPEN", amount=60000.0)
    res = human_escalation.evaluate_case(case)
    assert res.escalation_level == "CRITICAL"
    assert res.should_escalate is True

def test_escalation_high_risk_score_high_priority():
    case = RecoveryCase(id="c_risk", status="OPEN", amount=20.0, risk_score=75.0, ai_confidence=0.95)
    res = human_escalation.evaluate_case(case)
    assert res.escalation_level == "HIGH_PRIORITY"
    assert res.should_escalate is True

def test_escalation_low_ai_confidence_review():
    case = RecoveryCase(id="c_low_conf", status="OPEN", amount=20.0, risk_score=30.0, ai_confidence=0.60)
    res = human_escalation.evaluate_case(case)
    assert res.escalation_level in ["REVIEW", "HIGH_PRIORITY"]
    assert res.should_escalate is True

def test_escalation_explicitly_escalated_high_priority():
    case = RecoveryCase(id="c_esc", status="ESCALATED", amount=20.0)
    res = human_escalation.evaluate_case(case)
    assert res.escalation_level == "HIGH_PRIORITY"
    assert res.should_escalate is True

@pytest.mark.asyncio
async def test_human_action_approve_recovery(db_session):
    case = RecoveryCase(id="c_act_appr", merchant_id="m_test", amount=20.0, risk_level="MEDIUM", status="ESCALATED")
    db_session.add(case)
    await db_session.commit()

    req = HumanActionRequest(action="APPROVE_RECOVERY", reason="Approved after manual verification")
    res = await human_escalation.execute_human_action(case, req, db_session)
    assert res.success is True
    assert res.new_status == "ACTION_PENDING"
    assert case.status == "ACTION_PENDING"

@pytest.mark.asyncio
async def test_human_action_reject_recovery(db_session):
    case = RecoveryCase(id="c_act_rej", merchant_id="m_test", amount=20.0, risk_level="MEDIUM", status="ESCALATED")
    db_session.add(case)
    await db_session.commit()

    req = HumanActionRequest(action="REJECT_RECOVERY", reason="Suspected fraud risk")
    res = await human_escalation.execute_human_action(case, req, db_session)
    assert res.success is True
    assert res.new_status == "STOPPED"
    assert case.status == "STOPPED"

@pytest.mark.asyncio
async def test_human_action_request_info(db_session):
    case = RecoveryCase(id="c_act_info", merchant_id="m_test", amount=20.0, risk_level="MEDIUM", status="OPEN")
    db_session.add(case)
    await db_session.commit()

    req = HumanActionRequest(action="REQUEST_INFO", reason="Awaiting customer clarification")
    res = await human_escalation.execute_human_action(case, req, db_session)
    assert res.success is True
    assert res.new_status == "ESCALATED"
    assert case.status == "ESCALATED"

@pytest.mark.asyncio
async def test_human_action_already_recovered_rejects_approval(db_session):
    case = RecoveryCase(id="c_rec_appr", merchant_id="m_test", amount=10.0, risk_level="MEDIUM", status="RECOVERED")
    db_session.add(case)
    await db_session.commit()

    req = HumanActionRequest(action="APPROVE_RECOVERY", reason="Operator approval attempt")
    with pytest.raises(ValueError) as exc:
        await human_escalation.execute_human_action(case, req, db_session)
    assert "already marked RECOVERED" in str(exc.value)

@pytest.mark.asyncio
async def test_endpoint_get_escalated_cases(async_client, db_session):
    cid = "c_esc_ep_01"
    c = RecoveryCase(id=cid, merchant_id="m_test", amount=20.0, risk_level="MEDIUM", status="ESCALATED")
    db_session.add(c)
    await db_session.commit()

    res = await async_client.get("/api/v1/cases/escalated")
    assert res.status_code == 200
    items = res.json()
    assert any(item["id"] == cid for item in items)

@pytest.mark.asyncio
async def test_endpoint_get_case_escalation(async_client, db_session):
    cid = "c_esc_ep_02"
    c = RecoveryCase(id=cid, merchant_id="m_test", amount=20.0, risk_level="MEDIUM", status="OPEN")
    db_session.add(c)
    await db_session.commit()

    res = await async_client.get(f"/api/v1/cases/{cid}/escalation")
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == cid
    assert "escalation_level" in data

@pytest.mark.asyncio
async def test_endpoint_post_escalate_case(async_client, db_session):
    cid = "c_esc_ep_03"
    c = RecoveryCase(id=cid, merchant_id="m_test", amount=20.0, risk_level="MEDIUM", status="OPEN")
    db_session.add(c)
    await db_session.commit()

    res = await async_client.post(f"/api/v1/cases/{cid}/escalate?reason=Manual%20flag")
    assert res.status_code == 200
    assert res.json()["escalation_level"] == "HIGH_PRIORITY"

@pytest.mark.asyncio
async def test_endpoint_post_human_action_reject(async_client, db_session):
    cid = "c_esc_ep_04"
    c = RecoveryCase(id=cid, merchant_id="m_test", amount=20.0, risk_level="MEDIUM", status="ESCALATED")
    db_session.add(c)
    await db_session.commit()

    res = await async_client.post(f"/api/v1/cases/{cid}/human-action", json={
        "action": "REJECT_RECOVERY",
        "reason": "Rejected by operator test",
        "operator_id": "TEST_OPERATOR"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["new_status"] == "STOPPED"

@pytest.mark.asyncio
async def test_order_creation_blocked_for_escalated_case(async_client, db_session):
    cid = "c_esc_ep_05"
    c = RecoveryCase(id=cid, merchant_id="m_test", amount=20.0, risk_level="HIGH", status="ESCALATED")
    db_session.add(c)
    await db_session.commit()

    res = await async_client.post("/api/v1/checkout/create-order", json={"case_id": cid, "amount": 20.0})
    assert res.status_code == 400
    assert "human review" in res.json()["detail"].lower()
