import json
import hmac
import hashlib
import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.merchant import Merchant
from app.models.transaction import Transaction
from app.models.recovery_case import RecoveryCase
from app.models.recovery_action import RecoveryAction
from app.models.audit_log import AuditLog
from app.core.config import settings
from app.core.exceptions import PaymentGatewayException

SECRET = "test_webhook_secret_key"

@pytest.fixture(autouse=True)
def set_webhook_secret(monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", SECRET)

def compute_signature(payload_bytes: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

@pytest_asyncio.fixture
async def setup_test_case(db_session: AsyncSession):
    merchant = Merchant(
        id="mer_test_rec_001",
        name="Test Recovery Merchant",
        email="merchant@test.com"
    )
    db_session.add(merchant)

    txn = Transaction(
        id="txn_test_rec_001",
        merchant_id=merchant.id,
        amount=2499.00,
        currency="INR",
        status="failed",
        error_code="BAD_REQUEST_PAYMENT_TIMED_OUT",
        error_description="Payment timed out at gateway"
    )
    db_session.add(txn)

    case = RecoveryCase(
        id="case_test_rec_001",
        merchant_id=merchant.id,
        transaction_id=txn.id,
        amount=2499.00,
        risk_score=75.0,
        risk_level="HIGH",
        priority_score=80.0,
        priority_level="HIGH",
        status="DIAGNOSED",
        ai_root_cause="Network timeout during authorization",
        ai_recommended_action="RECOVERY_LINK",
        ai_confidence=0.88,
        ai_reasoning="Customer timed out. Generating a personalized payment recovery link will maximize conversion."
    )
    db_session.add(case)
    await db_session.commit()
    return case

@pytest.mark.asyncio
async def test_recovery_execution_success(async_client: AsyncClient, setup_test_case: RecoveryCase, db_session: AsyncSession):
    case = setup_test_case
    mock_plink = {
        "id": "plink_test_9999",
        "entity": "payment_link",
        "short_url": "https://rzp.io/i/plink_test_9999",
        "status": "created",
        "amount": 249900,
        "currency": "INR",
        "reference_id": f"PP-RECOVERY-{case.id[:8]}-100"
    }

    with patch("app.services.razorpay.client.razorpay_service.create_payment_link", return_value=mock_plink):
        res = await async_client.post(
            f"/api/v1/cases/{case.id}/execute",
            json={"action": "RECOVERY_LINK", "ai_confidence": 0.88}
        )

    assert res.status_code == 200
    data = res.json()
    assert data["allowed"] is True
    assert data["policy_allowed"] is True
    assert data["action"] == "RECOVERY_LINK"
    assert data["status"] == "CREATED"
    assert data["provider"] == "RAZORPAY"
    assert data["provider_reference"] == "plink_test_9999"
    assert data["payment_url"] == "https://rzp.io/i/plink_test_9999"
    assert data["amount"] == 2499.00
    assert data["currency"] == "INR"

    # Verify secrets are omitted
    res_str = str(data)
    assert "RAZORPAY_KEY_SECRET" not in res_str

    # Verify RecoveryAction DB record
    action_res = await db_session.execute(
        select(RecoveryAction).where(RecoveryAction.case_id == case.id)
    )
    action = action_res.scalars().first()
    assert action is not None
    assert action.action_type == "RECOVERY_LINK"
    assert action.status == "CREATED"
    assert action.razorpay_payment_link_id == "plink_test_9999"
    assert action.short_url == "https://rzp.io/i/plink_test_9999"

    # Verify Audit Logs
    audit_res = await db_session.execute(
        select(AuditLog).where(AuditLog.case_id == case.id)
    )
    audits = audit_res.scalars().all()
    event_types = [a.event_type for a in audits]
    assert "RECOVERY_EXECUTION_STARTED" in event_types
    assert "RECOVERY_PAYMENT_LINK_CREATED" in event_types

@pytest.mark.asyncio
async def test_recovery_execution_policy_block(async_client: AsyncClient, setup_test_case: RecoveryCase, db_session: AsyncSession):
    case = setup_test_case

    # Low confidence triggers policy block
    res = await async_client.post(
        f"/api/v1/cases/{case.id}/execute",
        json={"action": "RECOVERY_LINK", "ai_confidence": 0.10}
    )

    assert res.status_code == 200
    data = res.json()
    assert data["allowed"] is False
    assert data["policy_allowed"] is False
    assert data["status"] == "BLOCKED"
    assert data["execution_status"] == "BLOCKED"
    assert "Policy Safety Gate blocked" in data["message"]

    # Verify BLOCKED action record
    action_res = await db_session.execute(
        select(RecoveryAction).where(RecoveryAction.case_id == case.id)
    )
    action = action_res.scalars().first()
    assert action is not None
    assert action.status == "BLOCKED"

@pytest.mark.asyncio
async def test_recovery_execution_api_failure(async_client: AsyncClient, setup_test_case: RecoveryCase, db_session: AsyncSession):
    case = setup_test_case

    with patch("app.services.razorpay.client.razorpay_service.create_payment_link", side_effect=PaymentGatewayException("Razorpay gateway unreachable")):
        res = await async_client.post(
            f"/api/v1/cases/{case.id}/execute",
            json={"action": "RECOVERY_LINK", "ai_confidence": 0.90}
        )

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "FAILED"
    assert "failed" in data["message"].lower()

    # Verify FAILED action record
    action_res = await db_session.execute(
        select(RecoveryAction).where(RecoveryAction.case_id == case.id)
    )
    action = action_res.scalars().first()
    assert action is not None
    assert action.status == "FAILED"

@pytest.mark.asyncio
async def test_duplicate_execution_prevents_multiple_links(async_client: AsyncClient, setup_test_case: RecoveryCase):
    case = setup_test_case
    mock_plink = {
        "id": "plink_test_dup_1111",
        "short_url": "https://rzp.io/i/plink_test_dup_1111",
        "status": "created",
        "amount": 249900,
        "currency": "INR"
    }

    with patch("app.services.razorpay.client.razorpay_service.create_payment_link", return_value=mock_plink) as mock_api:
        # First execution creates link
        res1 = await async_client.post(
            f"/api/v1/cases/{case.id}/execute",
            json={"action": "RECOVERY_LINK", "ai_confidence": 0.88}
        )
        assert res1.json()["provider_reference"] == "plink_test_dup_1111"
        assert mock_api.call_count == 1

        # Second execution returns existing active link without calling Razorpay API again
        res2 = await async_client.post(
            f"/api/v1/cases/{case.id}/execute",
            json={"action": "RECOVERY_LINK", "ai_confidence": 0.88}
        )
        assert res2.json()["provider_reference"] == "plink_test_dup_1111"
        assert res2.json()["message"] == "Duplicate recovery action execution prevented. Returned existing action result."
        assert mock_api.call_count == 1  # Not incremented!

@pytest.mark.asyncio
async def test_payment_link_paid_webhook_idempotent(async_client: AsyncClient, setup_test_case: RecoveryCase, db_session: AsyncSession):
    case = setup_test_case

    # Pre-create RecoveryAction
    action = RecoveryAction(
        case_id=case.id,
        action_type="RECOVERY_LINK",
        status="CREATED",
        razorpay_payment_link_id="plink_webhook_test_2222",
        short_url="https://rzp.io/i/plink_webhook_test_2222"
    )
    db_session.add(action)
    await db_session.commit()

    webhook_payload = {
        "entity": "event",
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_webhook_test_2222",
                    "amount": 249900,
                    "currency": "INR",
                    "notes": {"case_id": case.id}
                }
            },
            "payment": {
                "entity": {
                    "id": "pay_wh_test_5555",
                    "amount": 249900,
                    "currency": "INR",
                    "status": "captured",
                    "order_id": "order_wh_test_5555"
                }
            }
        }
    }

    raw_bytes = json.dumps(webhook_payload).encode("utf-8")
    sig = compute_signature(raw_bytes)
    headers = {
        "X-Razorpay-Signature": sig,
        "X-Razorpay-Event-Id": "evt_wh_rec_001",
        "Content-Type": "application/json"
    }

    # First Webhook Delivery
    res1 = await async_client.post(
        "/api/v1/webhooks/razorpay",
        content=raw_bytes,
        headers=headers
    )
    assert res1.status_code == 200

    # Refresh Case from DB
    await db_session.refresh(case)
    await db_session.refresh(action)
    assert case.status == "RECOVERED"
    assert case.recovered_amount == 2499.00
    assert action.status == "COMPLETED"

    # Second Webhook Delivery (Idempotency Test)
    sig2 = compute_signature(raw_bytes)
    headers2 = {
        "X-Razorpay-Signature": sig2,
        "X-Razorpay-Event-Id": "evt_wh_rec_002",
        "Content-Type": "application/json"
    }
    res2 = await async_client.post(
        "/api/v1/webhooks/razorpay",
        content=raw_bytes,
        headers=headers2
    )
    assert res2.status_code == 200

    # Refresh Case from DB again — amount must NOT double
    await db_session.refresh(case)
    assert case.status == "RECOVERED"
    assert case.recovered_amount == 2499.00
