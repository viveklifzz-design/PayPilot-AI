import json
import hmac
import hashlib
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.recovery_case import RecoveryCase
from app.models.recovery_action import RecoveryAction
from app.models.transaction import Transaction
from app.models.merchant import Merchant
from app.models.audit_log import AuditLog
from app.core.config import settings

SECRET = "test_webhook_secret_key"

@pytest.fixture(autouse=True)
def setup_webhook_secret(monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", SECRET)

def compute_signature(payload_bytes: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

@pytest.mark.asyncio
async def test_recovery_link_execution_success(async_client: AsyncClient, db_session: AsyncSession):
    merchant = Merchant(name="Recovery Merchant", email="rec@merchant.com")
    db_session.add(merchant)
    await db_session.commit()

    txn = Transaction(
        merchant_id=merchant.id,
        razorpay_payment_id="pay_rec_001",
        amount=2500.0,
        status="failed",
        error_code="INSUFFICIENT_FUNDS"
    )
    db_session.add(txn)
    await db_session.commit()

    case = RecoveryCase(
        merchant_id=merchant.id,
        transaction_id=txn.id,
        amount=txn.amount,
        risk_score=35.0,
        risk_level="MEDIUM",
        status="OPEN"
    )
    db_session.add(case)
    await db_session.commit()

    res = await async_client.post(
        f"/api/v1/cases/{case.id}/execute",
        json={"action": "RECOVERY_LINK", "ai_confidence": 0.90}
    )
    assert res.status_code == 200
    data = res.json()

    assert data["policy_allowed"] is True
    assert data["execution_status"] in ("CREATED", "SUCCEEDED")
    assert data["effective_action"] == "RECOVERY_LINK"
    assert data["payment_link_url"] is not None
    assert "plink_" in data["provider_reference"]

    # Verify database persistence
    await db_session.refresh(case)
    assert case.status == "RECOVERING"
    assert case.retry_count == 1

    action_stmt = select(RecoveryAction).where(RecoveryAction.case_id == case.id)
    action_res = await db_session.execute(action_stmt)
    actions = action_res.scalars().all()
    assert len(actions) == 1
    assert actions[0].status in ("CREATED", "SUCCEEDED")

@pytest.mark.asyncio
async def test_mandatory_safety_test_high_amount_blocked(async_client: AsyncClient, db_session: AsyncSession):
    """
    CRITICAL MANDATORY SAFETY TEST (Section 18):
    AI recommends RECOVERY_LINK (confidence = 0.99),
    BUT amount = ₹80,000 (MAX_AUTO_RECOVERY_AMOUNT = ₹50,000).
    Expected: Policy = BLOCK, Razorpay Payment Link MUST NOT be created.
    """
    merchant = Merchant(name="High Amount Merchant", email="high@merchant.com")
    db_session.add(merchant)
    await db_session.commit()

    txn = Transaction(
        merchant_id=merchant.id,
        razorpay_payment_id="pay_high_001",
        amount=80000.0,  # Exceeds ₹50,000 auto limit
        status="failed",
        error_code="INSUFFICIENT_FUNDS"
    )
    db_session.add(txn)
    await db_session.commit()

    case = RecoveryCase(
        merchant_id=merchant.id,
        transaction_id=txn.id,
        amount=txn.amount,
        risk_score=60.0,
        risk_level="HIGH",
        status="OPEN"
    )
    db_session.add(case)
    await db_session.commit()

    res = await async_client.post(
        f"/api/v1/cases/{case.id}/execute",
        json={"action": "RECOVERY_LINK", "ai_confidence": 0.99}
    )
    assert res.status_code == 200
    data = res.json()

    assert data["policy_allowed"] is False
    assert data["execution_status"] == "BLOCKED"
    assert data["payment_link_url"] is None
    assert data["effective_action"] == "ESCALATE"

    # Verify no active Payment Link created
    await db_session.refresh(case)
    assert case.status == "ESCALATED"
    assert case.policy_passed is False

@pytest.mark.asyncio
async def test_critical_duplicate_execution_test(async_client: AsyncClient, db_session: AsyncSession):
    """
    CRITICAL DUPLICATE TEST (Section 19):
    Execute the same case twice.
    Expected: Only ONE recovery action, only ONE Razorpay Payment Link.
    Second execution returns existing action safely.
    """
    merchant = Merchant(name="Dup Merchant", email="dup@merchant.com")
    db_session.add(merchant)
    await db_session.commit()

    txn = Transaction(
        merchant_id=merchant.id,
        razorpay_payment_id="pay_dup_001",
        amount=1500.0,
        status="failed",
        error_code="BAD_REQUEST_PAYMENT_TIMED_OUT"
    )
    db_session.add(txn)
    await db_session.commit()

    case = RecoveryCase(
        merchant_id=merchant.id,
        transaction_id=txn.id,
        amount=txn.amount,
        risk_score=20.0,
        risk_level="LOW",
        status="OPEN"
    )
    db_session.add(case)
    await db_session.commit()

    # First Execution
    res1 = await async_client.post(
        f"/api/v1/cases/{case.id}/execute",
        json={"action": "RECOVERY_LINK", "ai_confidence": 0.90}
    )
    assert res1.status_code == 200
    data1 = res1.json()
    action_id_1 = data1["action_id"]
    plink_1 = data1["provider_reference"]

    # Second Execution (Duplicate Request)
    res2 = await async_client.post(
        f"/api/v1/cases/{case.id}/execute",
        json={"action": "RECOVERY_LINK", "ai_confidence": 0.90}
    )
    assert res2.status_code == 200
    data2 = res2.json()

    # Must return exact same action & payment link
    assert data2["action_id"] == action_id_1
    assert data2["provider_reference"] == plink_1
    assert "Duplicate recovery action execution prevented" in data2["message"]

    # Total RecoveryAction records in DB must still be 1
    action_stmt = select(RecoveryAction).where(RecoveryAction.case_id == case.id)
    action_res = await db_session.execute(action_stmt)
    actions = action_res.scalars().all()
    assert len(actions) == 1

@pytest.mark.asyncio
async def test_payment_link_paid_webhook_recovery_flow(async_client: AsyncClient, db_session: AsyncSession):
    """Verify end-to-end recovery lifecycle via payment_link.paid webhook."""
    merchant = Merchant(name="Flow Merchant", email="flow@merchant.com")
    db_session.add(merchant)
    await db_session.commit()

    txn = Transaction(
        merchant_id=merchant.id,
        razorpay_payment_id="pay_flow_failed",
        amount=3000.0,
        status="failed",
        error_code="INSUFFICIENT_FUNDS"
    )
    db_session.add(txn)
    await db_session.commit()

    case = RecoveryCase(
        merchant_id=merchant.id,
        transaction_id=txn.id,
        amount=txn.amount,
        risk_score=30.0,
        risk_level="MEDIUM",
        status="OPEN"
    )
    db_session.add(case)
    await db_session.commit()

    # Execute Recovery Link action
    exec_res = await async_client.post(
        f"/api/v1/cases/{case.id}/execute",
        json={"action": "RECOVERY_LINK", "ai_confidence": 0.90}
    )
    plink_id = exec_res.json()["provider_reference"]

    # Simulate incoming payment_link.paid webhook from Razorpay
    webhook_payload = {
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": plink_id,
                    "amount": 300000,
                    "status": "paid"
                }
            },
            "payment": {
                "entity": {
                    "id": "pay_flow_success",
                    "amount": 300000,
                    "status": "captured"
                }
            }
        }
    }
    raw_bytes = json.dumps(webhook_payload).encode("utf-8")
    sig = compute_signature(raw_bytes)
    headers = {"x-razorpay-signature": sig, "x-razorpay-event-id": "evt_plink_paid_001"}

    wh_res = await async_client.post("/api/v1/webhooks/razorpay", content=raw_bytes, headers=headers)
    assert wh_res.status_code == 200
    assert wh_res.json()["status"] == "success"

    # Verify Case transitioned to RECOVERED
    await db_session.refresh(case)
    assert case.status == "RECOVERED"
    assert float(case.recovered_amount) == 3000.0

    # Verify audit event created
    audit_stmt = select(AuditLog).where(AuditLog.case_id == case.id)
    audit_res = await db_session.execute(audit_stmt)
    audits = audit_res.scalars().all()
    event_types = [a.event_type for a in audits]
    assert "RECOVERY_PAYMENT_RECEIVED" in event_types

    # Already recovered case cannot execute another action
    res_after = await async_client.post(
        f"/api/v1/cases/{case.id}/execute",
        json={"action": "RECOVERY_LINK"}
    )
    assert res_after.status_code == 200
    assert res_after.json()["execution_status"] == "BLOCKED"
    assert "already RECOVERED" in res_after.json()["message"]
