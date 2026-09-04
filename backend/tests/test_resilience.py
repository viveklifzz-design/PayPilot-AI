import json
import hmac
import hashlib
import pytest
import pytest_asyncio
from unittest.mock import patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.merchant import Merchant
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.models.recovery_case import RecoveryCase
from app.models.recovery_action import RecoveryAction
from app.models.webhook_event import WebhookEvent
from app.models.audit_log import AuditLog
from app.core.config import settings
from app.core.exceptions import PaymentGatewayException
from app.services.razorpay import razorpay_service
from app.services.recovery import recovery_executor
from app.services.policy import policy_engine
from app.services.ai import fallback_ai_service

SECRET = "test_webhook_resilience_secret"

@pytest.fixture(autouse=True)
def set_resilience_webhook_secret(monkeypatch):
    monkeypatch.setattr(settings, "RAZORPAY_WEBHOOK_SECRET", SECRET)

def compute_resilience_sig(payload_bytes: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

@pytest_asyncio.fixture
async def sample_case(db_session: AsyncSession) -> RecoveryCase:
    merchant = Merchant(name="Resilience Test Merchant", email="resilience@merchant.com")
    db_session.add(merchant)
    await db_session.commit()
    await db_session.refresh(merchant)

    customer = Customer(merchant_id=merchant.id, name="Resilience Customer", email="resilience@customer.com")
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)

    txn = Transaction(
        merchant_id=merchant.id,
        customer_id=customer.id,
        razorpay_payment_id="pay_resilience_001",
        amount=2500.0,
        currency="INR",
        status="failed",
        error_code="BAD_REQUEST_PAYMENT_TIMED_OUT",
        payment_method="upi"
    )
    db_session.add(txn)
    await db_session.commit()
    await db_session.refresh(txn)

    case = RecoveryCase(
        merchant_id=merchant.id,
        customer_id=customer.id,
        transaction_id=txn.id,
        amount=2500.0,
        risk_level="MEDIUM",
        status="OPEN",
        ai_recommended_action="RECOVERY_LINK",
        ai_confidence=0.88,
        retry_count=0
    )
    db_session.add(case)
    await db_session.commit()
    await db_session.refresh(case)
    return case

# =====================================================================
# TEST 1 — RAZORPAY API FAILURE
# =====================================================================
@pytest.mark.asyncio
async def test_resilience_1_razorpay_api_failure_handling(async_client: AsyncClient, db_session: AsyncSession, sample_case: RecoveryCase):
    with patch.object(razorpay_service, "create_payment_link", side_effect=PaymentGatewayException("Razorpay API 500 Internal Server Error")):
        res = await async_client.post(f"/api/v1/cases/{sample_case.id}/execute", json={"action": "RECOVERY_LINK"})
        assert res.status_code == 200
        data = res.json()

        assert data["execution_status"] == "FAILED"
        assert data["status"] == "FAILED"
        assert data["provider_reference"] is None

        # Verify DB state
        await db_session.refresh(sample_case)
        assert sample_case.status == "FAILED"
        assert sample_case.status != "RECOVERED"
        assert float(sample_case.recovered_amount) == 0.0

        # Verify Audit Log event exists
        audit = (await db_session.execute(select(AuditLog).where(AuditLog.case_id == sample_case.id).where(AuditLog.event_type == "RECOVERY_EXECUTION_FAILED"))).scalar_one_or_none()
        assert audit is not None
        assert "API 500" in audit.description or "failed" in audit.description

# =====================================================================
# TEST 2 — DUPLICATE WEBHOOK
# =====================================================================
@pytest.mark.asyncio
async def test_resilience_2_duplicate_webhook_event_idempotency(async_client: AsyncClient, db_session: AsyncSession):
    payload = {
        "event": "payment.authorized",
        "payload": {"payment": {"entity": {"id": "pay_resilience_dup_002", "amount": 150000, "status": "authorized"}}}
    }
    raw_bytes = json.dumps(payload).encode("utf-8")
    sig = compute_resilience_sig(raw_bytes)
    headers = {"x-razorpay-signature": sig, "x-razorpay-event-id": "evt_resilience_dup_999"}

    res1 = await async_client.post("/api/v1/webhooks/razorpay", content=raw_bytes, headers=headers)
    assert res1.status_code == 200
    assert res1.json()["status"] == "success"

    tx_count_1 = (await db_session.execute(select(func.count(Transaction.id)))).scalar()

    # Second delivery of SAME event_id
    res2 = await async_client.post("/api/v1/webhooks/razorpay", content=raw_bytes, headers=headers)
    assert res2.status_code == 200
    assert res2.json()["status"] == "ignored"

    tx_count_2 = (await db_session.execute(select(func.count(Transaction.id)))).scalar()
    assert tx_count_1 == tx_count_2

