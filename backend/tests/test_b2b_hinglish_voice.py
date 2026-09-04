import pytest
from datetime import datetime, timezone, timedelta
from app.models.receivables_and_mandates import Invoice, PromiseToPay
from app.models.customer import Customer
from app.models.merchant import Merchant
from app.models.recovery_case import RecoveryCase
from app.services.recovery.voice_recovery_service import (
    voice_recovery_service,
    parse_hinglish_intent
)

@pytest.mark.asyncio
async def test_parse_hinglish_intents():
    assert parse_hinglish_intent("Friday ko payment kar dunga")[0] == "PROMISE_TO_PAY"
    assert parse_hinglish_intent("Payment link WhatsApp par bhejo")[0] == "PAYMENT_LINK_REQUEST"
    assert parse_hinglish_intent("Invoice amount kitna banta hai?")[0] == "INVOICE_DETAILS"
    assert parse_hinglish_intent("Due date kya thi?")[0] == "DUE_DATE_INQUIRY"
    assert parse_hinglish_intent("Mujhe human manager se baat karni hai")[0] == "HUMAN_ESCALATION"
    assert parse_hinglish_intent("Payment already kar diya kal")[0] == "ALREADY_PAID"
    assert parse_hinglish_intent("Payment link dobara bhejo")[0] == "RESEND_LINK"

@pytest.mark.asyncio
async def test_handle_voice_interaction_promise_to_pay(db_session):
    m = Merchant(name="Tech Corp", email="m_v1@test.com")
    db_session.add(m)
    await db_session.commit()

    inv = Invoice(
        merchant_id=m.id,
        invoice_number="INV_V_001",
        amount=48000.0,
        due_date=datetime.now(timezone.utc) - timedelta(days=10),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    res = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Friday ko payment kar dunga"
    )
    assert res.detected_intent == "PROMISE_TO_PAY"
    assert res.is_promise_registered is True
    assert "promise-to-pay" in res.response_text_hinglish.lower()
    assert inv.status == "PROMISE_TO_PAY"

@pytest.mark.asyncio
async def test_handle_voice_interaction_payment_link(db_session):
    m = Merchant(name="Scale Inc", email="m_v2@test.com")
    db_session.add(m)
    await db_session.commit()

    inv = Invoice(
        merchant_id=m.id,
        invoice_number="INV_V_002",
        amount=2500.0,
        due_date=datetime.now(timezone.utc) - timedelta(days=5),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    res = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Payment link WhatsApp par bhejo"
    )
    assert res.detected_intent == "PAYMENT_LINK_REQUEST"
    assert res.is_payment_link_sent is True
    assert res.payment_url is not None

@pytest.mark.asyncio
async def test_voice_human_escalation_intent(db_session):
    m = Merchant(name="Global Ltd", email="m_v3@test.com")
    db_session.add(m)
    await db_session.commit()

    inv = Invoice(
        merchant_id=m.id,
        invoice_number="INV_V_003",
        amount=95000.0,
        due_date=datetime.now(timezone.utc) - timedelta(days=20),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    res = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Mujhe human agent se baat karni hai"
    )
    assert res.detected_intent == "HUMAN_ESCALATION"
    assert res.action_taken == "ESCALATE_TO_HUMAN"
    assert res.safety_status == "ESCALATED"
    assert inv.status == "ESCALATED"

@pytest.mark.asyncio
async def test_get_b2b_analytics(db_session):
    an = await voice_recovery_service.get_b2b_analytics(db=db_session)
    assert an.total_receivables >= 0
    assert an.total_outstanding_amount >= 0.0
    assert an.recovery_rate >= 0.0

@pytest.mark.asyncio
async def test_voice_endpoints(async_client, db_session):
    m = Merchant(name="API Merchant", email="m_v_api@test.com")
    db_session.add(m)
    await db_session.commit()

    inv = Invoice(
        merchant_id=m.id,
        invoice_number="INV_API_001",
        amount=2500.0,
        due_date=datetime.now(timezone.utc) - timedelta(days=2),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    res_sim = await async_client.post("/api/v1/voice/simulate-intent", json={
        "invoice_id": inv.id,
        "customer_speech": "Kal payment kar dunga"
    })
    assert res_sim.status_code == 200
    assert res_sim.json()["detected_intent"] == "PROMISE_TO_PAY"

    res_an = await async_client.get("/api/v1/analytics/b2b-receivables")
    assert res_an.status_code == 200
    assert "total_receivables" in res_an.json()

@pytest.mark.asyncio
async def test_step_1_regression():
    from app.services.recovery.ai_decision_service import ai_decision_service
    case = RecoveryCase(id="c_v_s1", merchant_id="m_test", amount=10.0, risk_level="LOW", status="OPEN")
    eval_res = ai_decision_service.assess_case(case)
    assert eval_res.case_id == "c_v_s1"

@pytest.mark.asyncio
async def test_step_2_policy_gate_regression():
    from app.services.recovery.policy_gate import policy_gate
    case = RecoveryCase(id="c_v_s2", merchant_id="m_test", amount=10.0, risk_score=10.0, risk_level="LOW", status="OPEN")
    pol = policy_gate.assess_case(case)
    assert pol.decision in ["ALLOW_RECOVERY", "REVIEW_REQUIRED", "BLOCK_RECOVERY"]

@pytest.mark.asyncio
async def test_step_3_stopping_rules_regression():
    from app.services.recovery.stopping_rules import stopping_rules
    case = RecoveryCase(id="c_v_s3", merchant_id="m_test", amount=10.0, retry_count=0, risk_level="LOW", status="OPEN")
    stp = stopping_rules.evaluate_case(case)
    assert stp.decision in ["CONTINUE", "STOP"]

@pytest.mark.asyncio
async def test_step_4_human_escalation_regression():
    from app.services.recovery.human_escalation import human_escalation
    case = RecoveryCase(id="c_v_s4", merchant_id="m_test", amount=10.0, risk_level="LOW", status="ESCALATED")
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
        db_session, type="VOICE_RECOVERY_STARTED", severity="INFO", title="Voice Call Started", message="Call active", case_id="c_v_s8"
    )
    assert n.type == "VOICE_RECOVERY_STARTED"

