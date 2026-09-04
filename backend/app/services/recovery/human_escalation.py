from datetime import datetime, timezone
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import app.models
from app.models.recovery_case import RecoveryCase
from app.models.transaction import Transaction
from app.models.audit_log import AuditLog
from app.services.recovery.policy_gate import policy_gate
from app.services.recovery.stopping_rules import stopping_rules
from app.core.config import settings
from app.core.logging import logger

class EscalationTriggerRule(BaseModel):
    rule_id: str
    label: str
    description: str
    severity: Literal["INFO", "WARNING", "HIGH", "CRITICAL"]

class HumanEscalationResponse(BaseModel):
    case_id: str
    should_escalate: bool
    escalation_level: Literal["NONE", "REVIEW", "HIGH_PRIORITY", "CRITICAL"]
    escalation_reason: Optional[str] = None
    triggered_rules: List[EscalationTriggerRule]
    risk_score: float
    amount: float
    policy_decision: str
    stopping_rule_decision: str
    ai_confidence: Optional[float] = None
    recommended_human_action: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class HumanActionRequest(BaseModel):
    action: Literal["APPROVE_RECOVERY", "REJECT_RECOVERY", "STOP_RECOVERY", "REQUEST_INFO"]
    reason: Optional[str] = None
    operator_id: Optional[str] = "HUMAN_OPERATOR"

class HumanActionResponse(BaseModel):
    case_id: str
    action_taken: str
    previous_status: str
    new_status: str
    success: bool
    message: str
    audit_id: Optional[str] = None