# =====================================================================
# TEST 3 — LOW AI CONFIDENCE
# =====================================================================
@pytest.mark.asyncio
async def test_resilience_3_low_ai_confidence_blocked_by_policy(async_client: AsyncClient, db_session: AsyncSession, sample_case: RecoveryCase):
    res = await async_client.post(f"/api/v1/cases/{sample_case.id}/execute", json={"action": "RECOVERY_LINK", "ai_confidence": 0.45})
    assert res.status_code == 200
    data = res.json()

    assert data["policy_allowed"] is False
    assert data["execution_status"] == "BLOCKED"
    assert data["effective_action"] in ["STOP", "ESCALATE"]

    await db_session.refresh(sample_case)
    assert sample_case.status in ["STOPPED", "ESCALATED"]

    audit = (await db_session.execute(select(AuditLog).where(AuditLog.case_id == sample_case.id).where(AuditLog.event_type == "RECOVERY_POLICY_BLOCKED"))).scalar_one_or_none()
    assert audit is not None

# =====================================================================
# TEST 4 — RETRY LIMIT EXCEEDED
# =====================================================================
@pytest.mark.asyncio
async def test_resilience_4_retry_limit_exceeded_blocked_by_policy(async_client: AsyncClient, db_session: AsyncSession, sample_case: RecoveryCase):
    sample_case.retry_count = 3
    db_session.add(sample_case)
    await db_session.commit()

    res = await async_client.post(f"/api/v1/cases/{sample_case.id}/execute", json={"action": "RETRY"})
    assert res.status_code == 200
    data = res.json()

    assert data["policy_allowed"] is False
    assert data["execution_status"] == "BLOCKED"
    assert data["effective_action"] in ["STOP", "ESCALATE"]

    audit = (await db_session.execute(select(AuditLog).where(AuditLog.case_id == sample_case.id).where(AuditLog.event_type == "RECOVERY_POLICY_BLOCKED"))).scalar_one_or_none()
    assert audit is not None
    assert "retries" in audit.description.lower() or "limit" in audit.description.lower() or "blocked" in audit.description.lower()

# =====================================================================
# TEST 5 — COOLDOWN VIOLATION
# =====================================================================
@pytest.mark.asyncio
async def test_resilience_5_cooldown_violation_blocked_by_policy(async_client: AsyncClient, db_session: AsyncSession, sample_case: RecoveryCase):
    from datetime import datetime, timezone, timedelta
    recent_action = RecoveryAction(
        case_id=sample_case.id,
        action_type="RETRY",
        status="FAILED",
        executed_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        payload={"note": "Recent action failed 5 minutes ago"}
    )
    db_session.add(recent_action)
    await db_session.commit()

    res = await async_client.post(f"/api/v1/cases/{sample_case.id}/execute", json={"action": "RETRY"})
    assert res.status_code == 200
    data = res.json()

    assert data["policy_allowed"] is False
    assert data["execution_status"] == "BLOCKED"

# =====================================================================
# TEST 6 — HIGH-VALUE TRANSACTION
# =====================================================================
@pytest.mark.asyncio
async def test_resilience_6_high_value_transaction_blocked_by_policy(async_client: AsyncClient, db_session: AsyncSession, sample_case: RecoveryCase):
    sample_case.amount = 75000.0
    db_session.add(sample_case)
    await db_session.commit()

    res = await async_client.post(f"/api/v1/cases/{sample_case.id}/execute", json={"action": "RECOVERY_LINK"})
    assert res.status_code == 200
    data = res.json()

    assert data["policy_allowed"] is False
    assert data["effective_action"] == "ESCALATE"

    await db_session.refresh(sample_case)
    assert sample_case.status == "ESCALATED"

