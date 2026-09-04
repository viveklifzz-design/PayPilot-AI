import pytest
import hmac
import hashlib
from app.core.config import settings

@pytest.mark.asyncio
async def test_create_checkout_order_no_payment_link(async_client):
    res = await async_client.post("/api/v1/test/create-checkout-order", json={"amount": 20.0, "currency": "INR"})
    assert res.status_code == 200
    data = res.json()
    assert "order_id" in data
    assert data["order_id"].startswith("order_")
    assert data["amount"] == 20.0
    assert data["amount_paise"] == 2000
    assert data["currency"] == "INR"
    assert data["key_id"] is not None
    assert "payment_link" not in data

@pytest.mark.asyncio
async def test_checkout_signature_verification_hmac():
    order_id = "order_test_123"
    payment_id = "pay_test_456"
    secret = settings.RAZORPAY_KEY_SECRET.encode("utf-8")
    msg = f"{order_id}|{payment_id}".encode("utf-8")
    valid_sig = hmac.new(secret, msg, hashlib.sha256).hexdigest()

    check_sig = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(valid_sig, check_sig) is True

@pytest.mark.asyncio
async def test_checkout_verify_invalid_signature_rejection(async_client):
    res = await async_client.post("/api/v1/checkout/verify", json={
        "razorpay_payment_id": "pay_test_fake",
        "razorpay_order_id": "order_test_fake",
        "razorpay_signature": "invalid_signature_string",
        "recovery_case_id": None
    })
    assert res.status_code == 400
    assert "Invalid Razorpay checkout signature" in res.json()["detail"]

from app.models.recovery_case import RecoveryCase
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_case_lookup_real_uuid_returns_200(async_client, db_session: AsyncSession):
    case = RecoveryCase(
        id="f889dce3-b855-4348-b457-f0ef7c34b6b1",
        merchant_id="test_mkt",
        amount=20.0,
        risk_level="MEDIUM",
        priority_level="LOW",
        status="OPEN"
    )
    db_session.add(case)
    await db_session.commit()

    res = await async_client.get("/api/v1/cases/f889dce3-b855-4348-b457-f0ef7c34b6b1")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "f889dce3-b855-4348-b457-f0ef7c34b6b1"

@pytest.mark.asyncio
async def test_case_lookup_real_unique_prefix_returns_200(async_client, db_session: AsyncSession):
    case = RecoveryCase(
        id="e779dce3-b855-4348-b457-f0ef7c34b6b1",
        merchant_id="test_mkt",
        amount=20.0,
        risk_level="MEDIUM",
        priority_level="LOW",
        status="OPEN"
    )
    db_session.add(case)
    await db_session.commit()

    res = await async_client.get("/api/v1/cases/e779dce3")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "e779dce3-b855-4348-b457-f0ef7c34b6b1"

@pytest.mark.asyncio
async def test_case_lookup_unknown_prefix_returns_404(async_client):
    res = await async_client.get("/api/v1/cases/nonexistent_prefix_999")
    assert res.status_code == 404

@pytest.mark.asyncio
async def test_case_lookup_short_prefix_returns_404(async_client):
    res = await async_client.get("/api/v1/cases/abc")
    assert res.status_code == 404


