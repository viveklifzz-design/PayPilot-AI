import pytest
from datetime import datetime, timezone, timedelta
from app.models.receivables_and_mandates import Invoice
from app.models.merchant import Merchant
from app.models.customer import Customer
from app.services.recovery.voice_recovery_service import voice_recovery_service, parse_hinglish_intent
from app.models.base import utc_now, generate_uuid

async def setup_test_invoice(db):
    m = Merchant(name="Enterprise Tech Corp", email=f"tech_{generate_uuid()[:6]}@test.com")
    db.add(m)
    await db.commit()
    await db.refresh(m)

    c = Customer(merchant_id=m.id, name="Acme Logistics Pvt Ltd", email=f"acme_{generate_uuid()[:6]}@test.com")
    db.add(c)
    await db.commit()
    await db.refresh(c)

    inv = Invoice(
        merchant_id=m.id,
        customer_id=c.id,
        invoice_number=f"INV-MT-{generate_uuid()[:6]}",
        amount=1000.0,
        due_date=utc_now() - timedelta(days=2),
        days_overdue=2,
        status="OVERDUE"
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return inv

@pytest.mark.asyncio
async def test_full_multi_turn_voice_conversation_scenario(db_session):
    """
    Verifies the complete 7-turn conversation flow requested by user:
    Turn 1: "Invoice amount kitna hai?" -> INVOICE_DETAILS
    Turn 2: "Friday ko payment kar dunga." -> PROMISE_TO_PAY (No false escalation!)
    Turn 3: "Haan, note kar lo." -> PROMISE_CONFIRMATION
    Turn 4: "Payment link bhi bhejo." -> PAYMENT_LINK_REQUEST
    Turn 5: "WhatsApp pe bhejo." -> PAYMENT_LINK_REQUEST (Reused link)
    Turn 6: "Maine payment kar diya." -> ALREADY_PAID (Provider verification)
    Turn 7: "Human agent se baat karni hai." -> HUMAN_ESCALATION (Explicit escalation)
    """
    inv = await setup_test_invoice(db_session)
    sess_id = f"v_multi_turn_{generate_uuid()[:8]}"

    # Turn 1: Invoice details inquiry
    t1 = await voice_recovery_service.handle_voice_interaction(
        db=db_session, invoice_id=inv.id, customer_speech="Invoice amount kitna hai?", session_id=sess_id
    )
    assert t1.turn_count == 1
    assert t1.detected_intent == "INVOICE_DETAILS"
    assert "1,000" in t1.response_text_hinglish
    assert t1.action_taken == "INFO_PROVIDED"
    assert t1.safety_status == "SAFE"

    # Turn 2: Promise to Pay on Friday (MUST NOT escalate to human!)
    t2 = await voice_recovery_service.handle_voice_interaction(
        db=db_session, invoice_id=inv.id, customer_speech="Friday ko payment kar dunga.", session_id=sess_id
    )
    assert t2.turn_count == 2
    assert t2.detected_intent == "PROMISE_TO_PAY"
    assert t2.is_promise_registered is True
    assert t2.action_taken == "PROMISE_TO_PAY_REGISTERED"
    assert t2.safety_status == "SAFE"
    assert "human accounts manager" not in t2.response_text_hinglish.lower()
    assert "promise-to-pay" in t2.response_text_hinglish.lower() or "promise note" in t2.response_text_hinglish.lower()

    # Turn 3: Confirmation "Haan, note kar lo."
    t3 = await voice_recovery_service.handle_voice_interaction(
        db=db_session, invoice_id=inv.id, customer_speech="Haan, note kar lo.", session_id=sess_id
    )
    assert t3.turn_count == 3
    assert t3.detected_intent == "PROMISE_CONFIRMATION"
    assert t3.action_taken == "PROMISE_TO_PAY_REGISTERED"

    # Turn 4: Payment link request
    t4 = await voice_recovery_service.handle_voice_interaction(
        db=db_session, invoice_id=inv.id, customer_speech="Payment link bhi bhejo.", session_id=sess_id
    )
    assert t4.turn_count == 4
    assert t4.detected_intent == "PAYMENT_LINK_REQUEST"
    assert t4.is_payment_link_sent is True
    assert t4.payment_url is not None

    # Turn 5: WhatsApp link request (Reuses active link)
    t5 = await voice_recovery_service.handle_voice_interaction(
        db=db_session, invoice_id=inv.id, customer_speech="WhatsApp pe bhejo.", session_id=sess_id
    )
    assert t5.turn_count == 5
    assert t5.detected_intent == "PAYMENT_LINK_REQUEST"
    assert t5.action_taken == "PAYMENT_LINK_REUSED"
    assert t5.payment_url == t4.payment_url

    # Turn 6: Already paid claim (Triggers provider verification check)
    t6 = await voice_recovery_service.handle_voice_interaction(
        db=db_session, invoice_id=inv.id, customer_speech="Maine payment kar diya.", session_id=sess_id
    )
    assert t6.turn_count == 6
    assert t6.detected_intent == "ALREADY_PAID"
    assert t6.action_taken == "VERIFICATION_PENDING"
    assert "verify" in t6.response_text_hinglish.lower() or "provider" in t6.response_text_hinglish.lower()

    # Turn 7: Explicit human escalation request
    t7 = await voice_recovery_service.handle_voice_interaction(
        db=db_session, invoice_id=inv.id, customer_speech="Human agent se baat karni hai.", session_id=sess_id
    )
    assert t7.turn_count == 7
    assert t7.detected_intent == "HUMAN_ESCALATION"
    assert t7.action_taken == "ESCALATE_TO_HUMAN"
    assert t7.safety_status == "ESCALATED"
    assert "senior human accounts manager" in t7.response_text_hinglish
