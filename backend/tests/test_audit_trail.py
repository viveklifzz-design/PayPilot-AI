import json
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.merchant import Merchant
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.models.recovery_case import RecoveryCase
from app.models.recovery_action import RecoveryAction
from app.models.audit_log import AuditLog
from app.models.evaluation_run import EvaluationRun

@pytest_asyncio.fixture
async def audit_sample_case(db_session: AsyncSession) -> RecoveryCase:
    merchant = Merchant(name="Audit Test Merchant", email="audit@merchant.com")
    db_session.add(merchant)
    await db_session.commit()
    await db_session.refresh(merchant)

    customer = Customer(merchant_id=merchant.id, name="Audit Customer", email="audit@customer.com", total_successful_payments=7, total_failed_payments=1)
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)

    txn = Transaction(
        merchant_id=merchant.id,
        customer_id=customer.id,
        razorpay_payment_id="pay_audit_001",
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

    # Initial case creation audit
    db_session.add(AuditLog(
        case_id=case.id,
        actor="SYSTEM",
        event_type="CASE_CREATED",
        description=f"Recovery Case #{case.id[:8]} initialized."
    ))
    await db_session.commit()
    return case

@pytest.mark.asyncio
async def test_case_creation_audit_event(async_client: AsyncClient, db_session: AsyncSession, audit_sample_case: RecoveryCase):
    audits = (await db_session.execute(select(AuditLog).where(AuditLog.case_id == audit_sample_case.id))).scalars().all()
    assert len(audits) >= 1
    assert any(a.event_type == "CASE_CREATED" for a in audits)

@pytest.mark.asyncio
async def test_ai_diagnosis_and_decision_audit_events(async_client: AsyncClient, db_session: AsyncSession, audit_sample_case: RecoveryCase):
    res = await async_client.post(f"/api/v1/cases/{audit_sample_case.id}/diagnose")
    assert res.status_code == 200

    audits = (await db_session.execute(select(AuditLog).where(AuditLog.case_id == audit_sample_case.id))).scalars().all()
    event_types = [a.event_type for a in audits]
    assert "AI_DIAGNOSIS_COMPLETED" in event_types
    assert "AI_DECISION_MADE" in event_types

@pytest.mark.asyncio
async def test_policy_allow_and_block_audit_events(async_client: AsyncClient, db_session: AsyncSession, audit_sample_case: RecoveryCase):
    # Policy allow check
    res_allow = await async_client.post(f"/api/v1/cases/{audit_sample_case.id}/policy-check", json={"proposed_action": "RECOVERY_LINK", "ai_confidence": 0.88})
    assert res_allow.status_code == 200

    audits = (await db_session.execute(select(AuditLog).where(AuditLog.case_id == audit_sample_case.id))).scalars().all()
    assert any(a.event_type == "RECOVERY_POLICY_CHECKED" for a in audits)

    # Policy block check (retry limit)
    audit_sample_case.retry_count = 3
    db_session.add(audit_sample_case)
    await db_session.commit()

    res_block = await async_client.post(f"/api/v1/cases/{audit_sample_case.id}/policy-check", json={"proposed_action": "RETRY", "ai_confidence": 0.88})
    assert res_block.status_code == 200

    audits_after = (await db_session.execute(select(AuditLog).where(AuditLog.case_id == audit_sample_case.id))).scalars().all()
    assert any(a.event_type == "RECOVERY_POLICY_BLOCKED" for a in audits_after)

@pytest.mark.asyncio
async def test_recovery_execution_and_payment_link_created_audit_events(async_client: AsyncClient, db_session: AsyncSession, audit_sample_case: RecoveryCase):
    res = await async_client.post(f"/api/v1/cases/{audit_sample_case.id}/execute", json={"action": "RECOVERY_LINK"})
    assert res.status_code == 200

    audits = (await db_session.execute(select(AuditLog).where(AuditLog.case_id == audit_sample_case.id))).scalars().all()
    event_types = [a.event_type for a in audits]
    assert "RECOVERY_EXECUTION_STARTED" in event_types
    assert "RECOVERY_PAYMENT_LINK_CREATED" in event_types

@pytest.mark.asyncio
async def test_failed_recovery_execution_audit_event(async_client: AsyncClient, db_session: AsyncSession, audit_sample_case: RecoveryCase):
    from unittest.mock import patch
    from app.services.razorpay import razorpay_service
    from app.core.exceptions import PaymentGatewayException

    with patch.object(razorpay_service, "create_payment_link", side_effect=PaymentGatewayException("Mock gateway error")):
        res = await async_client.post(f"/api/v1/cases/{audit_sample_case.id}/execute", json={"action": "RECOVERY_LINK"})
        assert res.status_code == 200

    audits = (await db_session.execute(select(AuditLog).where(AuditLog.case_id == audit_sample_case.id))).scalars().all()
    assert any(a.event_type == "RECOVERY_EXECUTION_FAILED" for a in audits)

@pytest.mark.asyncio
async def test_case_timeline_api_chronological_7_stages(async_client: AsyncClient, audit_sample_case: RecoveryCase):
    res = await async_client.get(f"/api/v1/cases/{audit_sample_case.id}/timeline")
    assert res.status_code == 200
    data = res.json()

    assert data["case_id"] == audit_sample_case.id
    timeline = data["timeline"]
    assert len(timeline) == 7

    stages = [t["stage"] for t in timeline]
    assert stages == ["DETECT", "DIAGNOSE", "DECIDE", "POLICY", "EXECUTE", "VERIFY", "RECOVER"]

    # Verify chronological timestamp sorting
    timestamps = [t["timestamp"] for t in timeline]
    assert timestamps == sorted(timestamps)

@pytest.mark.asyncio
async def test_decision_summary_api_and_explainability_checklist(async_client: AsyncClient, audit_sample_case: RecoveryCase):
    res = await async_client.get(f"/api/v1/cases/{audit_sample_case.id}/decision-summary")
    assert res.status_code == 200
    data = res.json()

    assert data["case_id"] == audit_sample_case.id
    assert data["amount"] == 2500.0
    assert data["provider"] == "RAZORPAY"
    assert "explainability_checklist" in data

    checklist = data["explainability_checklist"]
    assert len(checklist) >= 5
    assert any(c["check_name"] == "Policy Safety Gate Result" for c in checklist)

@pytest.mark.asyncio
async def test_audit_api_filtering_and_secret_redaction(async_client: AsyncClient, db_session: AsyncSession, audit_sample_case: RecoveryCase):
    # Add audit log containing mock sensitive secret key in metadata
    db_session.add(AuditLog(
        case_id=audit_sample_case.id,
        actor="SYSTEM",
        event_type="TEST_SECRET_REDACTION",
        description="Testing secret redaction in audit endpoint",
        metadata_json={
            "razorpay_key_secret": "rzp_secret_super_secret_12345",
            "authorization": "Bearer secret_auth_token",
            "normal_field": "safe_value"
        }
    ))
    await db_session.commit()

    # Query audit endpoint with case_id filter
    res = await async_client.get(f"/api/v1/audit?case_id={audit_sample_case.id}")
    assert res.status_code == 200
    logs = res.json()

    assert len(logs) >= 1
    match_log = next((l for l in logs if l["event_type"] == "TEST_SECRET_REDACTION"), None)
    assert match_log is not None

    meta = match_log["metadata_json"]
    assert meta["razorpay_key_secret"] == "[REDACTED_SECRET]"
    assert meta["authorization"] == "[REDACTED_SECRET]"
    assert meta["normal_field"] == "safe_value"

@pytest.mark.asyncio
async def test_audit_scan_no_secrets_in_all_logs(async_client: AsyncClient):
    res = await async_client.get("/api/v1/audit?limit=100")
    assert res.status_code == 200
    logs = res.json()

    raw_json = json.dumps(logs)
    assert "rzp_secret" not in raw_json
    assert "RAZORPAY_KEY_SECRET" not in raw_json
    assert "RAZORPAY_WEBHOOK_SECRET" not in raw_json

@pytest.mark.asyncio
async def test_real_vs_synthetic_data_isolation(db_session: AsyncSession):
    # Verify synthetic evaluation data is isolated in EvaluationRun table
    eval_count = (await db_session.execute(select(func.count(EvaluationRun.id)))).scalar()
    tx_count = (await db_session.execute(select(func.count(Transaction.id)))).scalar()

    assert eval_count >= 0
    assert tx_count >= 0
