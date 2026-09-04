import pytest
from app.models.recovery_case import RecoveryCase
from app.models.transaction import Transaction
from app.schemas.ai_assessment import ProviderFacts, AIExplanation
from app.services.recovery.ai_decision_service import ai_decision_service

@pytest.mark.asyncio
async def test_ai_decision_service_provider_fact_immutability():
    case = RecoveryCase(
        id="d669dce3-b855-4348-b457-f0ef7c34b6b1",
        merchant_id="m_test",
        amount=10.0,
        ai_root_cause="international_transaction_not_allowed",
        retry_count=1,
        status="RECOVERED",
        recovered_amount=10.0
    )
    case.original_payment_id = "pay_TTXlSqxyg5hAiT"

    txn = Transaction(
        id="txn_test_001",
        merchant_id="m_test",
        razorpay_payment_id="pay_TTXlSqxyg5hAiT",
        razorpay_order_id="order_TTKk5jdEkFdEIY",
        amount=10.0,
        status="failed",
        error_code="BAD_REQUEST_ERROR",
        error_reason="international_transaction_not_allowed"
    )

    assessment = ai_decision_service.assess_case(case, txn)

    # Provider Facts Immutability Checks
    assert assessment.provider_facts.payment_id == "pay_TTXlSqxyg5hAiT"
    assert assessment.provider_facts.order_id == "order_TTKk5jdEkFdEIY"
    assert assessment.provider_facts.amount == 10.0
    assert assessment.provider_facts.currency == "INR"
    assert assessment.provider_facts.status == "RECOVERED"
    assert assessment.provider_facts.error_code == "BAD_REQUEST_ERROR"
    assert assessment.provider_facts.error_reason == "international_transaction_not_allowed"

    # Already recovered case CTA / Decision behavior
    assert assessment.decision == "COMPLETED"
    assert assessment.recommended_action == "Recovery Completed"

@pytest.mark.asyncio
async def test_ai_decision_service_unrecovered_case_cta():
    case = RecoveryCase(
        id="case_unrecovered_123",
        merchant_id="m_test",
        amount=50.0,
        ai_root_cause="insufficient_funds",
        retry_count=0,
        status="OPEN"
    )
    case.original_payment_id = "pay_failed_999"

    assessment = ai_decision_service.assess_case(case)

    # Unrecovered eligible case CTA behavior
    assert assessment.decision == "CREATE_RECOVERY_CHECKOUT"
    assert assessment.recommended_action == "Recovery Checkout"
    assert assessment.recoverable is True
    assert assessment.confidence == 0.92
    assert len(assessment.ai_explanation.customer_next_steps) >= 3

@pytest.mark.asyncio
async def test_ai_decision_service_fallback_explanation_generation():
    fallback = ai_decision_service._generate_fallback_explanation(
        amount=10.0,
        reason_code="international_transaction_not_allowed",
        case_status="OPEN",
        is_recovered=False
    )

    assert "10" in fallback.what_happened
    assert fallback.why_it_happened is not None
    assert len(fallback.customer_next_steps) >= 3
    assert len(fallback.recommended_payment_methods) >= 2
    assert len(fallback.safety_notes) >= 2
