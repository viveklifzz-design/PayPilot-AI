from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.subscription import Subscription, SubscriptionPaymentAttempt
from app.models.transaction import Transaction
from app.models.recovery_case import RecoveryCase
from app.models.customer import Customer
from app.models.audit_log import AuditLog
from app.services.revenue_risk.risk_engine import risk_engine
from app.services.recovery.policy_gate import policy_gate
from app.services.recovery.stopping_rules import stopping_rules
from app.services.recovery.human_escalation import human_escalation
from app.services.notification_service import notification_service
from app.models.base import utc_now
from app.core.logging import logger

SUBSCRIPTION_MAX_RETRY_ATTEMPTS = 3
MAX_SUBSCRIPTION_RETRIES = SUBSCRIPTION_MAX_RETRY_ATTEMPTS
SUBSCRIPTION_GRACE_PERIOD_HOURS = 72
SUBSCRIPTION_RETRY_DELAY_MINUTES = 60

class SubscriptionStateLineageItem(BaseModel):
    state: str
    timestamp: datetime
    description: str

class SubscriptionRecoveryStatusResponse(BaseModel):
    subscription_id: str
    merchant_id: str
    customer_id: Optional[str] = None
    plan_name: str
    amount: float
    currency: str = "INR"
    status: str
    recovery_status: str
    failure_reason: str
    retry_count: int
    max_retry_attempts: int
    grace_period_until: Optional[datetime] = None
    in_grace_period: bool = False
    retry_allowed: bool = False
    retry_block_reason: Optional[str] = None
    lineage: List[SubscriptionStateLineageItem] = []

class SubscriptionRetryResponse(BaseModel):
    subscription_id: str
    status: str
    message: str
    razorpay_order_id: Optional[str] = None
    retry_count: int
    policy_decision: str
    stopping_rule_decision: str

class SubscriptionAnalytics(BaseModel):
    total_subscriptions: int
    active_subscriptions_count: int
    failed_subscriptions_count: int
    retry_eligible_count: int
    retry_attempted_count: int
    retry_successful_count: int
    grace_period_count: int
    human_review_count: int
    stopped_count: int
    recovered_subscriptions_count: int
    subscription_risk_amount: float
    subscription_recovered_amount: float
    failure_rate: float
    recovery_rate: float

def classify_subscription_failure(
    error_code: Optional[str] = None,
    error_reason: Optional[str] = None,
    error_description: Optional[str] = None
) -> str:
    """Deterministic failure reason classification from provider facts."""
    code_str = (error_code or "").lower()
    reason_str = (error_reason or "").lower()
    desc_str = (error_description or "").lower()

    if "card_expired" in reason_str or "expired" in desc_str:
        return "PAYMENT_METHOD_EXPIRED"
    if "insufficient_funds" in reason_str or "balance" in desc_str or "limit_exceeded" in reason_str:
        return "INSUFFICIENT_FUNDS"
    if "card" in reason_str or "declined" in desc_str:
        return "CARD_DECLINED"
    if "invalid" in reason_str or "bad_request" in code_str or "bad_request" in reason_str:
        return "PAYMENT_METHOD_INVALID"
    if "bank" in reason_str or "issuer" in desc_str:
        return "BANK_DECLINED"
    if "network" in reason_str or "timeout" in desc_str or "gateway" in desc_str:
        return "NETWORK_FAILURE"
    if "provider" in reason_str or "razorpay" in desc_str:
        return "PROVIDER_FAILURE"
    if "pending" in reason_str or "processing" in desc_str:
        return "PAYMENT_PENDING"
    return "UNKNOWN"

