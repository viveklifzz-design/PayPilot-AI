from datetime import datetime, timezone
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
import app.models
from app.models.recovery_case import RecoveryCase
from app.models.transaction import Transaction
from app.services.recovery.policy_gate import policy_gate
from app.core.config import settings
from app.core.logging import logger

class StoppingRulesResponse(BaseModel):
    case_id: str
    decision: Literal["CONTINUE", "STOP"]
    should_stop: bool
    stop_reason: Optional[str] = None
    triggered_rules: List[str]
    remaining_attempts: int
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StoppingRulesService:
    """
    PayPilot Stopping Rules Engine.
    Enforces deterministic stopping boundaries after AI decision and Policy Gate evaluation.
    Guarantees automatic recovery stops when retry caps, policy blocks, or terminal states are reached.
    """

    TERMINAL_STATES = {"STOPPED", "CANCELLED", "FAILED_TERMINAL"}

    def evaluate_case(
        self,
        case: RecoveryCase,
        transaction: Optional[Transaction] = None
    ) -> StoppingRulesResponse:
        case_id = case.id if case else "unknown"
        status = (case.status if case and case.status else "OPEN").upper()
        retry_count = case.retry_count if (case and case.retry_count is not None) else 0
        amount = float(case.amount) if (case and case.amount is not None) else 0.0

        triggered_rules: List[str] = []
        reasons: List[str] = []

        # Rule 1: Already Recovered Check (CRITICAL MANDATORY PROTECTION)
        if status == "RECOVERED":
            triggered_rules.append("ALREADY_RECOVERED")
            reasons.append("Case is already marked RECOVERED.")

        # Evaluate Policy Gate
        policy_res = policy_gate.assess_case(case=case, transaction=transaction)

        # Rule 2: Policy Block Check
        if policy_res.decision == "BLOCK_RECOVERY":
            triggered_rules.append("POLICY_BLOCK")
            reasons.append(f"Policy Gate blocked recovery: {policy_res.explanation}")

        # Rule 3: Policy Review Required Check
        if policy_res.decision == "REVIEW_REQUIRED":
            triggered_rules.append("POLICY_REVIEW_REQUIRED")
            reasons.append("Policy Gate requires manual review. Automatic recovery cannot continue.")

        # Rule 4: Maximum Retry Attempts Check
        max_attempts = settings.MAX_RECOVERY_ATTEMPTS
        if retry_count >= max_attempts:
            triggered_rules.append("RETRY_LIMIT_REACHED")
            reasons.append(f"Maximum recovery attempts reached ({retry_count}/{max_attempts}).")

        # Rule 5: Terminal / Unsafe Case State Check
        if status in self.TERMINAL_STATES:
            triggered_rules.append("UNSAFE_TERMINAL_STATE")
            reasons.append(f"Case is in terminal state '{status}'.")

        # Rule 6: Amount Safety Limit Check
        if amount > settings.MAX_AUTO_RECOVERY_AMOUNT:
            triggered_rules.append("AMOUNT_SAFETY_LIMIT")
            reasons.append(f"Recovery amount ₹{amount:.2f} exceeds hard safety cap ₹{settings.MAX_AUTO_RECOVERY_AMOUNT:.2f}.")

        # Decision synthesis
        should_stop = len(triggered_rules) > 0
        decision: Literal["CONTINUE", "STOP"] = "STOP" if should_stop else "CONTINUE"
        stop_reason = " | ".join(reasons) if should_stop else None
        remaining_attempts = max(0, max_attempts - retry_count) if not should_stop else 0

        logger.info(f"Stopping Rules Evaluation for case '{case_id}': decision={decision}, triggered_rules={triggered_rules}")

        return StoppingRulesResponse(
            case_id=case_id,
            decision=decision,
            should_stop=should_stop,
            stop_reason=stop_reason,
            triggered_rules=triggered_rules,
            remaining_attempts=remaining_attempts
        )

stopping_rules = StoppingRulesService()