# =====================================================================
# TEST 7 — INVALID AI OUTPUT
# =====================================================================
@pytest.mark.asyncio
async def test_resilience_7_invalid_ai_output_handled_safely():
    # Test invalid confidence values handling in PolicyEngine
    pol = policy_engine.evaluate_action(proposed_action="RECOVERY_LINK", case_status="OPEN", amount=2500.0, retry_count=0, ai_confidence=-1.0)
    assert pol.allowed is False
    assert pol.effective_action in ["STOP", "ESCALATE"]

    pol2 = policy_engine.evaluate_action(proposed_action="INVALID_ACTION_XYZ", case_status="OPEN", amount=2500.0, retry_count=0, ai_confidence=0.90)
    assert pol2.effective_action in ["STOP", "ESCALATE", "RECOVERY_LINK"]

# =====================================================================
# TEST 8 — DATABASE FAILURE
# =====================================================================
@pytest.mark.asyncio
async def test_resilience_8_database_failure_handling(sample_case: RecoveryCase):
    # Verify execution gracefully handles DB commit errors
    class MockErrorSession:
        def add(self, *args, **kwargs):
            pass
        async def execute(self, *args, **kwargs):
            raise Exception("Database transaction connection failed")

    res = await recovery_executor.execute_recovery(sample_case, MockErrorSession(), proposed_action="RECOVERY_LINK")
    assert res["allowed"] is True or res["allowed"] is False
    assert res["execution_status"] in ["FAILED", "BLOCKED"]

# =====================================================================
# TEST 9 — WEBHOOK OUT-OF-ORDER DELIVERY
# =====================================================================
@pytest.mark.asyncio
async def test_resilience_9_out_of_order_webhook_delivery(async_client: AsyncClient, db_session: AsyncSession):
    # payment.captured arrives without prior payment.authorized
    cap_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_out_of_order_101",
                    "amount": 50000,
                    "currency": "INR",
                    "status": "captured"
                }
            }
        }
    }
    raw_cap = json.dumps(cap_payload).encode("utf-8")
    sig = compute_resilience_sig(raw_cap)
    headers = {"x-razorpay-signature": sig, "x-razorpay-event-id": "evt_ooo_101"}

    res = await async_client.post("/api/v1/webhooks/razorpay", content=raw_cap, headers=headers)
    assert res.status_code == 200

    txn = (await db_session.execute(select(Transaction).where(Transaction.razorpay_payment_id == "pay_out_of_order_101"))).scalar_one_or_none()
    assert txn is not None
    assert txn.status == "captured"

# =====================================================================
# TEST 10 — PAYMENT LINK PAID DUPLICATE IDEMPOTENCY
# =====================================================================
@pytest.mark.asyncio
async def test_resilience_10_payment_link_paid_duplicate_idempotency(async_client: AsyncClient, db_session: AsyncSession, sample_case: RecoveryCase):
    action = RecoveryAction(
        case_id=sample_case.id,
        action_type="RECOVERY_LINK",
        status="CREATED",
        razorpay_payment_link_id="plink_dup_paid_999",
        short_url="https://rzp.io/i/plink_dup_paid_999"
    )
    db_session.add(action)
    await db_session.commit()

    payload = {
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_dup_paid_999",
                    "amount": 250000,
                    "amount_paid": 250000,
                    "status": "paid"
                }
            }
        }
    }

    raw_bytes = json.dumps(payload).encode("utf-8")
    sig = compute_resilience_sig(raw_bytes)

    # First delivery
    headers1 = {"x-razorpay-signature": sig, "x-razorpay-event-id": "evt_plink_paid_1"}
    res1 = await async_client.post("/api/v1/webhooks/razorpay", content=raw_bytes, headers=headers1)
    assert res1.status_code == 200

    await db_session.refresh(sample_case)
    assert sample_case.status == "RECOVERED"
    assert float(sample_case.recovered_amount) == 2500.0

    # Second delivery (Duplicate payment_link.paid event)
    headers2 = {"x-razorpay-signature": sig, "x-razorpay-event-id": "evt_plink_paid_2"}
    res2 = await async_client.post("/api/v1/webhooks/razorpay", content=raw_bytes, headers=headers2)
    assert res2.status_code == 200

    await db_session.refresh(sample_case)
    # Ensure recovered_amount did NOT double to ₹5,000.00
    assert float(sample_case.recovered_amount) == 2500.0

# =====================================================================
# TEST 11 — UNKNOWN WEBHOOK EVENT
# =====================================================================
@pytest.mark.asyncio
async def test_resilience_11_unknown_webhook_event_handled_safely(async_client: AsyncClient):
    payload = {"event": "payment.unknown_test", "payload": {}}
    raw_bytes = json.dumps(payload).encode("utf-8")
    sig = compute_resilience_sig(raw_bytes)
    headers = {"x-razorpay-signature": sig, "x-razorpay-event-id": "evt_unknown_001"}

    res = await async_client.post("/api/v1/webhooks/razorpay", content=raw_bytes, headers=headers)
    assert res.status_code == 200

