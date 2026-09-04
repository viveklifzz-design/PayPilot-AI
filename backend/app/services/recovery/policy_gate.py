from datetime import datetime, timezone
from typing import List, Optional, Literal, Tuple
from pydantic import BaseModel, Field
from app.core.config import settings
from app.core.logging import logger
import app.models
from app.models.recovery_case import RecoveryCase
from app.models.transaction import Transaction

class PolicyRuleResult(BaseModel):
    rule_id: str
    label: str
    description: str
    passed: bool
    severity: Literal["INFO", "WARNING", "CRITICAL"] = "INFO"
    evidence: str

class PolicyGateResponse(BaseModel):
    case_id: str
    decision: Literal["ALLOW_RECOVERY", "REVIEW_REQUIRED", "BLOCK_RECOVERY"]
    allowed: bool
    requires_review: bool
    blocked: bool
    policy_score: int
    rules_evaluated: List[PolicyRuleResult]
    passed_rules: List[PolicyRuleResult]
    failed_rules: List[PolicyRuleResult]
    explanation: str
    customer_explanation: str
    recommended_action: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PolicyGateService:
    """
    PayPilot Safety Policy Gate Service.
    Acts as the authoritative safety decision maker before any autonomous recovery action or checkout order creation is allowed.
    Gemini AI provides plain-language explanations; Policy Gate authoritatively decides ALLOW, REVIEW, or BLOCK.
    """

    FRAUD_CODES = {"SUSPECTED_FRAUD", "RISK_CHECK_FAILED", "BLACKLISTED_CARD"}

    def assess_case(
        self,
        case: RecoveryCase,
        ai_confidence: Optional[float] = None,
        transaction: Optional[Transaction] = None
    ) -> PolicyGateResponse:
        amount = float(case.amount) if (case and case.amount is not None) else 0.0
        retry_count = case.retry_count if (case and case.retry_count is not None) else 0
        status = case.status if (case and case.status) else "OPEN"
        risk_score = float(case.risk_score) if (case and case.risk_score is not None) else 0.0
        error_code = (transaction.error_code if transaction else (case.ai_root_cause if case else None)) or ""
        confidence = ai_confidence if ai_confidence is not None else (float(case.ai_confidence) if (case and case.ai_confidence is not None) else 0.95)

        rules: List[PolicyRuleResult] = []

        # Rule 1: Case Not Already Recovered (CRITICAL)
        r1_passed = (status.upper() != "RECOVERED")
        rules.append(PolicyRuleResult(
            rule_id="RULE_CASE_NOT_RECOVERED",
            label="Case Not Already Recovered",
            description="Recovery is only allowed for cases that are not yet marked RECOVERED.",
            passed=r1_passed,
            severity="CRITICAL",
            evidence=f"Current case status: '{status}' (Expected != 'RECOVERED')"
        ))

        # Rule 2: Recovery Attempt Limit (CRITICAL)
        r2_passed = (retry_count < settings.MAX_RECOVERY_ATTEMPTS)
        rules.append(PolicyRuleResult(
            rule_id="RULE_ATTEMPT_LIMIT",
            label="Recovery Attempt Limit",
            description="Recovery attempts must remain below the maximum configured limit.",
            passed=r2_passed,
            severity="CRITICAL",
            evidence=f"Attempt count {retry_count} < max limit {settings.MAX_RECOVERY_ATTEMPTS}"
        ))

        # Rule 3: Hard Maximum Amount Limit (CRITICAL)
        r3_passed = (amount <= settings.MAX_AUTO_RECOVERY_AMOUNT)
        rules.append(PolicyRuleResult(
            rule_id="RULE_HARD_AMOUNT_LIMIT",
            label="Hard Maximum Amount Limit",
            description="Recovery amount must not exceed the hard safety cap of ₹50,000.",
            passed=r3_passed,
            severity="CRITICAL",
            evidence=f"₹{amount:.2f} <= ₹{settings.MAX_AUTO_RECOVERY_AMOUNT:.2f}"
        ))

        # Rule 4: Fraud & Security Guard (CRITICAL)
        r4_passed = (error_code.upper() not in self.FRAUD_CODES)
        rules.append(PolicyRuleResult(
            rule_id="RULE_FRAUD_SECURITY_GUARD",
            label="Security & Fraud Prevention Guard",
            description="Provider error code must not indicate suspected fraud or security blacklisting.",
            passed=r4_passed,
            severity="CRITICAL",
            evidence=f"Provider error code: '{error_code}' (Not in fraud set)"
        ))

        # Rule 5: Autonomous Amount Limit (WARNING)
        r5_passed = (amount <= settings.MAX_RECOVERY_AMOUNT)
        rules.append(PolicyRuleResult(
            rule_id="RULE_AUTONOMOUS_AMOUNT_LIMIT",
            label="Autonomous Amount Threshold",
            description="Autonomous checkout is recommended for amounts up to ₹5,000.",
            passed=r5_passed,
            severity="WARNING",
            evidence=f"₹{amount:.2f} <= ₹{settings.MAX_RECOVERY_AMOUNT:.2f}"
        ))

        # Rule 6: Minimum AI Confidence Threshold (WARNING)
        r6_passed = (confidence >= settings.MIN_AI_CONFIDENCE_FOR_AUTO_RECOVERY)
        rules.append(PolicyRuleResult(
            rule_id="RULE_AI_CONFIDENCE_THRESHOLD",
            label="AI Decision Confidence Threshold",
            description="AI diagnosis confidence must meet the autonomous threshold of 85%.",
            passed=r6_passed,
            severity="WARNING",
            evidence=f"Confidence {int(round(confidence * 100))}% >= {int(round(settings.MIN_AI_CONFIDENCE_FOR_AUTO_RECOVERY * 100))}%"
        ))

        # Rule 7: Risk Score Threshold (WARNING)
        r7_passed = (risk_score < settings.REVIEW_RISK_THRESHOLD)
        rules.append(PolicyRuleResult(
            rule_id="RULE_RISK_SCORE_CHECK",
            label="Risk Score Threshold",
            description="Risk score must be below elevated threshold (65.0) for automatic approval.",
            passed=r7_passed,
            severity="WARNING",
            evidence=f"Risk score {risk_score:.1f} < threshold {settings.REVIEW_RISK_THRESHOLD:.1f}"
        ))

        passed_rules = [r for r in rules if r.passed]
        failed_rules = [r for r in rules if not r.passed]
        critical_failed = [r for r in failed_rules if r.severity == "CRITICAL"]

        # Calculate Policy Score (0-100)
        policy_score = int((len(passed_rules) / len(rules)) * 100)

        # High-level Decision Logic
        if critical_failed:
            decision = "BLOCK_RECOVERY"
            allowed = False
            requires_review = False
            blocked = True
            rec_action = "STOP_RECOVERY"
            explanation = f"PayPilot Policy Gate BLOCKED recovery because critical safety rules failed: {', '.join([r.label for r in critical_failed])}."
            customer_explanation = "PayPilot has stopped this recovery attempt to prevent a duplicate or unsafe payment. No further payment is required at this time."
        elif failed_rules:
            decision = "REVIEW_REQUIRED"
            allowed = False
            requires_review = True
            blocked = False
            rec_action = "MERCHANT_REVIEW"
            explanation = f"PayPilot Policy Gate requires MANUAL REVIEW because elevated risk/amount rules flagged this case: {', '.join([r.label for r in failed_rules])}."
            customer_explanation = "PayPilot needs an additional safety review before another payment can be attempted. Please do not make another payment yet."
        else:
            decision = "ALLOW_RECOVERY"
            allowed = True
            requires_review = False
            blocked = False
            rec_action = "RAZORPAY_STANDARD_CHECKOUT"
            explanation = "PayPilot Policy Gate APPROVED recovery. All 7 safety rules passed successfully."
            customer_explanation = "PayPilot has checked this recovery against its safety rules and it is safe to continue."

        logger.info(f"Policy Gate Evaluation for case '{case.id}': decision={decision}, score={policy_score}, allowed={allowed}")

        return PolicyGateResponse(
            case_id=case.id,
            decision=decision,
            allowed=allowed,
            requires_review=requires_review,
            blocked=blocked,
            policy_score=policy_score,
            rules_evaluated=rules,
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            explanation=explanation,
            customer_explanation=customer_explanation,
            recommended_action=rec_action
        )

    NON_RETRYABLE_MANDATE_FAILURES = {
        "ACCOUNT_CLOSED", "MANDATE_REVOKED", "INVALID_MANDATE",
        "FROZEN_ACCOUNT", "CANCELLED", "EXPIRED", "CARD_EXPIRED"
    }

    def evaluate_mandate_retry_policy(
        self,
        attempt_count: int,
        max_attempts: int,
        mandate_status: str,
        failure_reason: str
    ) -> Tuple[bool, str, str]:
        """
        Evaluates Policy Gate rules for mandate retries.
        Returns (is_allowed: bool, decision_reason: str, action: str).
        """
        status_upper = mandate_status.upper() if mandate_status else "ACTIVE"
        reason_upper = failure_reason.upper() if failure_reason else ""

        if status_upper in {"RECOVERED", "CANCELLED", "ESCALATED"}:
            return False, f"Mandate is in terminal status '{status_upper}'", "STOP_RETRY"

        if attempt_count >= max_attempts:
            return False, f"Mandate retry limit reached ({attempt_count}/{max_attempts})", "ESCALATE_TO_HUMAN"

        for non_retry in self.NON_RETRYABLE_MANDATE_FAILURES:
            if non_retry in reason_upper:
                return False, f"Non-retryable failure reason detected: '{failure_reason}'", "CANCEL_MANDATE"

        return True, "Mandate retry approved by Policy Gate", "SCHEDULE_RETRY"

policy_gate = PolicyGateService()
