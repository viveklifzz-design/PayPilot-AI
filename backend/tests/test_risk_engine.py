import pytest
from app.services.revenue_risk import risk_engine, RevenueRiskEngine

def test_low_value_bank_timeout():
    res = risk_engine.assess_transaction(
        amount=500.0,
        error_code="BAD_REQUEST_PAYMENT_TIMED_OUT",
        customer_successful_payments=2
    )
    assert res.risk_level == "LOW"
    assert res.recoverability_score >= 0.80
    assert res.priority_level in ["LOW", "MEDIUM"]
    assert "Temporary infrastructure/bank outage detected" in "".join(res.risk_factors)

def test_high_value_payment_failure():
    res = risk_engine.assess_transaction(
        amount=150000.0,
        error_code="BAD_REQUEST_PAYMENT_DECLINED"
    )
    assert res.risk_score > 50.0
    assert res.risk_level in ["HIGH", "CRITICAL"]
    assert res.priority_level in ["HIGH", "CRITICAL"]

def test_reliable_returning_customer():
    res = risk_engine.assess_transaction(
        amount=2500.0,
        error_code="OTP_TIMEOUT",
        customer_successful_payments=10
    )
    assert res.recoverability_score > 0.70
    assert any("High-value loyal customer" in factor for factor in res.risk_factors)

def test_new_customer_with_no_history():
    res = risk_engine.assess_transaction(
        amount=1200.0,
        error_code="UNKNOWN_ERROR",
        customer_successful_payments=0,
        customer_failed_payments=0
    )
    assert any("New customer" in factor for factor in res.risk_factors)

def test_chronic_failing_customer():
    res = risk_engine.assess_transaction(
        amount=3000.0,
        error_code="BAD_REQUEST_PAYMENT_DECLINED",
        customer_successful_payments=0,
        customer_failed_payments=5
    )
    assert any("High historical failure rate" in factor for factor in res.risk_factors)
    assert res.recoverability_score < 0.60

def test_max_retries_exhausted_penalty():
    res = risk_engine.assess_transaction(
        amount=1000.0,
        error_code="BAD_REQUEST_PAYMENT_DECLINED",
        retry_count=3
    )
    assert any("Maximum retry attempts reached" in factor for factor in res.risk_factors)
    assert res.recoverability_score <= 0.20

def test_suspected_fraud_alert():
    res = risk_engine.assess_transaction(
        amount=5000.0,
        error_code="SUSPECTED_FRAUD"
    )
    assert res.recoverability_score <= 0.10
    assert res.risk_level == "CRITICAL"

def test_missing_optional_data_handles_gracefully():
    res = risk_engine.assess_transaction(
        amount=100.0,
        error_code=None,
        error_description=None
    )
    assert res.risk_score >= 0.0
    assert res.risk_score <= 100.0
    assert res.recoverability_score >= 0.0
    assert res.recoverability_score <= 1.0
