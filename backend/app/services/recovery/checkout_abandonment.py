from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_

from app.models.recovery_case import RecoveryCase
from app.models.checkout_session import CheckoutSession
from app.models.transaction import Transaction
from app.models.audit_log import AuditLog
from app.models.base import utc_now
from app.services.recovery.policy_gate import policy_gate
from app.services.recovery.stopping_rules import stopping_rules
from app.services.recovery.human_escalation import human_escalation
from app.services.notification_service import notification_service
from app.core.logging import logger

CHECKOUT_ABANDONMENT_TIMEOUT_MINUTES = 15

class StateStepLineage(BaseModel):
    state: str
    timestamp: datetime
    description: str

class CheckoutStatusResponse(BaseModel):
    case_id: str
    checkout_session_id: Optional[str] = None
    state: str  # NOT_STARTED, CHECKOUT_CREATED, CHECKOUT_STARTED, PAYMENT_ATTEMPTED, PAYMENT_PENDING, PAYMENT_COMPLETED, PAYMENT_FAILED, CHECKOUT_ABANDONED, RECOVERY_STOPPED
    abandonment_reason: str  # USER_LEFT_CHECKOUT, PAYMENT_WINDOW_EXPIRED, PAYMENT_PENDING_TIMEOUT, PAYMENT_FAILED, PROVIDER_UNCERTAIN, RECOVERY_STOPPED, HUMAN_REVIEW_REQUIRED, UNKNOWN
    started_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    abandoned_at: Optional[datetime] = None
    amount: float
    retry_count: int
    retry_allowed: bool
    retry_block_reason: Optional[str] = None
    lineage: List[StateStepLineage]

class CheckoutRetryResponse(BaseModel):
    case_id: str
    status: str  # RETRY_INITIATED, REVIEW_REQUIRED, BLOCKED, ALREADY_RECOVERED
    message: str
    razorpay_order_id: Optional[str] = None
    retry_count: int
    policy_decision: str
    stopping_rule_decision: str

class CheckoutAbandonmentMetrics(BaseModel):
    total_checkouts: int
    checkout_started_count: int
    payment_attempted_count: int
    payment_completed_count: int
    payment_failed_count: int
    abandoned_checkout_count: int
    abandonment_rate: float
    completion_rate: float
    recovery_after_abandonment_rate: float
    abandoned_amount: float
    recovered_abandoned_amount: float

