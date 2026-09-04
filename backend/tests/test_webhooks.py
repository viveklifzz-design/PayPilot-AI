import json
import hmac
import hashlib
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.webhook_event import WebhookEvent
from app.models.transaction import Transaction
from app.models.audit_log import AuditLog
from app.core.config import settings

SECRET = "test_webhook_secret_key"

@pytest.fixture(autouse=True)
def set_webhook_secret(monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", SECRET)

def compute_signature(payload_bytes: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

@pytest.mark.asyncio
async def test_webhook_valid_signature_payment_failed(async_client: AsyncClient, db_session: AsyncSession):
    payload = {
        "entity": "event",
        "account_id": "acc_123",
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_001",
                    "order_id": "order_test_001",
                    "amount": 250000,
                    "currency": "INR",
                    "status": "failed",
                    "error_code": "BAD_REQUEST_PAYMENT_DECLINED",
                    "error_description": "Issuing bank declined payment"
                }
            }
        }
    }
    raw_bytes = json.dumps(payload).encode("utf-8")
    sig = compute_signature(raw_bytes)
    headers = {
        "x-razorpay-signature": sig,
        "x-razorpay-event-id": "evt_test_001",
        "content-type": "application/json"
    }

    response = await async_client.post("/api/v1/webhooks/razorpay", content=raw_bytes, headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    assert res_data["event_id"] == "evt_test_001"

    # Verify DB event persistence
    evt = await db_session.execute(select(WebhookEvent).where(WebhookEvent.event_id == "evt_test_001"))
    assert evt.scalar_one_or_none() is not None

    # Verify transaction persistence & failure details
    txn = await db_session.execute(select(Transaction).where(Transaction.razorpay_payment_id == "pay_test_001"))
    txn_obj = txn.scalar_one_or_none()
    assert txn_obj is not None
    assert txn_obj.status == "failed"
    assert txn_obj.error_code == "BAD_REQUEST_PAYMENT_DECLINED"

    # Verify audit log creation
    audit = await db_session.execute(select(AuditLog).where(AuditLog.actor == "RAZORPAY_WEBHOOK"))
    assert audit.scalar_one_or_none() is not None

@pytest.mark.asyncio
async def test_webhook_lifecycle_idempotency_authorized_then_captured(async_client: AsyncClient, db_session: AsyncSession):
    payment_id = "pay_idemp_lifecycle_100"
    
    # 1. payment.authorized event
    auth_payload = {
        "event": "payment.authorized",
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": "order_idemp_100",
                    "amount": 1000, # ₹10.00
                    "currency": "INR",
                    "status": "authorized",
                    "method": "netbanking"
                }
            }
        }
    }
    raw_auth = json.dumps(auth_payload).encode("utf-8")
    sig_auth = compute_signature(raw_auth)
    headers_auth = {"x-razorpay-signature": sig_auth, "x-razorpay-event-id": "evt_auth_100"}

    res_auth = await async_client.post("/api/v1/webhooks/razorpay", content=raw_auth, headers=headers_auth)
    assert res_auth.status_code == 200

    # Verify transaction created
    txns = (await db_session.execute(select(Transaction).where(Transaction.razorpay_payment_id == payment_id))).scalars().all()
    assert len(txns) == 1
    assert txns[0].status == "authorized"
    assert txns[0].amount == 10.0

    # 2. payment.captured event for SAME payment_id
    cap_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": "order_idemp_100",
                    "amount": 1000, # ₹10.00
                    "currency": "INR",
                    "status": "captured",
                    "method": "netbanking"
                }
            }
        }
    }
    raw_cap = json.dumps(cap_payload).encode("utf-8")
    sig_cap = compute_signature(raw_cap)
    headers_cap = {"x-razorpay-signature": sig_cap, "x-razorpay-event-id": "evt_cap_100"}

    res_cap = await async_client.post("/api/v1/webhooks/razorpay", content=raw_cap, headers=headers_cap)
    assert res_cap.status_code == 200

    # Refresh session identity map
    db_session.expire_all()

    # Verify SAME transaction updated (NO duplicate created)
    txns_after = (await db_session.execute(select(Transaction).where(Transaction.razorpay_payment_id == payment_id))).scalars().all()
    assert len(txns_after) == 1
    assert txns_after[0].status == "captured"
    assert txns_after[0].id == txns[0].id

    # 3. GET /api/v1/transactions API endpoint returns persisted transaction
    txns_api_res = await async_client.get("/api/v1/transactions")
    assert txns_api_res.status_code == 200
    txns_list = txns_api_res.json()
    match = next((t for t in txns_list if t["razorpay_payment_id"] == payment_id), None)
    assert match is not None
    assert match["status"] == "captured"
    assert match["amount"] == 10.0

@pytest.mark.asyncio
async def test_webhook_invalid_signature(async_client: AsyncClient):
    payload = {"event": "payment.failed"}
    raw_bytes = json.dumps(payload).encode("utf-8")
    headers = {
        "x-razorpay-signature": "invalid_signature_hash_xyz",
        "x-razorpay-event-id": "evt_test_invalid",
        "content-type": "application/json"
    }

    response = await async_client.post("/api/v1/webhooks/razorpay", content=raw_bytes, headers=headers)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_webhook_missing_signature(async_client: AsyncClient):
    payload = {"event": "payment.failed"}
    raw_bytes = json.dumps(payload).encode("utf-8")

    response = await async_client.post("/api/v1/webhooks/razorpay", content=raw_bytes)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_webhook_modified_payload(async_client: AsyncClient):
    original_payload = {"event": "payment.failed", "amount": 1000}
    raw_bytes = json.dumps(original_payload).encode("utf-8")
    sig = compute_signature(raw_bytes)

    tampered_bytes = json.dumps({"event": "payment.failed", "amount": 999999}).encode("utf-8")
    headers = {"x-razorpay-signature": sig}

    response = await async_client.post("/api/v1/webhooks/razorpay", content=tampered_bytes, headers=headers)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_webhook_duplicate_event_idempotency(async_client: AsyncClient):
    payload = {"event": "payment.authorized", "payload": {"payment": {"entity": {"id": "pay_dup_1"}}}}
    raw_bytes = json.dumps(payload).encode("utf-8")
    sig = compute_signature(raw_bytes)
    headers = {"x-razorpay-signature": sig, "x-razorpay-event-id": "evt_dup_100"}

    res1 = await async_client.post("/api/v1/webhooks/razorpay", content=raw_bytes, headers=headers)
    assert res1.status_code == 200
    assert res1.json()["status"] == "success"

    res2 = await async_client.post("/api/v1/webhooks/razorpay", content=raw_bytes, headers=headers)
    assert res2.status_code == 200
    assert res2.json()["status"] == "ignored"

@pytest.mark.asyncio
async def test_webhook_malformed_json(async_client: AsyncClient):
    raw_bytes = b"{bad json string"
    sig = compute_signature(raw_bytes)
    headers = {"x-razorpay-signature": sig}

    response = await async_client.post("/api/v1/webhooks/razorpay", content=raw_bytes, headers=headers)
    assert response.status_code == 400