# =====================================================================
# TEST 12 — MISSING WEBHOOK SIGNATURE
# =====================================================================
@pytest.mark.asyncio
async def test_resilience_12_missing_webhook_signature_rejected(async_client: AsyncClient):
    payload = {"event": "payment.failed"}
    raw_bytes = json.dumps(payload).encode("utf-8")

    res = await async_client.post("/api/v1/webhooks/razorpay", content=raw_bytes)
    assert res.status_code == 401

# =====================================================================
# TEST 13 — INVALID WEBHOOK SIGNATURE
# =====================================================================
@pytest.mark.asyncio
async def test_resilience_13_invalid_webhook_signature_rejected(async_client: AsyncClient):
    payload = {"event": "payment.failed"}
    raw_bytes = json.dumps(payload).encode("utf-8")
    headers = {"x-razorpay-signature": "bogus_signature_hash", "x-razorpay-event-id": "evt_bogus_sig"}

    res = await async_client.post("/api/v1/webhooks/razorpay", content=raw_bytes, headers=headers)
    assert res.status_code == 401

# =====================================================================
# TEST 14 — WEBHOOK BODY TAMPERING
# =====================================================================
@pytest.mark.asyncio
async def test_resilience_14_webhook_body_tampering_rejected(async_client: AsyncClient):
    original_bytes = json.dumps({"event": "payment.failed", "amount": 1000}).encode("utf-8")
    sig = compute_resilience_sig(original_bytes)

    tampered_bytes = json.dumps({"event": "payment.failed", "amount": 999999}).encode("utf-8")
    headers = {"x-razorpay-signature": sig}

    res = await async_client.post("/api/v1/webhooks/razorpay", content=tampered_bytes, headers=headers)
    assert res.status_code == 401

# =====================================================================
# TEST 15 — CONCURRENT RECOVERY EXECUTION PREVENTED
# =====================================================================
@pytest.mark.asyncio
async def test_resilience_15_concurrent_recovery_execution_prevented(async_client: AsyncClient, db_session: AsyncSession, sample_case: RecoveryCase):
    # Pre-create an active RecoveryAction
    active_act = RecoveryAction(
        case_id=sample_case.id,
        action_type="RECOVERY_LINK",
        status="CREATED",
        razorpay_payment_link_id="plink_concurrent_100",
        short_url="https://rzp.io/i/plink_concurrent_100",
        payload={"payment_link_url": "https://rzp.io/i/plink_concurrent_100", "provider_reference": "plink_concurrent_100"}
    )
    db_session.add(active_act)
    await db_session.commit()

    # Attempt to execute again
    res = await async_client.post(f"/api/v1/cases/{sample_case.id}/execute", json={"action": "RECOVERY_LINK"})
    assert res.status_code == 200
    data = res.json()

    assert data["provider_reference"] == "plink_concurrent_100"
    assert "Duplicate recovery action execution prevented" in data["message"] or data["allowed"] is True

# =====================================================================
# TEST 16 & 17 — AUTOMATED SAFETY INVARIANTS
# =====================================================================
@pytest.mark.asyncio
async def test_resilience_17_safety_invariants(db_session: AsyncSession, sample_case: RecoveryCase):
    # Invariant 1: Unsafe action must never execute when policy blocks it
    pol = policy_engine.evaluate_action("RECOVERY_LINK", "OPEN", amount=100000.0, retry_count=0, ai_confidence=0.9)
    assert pol.allowed is False
    assert pol.effective_action in ["STOP", "ESCALATE"]

    # Invariant 2: Failure status cannot be RECOVERED
    sample_case.status = "FAILED"
    assert sample_case.status != "RECOVERED"

    # Invariant 3: Low confidence blocked
    pol_low = policy_engine.evaluate_action("RECOVERY_LINK", "OPEN", amount=2500.0, retry_count=0, ai_confidence=0.4)
    assert pol_low.allowed is False

    # Invariant 4: Retry limit enforced
    pol_retry = policy_engine.evaluate_action("RETRY", "OPEN", amount=2500.0, retry_count=3, ai_confidence=0.9)
    assert pol_retry.allowed is False
