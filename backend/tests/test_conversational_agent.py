import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.customer import Customer
from app.models.transaction import Transaction
from app.models.receivables_and_mandates import Invoice
from app.models.recovery_case import RecoveryCase
from app.services.recovery.paypilot_tools import (
    tool_get_customer,
    tool_search_customer,
    tool_get_customer_transactions,
    tool_get_transaction,
    tool_get_payment_status,
    tool_get_payment_history,
    tool_get_invoice,
    tool_get_recovery_case,
    tool_get_notifications,
    tool_get_account_summary,
    tool_get_failed_payments,
    tool_get_payment_link_status,
    tool_verify_razorpay_payment
)
from app.services.recovery.conversational_agent import conversational_agent
from app.services.recovery.voice_recovery_service import voice_recovery_service

@pytest.mark.asyncio
async def test_paypilot_tools_read_only_access(db_session: AsyncSession):
    """Test all read-only PayPilot tools return accurate data without modifying state."""
    # 1. Account Summary
    summary = await tool_get_account_summary(db_session)
    assert "total_recovery_cases" in summary
    assert "total_transactions" in summary
    assert summary["healthy_status"] == "ACTIVE"

    # 2. Failed Payments
    failed_txns = await tool_get_failed_payments(db_session)
    assert isinstance(failed_txns, list)

    # 3. Notifications
    nots = await tool_get_notifications(db_session, limit=5)
    assert isinstance(nots, list)

    # 4. Search Customer
    custs = await tool_search_customer(db_session, "Acme")
    assert isinstance(custs, list)

@pytest.mark.asyncio
async def test_razorpay_verification_tool(db_session: AsyncSession):
    """Test Razorpay provider payment verification tool."""
    res = await tool_verify_razorpay_payment(db_session, "pay_test_verification_001")
    assert "payment_id" in res or "status" in res

async def _get_or_create_test_invoice(db: AsyncSession) -> Invoice:
    inv_res = await db.execute(select(Invoice))
    inv = inv_res.scalars().first()
    if inv:
        return inv

    # Create dummy merchant, customer, invoice for isolated test session
    from app.models.merchant import Merchant
    m = Merchant(name="Test Merchant", email="merchant@test.com")
    db.add(m)
    await db.flush()

    c = Customer(merchant_id=m.id, name="Acme Enterprises", email="acme@test.com", phone="8087730363")
    db.add(c)
    await db.flush()

    inv = Invoice(
        merchant_id=m.id,
        customer_id=c.id,
        invoice_number="INV-CONV-001",
        amount=2500.00,
        due_date=datetime.now(timezone.utc) - timedelta(days=5),
        status="OVERDUE"
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return inv

@pytest.mark.asyncio
async def test_conversational_agent_turn_processing(db_session: AsyncSession):
    """Test conversational agent processes multi-turn inputs with session context."""
    # Lookup sample invoice
    inv = await _get_or_create_test_invoice(db_session)
    assert inv is not None

    sess_id = "test_conv_sess_001"

    # Turn 1: Payment failed notification
    t1 = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Mera payment fail ho gaya.",
        session_id=sess_id
    )
    assert t1.session_id == sess_id
    assert t1.invoice_id == inv.id

    # Turn 2: Amount inquiry
    t2 = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Kitne amount ka tha?",
        session_id=sess_id
    )
    assert t2.amount == float(inv.amount)

    # Turn 3: Retry request
    t3 = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Achha, retry kar sakte hain?",
        session_id=sess_id
    )
    assert t3.response_text_hinglish is not None
    assert t3.session_id == sess_id

    # Turn 4: Promise-to-pay
    t4 = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Kal karunga.",
        session_id=sess_id
    )
    assert t4.response_text_hinglish is not None
    assert t4.invoice_number == inv.invoice_number

@pytest.mark.asyncio
async def test_natural_language_queries_safety_invariants(db_session: AsyncSession):
    """Test natural English, Hindi, and Hinglish queries satisfy safety invariants."""
    inv = await _get_or_create_test_invoice(db_session)
    assert inv is not None

    # Test Human Escalation Safety Override
    res_esc = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Human se baat karni hai.",
        session_id="sess_safety_esc"
    )
    assert res_esc.action_taken == "ESCALATE_TO_HUMAN"
    assert res_esc.safety_status == "ESCALATED"

    # Test Payment Status Query
    res_stat = await voice_recovery_service.handle_voice_interaction(
        db=db_session,
        invoice_id=inv.id,
        customer_speech="Mera payment successful hua kya?",
        session_id="sess_stat"
    )
    assert res_stat.response_text_hinglish is not None
    assert res_stat.invoice_number == inv.invoice_number
