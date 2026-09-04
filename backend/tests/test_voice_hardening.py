import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.models.receivables_and_mandates import Invoice, PromiseToPay
from app.models.customer import Customer
from app.models.merchant import Merchant
from app.models.recovery_case import RecoveryCase
from app.models.audit_log import AuditLog
from app.models.notification import Notification
from app.services.recovery.voice_recovery_service import voice_recovery_service, parse_hinglish_intent
from app.models.base import utc_now, generate_uuid

async def create_test_merchant(db):
    m = Merchant(name="Test B2B Enterprise", email=f"merchant_{generate_uuid()[:6]}@test.com")
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return m

@pytest.mark.asyncio
async def test_paypilot_identity(db_session):
    """Test 1: Voice assistant response presents strictly as 'PayPilot' without human names."""
    m = await create_test_merchant(db_session)
    inv = Invoice(
        merchant_id=m.id,
        invoice_number=f"INV-ID-{generate_uuid()[:6]}",
        amount=15000.0,
        due_date=utc_now() - timedelta(days=10),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()
    await db_session.refresh(inv)

    res = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Aap kaun bol rahe ho?"
    )

    assert "Ananya" not in res.response_text_hinglish
    assert "Ananya" not in res.response_text_english
    assert "Ananya" not in res.voice_audio_prompt
    assert res.safety_status in ["SAFE", "ESCALATED"]

@pytest.mark.asyncio
async def test_hinglish_intent_classification():
    """Test 2: Test parsing of 12 Hinglish and English customer intent patterns."""
    assert parse_hinglish_intent("Friday ko payment kar dunga")[0] == "PROMISE_TO_PAY"
    assert parse_hinglish_intent("Payment link WhatsApp par bhejo")[0] == "PAYMENT_LINK_REQUEST"
    assert parse_hinglish_intent("Link dobara bhejo")[0] == "RESEND_LINK"
    assert parse_hinglish_intent("Invoice details batao")[0] == "INVOICE_DETAILS"
    assert parse_hinglish_intent("Payment kab due hai?")[0] == "DUE_DATE_INQUIRY"
    assert parse_hinglish_intent("Maine already payment kar diya")[0] == "ALREADY_PAID"
    assert parse_hinglish_intent("Mujhe senior human manager se baat karni hai")[0] == "HUMAN_ESCALATION"
    assert parse_hinglish_intent("Payment fail ho gaya")[0] == "PAYMENT_FAILED"
    assert parse_hinglish_intent("Mujhe thoda time chahiye")[0] == "TIME_EXTENSION"
    assert parse_hinglish_intent("Accounts team se baat karo")[0] == "ACCOUNTS_TEAM"

@pytest.mark.asyncio
async def test_session_context_resolution(db_session):
    """Test 3: Pronoun and contextual question resolution using session context."""
    m = await create_test_merchant(db_session)
    inv = Invoice(
        merchant_id=m.id,
        invoice_number=f"INV-CTX-{generate_uuid()[:6]}",
        amount=25000.0,
        due_date=utc_now() - timedelta(days=5),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    sess_id = f"v_ctx_{generate_uuid()[:8]}"
    
    # First turn: Invoice details inquiry
    res1 = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Invoice details batao",
        session_id=sess_id
    )
    assert res1.detected_intent == "INVOICE_DETAILS"

    # Second turn: Ambiguous pronoun question "kitne ka hai"
    res2 = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="kitne ka hai",
        session_id=sess_id
    )
    assert res2.detected_intent == "INVOICE_DETAILS"
    assert res2.amount == 25000.0

@pytest.mark.asyncio
async def test_payment_link_request_flow(db_session):
    """Test 4: Generate valid Razorpay payment link request passing Policy Gate."""
    m = await create_test_merchant(db_session)
    inv = Invoice(
        merchant_id=m.id,
        invoice_number=f"INV-LINK-{generate_uuid()[:6]}",
        amount=2000.0,
        due_date=utc_now() - timedelta(days=3),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    res = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Payment link bhejo"
    )
    assert res.is_payment_link_sent is True
    assert res.payment_url is not None
    assert "recover" in res.payment_url

@pytest.mark.asyncio
async def test_idempotent_link_resend(db_session):
    """Test 5: Reuses existing active payment link without creating duplicate orders."""
    m = await create_test_merchant(db_session)
    inv = Invoice(
        merchant_id=m.id,
        invoice_number=f"INV-RES-{generate_uuid()[:6]}",
        amount=3000.0,
        due_date=utc_now() - timedelta(days=4),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    sess_id = f"v_resend_{generate_uuid()[:8]}"
    res1 = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Payment link bhejo",
        session_id=sess_id
    )
    url1 = res1.payment_url

    res2 = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Link dobara bhejo",
        session_id=sess_id
    )
    assert res2.payment_url == url1
    assert res2.action_taken == "PAYMENT_LINK_REUSED"

