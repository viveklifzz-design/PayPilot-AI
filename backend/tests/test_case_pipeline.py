import json
import hmac
import hashlib
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.recovery_case import RecoveryCase
from app.models.transaction import Transaction
from app.models.audit_log import AuditLog
from app.core.config import settings

SECRET = "test_webhook_secret_key"

@pytest.fixture(autouse=True)
def setup_webhook_secret(monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", SECRET)

def compute_signature(payload_bytes: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

@pytest.mark.asyncio
async def test_end_to_end_payment_failed_to_recovery_case_creation(async_client: AsyncClient, db_session: AsyncSession):
    payload = {
        "entity": "event",
        "account_id": "acc_pipeline_01",
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_pipe_001",
                    "order_id": "order_pipe_001",
                    "amount": 350000, # INR 3500.00
                    "currency": "INR",
                    "status": "failed",
                    "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
                    "error_description": "Bank network timeout"
                }
            }
        }
    }
    raw_bytes = json.dumps(payload).encode("utf-8")
    sig = compute_signature(raw_bytes)
    headers = {
        "x-razorpay-signature": sig,
        "x-razorpay-event-id": "evt_pipe_001",
        "content-type": "application/json"
    }

    wh_res = await async_client.post("/api/v1/webhooks/razorpay", content=raw_bytes, headers=headers)
    assert wh_res.status_code == 200
    assert wh_res.json()["status"] == "success"

    # Verify RecoveryCase created automatically by Risk Engine
    case_stmt = select(RecoveryCase).join(Transaction).where(Transaction.razorpay_payment_id == "pay_pipe_001")
    case_res = await db_session.execute(case_stmt)
    case = case_res.scalar_one_or_none()
    assert case is not None
    assert float(case.amount) == 3500.0
    assert case.risk_level == "LOW"
    assert case.status == "OPEN"
    assert case.risk_factors is not None
    assert len(case.risk_factors) >= 1

    # Perform Policy Check via API
    policy_res = await async_client.post(
        f"/api/v1/cases/{case.id}/policy-check",
        json={"proposed_action": "RETRY", "ai_confidence": 0.90}
    )
    assert policy_res.status_code == 200
    p_data = policy_res.json()
    assert p_data["allowed"] is True
    assert p_data["effective_action"] == "RETRY"

    # Verify Audit Logs created
    audit_stmt = select(AuditLog).where(AuditLog.case_id == case.id)
    audit_res = await db_session.execute(audit_stmt)
    logs = audit_res.scalars().all()
    assert len(logs) >= 2
    event_types = [l.event_type for l in logs]
    assert "REVENUE_RISK_ASSESSED" in event_types
    assert ("POLICY_APPROVED" in event_types or "RECOVERY_POLICY_CHECKED" in event_types)

@pytest.mark.asyncio
async def test_high_value_payment_failed_forces_policy_escalation(async_client: AsyncClient, db_session: AsyncSession):
    payload = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_pipe_high_val",
                    "amount": 7500000,
                    "currency": "INR",
                    "status": "failed",
                    "error_code": "BAD_REQUEST_PAYMENT_DECLINED"
                }
            }
        }
    }
    raw_bytes = json.dumps(payload).encode("utf-8")
    sig = compute_signature(raw_bytes)
    headers = {"x-razorpay-signature": sig, "x-razorpay-event-id": "evt_pipe_002"}

    await async_client.post("/api/v1/webhooks/razorpay", content=raw_bytes, headers=headers)

    case_stmt = select(RecoveryCase).join(Transaction).where(Transaction.razorpay_payment_id == "pay_pipe_high_val")
    case_res = await db_session.execute(case_stmt)
    case = case_res.scalar_one_or_none()
    assert case is not None
    assert float(case.amount) == 75000.0

    policy_res = await async_client.post(
        f"/api/v1/cases/{case.id}/policy-check",
        json={"proposed_action": "RETRY"}
    )
    assert policy_res.status_code == 200
    p_data = policy_res.json()
    assert p_data["allowed"] is False
    assert "AMOUNT_EXCEEDS_AUTO_LIMIT" in p_data["violations"]
    assert p_data["effective_action"] == "ESCALATE"

    # Case status should transition to ESCALATED
    await db_session.refresh(case)
    assert case.status == "ESCALATED"
