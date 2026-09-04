from datetime import datetime, timezone
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from app.core.config import settings
from app.core.logging import logger

class PolicyCheckResult(BaseModel):
    allowed: bool
    action: str
    effective_action: str
    reason: str
    violations: List[str]
    requires_escalation: bool
    stop_automation: bool
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PolicyEngine:
    """
    Deterministic Policy Engine & Safety Gate for PayPilot AI.
    Enforces business safety constraints that CANNOT be bypassed by AI.
    """

    ALLOWED_ACTIONS = {"RETRY", "RECOVERY_LINK", "REMINDER", "ESCALATE", "STOP"}
    FRAUD_CODES = {"SUSPECTED_FRAUD", "RISK_CHECK_FAILED", "BLACKLISTED_CARD"}

    def evaluate_action(
        self,
        proposed_action: str,
        case_status: str,
        amount: float,
        retry_count: int = 0,
        ai_confidence: Optional[float] = None,
        last_action_timestamp: Optional[datetime] = None,
        error_code: Optional[str] = None
    ) -> PolicyCheckResult:
        violations: List[str] = []
        action_upper = (proposed_action or "").upper()
        now = datetime.now(timezone.utc)

        # Rule 1: Valid Action Check
        if action_upper not in self.ALLOWED_ACTIONS:
            violations.append("INVALID_ACTION_TYPE")

        # Rule 2: Already Recovered Check
        if case_status.upper() == "RECOVERED":
            violations.append("ALREADY_RECOVERED")

        # Rule 3: Max Retries Check
        if action_upper in {"RETRY", "RECOVERY_LINK"} and retry_count >= settings.MAX_RETRY_LIMIT:
            violations.append("MAX_RETRIES_EXCEEDED")

        # Rule 4: Cooldown Period Check
        if last_action_timestamp and action_upper in {"RETRY", "RECOVERY_LINK", "REMINDER"}:
            if last_action_timestamp.tzinfo is None:
                last_action_timestamp = last_action_timestamp.replace(tzinfo=timezone.utc)
            hours_passed = (now - last_action_timestamp).total_seconds() / 3600.0
            if hours_passed < settings.COOLDOWN_HOURS:
                violations.append("COOLDOWN_ACTIVE")

        # Rule 5: High-Value Amount Check
        if amount > settings.MAX_AUTO_RECOVERY_AMOUNT and action_upper in {"RETRY", "RECOVERY_LINK"}:
            violations.append("AMOUNT_EXCEEDS_AUTO_LIMIT")

        # Rule 6: Minimum AI Confidence Check
        if ai_confidence is not None and ai_confidence < settings.MIN_AI_CONFIDENCE and action_upper in {"RETRY", "RECOVERY_LINK"}:
            violations.append("LOW_AI_CONFIDENCE")

        # Rule 7: Fraud / Security Guard
        if (error_code or "").upper() in self.FRAUD_CODES:
            violations.append("SUSPECTED_FRAUD_GUARD")

        # Determine Decision & Effective Action
        if not violations:
            effective_action = action_upper
            reason = f"Action '{action_upper}' approved by Policy Safety Gate."
            allowed = True
            requires_escalation = (action_upper == "ESCALATE")
            stop_automation = (action_upper == "STOP")
        else:
            allowed = False
            reason = f"Action '{action_upper}' blocked by Policy Engine due to violations: {violations}"
            
            # Choose safe fallback effective action
            if "SUSPECTED_FRAUD_GUARD" in violations or "AMOUNT_EXCEEDS_AUTO_LIMIT" in violations or "LOW_AI_CONFIDENCE" in violations:
                effective_action = "ESCALATE"
                requires_escalation = True
                stop_automation = False
            else:
                effective_action = "STOP"
                requires_escalation = False
                stop_automation = True

        logger.info(
            f"Policy Evaluation: proposed={proposed_action}, allowed={allowed}, "
            f"effective={effective_action}, violations={violations}"
        )

        return PolicyCheckResult(
            allowed=allowed,
            action=action_upper,
            effective_action=effective_action,
            reason=reason,
            violations=violations,
            requires_escalation=requires_escalation,
            stop_automation=stop_automation,
            evaluated_at=now
        )

policy_engine = PolicyEngine()
