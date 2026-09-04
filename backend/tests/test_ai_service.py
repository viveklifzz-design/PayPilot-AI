import json
import pytest
from unittest.mock import MagicMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.ai import (
    get_ai_service,
    fallback_ai_service,
    GeminiAIService,
    AIDiagnosisOutput,
    PROMPT_VERSION
)
from app.models.recovery_case import RecoveryCase
from app.models.transaction import Transaction
from app.models.merchant import Merchant
from app.models.ai_diagnosis import AIDiagnosis
from app.models.audit_log import AuditLog
from app.core.config import settings

def test_fallback_ai_service_network_timeout():
    ctx = {
        "amount": 1500.0,
        "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT",
        "customer_successful_payments": 3,
        "risk_level": "LOW",
        "recoverability_score": 0.85
    }
    diag = fallback_ai_service.diagnose_payment_failure(ctx)
    assert isinstance(diag, AIDiagnosisOutput)
    assert diag.failure_category == "NETWORK"
    assert diag.recommended_action == "RETRY"
    assert diag.confidence >= 0.80

def test_fallback_ai_service_insufficient_funds():
    ctx = {
        "amount": 2500.0,
        "error_code": "INSUFFICIENT_FUNDS",
        "customer_successful_payments": 1,
        "risk_level": "MEDIUM",
        "recoverability_score": 0.60
    }
    diag = fallback_ai_service.diagnose_payment_failure(ctx)
    assert diag.failure_category == "INSUFFICIENT_FUNDS"
    assert diag.recommended_action == "RECOVERY_LINK"

def test_fallback_ai_service_suspected_fraud():
    ctx = {
        "amount": 5000.0,
        "error_code": "SUSPECTED_FRAUD",
        "risk_level": "CRITICAL"
    }
    diag = fallback_ai_service.diagnose_payment_failure(ctx)
    assert diag.failure_category == "FRAUD_OR_SECURITY"
    assert diag.recommended_action == "ESCALATE"
    assert diag.escalation_required is True

def test_gemini_service_unconfigured_reverts_to_fallback():
    gemini = GeminiAIService(api_key="", model="gemini-3.6-flash")
    assert gemini.is_configured is False
    
    ctx = {"amount": 1000.0, "error_code": "BAD_REQUEST_PAYMENT_TIMED_OUT"}
    diag = gemini.diagnose_payment_failure(ctx)
    assert isinstance(diag, AIDiagnosisOutput)
    assert diag.recommended_action == "RETRY"

@pytest.mark.asyncio
async def test_ai_diagnosis_api_endpoint_with_fallback(async_client: AsyncClient, db_session: AsyncSession):
    # Create test merchant & transaction
    merchant = Merchant(name="AI Test Merchant", email="ai@merchant.com")
    db_session.add(merchant)
    await db_session.commit()

    txn = Transaction(
        merchant_id=merchant.id,
        razorpay_payment_id="pay_ai_001",
        amount=2000.0,
        status="failed",
        error_code="OTP_TIMEOUT",
        error_description="Customer 3DS OTP timed out"
    )
    db_session.add(txn)
    await db_session.commit()

    case = RecoveryCase(
        merchant_id=merchant.id,
        transaction_id=txn.id,
        amount=txn.amount,
        risk_score=40.0,
        risk_level="MEDIUM",
        status="OPEN"
    )
    db_session.add(case)
    await db_session.commit()

    # Call AI Diagnosis endpoint
    response = await async_client.post(f"/api/v1/cases/{case.id}/diagnose")
    assert response.status_code == 200
    data = response.json()
    
    assert data["case_id"] == case.id
    assert data["prompt_version"] == PROMPT_VERSION
    assert "diagnosis" in data
    assert "policy_result" in data
    assert data["diagnosis"]["failure_category"] == "AUTHENTICATION"
    assert data["diagnosis"]["recommended_action"] == "RECOVERY_LINK"
    assert data["policy_result"]["allowed"] is True

    # Verify AIDiagnosis table persistence
    diag_stmt = select(AIDiagnosis).where(AIDiagnosis.case_id == case.id)
    diag_res = await db_session.execute(diag_stmt)
    diag_rec = diag_res.scalar_one_or_none()
    assert diag_rec is not None
    assert diag_rec.failure_category == "AUTHENTICATION"

    # Verify Audit Logs
    audit_stmt = select(AuditLog).where(AuditLog.case_id == case.id)
    audit_res = await db_session.execute(audit_stmt)
    audits = audit_res.scalars().all()
    event_types = [a.event_type for a in audits]
    assert "AI_DIAGNOSIS_STARTED" in event_types
    assert "AI_DIAGNOSIS_COMPLETED" in event_types

@pytest.mark.asyncio
async def test_mandatory_safety_test_ai_recommendation_overridden_by_policy(async_client: AsyncClient, db_session: AsyncSession):
    """
    CRITICAL MANDATORY SAFETY TEST:
    AI recommends RETRY with confidence = 0.99,
    BUT Policy Gate states MAX_RETRY_LIMIT is exceeded (retry_count = 3).
    Expected: allowed = False, effective_action = STOP / ESCALATE.
    The system MUST NOT retry.
    """
    merchant = Merchant(name="Safety Test Merchant", email="safety@merchant.com")
    db_session.add(merchant)
    await db_session.commit()

    txn = Transaction(
        merchant_id=merchant.id,
        razorpay_payment_id="pay_safety_001",
        amount=1000.0,
        status="failed",
        error_code="BAD_REQUEST_PAYMENT_TIMED_OUT"
    )
    db_session.add(txn)
    await db_session.commit()

    # Case has retry_count = 3 (MAX_RETRY_LIMIT exceeded)
    case = RecoveryCase(
        merchant_id=merchant.id,
        transaction_id=txn.id,
        amount=txn.amount,
        risk_score=15.0,
        risk_level="LOW",
        status="OPEN",
        retry_count=settings.MAX_RETRY_LIMIT  # 3
    )
    db_session.add(case)
    await db_session.commit()

    # Mock AI Service to return high confidence RETRY recommendation
    mock_ai_output = AIDiagnosisOutput(
        risk_level="LOW",
        recoverability_score=0.95,
        failure_category="NETWORK",
        root_cause="Network Timeout",
        recommended_action="RETRY",
        confidence=0.99,  # Extremely high AI confidence
        reason="Network timeout on low risk customer",
        explanation="AI strongly recommends immediate retry"
    )

    with patch("app.api.v1.endpoints.cases.get_ai_service") as mock_get_ai:
        mock_service = MagicMock()
        mock_service.provider_name = "mock_gemini"
        mock_service.model_name = "gemini-3.6-flash"
        mock_service.diagnose_payment_failure.return_value = mock_ai_output
        mock_get_ai.return_value = mock_service

        response = await async_client.post(f"/api/v1/cases/{case.id}/diagnose")
        assert response.status_code == 200
        data = response.json()

        # AI recommends RETRY with 0.99 confidence
        assert data["diagnosis"]["recommended_action"] == "RETRY"
        assert data["diagnosis"]["confidence"] == 0.99

        # Policy Engine MUST BLOCK the AI recommendation
        assert data["policy_result"]["allowed"] is False
        assert "MAX_RETRIES_EXCEEDED" in data["policy_result"]["violations"]
        assert data["policy_result"]["effective_action"] in ["STOP", "ESCALATE"]

        # Case status must reflect Policy override, NOT AI recommendation
        await db_session.refresh(case)
        assert case.status in ["STOPPED", "ESCALATED"]
        assert case.policy_passed is False