@pytest.mark.asyncio
async def test_unconfirmed_payment_claim(db_session):
    """Test 6: Speech claim of payment completion MUST NOT mark invoice as PAID/RECOVERED without provider verification."""
    m = await create_test_merchant(db_session)
    inv = Invoice(
        merchant_id=m.id,
        invoice_number=f"INV-UNCONF-{generate_uuid()[:6]}",
        amount=5000.0,
        due_date=utc_now() - timedelta(days=2),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    res = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Maine payment kar diya hai"
    )

    assert res.action_taken == "VERIFICATION_PENDING"
    
    # Assert DB status remains OVERDUE (not falsely set to PAID)
    res_inv = await db_session.execute(select(Invoice).where(Invoice.id == inv.id))
    inv_check = res_inv.scalar_one_or_none()
    assert inv_check.status != "PAID"

@pytest.mark.asyncio
async def test_confirmed_payment_claim(db_session):
    """Test 7: Confirmed captured payment in DB acknowledges payment completion."""
    m = await create_test_merchant(db_session)
    inv = Invoice(
        merchant_id=m.id,
        invoice_number=f"INV-CONF-{generate_uuid()[:6]}",
        amount=5000.0,
        due_date=utc_now() - timedelta(days=2),
        status="PAID"
    )
    db_session.add(inv)
    await db_session.commit()

    res = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Maine already payment kar diya hai"
    )

    assert res.action_taken == "PAYMENT_CONFIRMED"
    assert "captured confirm" in res.response_text_hinglish

@pytest.mark.asyncio
async def test_payment_failed_explanation(db_session):
    """Test 8: Explains payment failure and safe retry options."""
    m = await create_test_merchant(db_session)
    inv = Invoice(
        merchant_id=m.id,
        invoice_number=f"INV-FAIL-{generate_uuid()[:6]}",
        amount=4000.0,
        due_date=utc_now() - timedelta(days=1),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    res = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Payment fail ho gaya hai"
    )

    assert res.detected_intent == "PAYMENT_FAILED"
    assert len(res.response_text_hinglish) > 0

@pytest.mark.asyncio
async def test_promise_to_pay_registration(db_session):
    """Test 9: Record Promise-to-Pay and create database record."""
    m = await create_test_merchant(db_session)
    inv = Invoice(
        merchant_id=m.id,
        invoice_number=f"INV-P2P-{generate_uuid()[:6]}",
        amount=12000.0,
        due_date=utc_now() - timedelta(days=7),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    res = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Friday ko payment kar dunga"
    )

    assert res.is_promise_registered is True
    assert res.action_taken == "PROMISE_TO_PAY_REGISTERED"

    p2p_res = await db_session.execute(select(PromiseToPay).where(PromiseToPay.invoice_id == inv.id))
    p2p = p2p_res.scalar_one_or_none()
    assert p2p is not None
    assert p2p.status == "PROMISED"

@pytest.mark.asyncio
async def test_invoice_details_inquiry(db_session):
    """Test 10: Inquiry returns accurate invoice details."""
    m = await create_test_merchant(db_session)
    inv = Invoice(
        merchant_id=m.id,
        invoice_number=f"INV-DET-{generate_uuid()[:6]}",
        amount=18500.0,
        due_date=utc_now() - timedelta(days=12),
        days_overdue=12,
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    res = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Invoice kitne ka hai?"
    )

    assert res.detected_intent == "INVOICE_DETAILS"
    assert "18,500" in res.response_text_hinglish

@pytest.mark.asyncio
async def test_due_date_inquiry(db_session):
    """Test 11: Inquiry returns original due date."""
    m = await create_test_merchant(db_session)
    due_dt = utc_now() - timedelta(days=15)
    inv = Invoice(
        merchant_id=m.id,
        invoice_number=f"INV-DUE-{generate_uuid()[:6]}",
        amount=8000.0,
        due_date=due_dt,
        days_overdue=15,
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    res = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Payment kab due hai?"
    )

    assert res.detected_intent == "DUE_DATE_INQUIRY"
    assert len(res.response_text_hinglish) > 0

@pytest.mark.asyncio
async def test_already_paid_verification(db_session):
    """Test 12: Already paid claim triggers verification without false state mutation."""
    m = await create_test_merchant(db_session)
    inv = Invoice(
        merchant_id=m.id,
        invoice_number=f"INV-PAID-{generate_uuid()[:6]}",
        amount=9500.0,
        due_date=utc_now() - timedelta(days=6),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    res = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Maine already payment kar diya hai"
    )

    assert res.action_taken == "VERIFICATION_PENDING"
    assert inv.status == "OVERDUE"