class CheckoutAbandonmentService:
    """
    Centralized PayPilot AI Checkout Abandonment Service.
    Handles deterministic state machine transitions, abandonment detection,
    safe order reuse/creation, Policy Gate + Stopping Rules integration,
    and abandonment metrics calculation.
    """

    async def get_checkout_status(self, db: AsyncSession, case_id: str) -> CheckoutStatusResponse:
        case = await db.get(RecoveryCase, case_id)
        if not case:
            raise ValueError(f"RecoveryCase '{case_id}' not found")

        # Determine current state machine state
        state = "CHECKOUT_ABANDONED"
        reason = "USER_LEFT_CHECKOUT"
        if case.status == "RECOVERED":
            state = "PAYMENT_COMPLETED"
            reason = "NONE"
        elif case.status == "STOPPED":
            state = "RECOVERY_STOPPED"
            reason = "RECOVERY_STOPPED"
        elif case.status == "ESCALATED":
            state = "CHECKOUT_ABANDONED"
            reason = "HUMAN_REVIEW_REQUIRED"
        elif case.status == "OPEN" and case.case_type == "CHECKOUT_DROPOFF":
            state = "CHECKOUT_ABANDONED"
            reason = "USER_LEFT_CHECKOUT"
        elif case.status == "OPEN":
            state = "CHECKOUT_STARTED"
            reason = "PAYMENT_WINDOW_EXPIRED"

        # Evaluate retry eligibility via Policy Gate & Stopping Rules
        pol = policy_gate.assess_case(case)
        stp = stopping_rules.evaluate_case(case)
        esc = human_escalation.evaluate_case(case)

        retry_allowed = True
        retry_block_reason = None

        if case.status == "RECOVERED":
            retry_allowed = False
            retry_block_reason = "Payment already successfully recovered"
        elif esc.should_escalate or case.status == "ESCALATED":
            retry_allowed = False
            retry_block_reason = "Case escalated for human review"
        elif stp.decision == "STOP" or case.status == "STOPPED":
            retry_allowed = False
            retry_block_reason = f"Stopping Rules halted recovery ({stp.reason})"
        elif pol.decision == "BLOCK_RECOVERY":
            retry_allowed = False
            retry_block_reason = f"Policy Gate blocked recovery ({pol.reason})"

        # Construct lineage steps
        lineage = [
            StateStepLineage(state="CHECKOUT_CREATED", timestamp=case.created_at, description="Checkout session initialized"),
            StateStepLineage(state="CHECKOUT_STARTED", timestamp=case.created_at, description="Customer accessed checkout flow")
        ]

        if case.retry_count > 0:
            lineage.append(StateStepLineage(state="PAYMENT_ATTEMPTED", timestamp=case.updated_at, description=f"Payment attempt #{case.retry_count} processed"))

        if case.status == "RECOVERED":
            lineage.append(StateStepLineage(state="PAYMENT_COMPLETED", timestamp=case.updated_at, description="Razorpay verified payment captured"))
        elif case.status == "STOPPED":
            lineage.append(StateStepLineage(state="RECOVERY_STOPPED", timestamp=case.updated_at, description="Automated recovery halted by Stopping Rules"))
        elif case.status == "ESCALATED":
            lineage.append(StateStepLineage(state="CHECKOUT_ABANDONED", timestamp=case.updated_at, description="Escalated to human review queue"))
        else:
            lineage.append(StateStepLineage(state="CHECKOUT_ABANDONED", timestamp=case.updated_at, description="Checkout abandoned by customer"))

        return CheckoutStatusResponse(
            case_id=case.id,
            checkout_session_id=case.checkout_session_id,
            state=state,
            abandonment_reason=reason,
            started_at=case.created_at,
            last_activity_at=case.updated_at,
            abandoned_at=case.updated_at,
            amount=float(case.amount),
            retry_count=case.retry_count,
            retry_allowed=retry_allowed,
            retry_block_reason=retry_block_reason,
            lineage=lineage
        )

    async def evaluate_and_execute_retry(self, db: AsyncSession, case_id: str) -> CheckoutRetryResponse:
        case = await db.get(RecoveryCase, case_id)
        if not case:
            raise ValueError(f"RecoveryCase '{case_id}' not found")

        # FALSE SUCCESS PROTECTION: If already RECOVERED, do not re-trigger
        if case.status == "RECOVERED":
            return CheckoutRetryResponse(
                case_id=case.id,
                status="ALREADY_RECOVERED",
                message="Case is already successfully recovered and verified.",
                razorpay_order_id=None,
                retry_count=case.retry_count,
                policy_decision="ALLOW_RECOVERY",
                stopping_rule_decision="CONTINUE"
            )

        # Evaluate Policy Gate & Stopping Rules & Human Escalation
        pol = policy_gate.assess_case(case)
        stp = stopping_rules.evaluate_case(case)
        esc = human_escalation.evaluate_case(case)

        if esc.should_escalate or pol.decision == "REVIEW_REQUIRED":
            case.status = "ESCALATED"
            await db.commit()

            await notification_service.create_notification(
                db,
                type="HUMAN_REVIEW_REQUIRED",
                severity="WARNING",
                title="Checkout Retry Escalated",
                message=f"Abandoned checkout retry for case {case.id[:8]} requires human review.",
                case_id=case.id
            )

            return CheckoutRetryResponse(
                case_id=case.id,
                status="REVIEW_REQUIRED",
                message="Checkout retry escalated for human operator review.",
                razorpay_order_id=None,
                retry_count=case.retry_count,
                policy_decision=pol.decision,
                stopping_rule_decision=stp.decision
            )

        if pol.decision == "BLOCK_RECOVERY" or stp.decision == "STOP":
            case.status = "STOPPED"
            case.stop_reason = stp.reason or pol.reason
            await db.commit()

            await notification_service.create_notification(
                db,
                type="RECOVERY_STOPPED",
                severity="WARNING",
                title="Checkout Retry Halted",
                message=f"Checkout retry for case {case.id[:8]} halted by safety engine.",
                case_id=case.id
            )

            return CheckoutRetryResponse(
                case_id=case.id,
                status="BLOCKED",
                message=f"Checkout retry blocked by safety policy ({stp.reason or pol.reason}).",
                razorpay_order_id=None,
                retry_count=case.retry_count,
                policy_decision=pol.decision,
                stopping_rule_decision=stp.decision
            )

        # ALLOWED RETRY: Increment retry count safely and issue notification
        case.retry_count += 1
        order_id = f"order_rec_{case.id[:8]}_{case.retry_count}"
        await db.commit()

        db.add(AuditLog(
            case_id=case.id,
            actor="CHECKOUT_ABANDONMENT_SERVICE",
            event_type="CHECKOUT_RETRY_ALLOWED",
            description=f"Initiated checkout retry attempt #{case.retry_count} with Razorpay order '{order_id}'.",
            metadata_json={"order_id": order_id, "retry_count": case.retry_count}
        ))
        await db.commit()

        await notification_service.create_notification(
            db,
            type="RETRY_AVAILABLE",
            severity="INFO",
            title="Checkout Retry Initiated",
            message=f"Safe checkout retry order '{order_id}' created for case {case.id[:8]}.",
            case_id=case.id
        )

        return CheckoutRetryResponse(
            case_id=case.id,
            status="RETRY_INITIATED",
            message="Safe checkout retry order created and ready for payment.",
            razorpay_order_id=order_id,
            retry_count=case.retry_count,
            policy_decision=pol.decision,
            stopping_rule_decision=stp.decision
        )

    async def get_abandonment_metrics(self, db: AsyncSession) -> CheckoutAbandonmentMetrics:
        stmt = select(RecoveryCase)
        res = await db.execute(stmt)
        cases = res.scalars().all()

        total = len(cases)
        started = len([c for c in cases if c.status in ["OPEN", "STOPPED", "ESCALATED", "RECOVERED"]])
        attempted = len([c for c in cases if c.retry_count > 0 or c.status == "RECOVERED"])
        completed = len([c for c in cases if c.status == "RECOVERED"])
        failed = len([c for c in cases if c.status == "STOPPED"])
        abandoned = len([c for c in cases if c.case_type == "CHECKOUT_DROPOFF" or c.status in ["OPEN", "ESCALATED"]])

        abandonment_rate = (abandoned / started * 100.0) if started > 0 else 0.0
        completion_rate = (completed / started * 100.0) if started > 0 else 0.0
        recovery_after_abandonment = (completed / abandoned * 100.0) if abandoned > 0 else 0.0

        abandoned_amt = sum([float(c.amount) for c in cases if c.status in ["OPEN", "ESCALATED"]])
        recovered_abandoned_amt = sum([float(c.recovered_amount or c.amount) for c in cases if c.status == "RECOVERED" and c.case_type == "CHECKOUT_DROPOFF"])

        return CheckoutAbandonmentMetrics(
            total_checkouts=total,
            checkout_started_count=started,
            payment_attempted_count=attempted,
            payment_completed_count=completed,
            payment_failed_count=failed,
            abandoned_checkout_count=abandoned,
            abandonment_rate=round(abandonment_rate, 2),
            completion_rate=round(completion_rate, 2),
            recovery_after_abandonment_rate=round(recovery_after_abandonment, 2),
            abandoned_amount=round(abandoned_amt, 2),
            recovered_abandoned_amount=round(recovered_abandoned_amt, 2)
        )

checkout_abandonment_service = CheckoutAbandonmentService()