class SubscriptionRecoveryService:
    """
    Service for managing recurring payment failures, linking subscription attempts to recovery cases,
    enforcing deterministic subscription state machine boundaries, grace periods, Policy Gate, Stopping Rules,
    Human Escalation, and false-success protection.
    """

    async def create_subscription(
        self,
        db: AsyncSession,
        merchant_id: str,
        plan_name: str,
        amount: float,
        billing_interval: str = "monthly",
        customer_id: Optional[str] = None,
        provider_subscription_id: Optional[str] = None
    ) -> Subscription:
        sub = Subscription(
            merchant_id=merchant_id,
            customer_id=customer_id,
            plan_name=plan_name,
            amount=amount,
            currency="INR",
            billing_interval=billing_interval,
            status="ACTIVE",
            recovery_status="ACTIVE",
            failure_reason="NONE",
            retry_count=0,
            max_retry_attempts=SUBSCRIPTION_MAX_RETRY_ATTEMPTS,
            provider_subscription_id=provider_subscription_id
        )
        db.add(sub)
        await db.commit()
        await db.refresh(sub)
        logger.info(f"Created Subscription '{sub.id}' ({plan_name}, {billing_interval}) for amount ₹{amount}")
        return sub

    async def handle_failed_subscription_payment(
        self,
        db: AsyncSession,
        subscription_id: str,
        txn: Transaction,
        attempt_number: int = 1
    ) -> Tuple[SubscriptionPaymentAttempt, RecoveryCase]:
        # Fetch subscription
        sub_res = await db.execute(select(Subscription).where(Subscription.id == subscription_id))
        sub = sub_res.scalar_one_or_none()
        if not sub:
            raise ValueError(f"Subscription '{subscription_id}' not found.")

        classified_reason = classify_subscription_failure(
            error_code=txn.error_code,
            error_reason=txn.error_reason,
            error_description=txn.error_description
        )

        now = utc_now()
        grace_until = now + timedelta(hours=SUBSCRIPTION_GRACE_PERIOD_HOURS)

        # Update Subscription Status & Recovery Fields
        sub.status = "PAYMENT_FAILED"
        sub.recovery_status = "GRACE_PERIOD"
        sub.failure_reason = classified_reason
        sub.grace_period_until = grace_until
        sub.retry_count = max(sub.retry_count, attempt_number - 1)
        db.add(sub)

        # Create SubscriptionPaymentAttempt
        attempt = SubscriptionPaymentAttempt(
            subscription_id=sub.id,
            transaction_id=txn.id,
            attempt_number=attempt_number,
            amount=txn.amount,
            status="FAILED",
            failure_reason=f"{classified_reason}: {txn.error_description or 'Recurring payment declined'}",
            attempted_at=now,
            next_retry_at=now + timedelta(minutes=SUBSCRIPTION_RETRY_DELAY_MINUTES)
        )
        db.add(attempt)
        await db.commit()
        await db.refresh(attempt)

        # Customer history
        cust_succ = 0
        cust_fail = 0
        if txn.customer_id:
            c_res = await db.execute(select(Customer).where(Customer.id == txn.customer_id))
            cust = c_res.scalar_one_or_none()
            if cust:
                cust_succ = cust.total_successful_payments
                cust_fail = cust.total_failed_payments

        # Risk Assessment
        risk_assessment = risk_engine.assess_transaction(
            amount=float(txn.amount),
            error_code=txn.error_code or "SUBSCRIPTION_PAYMENT_FAILED",
            error_description=txn.error_description or f"Recurring payment attempt #{attempt_number} failed",
            customer_successful_payments=cust_succ,
            customer_failed_payments=cust_fail,
            retry_count=attempt_number - 1,
            payment_method=txn.payment_method
        )

        # Check existing RecoveryCase for idempotency
        case_res = await db.execute(select(RecoveryCase).where(RecoveryCase.subscription_id == sub.id))
        case = case_res.scalars().first()

        if not case:
            case = RecoveryCase(
                case_type="SUBSCRIPTION_FAILURE",
                merchant_id=sub.merchant_id,
                transaction_id=txn.id,
                subscription_id=sub.id,
                subscription_attempt_id=attempt.id,
                customer_id=sub.customer_id,
                amount=txn.amount,
                risk_score=risk_assessment.risk_score,
                risk_level=risk_assessment.risk_level,
                priority_score=risk_assessment.priority_score,
                priority_level=risk_assessment.priority_level,
                risk_factors=risk_assessment.risk_factors + [f"Subscription recurring attempt #{attempt_number} failed ({sub.plan_name})"],
                retry_count=attempt_number - 1,
                status="OPEN"
            )
            db.add(case)
            await db.commit()
            await db.refresh(case)

        # Triggers Step 8 Notifications safely
        await notification_service.create_notification(
            db=db,
            type="SUBSCRIPTION_PAYMENT_FAILED",
            severity="WARNING",
            title=f"Subscription Payment Failed ({sub.plan_name})",
            message=f"Recurring payment of INR {float(sub.amount):,.2f} failed due to {classified_reason}. 72h Grace Period active.",
            case_id=case.id
        )

        # Audit event
        db.add(AuditLog(
            case_id=case.id,
            actor="SUBSCRIPTION_RECOVERY_ENGINE",
            event_type="SUBSCRIPTION_PAYMENT_FAILED",
            description=f"Recurring subscription payment failed ({sub.plan_name}, attempt #{attempt_number}). Classification: '{classified_reason}'.",
            metadata_json={
                "subscription_id": sub.id,
                "attempt_id": attempt.id,
                "plan_name": sub.plan_name,
                "attempt_number": attempt_number,
                "amount": float(sub.amount),
                "failure_reason": classified_reason,
                "grace_period_until": grace_until.isoformat()
            }
        ))
        await db.commit()

        logger.info(f"Handled failed subscription payment for '{sub.id}' (Case '{case.id}')")
        return attempt, case

    async def get_subscription_recovery_status(
        self,
        db: AsyncSession,
        subscription_id: str
    ) -> SubscriptionRecoveryStatusResponse:
        sub_res = await db.execute(select(Subscription).where(Subscription.id == subscription_id))
        sub = sub_res.scalar_one_or_none()
        if not sub:
            raise ValueError(f"Subscription '{subscription_id}' not found.")

        # Find linked case
        case_res = await db.execute(select(RecoveryCase).where(RecoveryCase.subscription_id == sub.id))
        case = case_res.scalars().first()

        now = utc_now()
        in_grace = (sub.grace_period_until is not None and sub.grace_period_until > now)

        # Evaluate safety controls if case exists
        pol_allowed = True
        block_reason = None
        if case:
            pol = policy_gate.assess_case(case)
            stp = stopping_rules.evaluate_case(case)
            esc = human_escalation.evaluate_case(case)

            if sub.status == "PAYMENT_RECOVERED" or case.status == "RECOVERED":
                retry_allowed = False
                block_reason = "Subscription payment already recovered."
            elif stp.should_stop:
                retry_allowed = False
                block_reason = f"Stopped: {stp.stop_reason}"
            elif esc.should_escalate:
                retry_allowed = False
                block_reason = f"Escalated to Human Review ({esc.escalation_level})"
            elif not pol.allowed:
                retry_allowed = False
                block_reason = f"Policy Blocked: {pol.policy_score_reasons}"
            elif sub.retry_count >= sub.max_retry_attempts:
                retry_allowed = False
                block_reason = f"Maximum retries ({sub.max_retry_attempts}) reached."
            else:
                retry_allowed = True
        else:
            retry_allowed = (sub.status != "PAYMENT_RECOVERED" and sub.retry_count < sub.max_retry_attempts)

        # Build lineage
        lineage: List[SubscriptionStateLineageItem] = [
            SubscriptionStateLineageItem(
                state="ACTIVE",
                timestamp=sub.created_at,
                description=f"Subscription '{sub.plan_name}' initialized."
            )
        ]
        if sub.status != "ACTIVE":
            lineage.append(SubscriptionStateLineageItem(
                state="PAYMENT_FAILED",
                timestamp=sub.updated_at,
                description=f"Recurring billing failed ({sub.failure_reason})."
            ))
            if in_grace:
                lineage.append(SubscriptionStateLineageItem(
                    state="GRACE_PERIOD",
                    timestamp=sub.updated_at,
                    description=f"Active 72-hour merchant grace period."
                ))
            if sub.status in ["PAYMENT_RECOVERED", "RECOVERED"]:
                lineage.append(SubscriptionStateLineageItem(
                    state="PAYMENT_RECOVERED",
                    timestamp=sub.updated_at,
                    description=f"Recurring payment confirmed recovered by provider."
                ))
            elif sub.status == "HUMAN_REVIEW":
                lineage.append(SubscriptionStateLineageItem(
                    state="HUMAN_REVIEW",
                    timestamp=sub.updated_at,
                    description=f"Escalated for human operator review."
                ))
            elif sub.status == "STOPPED":
                lineage.append(SubscriptionStateLineageItem(
                    state="STOPPED",
                    timestamp=sub.updated_at,
                    description=f"Automatic recovery permanently stopped."
                ))

        return SubscriptionRecoveryStatusResponse(
            subscription_id=sub.id,
            merchant_id=sub.merchant_id,
            customer_id=sub.customer_id,
            plan_name=sub.plan_name,
            amount=float(sub.amount),
            currency=sub.currency,
            status=sub.status,
            recovery_status=sub.recovery_status,
            failure_reason=sub.failure_reason,
            retry_count=sub.retry_count,
            max_retry_attempts=sub.max_retry_attempts,
            grace_period_until=sub.grace_period_until,
            in_grace_period=in_grace,
            retry_allowed=retry_allowed,
            retry_block_reason=block_reason,
            lineage=lineage
        )

    async def evaluate_and_execute_subscription_retry(
        self,
        db: AsyncSession,
        subscription_id: str
    ) -> SubscriptionRetryResponse:
        sub_res = await db.execute(select(Subscription).where(Subscription.id == subscription_id))
        sub = sub_res.scalar_one_or_none()
        if not sub:
            raise ValueError(f"Subscription '{subscription_id}' not found.")

        # Protection: Cannot retry if already recovered
        if sub.status in ["PAYMENT_RECOVERED", "RECOVERED"]:
            return SubscriptionRetryResponse(
                subscription_id=sub.id,
                status="ALREADY_RECOVERED",
                message="Subscription payment is already recovered.",
                retry_count=sub.retry_count,
                policy_decision="ALLOW_RECOVERY",
                stopping_rule_decision="STOP"
            )

        # Find linked case
        case_res = await db.execute(select(RecoveryCase).where(RecoveryCase.subscription_id == sub.id))
        case = case_res.scalars().first()

        pol_decision = "ALLOW_RECOVERY"
        stp_decision = "CONTINUE"

        if case:
            pol = policy_gate.assess_case(case)
            stp = stopping_rules.evaluate_case(case)
            esc = human_escalation.evaluate_case(case)
            pol_decision = pol.decision
            stp_decision = stp.decision

            if esc.should_escalate or pol.decision == "REVIEW_REQUIRED":
                sub.status = "HUMAN_REVIEW"
                sub.recovery_status = "HUMAN_REVIEW"
                case.status = "ESCALATED"
                db.add(sub)
                db.add(case)
                await db.commit()

                await notification_service.create_notification(
                    db=db,
                    type="SUBSCRIPTION_HUMAN_REVIEW",
                    severity="WARNING",
                    title="Subscription Escalated to Human Review",
                    message=f"Subscription '{sub.plan_name}' requires human review before retry.",
                    case_id=case.id
                )
                return SubscriptionRetryResponse(
                    subscription_id=sub.id,
                    status="REVIEW_REQUIRED",
                    message="Subscription recovery requires human operator review.",
                    retry_count=sub.retry_count,
                    policy_decision=pol.decision,
                    stopping_rule_decision=stp.decision
                )

            if pol.decision == "BLOCK_RECOVERY" or stp.decision == "STOP" or sub.retry_count >= sub.max_retry_attempts:
                sub.status = "STOPPED"
                sub.recovery_status = "STOPPED"
                case.status = "STOPPED"
                db.add(sub)
                db.add(case)
                await db.commit()

                await notification_service.create_notification(
                    db=db,
                    type="SUBSCRIPTION_RECOVERY_STOPPED",
                    severity="CRITICAL",
                    title="Subscription Recovery Stopped",
                    message=f"Subscription '{sub.plan_name}' recovery stopped by safety controls.",
                    case_id=case.id
                )
                return SubscriptionRetryResponse(
                    subscription_id=sub.id,
                    status="BLOCKED",
                    message=f"Subscription retry blocked: {stp.stop_reason if stp.should_stop else 'Policy limit reached'}",
                    retry_count=sub.retry_count,
                    policy_decision=pol.decision,
                    stopping_rule_decision=stp.decision
                )

        # Execute Retry: Increment retry_count, generate order ID
        sub.retry_count += 1
        sub.status = "RETRY_PENDING"
        sub.recovery_status = "RETRY_PENDING"
        if case:
            case.retry_count = sub.retry_count
            case.status = "RECOVERING"
            db.add(case)
        db.add(sub)

        order_id = f"order_sub_rec_{sub.id[:8]}_{sub.retry_count}"

        db.add(AuditLog(
            case_id=case.id if case else sub.id,
            actor="SUBSCRIPTION_RECOVERY_ENGINE",
            event_type="SUBSCRIPTION_RETRY_STARTED",
            description=f"Subscription retry attempt #{sub.retry_count} initiated. Generated Order ID '{order_id}'.",
            metadata_json={
                "subscription_id": sub.id,
                "retry_count": sub.retry_count,
                "order_id": order_id
            }
        ))
        await db.commit()

        await notification_service.create_notification(
            db=db,
            type="SUBSCRIPTION_RETRY_STARTED",
            severity="INFO",
            title="Subscription Retry Initiated",
            message=f"Subscription '{sub.plan_name}' retry attempt #{sub.retry_count} started.",
            case_id=case.id if case else None
        )

        return SubscriptionRetryResponse(
            subscription_id=sub.id,
            status="RETRY_INITIATED",
            message=f"Subscription retry attempt #{sub.retry_count} initiated successfully.",
            razorpay_order_id=order_id,
            retry_count=sub.retry_count,
            policy_decision=pol_decision,
            stopping_rule_decision=stp_decision
        )

    async def get_subscription_analytics(self, db: AsyncSession) -> SubscriptionAnalytics:
        subs_res = await db.execute(select(Subscription))
        subs = subs_res.scalars().all()

        total = len(subs)
        active = sum(1 for s in subs if s.status == "ACTIVE")
        failed = sum(1 for s in subs if s.status in ["PAYMENT_FAILED", "RETRY_ELIGIBLE", "RETRY_PENDING", "GRACE_PERIOD", "HUMAN_REVIEW", "STOPPED"])
        
        now = utc_now()
        grace_count = sum(1 for s in subs if s.grace_period_until is not None and s.grace_period_until > now and s.status != "PAYMENT_RECOVERED")
        human_review = sum(1 for s in subs if s.status == "HUMAN_REVIEW")
        stopped = sum(1 for s in subs if s.status == "STOPPED")
        recovered = sum(1 for s in subs if s.status in ["PAYMENT_RECOVERED", "RECOVERED"])
        retry_eligible = sum(1 for s in subs if s.status in ["PAYMENT_FAILED", "GRACE_PERIOD", "RETRY_ELIGIBLE"] and s.retry_count < s.max_retry_attempts)
        retry_attempted = sum(1 for s in subs if s.retry_count > 0)
        retry_successful = recovered

        risk_amount = sum(float(s.amount) for s in subs if s.status in ["PAYMENT_FAILED", "GRACE_PERIOD", "RETRY_PENDING", "HUMAN_REVIEW"])
        recovered_amount = sum(float(s.amount) for s in subs if s.status in ["PAYMENT_RECOVERED", "RECOVERED"])

        failure_rate = round((failed / total * 100.0), 2) if total > 0 else 0.0
        recovery_rate = round((recovered / failed * 100.0), 2) if failed > 0 else 0.0

        return SubscriptionAnalytics(
            total_subscriptions=total,
            active_subscriptions_count=active,
            failed_subscriptions_count=failed,
            retry_eligible_count=retry_eligible,
            retry_attempted_count=retry_attempted,
            retry_successful_count=retry_successful,
            grace_period_count=grace_count,
            human_review_count=human_review,
            stopped_count=stopped,
            recovered_subscriptions_count=recovered,
            subscription_risk_amount=risk_amount,
            subscription_recovered_amount=recovered_amount,
            failure_rate=failure_rate,
            recovery_rate=recovery_rate
        )

subscription_recovery_service = SubscriptionRecoveryService()