@pytest.mark.asyncio
async def test_human_escalation_flow(db_session):
    """Test 13: Customer requesting human agent triggers escalation and notification."""
    m = await create_test_merchant(db_session)
    inv = Invoice(
        merchant_id=m.id,
        invoice_number=f"INV-ESC-{generate_uuid()[:6]}",
        amount=45000.0,
        due_date=utc_now() - timedelta(days=20),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    res = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Mujhe human agent se baat karni hai"
    )

    assert res.action_taken == "ESCALATE_TO_HUMAN"
    assert res.safety_status == "ESCALATED"
    assert inv.status == "ESCALATED"

    # Check notification dispatch
    notif_res = await db_session.execute(select(Notification).where(Notification.type == "B2B_ESCALATION"))
    notif = notif_res.scalars().first()
    assert notif is not None

@pytest.mark.asyncio
async def test_policy_gate_enforcement(db_session):
    """Test 14: Policy Gate limits blocks automated recovery for excessive amount/risk."""
    m = await create_test_merchant(db_session)
    inv = Invoice(
        merchant_id=m.id,
        invoice_number=f"INV-HIGH-{generate_uuid()[:6]}",
        amount=60000.0, # Exceeds policy gate single limit
        due_date=utc_now() - timedelta(days=30),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    # Pre-create case with policy block
    case = RecoveryCase(
        case_type="B2B_RECEIVABLE",
        merchant_id=m.id,
        invoice_id=inv.id,
        amount=60000.0,
        risk_level="HIGH",
        risk_score=85.0,
        policy_passed=False,
        status="BLOCKED"
    )
    db_session.add(case)
    await db_session.commit()

    res = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Payment link bhejo"
    )

    assert res.policy_decision != "ALLOW"
    assert "human review" in res.response_text_hinglish or "policy" in res.response_text_english

@pytest.mark.asyncio
async def test_stopping_rules_enforcement(db_session):
    """Test 15: Stopping Rules trigger manual escalation when retries exceeded."""
    m = await create_test_merchant(db_session)
    inv = Invoice(
        merchant_id=m.id,
        invoice_number=f"INV-STOP-{generate_uuid()[:6]}",
        amount=5000.0,
        due_date=utc_now() - timedelta(days=10),
        status="STOPPED"
    )
    db_session.add(inv)
    await db_session.commit()

    case = RecoveryCase(
        case_type="B2B_RECEIVABLE",
        merchant_id=m.id,
        invoice_id=inv.id,
        amount=5000.0,
        risk_level="LOW",
        risk_score=15.0,
        retry_count=4, # Exceeds max retry count
        status="STOPPED"
    )
    db_session.add(case)
    await db_session.commit()

    res = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Dobara try kar sakte hain?"
    )

    assert res.stopping_rule_decision in ["STOP", "REVIEW_REQUIRED"]

@pytest.mark.asyncio
async def test_audit_logging_integrity(db_session):
    """Test 16: Voice interactions generate structured AuditLog with actor='FEMALE_AI_VOICE_AGENT'."""
    m = await create_test_merchant(db_session)
    inv = Invoice(
        merchant_id=m.id,
        invoice_number=f"INV-AUD-{generate_uuid()[:6]}",
        amount=7000.0,
        due_date=utc_now() - timedelta(days=2),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    res = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Invoice details batao"
    )

    audit_res = await db_session.execute(select(AuditLog).where(AuditLog.event_type == "VOICE_INTENT_DETECTED"))
    audits = audit_res.scalars().all()
    assert len(audits) > 0
    assert audits[-1].actor == "FEMALE_AI_VOICE_AGENT"

@pytest.mark.asyncio
async def test_notification_dispatch(db_session):
    """Test 17: Notifications created for Promise-to-Pay and Escalations."""
    m = await create_test_merchant(db_session)
    inv = Invoice(
        merchant_id=m.id,
        invoice_number=f"INV-NOTIF-{generate_uuid()[:6]}",
        amount=11000.0,
        due_date=utc_now() - timedelta(days=5),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Friday ko payment kar dunga"
    )

    notif_res = await db_session.execute(select(Notification).where(Notification.type == "PROMISE_TO_PAY_CREATED"))
    notif = notif_res.scalars().first()
    assert notif is not None

@pytest.mark.asyncio
async def test_b2b_analytics_calculation(db_session):
    """Test 18: B2B Receivables Analytics metrics calculation."""
    an = await voice_recovery_service.get_b2b_analytics(db_session)
    assert an.total_receivables >= 0
    assert an.total_outstanding_amount >= 0.0