class HumanEscalationService:
    """
    PayPilot Human Escalation Engine.
    Evaluates recovery cases for human review requirements and provides controlled operator action handlers.
    Determines escalation levels (NONE, REVIEW, HIGH_PRIORITY, CRITICAL) based on deterministic safety rules.
    """

    def evaluate_case(
        self,
        case: RecoveryCase,
        transaction: Optional[Transaction] = None
    ) -> HumanEscalationResponse:
        case_id = case.id if case else "unknown"
        status = (case.status if case and case.status else "OPEN").upper()
        risk_score = float(case.risk_score) if (case and case.risk_score is not None) else 0.0
        amount = float(case.amount) if (case and case.amount is not None) else 0.0
        ai_confidence = float(case.ai_confidence) if (case and case.ai_confidence is not None) else None
        retry_count = case.retry_count if (case and case.retry_count is not None) else 0

        # Run Policy Gate & Stopping Rules
        policy_res = policy_gate.assess_case(case=case, transaction=transaction)
        stopping_res = stopping_rules.evaluate_case(case=case, transaction=transaction)

        triggered_rules: List[EscalationTriggerRule] = []

        # Rule 1: Case Already Recovered or Stopped
        if status == "RECOVERED":
            triggered_rules.append(EscalationTriggerRule(
                rule_id="RULE_CASE_RECOVERED",
                label="Case Already Recovered",
                description="Case is marked RECOVERED. Duplicate payments are blocked.",
                severity="CRITICAL"
            ))
        elif status == "STOPPED":
            triggered_rules.append(EscalationTriggerRule(
                rule_id="RULE_CASE_STOPPED",
                label="Case Previously Stopped",
                description="Case has been stopped by system rules or human operator.",
                severity="CRITICAL"
            ))

        # Rule 2: Policy Gate Decision
        if policy_res.decision == "BLOCK_RECOVERY":
            triggered_rules.append(EscalationTriggerRule(
                rule_id="RULE_POLICY_BLOCKED",
                label="Policy Gate Blocked",
                description=policy_res.explanation,
                severity="CRITICAL"
            ))
        elif policy_res.decision == "REVIEW_REQUIRED":
            triggered_rules.append(EscalationTriggerRule(
                rule_id="RULE_POLICY_REVIEW",
                label="Policy Gate Review Required",
                description=policy_res.explanation,
                severity="HIGH"
            ))

        # Rule 3: Stopping Rules Decision
        if stopping_res.should_stop and status != "RECOVERED":
            triggered_rules.append(EscalationTriggerRule(
                rule_id="RULE_STOPPING_TRIGGERED",
                label="Stopping Rule Halted Recovery",
                description=stopping_res.stop_reason or "Automatic recovery stopped by system boundary.",
                severity="HIGH"
            ))

        # Rule 4: Risk Score Threshold
        if risk_score >= settings.REVIEW_RISK_THRESHOLD:
            triggered_rules.append(EscalationTriggerRule(
                rule_id="RULE_HIGH_RISK_SCORE",
                label="High Risk Score",
                description=f"Transaction risk score {risk_score:.1f} exceeds threshold {settings.REVIEW_RISK_THRESHOLD:.1f}.",
                severity="HIGH"
            ))

        # Rule 5: Recovery Amount Thresholds
        if amount > settings.MAX_AUTO_RECOVERY_AMOUNT:
            triggered_rules.append(EscalationTriggerRule(
                rule_id="RULE_HARD_AMOUNT_EXCEEDED",
                label="Hard Amount Cap Exceeded",
                description=f"Transaction amount ₹{amount:,.2f} exceeds hard limit ₹{settings.MAX_AUTO_RECOVERY_AMOUNT:,.2f}.",
                severity="CRITICAL"
            ))
        elif amount > settings.MAX_RECOVERY_AMOUNT:
            triggered_rules.append(EscalationTriggerRule(
                rule_id="RULE_AUTONOMOUS_AMOUNT_EXCEEDED",
                label="Autonomous Cap Exceeded",
                description=f"Transaction amount ₹{amount:,.2f} exceeds autonomous cap ₹{settings.MAX_RECOVERY_AMOUNT:,.2f}.",
                severity="WARNING"
            ))

        # Rule 6: AI Confidence Threshold
        if ai_confidence is not None and ai_confidence < settings.MIN_AI_CONFIDENCE_FOR_AUTO_RECOVERY:
            triggered_rules.append(EscalationTriggerRule(
                rule_id="RULE_LOW_AI_CONFIDENCE",
                label="Low AI Confidence",
                description=f"AI confidence {ai_confidence:.2f} is below minimum required {settings.MIN_AI_CONFIDENCE_FOR_AUTO_RECOVERY:.2f}.",
                severity="WARNING"
            ))

        # Rule 7: Status explicit ESCALATED
        if status == "ESCALATED":
            triggered_rules.append(EscalationTriggerRule(
                rule_id="RULE_EXPLICITLY_ESCALATED",
                label="Explicit Human Review Requested",
                description="Case has been explicitly assigned to the Human Review Queue.",
                severity="HIGH"
            ))

        # Determine Escalation Level & Action
        severities = {r.severity for r in triggered_rules}
        if "CRITICAL" in severities:
            escalation_level: Literal["NONE", "REVIEW", "HIGH_PRIORITY", "CRITICAL"] = "CRITICAL"
            should_escalate = True
            recommended_action = "STOP_AND_INSPECT_SECURITY_FLAGS"
        elif "HIGH" in severities:
            escalation_level = "HIGH_PRIORITY"
            should_escalate = True
            recommended_action = "HUMAN_OPERATOR_REVIEW_AND_DECIDE"
        elif "WARNING" in severities:
            escalation_level = "REVIEW"
            should_escalate = True
            recommended_action = "VERIFY_CUSTOMER_CREDENTIALS"
        else:
            escalation_level = "NONE"
            should_escalate = False
            recommended_action = "PROCEED_WITH_AUTONOMOUS_RECOVERY"

        reasons = [r.description for r in triggered_rules]
        escalation_reason = " | ".join(reasons) if triggered_rules else "No escalation trigger present."

        return HumanEscalationResponse(
            case_id=case_id,
            should_escalate=should_escalate,
            escalation_level=escalation_level,
            escalation_reason=escalation_reason,
            triggered_rules=triggered_rules,
            risk_score=risk_score,
            amount=amount,
            policy_decision=policy_res.decision,
            stopping_rule_decision=stopping_res.decision,
            ai_confidence=ai_confidence,
            recommended_human_action=recommended_action
        )

    async def execute_human_action(
        self,
        case: RecoveryCase,
        action_req: HumanActionRequest,
        db: AsyncSession
    ) -> HumanActionResponse:
        case_id = case.id
        previous_status = case.status
        action = action_req.action
        reason = action_req.reason or f"Human action '{action}' performed by operator {action_req.operator_id}."

        logger.info(f"Executing Human Action '{action}' on case '{case_id}' (Current status: '{previous_status}')")

        # Mandatory Safety Verification: Check if case is already RECOVERED
        if previous_status == "RECOVERED" and action == "APPROVE_RECOVERY":
            raise ValueError(f"Cannot approve recovery on case '{case_id}' because it is already marked RECOVERED.")

        if action == "APPROVE_RECOVERY":
            # Re-check Policy Gate & Stopping Rules for safety
            policy_res = policy_gate.assess_case(case=case)
            if policy_res.decision == "BLOCK_RECOVERY":
                raise ValueError(f"Human approval rejected: Case is blocked by critical safety policy ({policy_res.explanation}).")

            case.status = "ACTION_PENDING"
            new_status = "ACTION_PENDING"
            message = "Recovery approved by human operator. Case moved to ACTION_PENDING state."
            event_type = "HUMAN_RECOVERY_APPROVED"

        elif action in ["REJECT_RECOVERY", "STOP_RECOVERY"]:
            case.status = "STOPPED"
            case.stop_reason = f"Human Operator ({action_req.operator_id}): {reason}"
            new_status = "STOPPED"
            message = "Recovery rejected and stopped by human operator."
            event_type = "HUMAN_RECOVERY_REJECTED" if action == "REJECT_RECOVERY" else "HUMAN_RECOVERY_STOPPED"

        elif action == "REQUEST_INFO":
            case.status = "ESCALATED"
            new_status = "ESCALATED"
            message = "Case marked as ESCALATED pending additional customer information."
            event_type = "HUMAN_INFO_REQUESTED"

        else:
            raise ValueError(f"Unsupported human action '{action}'.")

        # Persist AuditLog record
        audit = AuditLog(
            case_id=case_id,
            actor="HUMAN_OPERATOR",
            event_type=event_type,
            description=f"Human Action '{action}' executed by {action_req.operator_id}: {reason}",
            metadata_json={
                "action": action,
                "operator_id": action_req.operator_id,
                "previous_status": previous_status,
                "new_status": new_status,
                "reason": reason
            }
        )
        db.add(audit)
        await db.commit()
        await db.refresh(case)

        return HumanActionResponse(
            case_id=case_id,
            action_taken=action,
            previous_status=previous_status,
            new_status=new_status,
            success=True,
            message=message,
            audit_id=audit.id
        )

human_escalation = HumanEscalationService()
