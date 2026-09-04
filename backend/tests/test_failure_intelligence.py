import pytest
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionResponse
from app.services.revenue_risk.failure_classifier import classify_razorpay_failure
from app.services.ai.prompts import build_user_prompt

def test_failure_classifier_authentication():
    res = classify_razorpay_failure(
        error_code="BAD_REQUEST_ERROR",
        error_source="bank",
        error_step="payment_authentication",
        error_reason="incorrect_otp"
    )
    assert res.category == "AUTHENTICATION_FAILURE"
    assert "incorrect_otp" in res.reason or "authentication" in res.reason

def test_failure_classifier_insufficient_funds():
    res = classify_razorpay_failure(
        error_code="BAD_REQUEST_ERROR",
        error_source="bank",
        error_step="payment_authorization",
        error_reason="insufficient_funds"
    )
    assert res.category == "INSUFFICIENT_FUNDS"

def test_failure_classifier_gateway_failure():
    res = classify_razorpay_failure(
        error_code="GATEWAY_ERROR",
        error_source="gateway",
        error_step="payment_authorization",
        error_reason="gateway_technical_error"
    )
    assert res.category == "GATEWAY_FAILURE"

def test_failure_classifier_bank_failure():
    res = classify_razorpay_failure(
        error_code="BAD_REQUEST_ERROR",
        error_source="bank",
        error_step="payment_authorization",
        error_reason="decline_by_bank"
    )
    assert res.category == "BANK_FAILURE"

def test_failure_classifier_fallback_unknown():
    res = classify_razorpay_failure(
        error_code="CUSTOM_UNRECOGNIZED_CODE",
        error_source="unknown",
        error_step="unknown",
        error_reason="custom_reason"
    )
    assert res.category == "UNKNOWN_FAILURE"

def test_transaction_schema_exposes_failure_fields():
    t_resp = TransactionResponse(
        id="txn_123",
        merchant_id="m_123",
        amount=100.0,
        currency="INR",
        status="failed",
        error_code="BAD_REQUEST_ERROR",
        error_description="Payment verification failed",
        error_source="bank",
        error_step="payment_authorization",
        error_reason="payment_verification_failed",
        payment_method="upi",
        created_at="2026-08-24T20:00:00Z"
    )
    assert t_resp.error_source == "bank"
    assert t_resp.error_step == "payment_authorization"
    assert t_resp.error_reason == "payment_verification_failed"

def test_ai_prompt_includes_observed_facts():
    ctx = {
        "amount": 100.0,
        "currency": "INR",
        "payment_method": "upi",
        "error_code": "BAD_REQUEST_ERROR",
        "error_description": "Payment verification failed",
        "error_source": "bank",
        "error_step": "payment_authorization",
        "error_reason": "payment_verification_failed",
        "normalized_failure_category": "BANK_FAILURE"
    }
    prompt = build_user_prompt(ctx)
    assert "OBSERVED RAZORPAY PAYMENT FACTS (AUTHORITATIVE):" in prompt
    assert "Error Source: bank" in prompt
    assert "Error Step: payment_authorization" in prompt
    assert "Error Reason: payment_verification_failed" in prompt
    assert "Pre-classified Failure Category: BANK_FAILURE" in prompt