@pytest.mark.asyncio
async def test_step_9_checkout_abandonment_regression(db_session):
    from app.services.recovery.checkout_abandonment import checkout_abandonment_service
    case = RecoveryCase(id="c_v_s9", merchant_id="m_test", amount=10.0, risk_level="LOW", status="OPEN", case_type="CHECKOUT_DROPOFF")
    db_session.add(case)
    await db_session.commit()
    chk = await checkout_abandonment_service.get_checkout_status(db_session, case.id)
    assert chk.state == "CHECKOUT_ABANDONED"

@pytest.mark.asyncio
async def test_step_10_subscription_recovery_regression(db_session):
    from app.services.revenue_risk.subscription_recovery import subscription_recovery_service
    sub = await subscription_recovery_service.create_subscription(
        db=db_session, merchant_id="m_v_sub", plan_name="SaaS Plan", amount=1999.0
    )
    assert sub.id is not None
    assert sub.recovery_status == "ACTIVE"

@pytest.mark.asyncio
async def test_voice_session_audit_endpoint(async_client, db_session):
    m = Merchant(name="Session Merchant", email="m_sess@test.com")
    db_session.add(m)
    await db_session.commit()

    inv = Invoice(
        merchant_id=m.id,
        invoice_number="INV_SESS_001",
        amount=1500.0,
        due_date=datetime.now(timezone.utc) - timedelta(days=1),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    sim = await async_client.post("/api/v1/voice/simulate-intent", json={
        "invoice_id": inv.id,
        "customer_speech": "Payment link WhatsApp par bhejo",
        "session_id": "v_sess_aud_101"
    })
    assert sim.status_code == 200

    aud = await async_client.get("/api/v1/voice/sessions/v_sess_aud_101")
    assert aud.status_code == 200
    data = aud.json()
    assert data["session_id"] == "v_sess_aud_101"
    assert data["total_turns"] >= 1

@pytest.mark.asyncio
async def test_promise_to_pay_endpoint(async_client, db_session):
    m = Merchant(name="Promise Merchant", email="m_p2p@test.com")
    db_session.add(m)
    await db_session.commit()

    inv = Invoice(
        merchant_id=m.id,
        invoice_number="INV_P2P_001",
        amount=5000.0,
        due_date=datetime.now(timezone.utc) - timedelta(days=3),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    p_res = await async_client.post("/api/v1/voice/promise-to-pay", json={
        "invoice_id": inv.id,
        "promise_date": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        "session_id": "v_sess_p2p_202"
    })
    assert p_res.status_code == 200
    assert p_res.json()["status"] == "PROMISED"

@pytest.mark.asyncio
async def test_voice_response_hinglish_generation(db_session):
    m = Merchant(name="Gen Merchant", email="m_gen@test.com")
    db_session.add(m)
    await db_session.commit()

    inv = Invoice(
        merchant_id=m.id,
        invoice_number="INV_GEN_001",
        amount=3500.0,
        due_date=datetime.now(timezone.utc) - timedelta(days=4),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    res = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Invoice amount kitna banta hai?"
    )
    assert res.detected_intent == "INVOICE_DETAILS"
    assert "₹3,500.00" in res.response_text_hinglish

@pytest.mark.asyncio
async def test_voice_duplicate_request_protection(db_session):
    m = Merchant(name="Dup Merchant", email="m_dup@test.com")
    db_session.add(m)
    await db_session.commit()

    inv = Invoice(
        merchant_id=m.id,
        invoice_number="INV_DUP_001",
        amount=1800.0,
        due_date=datetime.now(timezone.utc) - timedelta(days=2),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    res1 = await voice_recovery_service.handle_voice_interaction(db=db_session, invoice_id=inv.id, customer_speech="Friday ko payment kar dunga", session_id="sess_dup")
    res2 = await voice_recovery_service.handle_voice_interaction(db=db_session, invoice_id=inv.id, customer_speech="Friday ko payment kar dunga", session_id="sess_dup")
    assert res1.is_promise_registered is True
    assert res2.is_promise_registered is True

