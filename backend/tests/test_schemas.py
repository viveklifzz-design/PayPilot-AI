import pytest
from pydantic import ValidationError
from app.schemas.transaction import TransactionCreate
from app.schemas.recovery_case import RecoveryCaseCreate
from app.schemas.evaluation_run import EvaluationRunCreate

def test_valid_transaction_schema():
    txn = TransactionCreate(
        merchant_id="m_123",
        amount=2500.0,
        status="failed"
    )
    assert txn.amount == 2500.0
    assert txn.currency == "INR"

def test_invalid_transaction_amount():
    with pytest.raises(ValidationError):
        TransactionCreate(
            merchant_id="m_123",
            amount=-500.0,  # Must be > 0
            status="failed"
        )

def test_valid_recovery_case_schema():
    case = RecoveryCaseCreate(
        merchant_id="m_123",
        transaction_id="t_456",
        amount=1200.0,
        risk_score=85.0,
        risk_level="HIGH",
        status="OPEN"
    )
    assert case.risk_level == "HIGH"
    assert case.status == "OPEN"

def test_invalid_recovery_case_status():
    with pytest.raises(ValidationError):
        RecoveryCaseCreate(
            merchant_id="m_123",
            transaction_id="t_456",
            amount=1200.0,
            risk_score=85.0,
            risk_level="HIGH",
            status="UNKNOWN_STATUS"  # Invalid status literal
        )

def test_invalid_risk_score_bounds():
    with pytest.raises(ValidationError):
        RecoveryCaseCreate(
            merchant_id="m_123",
            transaction_id="t_456",
            amount=1200.0,
            risk_score=150.0,  # Must be <= 100.0
            risk_level="HIGH",
            status="OPEN"
        )
