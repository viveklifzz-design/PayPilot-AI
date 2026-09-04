import pytest
from app.models.recovery_case import RecoveryCase
from app.models.transaction import Transaction
from app.services.recovery.stopping_rules import stopping_rules

def test_stopping_rule_1_eligible_case_continues():
    case = RecoveryCase(id="c_cont", status="OPEN", amount=20.0, retry_count=0, risk_score=30.0, ai_confidence=0.95)
    res = stopping_rules.evaluate_case(case)
    assert res.decision == "CONTINUE"
    assert res.should_stop is False
    assert res.remaining_attempts == 3
    assert len(res.triggered_rules) == 0

def test_stopping_rule_2_max_retries_stops():
    case = RecoveryCase(id="c_max_retry", status="OPEN", amount=20.0, retry_count=3)
    res = stopping_rules.evaluate_case(case)
    assert res.decision == "STOP"
    assert res.should_stop is True
    assert "RETRY_LIMIT_REACHED" in res.triggered_rules

def test_stopping_rule_3_already_recovered_stops():
    case = RecoveryCase(id="d669dce3-b855-4348-b457-f0ef7c34b6b1", status="RECOVERED", amount=10.0, retry_count=1)
    res = stopping_rules.evaluate_case(case)
    assert res.decision == "STOP"
    assert res.should_stop is True
    assert "ALREADY_RECOVERED" in res.triggered_rules

def test_stopping_rule_4_policy_block_stops():
    case = RecoveryCase(id="c_pol_block", status="OPEN", amount=60000.0)
    res = stopping_rules.evaluate_case(case)
    assert res.decision == "STOP"
    assert res.should_stop is True
    assert "POLICY_BLOCK" in res.triggered_rules

def test_stopping_rule_5_policy_review_stops_automation():
    case = RecoveryCase(id="c_pol_review", status="OPEN", amount=15000.0, risk_score=30.0, ai_confidence=0.95)
    res = stopping_rules.evaluate_case(case)
    assert res.decision == "STOP"
    assert res.should_stop is True
    assert "POLICY_REVIEW_REQUIRED" in res.triggered_rules

def test_stopping_rule_6_terminal_state_stopped_stops():
    case = RecoveryCase(id="c_terminal", status="STOPPED", amount=20.0, retry_count=1)
    res = stopping_rules.evaluate_case(case)
    assert res.decision == "STOP"
    assert res.should_stop is True
    assert "UNSAFE_TERMINAL_STATE" in res.triggered_rules

def test_stopping_rule_7_unsafe_amount_stops():
    case = RecoveryCase(id="c_unsafe_amt", status="OPEN", amount=100000.0)
    res = stopping_rules.evaluate_case(case)
    assert res.decision == "STOP"
    assert res.should_stop is True
    assert "AMOUNT_SAFETY_LIMIT" in res.triggered_rules

def test_stopping_rule_8_multiple_rules_triggered():
    case = RecoveryCase(id="c_multi", status="RECOVERED", amount=60000.0, retry_count=3)
    res = stopping_rules.evaluate_case(case)
    assert res.decision == "STOP"
    assert res.should_stop is True
    assert "ALREADY_RECOVERED" in res.triggered_rules
    assert "POLICY_BLOCK" in res.triggered_rules
    assert "RETRY_LIMIT_REACHED" in res.triggered_rules

def test_stopping_rule_9_valid_case_remaining_attempts():
    case = RecoveryCase(id="c_rem", status="OPEN", amount=20.0, retry_count=1, risk_score=30.0, ai_confidence=0.95)
    res = stopping_rules.evaluate_case(case)
    assert res.decision == "CONTINUE"
    assert res.remaining_attempts == 2

def test_stopping_rule_10_non_mutating():
    case = RecoveryCase(id="c_no_mutate", status="OPEN", amount=20.0, retry_count=0, recovered_amount=0.0)
    stopping_rules.evaluate_case(case)
    assert case.status == "OPEN"
    assert case.recovered_amount == 0.0

@pytest.mark.asyncio
async def test_stopping_rule_11_endpoint_full_uuid(async_client, db_session):
    cid = "e910a5b2-3c8d-4f1e-9a2b-7c4d1e8f3a5b"
    c = RecoveryCase(id=cid, merchant_id="m_test", amount=20.0, risk_level="MEDIUM", status="OPEN")
    db_session.add(c)
    await db_session.commit()

    res = await async_client.get(f"/api/v1/cases/{cid}/stopping-rules")
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["case_id"] == cid
    assert "decision" in json_data

@pytest.mark.asyncio
async def test_stopping_rule_12_endpoint_short_prefix(async_client, db_session):
    cid = "d669dce3-b855-4348-b457-f0ef7c34b6b1"
    c = RecoveryCase(id=cid, merchant_id="m_test", amount=10.0, risk_level="MEDIUM", status="RECOVERED")
    db_session.add(c)
    await db_session.commit()

    res = await async_client.get("/api/v1/cases/d669dce3/stopping-rules")
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["decision"] == "STOP"
    assert json_data["should_stop"] is True

@pytest.mark.asyncio
async def test_stopping_rule_13_endpoint_unknown_id_404(async_client):
    res = await async_client.get("/api/v1/cases/99999999-9999-9999-9999-999999999999/stopping-rules")
    assert res.status_code == 404

@pytest.mark.asyncio
async def test_stopping_rule_14_order_creation_blocked_for_stopped_case(async_client, db_session):
    cid = "d669dce3-b855-4348-b457-f0ef7c34b6b1"
    c = RecoveryCase(id=cid, merchant_id="m_test", amount=10.0, risk_level="MEDIUM", status="RECOVERED")
    db_session.add(c)
    await db_session.commit()

    res = await async_client.post("/api/v1/checkout/create-order", json={"case_id": cid, "amount": 10.0})
    assert res.status_code == 400
    assert "blocked" in res.json()["detail"].lower() or "stopped" in res.json()["detail"].lower()
