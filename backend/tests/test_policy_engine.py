import pytest
from datetime import datetime, timezone, timedelta
from app.services.policy import policy_engine, PolicyEngine
from app.core.config import settings

def test_valid_retry_action():
    res = policy_engine.evaluate_action(
        proposed_action="RETRY",
        case_status="OPEN",
        amount=1000.0,
        retry_count=0,
        ai_confidence=0.85
    )
    assert res.allowed is True
    assert res.effective_action == "RETRY"
    assert len(res.violations) == 0

def test_valid_recovery_link_action():
    res = policy_engine.evaluate_action(
        proposed_action="RECOVERY_LINK",
        case_status="OPEN",
        amount=5000.0,
        retry_count=1,
        ai_confidence=0.90
    )
    assert res.allowed is True
    assert res.effective_action == "RECOVERY_LINK"

def test_max_retries_exceeded_violation():
    res = policy_engine.evaluate_action(
        proposed_action="RETRY",
        case_status="OPEN",
        amount=1000.0,
        retry_count=settings.MAX_RETRY_LIMIT  # 3
    )
    assert res.allowed is False
    assert "MAX_RETRIES_EXCEEDED" in res.violations
    assert res.effective_action in ["STOP", "ESCALATE"]

def test_cooldown_active_violation():
    recent_timestamp = datetime.now(timezone.utc) - timedelta(minutes=30)
    res = policy_engine.evaluate_action(
        proposed_action="RETRY",
        case_status="OPEN",
        amount=1000.0,
        retry_count=0,
        last_action_timestamp=recent_timestamp
    )
    assert res.allowed is False
    assert "COOLDOWN_ACTIVE" in res.violations

def test_high_value_transaction_auto_limit_violation():
    res = policy_engine.evaluate_action(
        proposed_action="RETRY",
        case_status="OPEN",
        amount=75000.0,  # Exceeds max 50,000
        retry_count=0
    )
    assert res.allowed is False
    assert "AMOUNT_EXCEEDS_AUTO_LIMIT" in res.violations
    assert res.effective_action == "ESCALATE"
    assert res.requires_escalation is True

def test_low_ai_confidence_violation():
    res = policy_engine.evaluate_action(
        proposed_action="RECOVERY_LINK",
        case_status="OPEN",
        amount=2000.0,
        ai_confidence=0.45  # Below 0.70
    )
    assert res.allowed is False
    assert "LOW_AI_CONFIDENCE" in res.violations
    assert res.effective_action == "ESCALATE"

def test_already_recovered_case_protection():
    res = policy_engine.evaluate_action(
        proposed_action="RETRY",
        case_status="RECOVERED",
        amount=1500.0
    )
    assert res.allowed is False
    assert "ALREADY_RECOVERED" in res.violations

def test_suspected_fraud_guard():
    res = policy_engine.evaluate_action(
        proposed_action="RETRY",
        case_status="OPEN",
        amount=1000.0,
        error_code="SUSPECTED_FRAUD"
    )
    assert res.allowed is False
    assert "SUSPECTED_FRAUD_GUARD" in res.violations
    assert res.effective_action == "ESCALATE"

def test_invalid_action_type():
    res = policy_engine.evaluate_action(
        proposed_action="INVALID_MAGIC_ACTION",
        case_status="OPEN",
        amount=1000.0
    )
    assert res.allowed is False
    assert "INVALID_ACTION_TYPE" in res.violations

def test_multiple_simultaneous_violations():
    res = policy_engine.evaluate_action(
        proposed_action="RETRY",
        case_status="OPEN",
        amount=100000.0,  # High value
        retry_count=5,  # Max retries
        ai_confidence=0.20,  # Low confidence
        error_code="SUSPECTED_FRAUD"  # Fraud
    )
    assert res.allowed is False
    assert len(res.violations) >= 3
    assert "MAX_RETRIES_EXCEEDED" in res.violations
    assert "AMOUNT_EXCEEDS_AUTO_LIMIT" in res.violations
    assert "LOW_AI_CONFIDENCE" in res.violations
    assert "SUSPECTED_FRAUD_GUARD" in res.violations