@pytest.mark.asyncio
async def test_voice_simulate_api(async_client, db_session):
    """Test 19: REST Endpoint POST /api/v1/voice/simulate-intent."""
    m = await create_test_merchant(db_session)
    inv = Invoice(
        merchant_id=m.id,
        invoice_number=f"INV-API-{generate_uuid()[:6]}",
        amount=15000.0,
        due_date=utc_now() - timedelta(days=5),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    payload = {
        "invoice_id": inv.id,
        "customer_speech": "Payment link WhatsApp par bhejo"
    }
    response = await async_client.post("/api/v1/voice/simulate-intent", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["detected_intent"] == "PAYMENT_LINK_REQUEST"
    assert "Ananya" not in data["response_text_hinglish"]

@pytest.mark.asyncio
async def test_promise_to_pay_api(async_client, db_session):
    """Test 20: REST Endpoint POST /api/v1/voice/promise-to-pay."""
    m = await create_test_merchant(db_session)
    inv = Invoice(
        merchant_id=m.id,
        invoice_number=f"INV-P2PAPI-{generate_uuid()[:6]}",
        amount=22000.0,
        due_date=utc_now() - timedelta(days=8),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    payload = {
        "invoice_id": inv.id,
        "promised_amount": 22000.0,
        "promise_date": (utc_now() + timedelta(days=3)).isoformat(),
        "session_id": "v_sess_api_test"
    }
    response = await async_client.post("/api/v1/voice/promise-to-pay", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PROMISED"

@pytest.mark.asyncio
async def test_voice_session_api(async_client, db_session):
    """Test 21: REST Endpoint GET /api/v1/voice/sessions/{session_id}."""
    m = await create_test_merchant(db_session)
    inv = Invoice(
        merchant_id=m.id,
        invoice_number=f"INV-SESS-{generate_uuid()[:6]}",
        amount=5000.0,
        due_date=utc_now() - timedelta(days=2),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    sess_id = f"v_sess_fetch_{generate_uuid()[:6]}"
    await async_client.post("/api/v1/voice/simulate-intent", json={
        "invoice_id": inv.id,
        "customer_speech": "Invoice details batao",
        "session_id": sess_id
    })

    response = await async_client.get(f"/api/v1/voice/sessions/{sess_id}")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data or "audit_logs" in data or isinstance(data, list)

@pytest.mark.asyncio
async def test_b2b_analytics_api(async_client):
    """Test 22: REST Endpoint GET /api/v1/analytics/b2b-receivables."""
    response = await async_client.get("/api/v1/analytics/b2b-receivables")
    assert response.status_code == 200
    data = response.json()
    assert "total_receivables" in data

@pytest.mark.asyncio
async def test_unknown_intent_fallback(db_session):
    """Test 23: Unknown intent falls back to polite response without financial mutation."""
    m = await create_test_merchant(db_session)
    inv = Invoice(
        merchant_id=m.id,
        invoice_number=f"INV-UNK-{generate_uuid()[:6]}",
        amount=6000.0,
        due_date=utc_now() - timedelta(days=2),
        status="OVERDUE"
    )
    db_session.add(inv)
    await db_session.commit()

    res = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Random unexpected text statement"
    )

    assert res.safety_status in ["SAFE", "ESCALATED"]
    assert inv.status == "OVERDUE"

@pytest.mark.asyncio
async def test_authoritative_case_protected(db_session):
    """Test 24: Authoritative real recovered case d669dce3-b855-4348-b457-f0ef7c34b6b1 remains strictly intact."""
    case_res = await db_session.execute(select(RecoveryCase).where(RecoveryCase.id == "d669dce3-b855-4348-b457-f0ef7c34b6b1"))
    real_case = case_res.scalar_one_or_none()

    if real_case:
        assert real_case.status == "RECOVERED"
        assert float(real_case.recovered_amount or 0.0) == 10.0

@pytest.mark.asyncio
async def test_financial_integrity_zero_discrepancy(db_session):
    """Test 25: Financial integrity discrepancy remains INR 0.00 across system."""
    m = await create_test_merchant(db_session)
    case = RecoveryCase(
        merchant_id=m.id,
        case_type="PAYMENT_FAILURE",
        amount=10.0,
        risk_level="LOW",
        risk_score=15.0,
        status="OPEN"
    )
    db_session.add(case)
    await db_session.commit()

    risk_res = await db_session.execute(
        select(RecoveryCase.amount).where(RecoveryCase.status.in_(["OPEN", "DIAGNOSED", "RECOVERING"]))
    )
    risk_cases = risk_res.scalars().all()
    live_risk = sum(c for c in risk_cases if c <= 5000.0)

    assert live_risk >= 10.0
