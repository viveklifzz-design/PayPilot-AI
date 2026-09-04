import pytest
from app.models.recovery_case import RecoveryCase
from app.models.transaction import Transaction
from app.services.recovery.policy_gate import policy_gate

def test_policy_gate_allow_recovery():
    case = RecoveryCase(id="c_eligible", status="OPEN", amount=20.0, retry_count=0, risk_score=30.0, ai_confidence=0.95)
    assessment = policy_gate.assess_case(case)
    assert assessment.decision == "ALLOW_RECOVERY"
    assert assessment.allowed is True
    assert assessment.blocked is False
    assert assessment.requires_review is False
    assert assessment.policy_score == 100

def test_policy_gate_already_recovered_blocks():
    case = RecoveryCase(id="c_rec", status="RECOVERED", amount=20.0)
    assessment = policy_gate.assess_case(case)
    assert assessment.decision == "BLOCK_RECOVERY"
    assert assessment.blocked is True
    assert assessment.allowed is False
    assert any(r.rule_id == "RULE_CASE_NOT_RECOVERED" for r in assessment.failed_rules)

def test_policy_gate_attempt_limit_blocks():
    case = RecoveryCase(id="c_attempts", status="OPEN", amount=20.0, retry_count=3)
    assessment = policy_gate.assess_case(case)
    assert assessment.decision == "BLOCK_RECOVERY"
    assert assessment.blocked is True
    assert any(r.rule_id == "RULE_ATTEMPT_LIMIT" for r in assessment.failed_rules)

def test_policy_gate_hard_amount_limit_blocks():
    case = RecoveryCase(id="c_high_amt", status="OPEN", amount=60000.0)
    assessment = policy_gate.assess_case(case)
    assert assessment.decision == "BLOCK_RECOVERY"
    assert assessment.blocked is True
    assert any(r.rule_id == "RULE_HARD_AMOUNT_LIMIT" for r in assessment.failed_rules)

def test_policy_gate_fraud_code_blocks():
    case = RecoveryCase(id="c_fraud", status="OPEN", amount=20.0)
    txn = Transaction(error_code="SUSPECTED_FRAUD")
    assessment = policy_gate.assess_case(case, transaction=txn)
    assert assessment.decision == "BLOCK_RECOVERY"
    assert assessment.blocked is True
    assert any(r.rule_id == "RULE_FRAUD_SECURITY_GUARD" for r in assessment.failed_rules)

def test_policy_gate_low_ai_confidence_requires_review():
    case = RecoveryCase(id="c_low_conf", status="OPEN", amount=20.0, risk_score=30.0, ai_confidence=0.60)
    assessment = policy_gate.assess_case(case, ai_confidence=0.60)
    assert assessment.decision == "REVIEW_REQUIRED"
    assert assessment.requires_review is True
    assert assessment.allowed is False
    assert any(r.rule_id == "RULE_AI_CONFIDENCE_THRESHOLD" for r in assessment.failed_rules)

def test_policy_gate_elevated_risk_requires_review():
    case = RecoveryCase(id="c_high_risk", status="OPEN", amount=20.0, risk_score=75.0, ai_confidence=0.95)
    assessment = policy_gate.assess_case(case)
    assert assessment.decision == "REVIEW_REQUIRED"
    assert assessment.requires_review is True
    assert any(r.rule_id == "RULE_RISK_SCORE_CHECK" for r in assessment.failed_rules)

def test_policy_gate_autonomous_amount_exceeded_requires_review():
    case = RecoveryCase(id="c_mid_amt", status="OPEN", amount=15000.0, risk_score=30.0, ai_confidence=0.95)
    assessment = policy_gate.assess_case(case)
    assert assessment.decision == "REVIEW_REQUIRED"
    assert assessment.requires_review is True
    assert any(r.rule_id == "RULE_AUTONOMOUS_AMOUNT_LIMIT" for r in assessment.failed_rules)

def test_policy_gate_non_mutating():
    case = RecoveryCase(id="c_test_mutate", status="OPEN", amount=20.0, recovered_amount=0.0)
    policy_gate.assess_case(case)
    assert case.status == "OPEN"
    assert case.recovered_amount == 0.0
