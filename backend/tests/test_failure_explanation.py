import pytest
from app.services.revenue_risk.failure_explanation import explain_razorpay_failure

def test_explain_razorpay_failure_known_reasons():
    exp1 = explain_razorpay_failure(error_reason="insufficient_funds")
    assert "insufficient funds" in exp1.lower()

    exp2 = explain_razorpay_failure(error_reason="card_expired")
    assert "expired" in exp2.lower()

    exp3 = explain_razorpay_failure(error_reason="otp_timeout")
    assert "otp" in exp3.lower() or "authentication" in exp3.lower()

def test_explain_razorpay_failure_missing_reason():
    exp_empty = explain_razorpay_failure()
    assert exp_empty == "Razorpay did not provide a failure reason."

def test_explain_razorpay_failure_unknown_code():
    exp_unk = explain_razorpay_failure(error_code="CUSTOM_UNKNOWN_CODE")
    assert "CUSTOM_UNKNOWN_CODE" in exp_unk
    assert "insufficient funds" not in exp_unk.lower()
